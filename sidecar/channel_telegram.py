"""
sidecar/channel_telegram.py - Telegram ChannelProvider for Locus OS.

Implements ChannelProvider interface registered under ('channel', 'telegram'):
- Feature toggle: locus.channel.telegram.enabled (when false: no network, no polling).
- Security: enforces one-time pairing (S-1) via TelegramPairingManager.
- Execution: paired owner messages trigger run_pi_turn with session_id="telegram_<chat_id>".
- Isolation: messages from unpaired/unauthorized senders are rejected/ignored with no code execution.
- Webhook security: requires TELEGRAM_WEBHOOK_SECRET; fails closed if unset.
- Constraints: chunks messages exceeding Telegram's 4096 character limit.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from sidecar.config import get as config_get, get_env, is_enabled as config_is_enabled
from sidecar.pi_bridge import PiTurnResult, run_pi_turn
from sidecar.registry import BaseProvider, get_registry
from sidecar.telegram_pairing import TelegramPairingManager, validate_webhook_config

logger = logging.getLogger("sidecar.channel_telegram")

MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def chunk_message(text: str, max_length: int = MAX_TELEGRAM_MESSAGE_LENGTH) -> list[str]:
    """Split text into chunks not exceeding max_length."""
    if not text:
        return [""]
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current_pos = 0
    total_len = len(text)

    while current_pos < total_len:
        end_pos = min(current_pos + max_length, total_len)
        if end_pos < total_len:
            # Try to break cleanly at newline
            last_newline = text.rfind("\n", current_pos, end_pos)
            if last_newline > current_pos + (max_length // 2):
                end_pos = last_newline + 1
            else:
                # Try to break at space
                last_space = text.rfind(" ", current_pos, end_pos)
                if last_space > current_pos + (max_length // 2):
                    end_pos = last_space + 1

        chunk = text[current_pos:end_pos]
        chunks.append(chunk)
        current_pos = end_pos

    return chunks


class ChannelProvider(BaseProvider):
    """Base interface for all Locus communication channels."""

    name: str = "channel"

    def send_message(self, recipient: str | int, text: str, keyboard: Any = None) -> bool:
        """Send message to recipient."""
        raise NotImplementedError

    def is_connected(self) -> bool:
        """Check if channel is connected and ready."""
        return False


class TelegramChannelProvider(ChannelProvider):
    """Telegram gateway adapter implementing ChannelProvider."""

    name: str = "telegram"

    def __init__(
        self,
        token: Optional[str] = None,
        config_path: Optional[Path] = None,
        pairing_manager: Optional[TelegramPairingManager] = None,
        custom_config_path: Optional[Path] = None,
    ):
        self.custom_config_path = custom_config_path
        self._explicit_token = token
        self._config_path = config_path
        self._pairing_manager = pairing_manager
        self._connected = False
        self._webhook_url: Optional[str] = None
        self._webhook_secret: Optional[str] = None

        # Message transport hook for mock/test injection
        self._transport_sender: Optional[Any] = None

    @property
    def pairing_manager(self) -> TelegramPairingManager:
        if self._pairing_manager is None:
            cfg_path = self._config_path or self.custom_config_path
            self._pairing_manager = TelegramPairingManager(config_path=cfg_path)
        return self._pairing_manager

    def is_enabled(self) -> bool:
        """Check if Telegram channel is enabled in configuration."""
        return config_is_enabled("locus.channel.telegram.enabled", custom_path=self.custom_config_path)

    def get_token(self) -> Optional[str]:
        """Resolve bot token from explicit value, config, or environment."""
        if self._explicit_token:
            return self._explicit_token
        cfg_token = config_get("locus.channel.telegram.token", custom_path=self.custom_config_path)
        if cfg_token:
            return str(cfg_token)
        return get_env("TELEGRAM_BOT_TOKEN")

    def initialize(self, options: Optional[dict[str, Any]] = None) -> None:
        """Initialize channel with configuration options."""
        options = options or {}
        if not self.is_enabled():
            logger.info("Telegram channel is disabled by config: skipping connection.")
            self._connected = False
            return

        token = self.get_token()
        if not token:
            logger.warning("Telegram channel enabled but no bot token configured.")
            self._connected = False
            return

        self._webhook_url = options.get("webhook_url") or config_get(
            "locus.channel.telegram.webhook_url", custom_path=self.custom_config_path
        ) or get_env("TELEGRAM_WEBHOOK_URL")

        self._webhook_secret = options.get("webhook_secret") or config_get(
            "locus.channel.telegram.webhook_secret", custom_path=self.custom_config_path
        ) or get_env("TELEGRAM_WEBHOOK_SECRET")

        if self._webhook_url:
            validate_webhook_config(self._webhook_url, self._webhook_secret)

        self._connected = True

    def shutdown(self) -> None:
        """Clean up channel resources."""
        self._connected = False

    def is_connected(self) -> bool:
        """Return True only if enabled, initialized, and token available."""
        if not self.is_enabled():
            return False
        return self._connected and bool(self.get_token())

    def send_message(self, recipient: str | int, text: str, keyboard: Any = None) -> bool:
        """
        Send text message to Telegram chat.
        Automatically chunks text exceeding 4096 characters.
        """
        if not self.is_enabled():
            logger.warning("Cannot send Telegram message: channel is disabled by config.")
            return False

        token = self.get_token()
        if not token and not self._transport_sender:
            logger.error("Cannot send Telegram message: bot token missing.")
            return False

        chunks = chunk_message(text, MAX_TELEGRAM_MESSAGE_LENGTH)
        success = True

        for chunk in chunks:
            if self._transport_sender is not None:
                ok = self._transport_sender(recipient, chunk, keyboard)
                if not ok:
                    success = False
                continue

            # Standard Telegram Bot API sendMessage
            api_url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": recipient,
                "text": chunk,
            }
            if keyboard is not None:
                payload["reply_markup"] = keyboard

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                api_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status != 200:
                        success = False
            except Exception as e:
                logger.error("Failed to send Telegram message to %s: %s", recipient, e)
                success = False

        return success

    def handle_inbound_message(
        self,
        sender_id: int,
        chat_id: int,
        text: str,
        chat_type: str = "private",
    ) -> dict[str, Any]:
        """
        Process an inbound message with strict authorization and Pi routing.
        - Unpaired/unauthorized senders get denial or pairing response; Pi is NEVER called.
        - Paired owner messages execute run_pi_turn and send reply back to chat_id.
        """
        if not self.is_enabled():
            return {"status": "disabled", "error": "Telegram channel is disabled"}

        # S-1 Authorization check via pairing manager
        is_direct = (chat_type == "private")
        authorized, reply_msg = self.pairing_manager.handle_inbound_message(
            user_id=sender_id,
            text=text,
            is_direct=is_direct,
        )

        if not authorized:
            if reply_msg:
                self.send_message(recipient=chat_id, text=reply_msg)
            return {
                "status": "denied",
                "user_id": sender_id,
                "reply_sent": bool(reply_msg),
                "executed": False,
            }

        # Handle pairing command completion if reply_msg is not AUTHORIZED
        if reply_msg != "AUTHORIZED":
            if reply_msg:
                self.send_message(recipient=chat_id, text=reply_msg)
            return {
                "status": "paired",
                "user_id": sender_id,
                "reply_sent": bool(reply_msg),
                "executed": False,
            }

        # Authorized owner message: execute Pi turn
        session_id = f"telegram_{chat_id}"
        logger.info("Executing Pi turn for paired owner chat %s (user %s)", chat_id, sender_id)

        pi_result: PiTurnResult = run_pi_turn(
            prompt=text,
            session_id=session_id,
        )

        response_text = pi_result.stdout.strip() if pi_result.stdout else "No output from Pi Agent."
        if not pi_result.ok and pi_result.stderr:
            response_text = f"Error: {pi_result.stderr.strip()}\n{response_text}"

        # Deliver Pi response back to owner chat
        send_ok = self.send_message(recipient=chat_id, text=response_text)

        return {
            "status": "executed",
            "user_id": sender_id,
            "session_id": session_id,
            "reply_sent": send_ok,
            "response": response_text,
            "executed": True,
        }

    def handle_webhook_update(
        self,
        update_data: dict[str, Any],
        secret_header: Optional[str] = None,
    ) -> tuple[int, dict[str, Any]]:
        """
        Handle inbound webhook payload from Telegram.
        Validates secret header if webhook mode is active.
        """
        if not self.is_enabled():
            return 503, {"disabled": "locus.channel.telegram.enabled"}

        if self._webhook_url:
            if not self._webhook_secret or secret_header != self._webhook_secret:
                logger.warning("Rejected webhook: secret mismatch or missing header.")
                return 403, {"error": "Invalid webhook secret"}

        message = update_data.get("message") or update_data.get("edited_message")
        if not message or not isinstance(message, dict):
            return 200, {"status": "ignored", "reason": "no message payload"}

        sender = message.get("from") or {}
        sender_id = sender.get("id")
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        chat_type = chat.get("type", "private")
        text = message.get("text", "")

        if sender_id is None or chat_id is None:
            return 200, {"status": "ignored", "reason": "missing sender or chat id"}

        result = self.handle_inbound_message(
            sender_id=int(sender_id),
            chat_id=int(chat_id),
            text=str(text),
            chat_type=str(chat_type),
        )
        return 200, result

    def health_check(self) -> dict[str, Any]:
        """Check Telegram provider health status."""
        if not self.is_enabled():
            return {"status": "disabled", "latency_ms": 0.0, "error": None}

        token = self.get_token()
        if not token:
            return {"status": "down", "latency_ms": 0.0, "error": "Bot token missing"}

        return {"status": "ok", "latency_ms": 0.0, "error": None}


def register_telegram_channel(custom_config_path: Optional[Path] = None) -> TelegramChannelProvider:
    """Register TelegramChannelProvider in global ProviderRegistry."""
    registry = get_registry()
    provider = TelegramChannelProvider(custom_config_path=custom_config_path)
    registry.register("channel", "telegram", provider, is_default=True)
    return provider
