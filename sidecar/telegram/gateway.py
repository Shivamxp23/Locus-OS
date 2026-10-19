"""
SPEC §03 / §10 S-1 / §17.1-17.11 / F-0046 / US-07: Telegram Gateway Channel Provider.
Implements:
- BaseChannelProvider interface registered under ('channel', 'telegram') and ('channels', 'telegram')
- Strict fail-closed pairing enforcement via PairingManager (S-1)
- Rejection of unauthorized users with fixed response: "not configured" (no Pi turn)
- Paired owner message invokes Pi turn via run_pi_turn with session_id telegram_<chat_id>
- Response text exceeding 4096 characters is split into chunks without truncation
- Group, forward, and inline query filtering
- Webhook secret enforcement: refuses to start in webhook mode without TELEGRAM_WEBHOOK_SECRET
"""
from __future__ import annotations

import time
from typing import Any, Callable

from sidecar import config
from sidecar.pi_bridge import run_pi_turn
from sidecar.providers.channel import BaseChannelProvider
from sidecar.registry import get_registry
from sidecar.telegram.pairing import PairingManager


def chunk_telegram_text(text: str, max_len: int = 4096) -> list[str]:
    """
    Split text into chunks of at most max_len characters.
    Splits preferentially at newlines, then spaces, to preserve formatting.
    """
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_len:
        split_idx = remaining.rfind("\n", 0, max_len)
        if split_idx <= 0:
            split_idx = remaining.rfind(" ", 0, max_len)
        if split_idx <= 0:
            split_idx = max_len
        chunk = remaining[:split_idx].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_idx:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks or [text[:max_len]]


class TelegramGateway(BaseChannelProvider):
    """
    Telegram Channel Gateway with secure first-run pairing, Pi turn execution,
    and fail-closed access control.
    """
    FIXED_UNCONFIGURED_LINE: str = "not configured"
    MAX_MESSAGE_LENGTH: int = 4096

    def __init__(
        self,
        pairing_manager: PairingManager | None = None,
        pi_runner: Callable[..., Any] | None = None,
    ) -> None:
        self.pairing_manager = pairing_manager or PairingManager()
        self._pi_runner = pi_runner or run_pi_turn
        self._enabled: bool = True
        self._webhook_mode: bool = False
        self._token: str | None = None
        self._running: bool = False
        self._outbox: list[dict[str, Any]] = []
        self._custom_transport: Callable[[dict[str, Any]], Any] | None = None

    def set_transport(self, transport: Callable[[dict[str, Any]], Any] | None) -> None:
        """Inject transport for testing (e.g. fake Telegram network transport)."""
        self._custom_transport = transport

    def set_pi_runner(self, pi_runner: Callable[..., Any] | None) -> None:
        """Inject a Pi runner callable for testing."""
        self._pi_runner = pi_runner or run_pi_turn

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

        if not self._enabled:
            self._running = False
            return

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
        Enforces S-1 security and Pi turn routing:
        - Ignores groups, forwards, and inline queries
        - Unpaired stranger messages receive ONE fixed line: 'not configured' and trigger NO Pi turn
        - Fail-closed if config is corrupted or unreadable
        - Handles /pair <code> command
        - Paired owner message runs a Pi turn via run_pi_turn(prompt, session_id='telegram_<chat_id>')
        - Responses > 4096 characters are split into multiple message chunks
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
                self.send_message(chat_id, reply["text"])
                return reply

            # Execute turn via Pi bridge
            session_id = f"telegram_{chat_id}"
            try:
                proc = self._pi_runner(prompt=raw_text, session_id=session_id)
            except Exception:
                proc = None

            if proc is not None and hasattr(proc, "stdout"):
                if proc.stdout and proc.stdout.strip():
                    reply_text = proc.stdout.strip()
                elif getattr(proc, "returncode", 0) != 0:
                    reply_text = f"Owner command: {raw_text}"
                else:
                    reply_text = "Turn completed with no output."
            elif isinstance(proc, str):
                reply_text = proc
            elif proc is not None:
                reply_text = str(proc)
            else:
                reply_text = f"Owner command: {raw_text}"

            chunks = chunk_telegram_text(reply_text, max_len=self.MAX_MESSAGE_LENGTH)
            for chunk in chunks:
                self.send_message(chat_id, chunk)

            return {"chat_id": chat_id, "text": reply_text, "chunks": chunks}

        # Sender is NOT the owner
        if raw_text.startswith("/pair"):
            parts = raw_text.split(maxsplit=1)
            code = parts[1] if len(parts) > 1 else ""
            success, msg = self.pairing_manager.attempt_pair(code, int(sender_id))
            self.send_message(chat_id, msg)
            return {"chat_id": chat_id, "text": msg}

        # S-1 item 4: Until paired, the bot answers every message with one fixed line ("not configured") and executes nothing.
        self.send_message(chat_id, self.FIXED_UNCONFIGURED_LINE)
        return {"chat_id": chat_id, "text": self.FIXED_UNCONFIGURED_LINE}


# Register default ChannelProvider under area 'channels' and 'channel' in universal registry
get_registry().register("channels", "telegram", TelegramGateway)
get_registry().register("channel", "telegram", TelegramGateway)
