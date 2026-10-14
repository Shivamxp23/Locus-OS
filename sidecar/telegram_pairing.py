"""
sidecar/telegram_pairing.py - S-1 Telegram access: one-time pairing, fail closed.

Implements owner verification and one-time code pairing for Locus OS:
- Setup creates a one-time pairing code (8+ chars from `secrets`).
- Code valid for 10 minutes, single use, SHA-256 hash stored.
- 5 wrong attempts lock pairing for 15 minutes.
- Pairing via `/pair <code>`: saves numeric Telegram user ID to LOCUS_HOME/config.yaml.
- Until paired, answers every message with fixed line ("Locus is not configured.") and executes nothing.
- Fail closed: if allow-list cannot be read or written, refuses ALL messages.
- Ignores group chats, forwards, and non-direct messages.
- Webhook mode refuses to start without TELEGRAM_WEBHOOK_SECRET.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

import yaml

UNCONFIGURED_MESSAGE = "Locus is not configured."
PAIRING_CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # Unambiguous alphanumeric (no 0/O, 1/I)
DEFAULT_CODE_LENGTH = 10
CODE_EXPIRY_SECONDS = 600.0       # 10 minutes
LOCKOUT_DURATION_SECONDS = 900.0  # 15 minutes
MAX_FAILED_ATTEMPTS = 5


class PairingStorageError(Exception):
    """Raised when reading or writing pairing configuration fails."""
    pass


def generate_pairing_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    """Generate a cryptographically secure random pairing code."""
    if length < 8:
        raise ValueError("Pairing code length must be at least 8 characters")
    return "".join(secrets.choice(PAIRING_CHARSET) for _ in range(length))


def hash_pairing_code(code: str) -> str:
    """Hash a pairing code with SHA-256 for secure in-memory comparison."""
    normalized = code.strip().upper().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def get_default_config_path() -> Path:
    """Determine canonical config.yaml path in LOCUS_HOME."""
    from sidecar.config import get_config_path

    return get_config_path()


def validate_webhook_config(webhook_url: Optional[str], webhook_secret: Optional[str]) -> bool:
    """
    Validate webhook configuration.
    Refuses to start webhook mode without a non-empty TELEGRAM_WEBHOOK_SECRET (fail closed).
    """
    if webhook_url and webhook_url.strip():
        if not webhook_secret or not webhook_secret.strip():
            raise ValueError(
                "TELEGRAM_WEBHOOK_SECRET is required when webhook mode is enabled (refusing to start open)"
            )
    return True


class TelegramPairingManager:
    """
    Manages Telegram pairing lifecycle and message authorization with fail-closed semantics.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        locus_home: Optional[Path] = None,
        code_expiry: float = CODE_EXPIRY_SECONDS,
        lockout_duration: float = LOCKOUT_DURATION_SECONDS,
        max_attempts: int = MAX_FAILED_ATTEMPTS,
    ):
        if config_path is not None:
            self.config_path = Path(config_path)
        elif locus_home is not None:
            self.config_path = Path(locus_home) / "config.yaml"
        else:
            self.config_path = get_default_config_path()

        self.code_expiry = code_expiry
        self.lockout_duration = lockout_duration
        self.max_attempts = max_attempts

        # In-memory pairing session state
        self._pairing_hash: Optional[str] = None
        self._code_created_at: float = 0.0
        self._wrong_attempts: int = 0
        self._locked_until: float = 0.0

    @property
    def wrong_attempts(self) -> int:
        return self._wrong_attempts

    @property
    def locked_until(self) -> float:
        return self._locked_until

    def is_locked(self, now: Optional[float] = None) -> bool:
        """Check if pairing is locked out due to excessive failed attempts."""
        current = time.time() if now is None else now
        return current < self._locked_until

    def is_code_active(self, now: Optional[float] = None) -> bool:
        """Check if a pairing code is currently active and unexpired."""
        if self._pairing_hash is None:
            return False
        current = time.time() if now is None else now
        if self.is_locked(current):
            return False
        return (current - self._code_created_at) <= self.code_expiry

    def start_pairing(self, length: int = DEFAULT_CODE_LENGTH, now: Optional[float] = None) -> str:
        """
        Create a one-time pairing code and arm the pairing session.
        Shows the code on the host machine only; only the hash is retained.
        """
        current = time.time() if now is None else now
        if self.is_locked(current):
            remaining = int(self._locked_until - current)
            raise PermissionError(f"Pairing is locked due to too many failed attempts. Try again in {remaining}s")

        code = generate_pairing_code(length)
        self._pairing_hash = hash_pairing_code(code)
        self._code_created_at = current
        self._wrong_attempts = 0
        return code

    def cancel_pairing(self) -> None:
        """Destroy active pairing code and reset pairing session."""
        self._pairing_hash = None
        self._code_created_at = 0.0

    def get_allowed_user_ids(self) -> List[int]:
        """
        Read allowed Telegram user IDs from config.yaml.
        Raises PairingStorageError if the file exists but cannot be parsed or read.
        """
        if not self.config_path.is_file():
            return []

        try:
            content = self.config_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if data is None:
                return []
            if not isinstance(data, dict):
                raise PairingStorageError(f"Config root must be a mapping, got {type(data).__name__}")

            locus = data.get("locus", {})
            if not isinstance(locus, dict):
                raise PairingStorageError("locus section in config is not a mapping")

            channels = locus.get("channels", {})
            if not isinstance(channels, dict):
                raise PairingStorageError("locus.channels section in config is not a mapping")

            telegram = channels.get("telegram", {})
            if not isinstance(telegram, dict):
                raise PairingStorageError("locus.channels.telegram section in config is not a mapping")

            raw_ids = telegram.get("allowed_user_ids")
            if raw_ids is None:
                single_id = telegram.get("allowed_user_id")
                raw_ids = [single_id] if single_id is not None else []
            elif not isinstance(raw_ids, list):
                raw_ids = [raw_ids]

            allowed: List[int] = []
            for item in raw_ids:
                try:
                    allowed.append(int(item))
                except (ValueError, TypeError) as err:
                    raise PairingStorageError(f"Invalid non-numeric allowed user ID: {item}") from err
            return allowed
        except Exception as e:
            if isinstance(e, PairingStorageError):
                raise
            raise PairingStorageError(f"Failed to read allow-list from {self.config_path}: {e}") from e

    def save_allowed_user_id(self, user_id: int) -> None:
        """
        Save the paired numeric user ID to LOCUS_HOME/config.yaml.
        Fails closed on storage or write errors.
        """
        try:
            uid_int = int(user_id)
        except (ValueError, TypeError) as err:
            raise PairingStorageError(f"Invalid numeric user ID: {user_id}") from err

        try:
            if self.config_path.is_file():
                raw = self.config_path.read_text(encoding="utf-8")
                data = yaml.safe_load(raw)
                if data is None:
                    data = {}
                elif not isinstance(data, dict):
                    raise PairingStorageError("Cannot update corrupted config mapping")
            else:
                data = {}
                self.config_path.parent.mkdir(parents=True, exist_ok=True)

            locus = data.setdefault("locus", {})
            if not isinstance(locus, dict):
                raise PairingStorageError("locus section corrupted")
            channels = locus.setdefault("channels", {})
            if not isinstance(channels, dict):
                raise PairingStorageError("channels section corrupted")
            telegram = channels.setdefault("telegram", {})
            if not isinstance(telegram, dict):
                raise PairingStorageError("telegram section corrupted")

            current_ids: Any = telegram.get("allowed_user_ids")
            if current_ids is None:
                current_ids = []
            elif not isinstance(current_ids, list):
                current_ids = [current_ids]

            norm_ids = [int(x) for x in current_ids if str(x).isdigit() or isinstance(x, int)]
            if uid_int not in norm_ids:
                norm_ids.append(uid_int)
            telegram["allowed_user_ids"] = norm_ids

            # Atomic write
            tmp_path = self.config_path.with_suffix(".tmp")
            tmp_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            tmp_path.replace(self.config_path)
        except Exception as e:
            if isinstance(e, PairingStorageError):
                raise
            raise PairingStorageError(f"Failed to save allow-list to {self.config_path}: {e}") from e

    def is_paired(self) -> bool:
        """Check if an owner is configured."""
        try:
            return len(self.get_allowed_user_ids()) > 0
        except Exception:
            # Storage error -> fail closed
            return False

    def is_configured(self) -> bool:
        """Alias for is_paired: True when at least one owner ID is validly stored."""
        return self.is_paired()

    def is_allowed(self, user_id: int | str) -> bool:
        """
        Check if user_id is the paired owner.
        FAIL CLOSED: Any error reading or parsing the allow-list returns False.
        """
        try:
            allowed = self.get_allowed_user_ids()
            if not allowed:
                return False
            return int(user_id) in allowed
        except Exception:
            # Corrupted allow-list or unreadable file -> fail closed!
            return False

    def handle_pairing_attempt(
        self, user_id: int | str, candidate_code: str, now: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Process a pairing attempt with /pair <code>.
        Returns (success, message).
        """
        current = time.time() if now is None else now

        if self.is_allowed(user_id):
            return True, "Already paired."

        if self.is_paired():
            return False, "Pairing is closed: an owner is already configured."

        if self.is_locked(current):
            remaining = int(self._locked_until - current)
            return False, f"Pairing is locked due to too many failed attempts. Try again in {remaining}s."

        if self._pairing_hash is None:
            return False, UNCONFIGURED_MESSAGE

        if (current - self._code_created_at) > self.code_expiry:
            self.cancel_pairing()
            return False, "Pairing code has expired. Generate a new code on the host machine."

        # Constant-time comparison
        cand_hash = hash_pairing_code(candidate_code)
        if hmac.compare_digest(cand_hash, self._pairing_hash):
            try:
                uid_int = int(user_id)
            except (ValueError, TypeError):
                return False, "Invalid numeric Telegram user ID."

            try:
                self.save_allowed_user_id(uid_int)
            except PairingStorageError as err:
                return False, f"Failed to persist pairing: {err}"

            # Destroy code immediately upon success
            self.cancel_pairing()
            self._wrong_attempts = 0
            return True, "Paired successfully. You are now the Locus owner."

        # Wrong code
        self._wrong_attempts += 1
        if self._wrong_attempts >= self.max_attempts:
            self._locked_until = current + self.lockout_duration
            self.cancel_pairing()
            return False, "Too many failed attempts. Pairing is locked for 15 minutes."

        remaining = self.max_attempts - self._wrong_attempts
        return False, f"Invalid pairing code. {remaining} attempt(s) remaining."

    def handle_inbound_message(
        self,
        user_id: int | str,
        text: str,
        is_direct: bool = True,
        now: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Handle an inbound Telegram message.
        - Non-direct messages (groups, forwards, channels) are ignored.
        - Allowed owner gets authorized access.
        - /pair <code> executes pairing.
        - Stranger or unconfigured gets UNCONFIGURED_MESSAGE.
        Returns (authorized, response_text).
        """
        if not is_direct:
            return False, ""

        if self.is_allowed(user_id):
            return True, "AUTHORIZED"

        cleaned = text.strip()
        if cleaned.startswith("/pair"):
            parts = cleaned.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                # Missing code
                current = time.time() if now is None else now
                if self.is_code_active(current):
                    self._wrong_attempts += 1
                    if self._wrong_attempts >= self.max_attempts:
                        self._locked_until = current + self.lockout_duration
                        self.cancel_pairing()
                        return False, "Too many failed attempts. Pairing is locked for 15 minutes."
                return False, "Usage: /pair <CODE>"

            code = parts[1].strip()
            success, msg = self.handle_pairing_attempt(user_id, code, now=now)
            return success, msg

        # Unpaired stranger or unconfigured
        return False, UNCONFIGURED_MESSAGE
