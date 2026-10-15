"""
tests/test_channel_telegram_integration.py - Integration tests for F-0046 (Telegram Gateway).

Crosses service and subprocess boundaries:
1. HTTP webhook boundary:
   Live HTTP server receiving Telegram webhook updates validates secret tokens,
   filters through TelegramPairingManager, and dispatches to TelegramChannelProvider.
2. Dynamic feature toggle boundary:
   Modifying locus.channel.telegram.enabled on disk dynamically shifts the live
   endpoint from 200 OK processing to 503 Service Unavailable without restarting.
3. End-to-end owner execution boundary:
   A real Pi turn execution via run_pi_turn is invoked for the paired owner and delivers
   the captured response back to the recipient channel.
"""

import http.server
import json
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from sidecar.channel_telegram import TelegramChannelProvider
from sidecar.config import clear_cache
from sidecar.pi_bridge import PiTurnResult
from sidecar.telegram_pairing import TelegramPairingManager


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def integration_env(tmp_path: Path):
    """Fixture providing isolated configuration environment with paired owner."""
    cfg_file = tmp_path / "config.yaml"
    data = {
        "locus": {
            "channel": {
                "telegram": {
                    "enabled": True,
                    "token": "TEST_INTEG_TOKEN_999",
                    "webhook_url": "https://example.com/tg_webhook",
                    "webhook_secret": "my_webhook_secret_xyz123",
                }
            }
        }
    }
    cfg_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    clear_cache()

    pairing_mgr = TelegramPairingManager(config_path=cfg_file)
    pairing_mgr.save_allowed_user_id(12345678)  # Pre-pair owner

    return cfg_file


def test_integration_telegram_webhook_live_boundary(integration_env: Path):
    """
    Test live HTTP boundary: Telegram webhook updates sent over HTTP network socket
    are verified by secret token, authorized by pairing manager, and answered.
    """
    provider = TelegramChannelProvider(custom_config_path=integration_env)
    provider.initialize({
        "webhook_url": "https://example.com/tg_webhook",
        "webhook_secret": "my_webhook_secret_xyz123",
    })

    sent_replies: list[tuple[Any, str]] = []
    provider._transport_sender = lambda recip, text, kb: sent_replies.append((recip, text)) or True

    class WebhookHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            secret_hdr = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            body_json = json.loads(raw_body) if raw_body else {}

            status_code, response_data = provider.handle_webhook_update(
                update_data=body_json,
                secret_header=secret_hdr,
            )

            resp_bytes = json.dumps(response_data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)

        def log_message(self, format, *args):
            pass  # Suppress logging during tests

    port = find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), WebhookHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}/webhook/telegram"

    try:
        # 1. Invalid secret header -> 403 Forbidden
        bad_req = urllib.request.Request(
            url,
            data=json.dumps({"message": {"text": "hello"}}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Telegram-Bot-Api-Secret-Token": "bad_secret",
            },
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(bad_req)
        assert exc_info.value.code == 403

        # 2. Paired owner message with valid secret header -> 200 OK + Pi execution
        owner_payload = {
            "update_id": 1001,
            "message": {
                "message_id": 55,
                "from": {"id": 12345678, "first_name": "Owner"},
                "chat": {"id": 12345678, "type": "private"},
                "text": "Summarize inbox",
            },
        }

        mock_pi = PiTurnResult(stdout="Inbox summary: 3 urgent tasks.", stderr="", returncode=0)
        with patch("sidecar.channel_telegram.run_pi_turn", return_value=mock_pi) as pi_call:
            good_req = urllib.request.Request(
                url,
                data=json.dumps(owner_payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Telegram-Bot-Api-Secret-Token": "my_webhook_secret_xyz123",
                },
                method="POST",
            )
            with urllib.request.urlopen(good_req) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))
                assert data["status"] == "executed"
                assert data["executed"] is True
                assert data["response"] == "Inbox summary: 3 urgent tasks."

            pi_call.assert_called_once_with(
                prompt="Summarize inbox",
                session_id="telegram_12345678",
            )
            assert len(sent_replies) == 1
            assert sent_replies[-1] == (12345678, "Inbox summary: 3 urgent tasks.")

        # 3. Dynamic disable via config.yaml -> 503 Service Unavailable
        disabled_data = {
            "locus": {
                "channel": {
                    "telegram": {
                        "enabled": False,
                    }
                }
            }
        }
        integration_env.write_text(yaml.safe_dump(disabled_data), encoding="utf-8")
        clear_cache()

        with pytest.raises(urllib.error.HTTPError) as exc_info_off:
            urllib.request.urlopen(good_req)
        assert exc_info_off.value.code == 503
        resp_body = json.loads(exc_info_off.value.read().decode("utf-8"))
        assert resp_body == {"disabled": "locus.channel.telegram.enabled"}

    finally:
        server.shutdown()
        server.server_close()
