"""
SPEC §10 S-1 / F-0083 / US-04: Secure Telegram Pairing Manager.
Enforces:
1. One-time code (8+ characters generated via secrets module).
2. Valid for 10 minutes, single use (destroyed on first success).
3. Only SHA-256 hash of the code is stored in memory.
4. 5 wrong attempts lock pairing for 15 minutes.
5. Allowed owner numeric Telegram ID saved to configuration.
6. Fail-closed: corrupted or unreadable config refuses all messages.
"""
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
import secrets
import string
import time
from typing import Any

from sidecar import config


class PairingManager:
    """
    Manages one-time code generation, verification, and owner access verification for Telegram.
    """
    CODE_LENGTH: int = 10
    CODE_TTL_SECONDS: float = 600.0  # 10 minutes
    MAX_WRONG_ATTEMPTS: int = 5
    LOCKOUT_SECONDS: float = 900.0   # 15 minutes

    def __init__(self) -> None:
        self._code_hash: str | None = None
        self._created_at: float = 0.0
        self._wrong_attempts: int = 0
        self._locked_until: float = 0.0

    @property
    def is_locked(self) -> bool:
        """Return True if pairing is currently locked due to too many failed attempts."""
        return time.time() < self._locked_until

    def generate_pairing_code(self) -> str:
        """
        Generate a new one-time pairing code (10 uppercase chars/digits).
        Stores only the SHA-256 hash. Returns plaintext code to display on local screen once.
        """
        alphabet = string.ascii_uppercase + string.digits
        # Cryptographically secure random selection per S-1 requirement
        code = "".join(secrets.choice(alphabet) for _ in range(self.CODE_LENGTH))
        self._code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
        self._created_at = time.time()
        self._wrong_attempts = 0
        self._locked_until = 0.0
        return code

    def attempt_pair(self, code: str, telegram_user_id: int) -> tuple[bool, str]:
        """
        Attempt to pair a user with the generated code.
        Returns (success: bool, message: str).
        """
        now = time.time()
        if now < self._locked_until:
            rem = int(self._locked_until - now)
            return False, f"Pairing is locked due to too many failed attempts. Try again in {rem}s."

        if not self._code_hash:
            return False, "No active pairing code. Run pairing setup on the host machine."

        if (now - self._created_at) > self.CODE_TTL_SECONDS:
            self._code_hash = None
            return False, "Pairing code has expired. Generate a new code on the host machine."

        # Constant-time comparison to prevent timing attacks
        candidate_hash = hashlib.sha256(code.strip().encode("utf-8")).hexdigest()
        if not hmac.compare_digest(candidate_hash, self._code_hash):
            self._wrong_attempts += 1
            if self._wrong_attempts >= self.MAX_WRONG_ATTEMPTS:
                self._locked_until = now + self.LOCKOUT_SECONDS
                self._code_hash = None
                return False, "Too many wrong attempts. Pairing is locked for 15 minutes."
            remaining = self.MAX_WRONG_ATTEMPTS - self._wrong_attempts
            return False, f"Invalid pairing code. ({remaining} attempts remaining)"

        # Match succeeded! Single use: destroy code immediately
        self._code_hash = None
        self._created_at = 0.0
        self._wrong_attempts = 0

        # Persist numeric Telegram ID via config accessor (fail closed if writing fails)
        try:
            config.set_value("channels.telegram.allowed_user_id", int(telegram_user_id))
        except Exception as e:
            return False, f"Pairing failed to persist owner ID: {e}"

        return True, "Paired successfully. You are now the owner of this Locus instance."

    def is_allowed_user(self, telegram_user_id: int | None) -> bool:
        """
        Verify if the given numeric Telegram user ID is the configured owner.
        Fails closed: if config file is invalid, corrupted, or unreadable, returns False.
        """
        if telegram_user_id is None:
            return False

        # Fail closed on corrupted or invalid config
        if not config.is_config_valid():
            return False

        try:
            allowed_id = config.get("channels.telegram.allowed_user_id")
            if allowed_id is None:
                # Also check legacy/flat key
                allowed_id = config.get("telegram.allowed_user_id")
            if allowed_id is None:
                return False
            return int(telegram_user_id) == int(allowed_id)
        except Exception:
            return False

    def get_owner_id(self) -> int | None:
        """Retrieve configured owner numeric ID, or None if unpaired / corrupted."""
        if not config.is_config_valid():
            return None
        try:
            val = config.get("channels.telegram.allowed_user_id")
            if val is None:
                val = config.get("telegram.allowed_user_id")
            return int(val) if val is not None else None
        except Exception:
            return None

    def save_owner_id(self, telegram_user_id: int) -> None:
        """Save owner numeric ID to configuration."""
        config.set_value("channels.telegram.allowed_user_id", int(telegram_user_id))
