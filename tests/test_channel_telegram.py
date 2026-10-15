"""
tests/test_channel_telegram.py - Unit tests for US-07 (F-0046).

Acceptance criteria:
- sidecar/channel_telegram.py implements the ChannelProvider interface and registers under ('channel', 'telegram') in ProviderRegistry.
- When locus.channel.telegram.enabled is false, the gateway does not connect to Telegram or poll for updates.
- Inbound messages from the paired owner chat ID trigger run_pi_turn and stream/reply the generated answer back to the owner's Telegram chat.
- Messages from any chat ID other than the paired owner are rejected/ignored with no execution or leak of system info.
- Webhook mode requires TELEGRAM_WEBHOOK_SECRET and fails closed if unset.
"""

from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sidecar.channel_telegram import (
    ChannelProvider,
    TelegramChannelProvider,
    chunk_message,
    register_telegram_channel,
)
from sidecar.config import clear_cache
from sidecar.pi_bridge import PiTurnResult
from sidecar.registry import ProviderRegistry, get_registry
from sidecar.telegram_pairing import TelegramPairingManager


@pytest.fixture
def test_config_env(tmp_path: Path):
    """Fixture providing temporary configuration directory and config.yaml."""
    cfg_file = tmp_path / "config.yaml"
    data = {
        "locus": {
            "channel": {
                "telegram": {
                    "enabled": True,
                    "token": "TEST_BOT_TOKEN_12345",
                }
            }
        }
    }
    cfg_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    clear_cache()
    return cfg_file


def test_telegram_channel_implements_interface_and_registers(test_config_env: Path):
    """Verify ChannelProvider interface adherence and ProviderRegistry registration."""
    provider = TelegramChannelProvider(custom_config_path=test_config_env)
    assert isinstance(provider, ChannelProvider)
    assert provider.name == "telegram"

    reg = ProviderRegistry()
    reg.register("channel", "telegram", provider, is_default=True)
    resolved = reg.get("channel", name="telegram")
    assert resolved is provider

    # Test global registration helper
    registered_prov = register_telegram_channel(custom_config_path=test_config_env)
    assert isinstance(registered_prov, TelegramChannelProvider)
    assert get_registry().get("channel", name="telegram") is registered_prov


def test_telegram_channel_disabled_behavior(tmp_path: Path):
    """
    Acceptance criterion: When locus.channel.telegram.enabled is false,
    the gateway does not connect to Telegram or poll for updates.
    """
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.safe_dump({"locus": {"channel": {"telegram": {"enabled": False}}}}),
        encoding="utf-8",
    )
    clear_cache()

    provider = TelegramChannelProvider(custom_config_path=cfg_file)
    assert provider.is_enabled() is False

    provider.initialize()
    assert provider.is_connected() is False

    # Outbound send fails immediately when disabled
    assert provider.send_message(12345, "Hello") is False

    # Inbound message is refused
    inbound_res = provider.handle_inbound_message(sender_id=12345, chat_id=12345, text="Hello")
    assert inbound_res["status"] == "disabled"

    # Webhook endpoint answers 503 Service Unavailable
    code, payload = provider.handle_webhook_update({"message": {"text": "hi"}})
    assert code == 503
    assert payload == {"disabled": "locus.channel.telegram.enabled"}


def test_telegram_channel_unpaired_sender_rejected(test_config_env: Path):
    """
    Acceptance criterion: Messages from any chat ID other than the paired owner
    are rejected/ignored with no execution or leak of system info.
    """
    pairing_mgr = TelegramPairingManager(config_path=test_config_env)
    provider = TelegramChannelProvider(
        custom_config_path=test_config_env,
        pairing_manager=pairing_mgr,
    )

    sent_messages: list[tuple[Any, str]] = []
    provider._transport_sender = lambda recip, text, kb: sent_messages.append((recip, text)) or True

    with patch("sidecar.channel_telegram.run_pi_turn") as mock_pi:
        res = provider.handle_inbound_message(sender_id=99999, chat_id=99999, text="Status update?")
        assert res["status"] == "denied"
        assert res["executed"] is False
        mock_pi.assert_not_called()

    # Fixed line returned without system leak
    assert len(sent_messages) == 1
    assert sent_messages[0] == (99999, "Locus is not configured.")


def test_telegram_channel_pairing_and_paired_owner_triggers_pi(test_config_env: Path):
    """
    Acceptance criterion: Inbound messages from the paired owner chat ID trigger run_pi_turn
    and stream/reply the generated answer back to the owner's Telegram chat.
    """
    pairing_mgr = TelegramPairingManager(config_path=test_config_env)
    code = pairing_mgr.start_pairing()

    provider = TelegramChannelProvider(
        custom_config_path=test_config_env,
        pairing_manager=pairing_mgr,
    )

    sent_messages: list[tuple[Any, str]] = []
    provider._transport_sender = lambda recip, text, kb: sent_messages.append((recip, text)) or True

    owner_id = 7771234
    owner_chat_id = 7771234

    # Step 1: Pair owner using /pair <code>
    pair_res = provider.handle_inbound_message(
        sender_id=owner_id,
        chat_id=owner_chat_id,
        text=f"/pair {code}",
    )
    assert pair_res["status"] == "paired"
    assert "Paired" in sent_messages[-1][1]

    # Step 2: Inbound message from paired owner triggers Pi turn
    mock_pi_result = PiTurnResult(stdout="Pi: Research completed successfully.", stderr="", returncode=0)

    with patch("sidecar.channel_telegram.run_pi_turn", return_value=mock_pi_result) as mock_pi:
        exec_res = provider.handle_inbound_message(
            sender_id=owner_id,
            chat_id=owner_chat_id,
            text="Run research on quantum computing",
        )

        assert exec_res["status"] == "executed"
        assert exec_res["executed"] is True
        assert exec_res["session_id"] == f"telegram_{owner_chat_id}"
        assert exec_res["response"] == "Pi: Research completed successfully."

        # Verify Pi called with exact prompt and deterministic per-chat session ID
        mock_pi.assert_called_once_with(
            prompt="Run research on quantum computing",
            session_id=f"telegram_{owner_chat_id}",
        )

    # Verify response sent back to owner chat
    assert sent_messages[-1] == (owner_chat_id, "Pi: Research completed successfully.")


def test_telegram_channel_stranger_rejected_after_owner_paired(test_config_env: Path):
    """Verify that messages from strangers are rejected after owner is paired."""
    pairing_mgr = TelegramPairingManager(config_path=test_config_env)
    pairing_mgr.save_allowed_user_id(7771234)  # Owner paired

    provider = TelegramChannelProvider(
        custom_config_path=test_config_env,
        pairing_manager=pairing_mgr,
    )

    sent_messages: list[tuple[Any, str]] = []
    provider._transport_sender = lambda recip, text, kb: sent_messages.append((recip, text)) or True

    stranger_id = 8889999
    with patch("sidecar.channel_telegram.run_pi_turn") as mock_pi:
        res = provider.handle_inbound_message(
            sender_id=stranger_id,
            chat_id=stranger_id,
            text="Execute unauthorized command",
        )
        assert res["status"] == "denied"
        assert res["executed"] is False
        mock_pi.assert_not_called()

    # Fixed unconfigured message sent without leaking system info or executing
    assert len(sent_messages) == 1
    assert sent_messages[0] == (stranger_id, "Locus is not configured.")


def test_telegram_webhook_secret_required_and_validated(test_config_env: Path):
    """
    Acceptance criterion: Webhook mode requires TELEGRAM_WEBHOOK_SECRET and fails closed if unset.
    """
    # Fail closed on initialization if secret is missing
    prov_no_secret = TelegramChannelProvider(custom_config_path=test_config_env)
    with pytest.raises(ValueError, match="TELEGRAM_WEBHOOK_SECRET is required"):
        prov_no_secret.initialize({"webhook_url": "https://example.com/webhook", "webhook_secret": None})

    # When secret is configured, valid secret is accepted
    prov_with_secret = TelegramChannelProvider(custom_config_path=test_config_env)
    prov_with_secret.initialize({
        "webhook_url": "https://example.com/webhook",
        "webhook_secret": "secure_secret_token_abc",
    })
    assert prov_with_secret.is_connected() is True

    # Bad secret header returns 403 Forbidden
    status_bad, body_bad = prov_with_secret.handle_webhook_update(
        {"message": {"text": "hello"}},
        secret_header="wrong_secret",
    )
    assert status_bad == 403
    assert body_bad == {"error": "Invalid webhook secret"}

    # Good secret header is processed
    status_ok, body_ok = prov_with_secret.handle_webhook_update(
        {"message": {"from": {"id": 123}, "chat": {"id": 123}, "text": "hello"}},
        secret_header="secure_secret_token_abc",
    )
    assert status_ok == 200


def test_telegram_message_chunking():
    """Verify long responses (>4096 chars) are safely chunked."""
    short_text = "Short text"
    assert chunk_message(short_text) == ["Short text"]

    long_text = ("Line " * 200 + "\n") * 10  # > 10,000 chars
    chunks = chunk_message(long_text, max_length=4096)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 4096

    reconstructed = "".join(chunks)
    assert reconstructed == long_text


def test_telegram_channel_health_check(test_config_env: Path, tmp_path: Path):
    """Verify health_check reports disabled, down, and ok status accurately."""
    # 1. OK status
    prov_ok = TelegramChannelProvider(custom_config_path=test_config_env)
    prov_ok.initialize()
    health_ok = prov_ok.health_check()
    assert health_ok["status"] == "ok"
    assert health_ok["error"] is None

    # 2. Disabled status
    cfg_off = tmp_path / "config_off.yaml"
    cfg_off.write_text(yaml.safe_dump({"locus": {"channel": {"telegram": {"enabled": False}}}}), encoding="utf-8")
    prov_off = TelegramChannelProvider(custom_config_path=cfg_off)
    health_off = prov_off.health_check()
    assert health_off["status"] == "disabled"

    # 3. Down status (token missing)
    cfg_no_token = tmp_path / "config_no_token.yaml"
    cfg_no_token.write_text(yaml.safe_dump({"locus": {"channel": {"telegram": {"enabled": True}}}}), encoding="utf-8")
    prov_down = TelegramChannelProvider(custom_config_path=cfg_no_token)
    health_down = prov_down.health_check()
    assert health_down["status"] == "down"
    assert "token missing" in health_down["error"]
