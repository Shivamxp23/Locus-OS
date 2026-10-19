"""
SPEC §18 / R4 / F-0083 / US-14: Secret Reference Flow Manager for Late Key Entry via Telegram.
Enforces:
1. Opaque secret reference token generated cryptographically (16-byte hex).
2. 5-minute timeout (token expires and cannot be consumed).
3. 15-minute cleanup (expired references purged from memory).
4. Single-use: consumed immediately upon successful persistence.
5. Secrets written securely to LOCUS_HOME/.env with restricted permissions (0600).
6. Secrets are never echoed, logged, or returned in status messages.
"""
from __future__ import annotations

import os
from pathlib import Path
import secrets
import stat
import time
from typing import Dict, Optional, Tuple

from sidecar import config

PROVIDER_ENV_MAP: Dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "telegram": "TELEGRAM_BOT_TOKEN",
    "composio": "COMPOSIO_API_KEY",
}


class SecretReference:
    """Represents an active or expired secret reference session."""

    TIMEOUT_SECONDS: float = 300.0   # 5 minutes
    CLEANUP_SECONDS: float = 900.0   # 15 minutes

    def __init__(self, ref_id: str, provider: str, created_at: Optional[float] = None) -> None:
        self.ref_id = ref_id
        self.provider = provider.lower().strip()
        self.created_at = created_at if created_at is not None else time.time()
        self.is_consumed = False

    def is_expired(self, now: Optional[float] = None) -> bool:
        current = now if now is not None else time.time()
        return (current - self.created_at) > self.TIMEOUT_SECONDS

    def is_cleanable(self, now: Optional[float] = None) -> bool:
        current = now if now is not None else time.time()
        return (current - self.created_at) > self.CLEANUP_SECONDS


class SecretReferenceManager:
    """Manages the lifecycle of secret references for late key entry (R4)."""

    def __init__(self) -> None:
        self._references: Dict[str, SecretReference] = {}

    def cleanup(self, now: Optional[float] = None) -> int:
        """Remove references that have exceeded the 15-minute cleanup window."""
        current = now if now is not None else time.time()
        to_remove = [k for k, ref in self._references.items() if ref.is_cleanable(current)]
        for k in to_remove:
            del self._references[k]
        return len(to_remove)

    def create_secret_reference(self, provider: str) -> str:
        """
        Generate an opaque, cryptographically random secret reference token (R4).
        Valid for 5 minutes. Cleaned up after 15 minutes.
        """
        self.cleanup()
        ref_id = secrets.token_hex(16)
        ref = SecretReference(ref_id=ref_id, provider=provider)
        self._references[ref_id] = ref
        return ref_id

    def get_reference(self, ref_id: str) -> Optional[SecretReference]:
        """Lookup reference by ID."""
        return self._references.get(ref_id)

    def consume_secret_reference(
        self,
        ref_id: str,
        secret_value: str,
        env_file: Optional[Path] = None,
        now: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Consume a secret reference by persisting the secret to LOCUS_HOME/.env (R4).
        Enforces 5-minute timeout and single-use consumption.
        Never logs or echoes secret_value.
        """
        self.cleanup(now=now)
        ref = self._references.get(ref_id)
        if not ref:
            return False, "Invalid or unrecognized secret reference token."

        current = now if now is not None else time.time()
        if ref.is_expired(current):
            return False, "Secret reference has expired (5-minute timeout). Please run /setup again."

        if ref.is_consumed:
            return False, "Secret reference has already been consumed."

        if not secret_value or not secret_value.strip():
            return False, "Secret value cannot be empty."

        clean_secret = secret_value.strip()

        # Resolve target environment file
        target_env = env_file
        if target_env is None:
            target_env = config.get_locus_home() / ".env"

        # Resolve environment variable key name
        env_var = PROVIDER_ENV_MAP.get(ref.provider, f"{ref.provider.upper()}_API_KEY")

        # Read existing .env lines
        existing_lines: list[str] = []
        found = False
        if target_env.is_file():
            try:
                for line in target_env.read_text(encoding="utf-8").splitlines():
                    trimmed = line.strip()
                    if trimmed and not trimmed.startswith("#") and "=" in trimmed:
                        k, _ = trimmed.split("=", 1)
                        if k.strip() == env_var:
                            existing_lines.append(f"{env_var}={clean_secret}")
                            found = True
                            continue
                    existing_lines.append(line)
            except Exception:
                existing_lines = []

        if not found:
            existing_lines.append(f"{env_var}={clean_secret}")

        # Write .env with 0600 permissions
        try:
            target_env.parent.mkdir(parents=True, exist_ok=True)
            content = "\n".join(existing_lines) + "\n"
            target_env.write_text(content, encoding="utf-8")
            if hasattr(os, "chmod"):
                try:
                    os.chmod(target_env, stat.S_IRUSR | stat.S_IWUSR)
                except Exception:
                    pass
        except Exception as exc:
            return False, f"Failed to persist key to .env: {exc}"

        # Mark reference as consumed (single-use)
        ref.is_consumed = True
        return True, f"Key for '{ref.provider}' saved securely to .env. Secret reference consumed."
