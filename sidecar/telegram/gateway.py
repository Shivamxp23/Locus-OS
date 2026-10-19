"""
SPEC §03 / §10 S-1 / F-0083 / US-04: Telegram Gateway Channel Provider.
Implements:
- BaseChannelProvider interface
- Strict fail-closed pairing enforcement via PairingManager
- Rejection of unauthorized users with fixed response: "not configured"
- Group, forward, and inline query filtering
- Webhook secret enforcement: refuses to start in webhook mode without TELEGRAM_WEBHOOK_SECRET
"""
from __future__ import annotations

import time
from typing import Any, Callable

from sidecar import config
from sidecar.providers.channel import BaseChannelProvider
from sidecar.registry import get_registry
from sidecar.telegram.pairing import PairingManager


class TelegramGateway(BaseChannelProvider):
    """
    Telegram Channel Gateway with secure first-run pairing and fail-closed access control.
    """
    FIXED_UNCONFIGURED_LINE: str = "not configured"

    def __init__(self, pairing_manager: PairingManager | None = None) -> None:
        self.pairing_manager = pairing_manager or PairingManager()
        self._enabled: bool = True
        self._webhook_mode: bool = False
        self._token: str | None = None
        self._running: bool = False
        self._outbox: list[dict[str, Any]] = []
        self._custom_transport: Callable[[dict[str, Any]], Any] | None = None

    def set_transport(self, transport: Callable[[dict[str, Any]], Any] | None) -> None:
        """Inject transport for testing (e.g. fake Telegram network transport)."""
        self._custom_transport = transport

    def initialize(self, options: dict[str, Any] | None = None) -> None:
        """
        Initialize the gateway with options.
        Validates webhook secret requirement and token configuration.
        """
        opts = options or {}
        self._enabled = config.is_enabled("locus.channels.telegram.enabled")
        # If not explicitly configured in config, default to enabled if options say so or True
        if config.get("locus.channels.telegram.enabled") is None:
            self._enabled = opts.get("enabled", True)

        self._webhook_mode = bool(
            opts.get("webhook", False) or config.is_enabled("locus.channels.telegram.webhook")
        )

        # SPEC §10 S-1 item 7: Webhook mode refuses to start without TELEGRAM_WEBHOOK_SECRET
        if self._webhook_mode:
            secret = config.get_env("TELEGRAM_WEBHOOK_SECRET") or opts.get("webhook_secret")
            if not secret or not str(secret).strip():
                raise ValueError("Webhook mode requires TELEGRAM_WEBHOOK_SECRET")

        self._token = opts.get("token") or config.get_env("TELEGRAM_BOT_TOKEN")
        self._running = True

    def shutdown(self) -> None:
        """Cleanly shutdown the gateway."""
        self._running = False

    def health_check(self) -> dict[str, Any]:
        """
        Check health of the Telegram gateway.
        Returns status ('ok', 'degraded', 'error'), latency_ms, and provider details.
        """
        start = time.perf_counter()
        if not self._enabled:
            return {
                "status": "degraded",
                "provider": "telegram",
                "enabled": False,
                "latency_ms": 0.0,
                "message": "Telegram channel is disabled in configuration",
            }

        # Check configuration validity (fail closed)
        if not config.is_config_valid():
            return {
                "status": "error",
                "provider": "telegram",
                "enabled": True,
                "latency_ms": 0.0,
                "error": "Configuration file is corrupted or unreadable",
            }

        latency_ms = (time.perf_counter() - start) * 1000.0
        owner_id = self.pairing_manager.get_owner_id()
        return {
            "status": "ok",
            "provider": "telegram",
            "enabled": True,
            "paired": owner_id is not None,
            "owner_id": owner_id,
            "webhook_mode": self._webhook_mode,
            "latency_ms": round(latency_ms, 3),
        }

    def send_message(self, target: str | int, text: str) -> bool:
        """Send a message to a Telegram chat ID."""
        if not self._running or not self._enabled:
            return False

        payload = {"chat_id": int(target), "text": text}
        self._outbox.append(payload)

        if self._custom_transport is not None:
            self._custom_transport(payload)
            return True

        return True

    def handle_update(self, update: dict[str, Any]) -> dict[str, Any] | None:
        """
        Handle an incoming Telegram update object.
        Enforces S-1 security:
        - Ignores groups, forwards, and inline queries
        - Unpaired stranger messages receive ONE fixed line: 'not configured'
        - Fail-closed if config is corrupted or unreadable
        - Handles /pair <code> command
        - Executes nothing for strangers
        """
        if not self._enabled or not self._running:
            return None

        # Ignore inline queries, edited messages, channel posts
        message = update.get("message")
        if not isinstance(message, dict):
            return None

        # S-1 item 6: Messages from other ids, groups, forwards, and inline queries are ignored.
        chat = message.get("chat", {})
        if chat.get("type") != "private":
            return None

        if "forward_from" in message or "forward_date" in message:
            return None

        sender = message.get("from", {})
        sender_id = sender.get("id")
        if sender_id is None:
            return None

        chat_id = chat.get("id", sender_id)
        raw_text = str(message.get("text") or "").strip()

        # S-1 item 5: If the allowed-id list cannot be read or written, the bot refuses ALL messages (fail closed)
        if not config.is_config_valid():
            reply = {"chat_id": chat_id, "text": "Configuration error: fail-closed"}
            self._outbox.append(reply)
            return reply

        # Check if sender is the paired owner
        if self.pairing_manager.is_allowed_user(sender_id):
            if raw_text.startswith("/pair"):
                reply = {"chat_id": chat_id, "text": "Already paired with owner."}
            else:
                reply = {"chat_id": chat_id, "text": f"Owner command: {raw_text}"}
            self._outbox.append(reply)
            return reply

        # Sender is NOT the owner
        if raw_text.startswith("/pair"):
            parts = raw_text.split(maxsplit=1)
            code = parts[1] if len(parts) > 1 else ""
            success, msg = self.pairing_manager.attempt_pair(code, int(sender_id))
            reply = {"chat_id": chat_id, "text": msg}
            self._outbox.append(reply)
            return reply

        # S-1 item 4: Until paired, the bot answers every message with one fixed line ("not configured") and executes nothing.
        reply = {"chat_id": chat_id, "text": self.FIXED_UNCONFIGURED_LINE}
        self._outbox.append(reply)
        return reply


# Register default ChannelProvider under area 'channels' and name 'telegram' in universal registry
get_registry().register("channels", "telegram", TelegramGateway)
