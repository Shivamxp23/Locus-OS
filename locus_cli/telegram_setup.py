"""locus_cli.telegram_setup - Telegram setup wizard and secret-reference flow.

Implements R6 and R4:
- Secure one-time code pairing verification (S-1) showing code in terminal.
- 10-minute validity, single-use, 5 wrong attempts lock out for 15 minutes.
- Owner ID persistence to LOCUS_HOME/allowed_users.json and LOCUS_HOME/config.yaml.
- Fail closed: strangers and corrupted configurations are rejected.
- /setup secret-reference flow (R4, spec section 18):
  - Opaque secret references (secret://<hex>)
  - 5-minute expiry timeout
  - 15-minute cleanup
  - Consumed on persist (single use)
  - Secrets are never echoed, logged, or placed in git
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import yaml

from locus_cli.setup import load_secret_env, save_secret_env
from sidecar.telegram_pairing import (
    TelegramPairingManager,
    UNCONFIGURED_MESSAGE,
    PairingStorageError,
)

logger = logging.getLogger("locus_cli.telegram_setup")

SECRET_REF_PREFIX = "secret://"
DEFAULT_REF_TTL_SECONDS = 300.0       # 5 minutes (R4 / spec section 18)
DEFAULT_REF_CLEANUP_SECONDS = 900.0   # 15 minutes (R4 / spec section 18)


def _set_posix_permissions(path: Path, mode: int) -> None:
    """Set filesystem permissions on POSIX systems (no-op on Windows)."""
    if sys.platform != "win32":
        try:
            os.chmod(path, mode)
        except OSError as e:
            logger.debug("Failed to set permissions %o on %s: %s", mode, path, e)


def save_allowed_users(locus_home: Path, user_ids: list[int | str]) -> Path:
    """Persist allowed numeric Telegram user IDs to LOCUS_HOME/allowed_users.json."""
    home = Path(locus_home).expanduser().resolve()
    home.mkdir(parents=True, exist_ok=True)
    target = home / "allowed_users.json"

    norm_ids: list[int] = []
    for uid in user_ids:
        try:
            norm_ids.append(int(uid))
        except (ValueError, TypeError):
            continue

    data = {
        "allowed_user_ids": norm_ids,
        "allowed_users": norm_ids,
    }

    tmp_path = target.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp_path.replace(target)
    _set_posix_permissions(target, 0o600)
    return target


def load_allowed_users(locus_home: Path) -> list[int]:
    """Load allowed numeric Telegram user IDs from LOCUS_HOME/allowed_users.json."""
    home = Path(locus_home).expanduser().resolve()
    target = home / "allowed_users.json"
    if not target.is_file():
        return []

    try:
        content = target.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, list):
            return [int(x) for x in data if str(x).isdigit() or isinstance(x, int)]
        if isinstance(data, dict):
            raw = data.get("allowed_user_ids") or data.get("allowed_users") or []
            if isinstance(raw, list):
                return [int(x) for x in raw if str(x).isdigit() or isinstance(x, int)]
            if str(raw).isdigit():
                return [int(raw)]
    except Exception:
        # Fail closed on corrupt or unreadable allow-list
        return []
    return []


@dataclass
class SecretReference:
    """In-memory opaque secret reference item."""
    ref: str
    key_name: str
    description: str
    value: Optional[str]
    created_at: float
    expires_at: float
    fulfilled: bool = False


class SecretReferenceManager:
    """
    Manages short-lived opaque secret references (R4, spec section 18).
    - 5-minute timeout for pending references.
    - 15-minute cleanup of expired references.
    - Consumed on persist (single use).
    - Values are held in memory only, never echoed or logged.
    """

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_REF_TTL_SECONDS,
        cleanup_age_seconds: float = DEFAULT_REF_CLEANUP_SECONDS,
    ):
        self.ttl_seconds = ttl_seconds
        self.cleanup_age_seconds = cleanup_age_seconds
        self._refs: dict[str, SecretReference] = {}

    def create_secret_ref(
        self,
        key_name: str,
        description: str = "",
        ttl_seconds: Optional[float] = None,
        now: Optional[float] = None,
    ) -> str:
        """Create an opaque secret reference token valid for ttl_seconds (default 5m)."""
        current = time.time() if now is None else now
        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds
        token_id = secrets.token_hex(16)
        ref = f"{SECRET_REF_PREFIX}{token_id}"

        self._refs[ref] = SecretReference(
            ref=ref,
            key_name=key_name.strip(),
            description=description.strip(),
            value=None,
            created_at=current,
            expires_at=current + ttl,
            fulfilled=False,
        )
        return ref

    def fulfill_secret_ref(
        self,
        ref: str,
        value: str,
        now: Optional[float] = None,
    ) -> bool:
        """Fulfill an opaque reference with a secret value. Value held in memory only."""
        current = time.time() if now is None else now
        item = self._refs.get(ref)
        if item is None:
            return False
        if current > item.expires_at:
            # Expired
            return False
        if item.fulfilled:
            # Already fulfilled
            return False

        item.value = value
        item.fulfilled = True
        return True

    def resolve_secret_ref(
        self,
        ref: str,
        now: Optional[float] = None,
    ) -> Optional[str]:
        """Resolve the fulfilled secret value if unexpired (without consuming)."""
        current = time.time() if now is None else now
        item = self._refs.get(ref)
        if item is None or not item.fulfilled or item.value is None:
            return None
        if current > item.expires_at:
            return None
        return item.value

    def get_ref_metadata(self, ref: str) -> Optional[tuple[str, str, bool]]:
        """Return (key_name, description, fulfilled) for reference if it exists."""
        item = self._refs.get(ref)
        if item is None:
            return None
        return item.key_name, item.description, item.fulfilled

    def consume_secret_ref(
        self,
        ref: str,
        now: Optional[float] = None,
    ) -> Optional[str]:
        """Consume the reference on persist (single use). Removes ref from memory immediately."""
        current = time.time() if now is None else now
        item = self._refs.get(ref)
        if item is None or not item.fulfilled or item.value is None:
            return None
        if current > item.expires_at:
            self._refs.pop(ref, None)
            return None
        self._refs.pop(ref, None)
        return item.value

    def cleanup_expired(
        self,
        now: Optional[float] = None,
        max_age_seconds: Optional[float] = None,
    ) -> int:
        """15-minute cleanup: purge any references older than max_age or expired."""
        current = time.time() if now is None else now
        max_age = self.cleanup_age_seconds if max_age_seconds is None else max_age_seconds

        to_remove = [
            ref
            for ref, item in self._refs.items()
            if (current - item.created_at) >= max_age or current > item.expires_at
        ]
        for ref in to_remove:
            self._refs.pop(ref, None)
        return len(to_remove)


class TelegramSetupWizard:
    """
    Orchestrates Telegram pairing and setup verification (R6, S-1) and /setup (R4).
    """

    def __init__(
        self,
        locus_home: Path,
        pairing_manager: Optional[TelegramPairingManager] = None,
        secret_manager: Optional[SecretReferenceManager] = None,
    ):
        self.locus_home = Path(locus_home).expanduser().resolve()
        self.pairing_manager = pairing_manager or TelegramPairingManager(locus_home=self.locus_home)
        self.secret_manager = secret_manager or SecretReferenceManager()
        self.allowed_users_file = self.locus_home / "allowed_users.json"

    def is_already_paired(self) -> bool:
        """Check if an owner is already paired via allowed_users.json or config.yaml."""
        if load_allowed_users(self.locus_home):
            return True
        return self.pairing_manager.is_paired()

    def get_paired_owner_ids(self) -> list[int]:
        """Return list of paired numeric Telegram owner IDs."""
        ids_from_file = load_allowed_users(self.locus_home)
        ids_from_config = self.pairing_manager.get_allowed_user_ids()
        combined = list(dict.fromkeys(ids_from_file + ids_from_config))
        return combined

    def start_pairing_session(
        self,
        code_length: int = 6,
        now: Optional[float] = None,
    ) -> str:
        """
        Start pairing session and return one-time pairing code valid for 10 minutes.
        Supports 6-digit code for terminal-to-bot pairing.
        """
        if self.is_already_paired():
            raise RuntimeError("Telegram is already paired to an owner. Re-pairing requires --repair telegram.")

        # Generate 6-digit or N-char pairing code
        digits = "".join(secrets.choice("0123456789") for _ in range(code_length))
        self.pairing_manager.start_pairing(now=now, code=digits)
        return digits

    def verify_pairing_attempt(
        self,
        user_id: int | str,
        code: str,
        now: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Verify pairing attempt from Telegram bot update (/pair <code>).
        Persists owner ID to allowed_users.json and config.yaml upon success.
        """
        try:
            uid_int = int(user_id)
        except (ValueError, TypeError):
            return False, "Invalid numeric Telegram user ID."

        if self.is_already_paired():
            if uid_int in self.get_paired_owner_ids():
                return True, "Already paired."
            return False, "Pairing is closed: an owner is already configured."

        success, msg = self.pairing_manager.handle_pairing_attempt(user_id, code, now=now)
        if success:
            if "already paired" in msg.lower():
                return True, msg
            try:
                save_allowed_users(self.locus_home, [uid_int])
            except Exception as e:
                return False, f"Failed to persist allowed_users.json: {e}"
            return True, "Pairing successful. Owner ID stored."
        return False, msg

    def handle_inbound_telegram_message(
        self,
        user_id: int | str,
        text: str,
        is_direct: bool = True,
        now: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Handle incoming Telegram updates (R6, S-1, R4):
        - Strangers receive UNCONFIGURED_MESSAGE.
        - /pair <code> executes pairing.
        - /setup generates short-lived secret reference (R4).
        - /secret <ref> <value> fulfills, consumes on persist, and stores to .env.
        """
        if not is_direct:
            return False, ""

        cleaned = text.strip()

        # 1. Pairing command (/pair <code>)
        if cleaned.startswith("/pair"):
            parts = cleaned.split(maxsplit=1)
            candidate = parts[1].strip() if len(parts) > 1 else ""
            if not candidate:
                return False, "Usage: /pair <CODE>"
            return self.verify_pairing_attempt(user_id, candidate, now=now)

        # 2. Check authorization for all other commands
        is_owner = False
        try:
            uid_int = int(user_id)
            is_owner = uid_int in self.get_paired_owner_ids()
        except (ValueError, TypeError):
            is_owner = False

        if not is_owner:
            return False, UNCONFIGURED_MESSAGE

        # 3. Paired owner: /setup command (R4 secret-reference flow)
        if cleaned.startswith("/setup"):
            parts = cleaned.split(maxsplit=1)
            target_key = parts[1].strip().upper() if len(parts) > 1 else "ANTHROPIC_API_KEY"
            ref = self.secret_manager.create_secret_ref(
                key_name=target_key,
                description=f"Telegram /setup key for {target_key}",
                now=now,
            )
            # Instruct owner with opaque ref, never echoing secrets
            msg = (
                f"Setup requested for {target_key}.\n"
                f"Opaque reference: {ref}\n"
                f"Send: /secret {ref} <YOUR_KEY> (valid for 5 minutes)"
            )
            return True, msg

        # 4. Paired owner: /secret <ref> <value>
        if cleaned.startswith("/secret"):
            parts = cleaned.split(maxsplit=2)
            if len(parts) < 3:
                return False, "Usage: /secret <secret://ref> <value>"
            ref = parts[1].strip()
            secret_value = parts[2].strip()

            meta = self.secret_manager.get_ref_metadata(ref)
            if meta is None:
                return False, "Invalid or expired secret reference."
            key_name, _, _ = meta

            fulfilled = self.secret_manager.fulfill_secret_ref(ref, secret_value, now=now)
            if not fulfilled:
                return False, "Failed to fulfill secret reference (expired or invalid)."

            # Consume on persist (single-use)
            consumed_val = self.secret_manager.consume_secret_ref(ref, now=now)
            if consumed_val is None:
                return False, "Failed to consume secret reference."

            # Persist strictly to LOCUS_HOME/.env with mode 0600 (S-0)
            existing = load_secret_env(self.locus_home)
            existing[key_name] = consumed_val
            save_secret_env(self.locus_home, existing)

            return True, f"Secret for {key_name} persisted successfully."

        # Other messages from authorized owner
        return True, "AUTHORIZED"


def run_telegram_setup(
    locus_home: Path,
    print_fn: Callable[[str], None] = print,
    now: Optional[float] = None,
) -> dict[str, Any]:
    """
    Run the Telegram setup wizard.
    Reports already paired if owner exists (R8 safe re-run).
    Otherwise generates a 6-digit one-time code valid for 10 minutes (S-1).
    """
    wizard = TelegramSetupWizard(locus_home=locus_home)

    if wizard.is_already_paired():
        owners = wizard.get_paired_owner_ids()
        print_fn(f"[PASS] Telegram is already paired to owner ID(s): {owners}")
        return {
            "status": "already_paired",
            "allowed_users": owners,
            "wizard": wizard,
        }

    code = wizard.start_pairing_session(code_length=6, now=now)
    print_fn("--- [Locus Telegram Setup Wizard] ---")
    print_fn(f"Your Locus pairing code is: {code}")
    print_fn("Valid for 10 minutes. Send '/pair " + code + "' to your Telegram bot.")

    return {
        "status": "pairing_started",
        "pairing_code": code,
        "expires_in": 600,
        "wizard": wizard,
    }
