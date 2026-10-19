"""
SPEC §17.1-17.11 / §10 S-1 / F-0046 / US-07: Telegram Gateway ChannelProvider and Pi Bridge Integration.
Tests:
- TelegramGateway implements BaseChannelProvider and registers in ProviderRegistry
- Paired owner message runs a Pi turn via run_pi_turn with session_id telegram_<chat_id>
- Reply text exceeding 4096 characters is split into chunks without truncation
- Stranger/unpaired user gets fixed response "not configured" and triggers no Pi turn
- Disabled gateway suppresses processing and Pi turns
- Groups, forwards, and non-private chats are filtered out
"""
from __future__ import annotations

import subprocess
from pathlib import Path
import pytest
import yaml

from sidecar import config
from sidecar.providers.channel import BaseChannelProvider
from sidecar.registry import get_registry
from sidecar.telegram.gateway import TelegramGateway, chunk_telegram_text
from sidecar.telegram.pairing import PairingManager


@pytest.fixture
def clean_locus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated LOCUS_HOME for configuration testing."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    return locus_home


def test_telegram_gateway_implements_channel_provider(clean_locus_env: Path):
    """SPEC 17.1-17.11 line 3950: "EVERY channel adapter MUST implement: name, initialize, send_message, receive_messages, is_connected, shutdown"."""
    gateway = TelegramGateway()
    assert isinstance(gateway, BaseChannelProvider)

    reg = get_registry()
    provider_cls_channel = reg.get("channel", "telegram")
    provider_cls_channels = reg.get("channels", "telegram")
    assert provider_cls_channel is TelegramGateway
    assert provider_cls_channels is TelegramGateway


def test_paired_owner_message_triggers_pi_turn_and_replies(clean_locus_env: Path):
    """SPEC 17.1-17.11 line 4000: "TELEGRAM ADAPTER (Locus primary channel) ... paired owner message gets a Pi turn"."""
    owner_id = 778899
    pairing_mgr = PairingManager()
    pairing_mgr.save_owner_id(owner_id)

    recorded_calls = []

    def fake_pi_runner(prompt: str, session_id: str | None = None, **kwargs):
        recorded_calls.append({"prompt": prompt, "session_id": session_id})
        return subprocess.CompletedProcess(
            args=["fake-pi"],
            returncode=0,
            stdout="Locus: Cognitive turn completed successfully.",
            stderr="",
        )

    gateway = TelegramGateway(pairing_manager=pairing_mgr, pi_runner=fake_pi_runner)
    gateway.initialize()

    sent_messages = []
    gateway.set_transport(lambda payload: sent_messages.append(payload))

    owner_update = {
        "update_id": 2001,
        "message": {
            "from": {"id": owner_id, "first_name": "Shivam"},
            "chat": {"id": owner_id, "type": "private"},
            "text": "What is my top priority today?",
        },
    }

    result = gateway.handle_update(owner_update)
    assert result is not None
    assert result["text"] == "Locus: Cognitive turn completed successfully."

    # Assert Pi bridge turn was called with correct prompt and session_id
    assert len(recorded_calls) == 1
    assert recorded_calls[0]["prompt"] == "What is my top priority today?"
    assert recorded_calls[0]["session_id"] == f"telegram_{owner_id}"

    # Assert message was delivered via transport
    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == owner_id
    assert sent_messages[0]["text"] == "Locus: Cognitive turn completed successfully."


def test_long_message_chunking_under_4096_chars(clean_locus_env: Path):
    """SPEC 17.1-17.11 line 3975: "MAX_MESSAGE_LENGTH = 4096 // Telegram limit"."""
    owner_id = 556677
    pairing_mgr = PairingManager()
    pairing_mgr.save_owner_id(owner_id)

    # Generate a response exceeding 9000 chars across multiple paragraphs
    paragraph = "Paragraph describing research findings on cognitive architectures and modular agent state.\n\n"
    long_response = paragraph * 100  # ~9200 chars

    def fake_pi_runner(prompt: str, session_id: str | None = None, **kwargs):
        return subprocess.CompletedProcess(
            args=["fake-pi"],
            returncode=0,
            stdout=long_response,
            stderr="",
        )

    gateway = TelegramGateway(pairing_manager=pairing_mgr, pi_runner=fake_pi_runner)
    gateway.initialize()

    sent_messages = []
    gateway.set_transport(lambda payload: sent_messages.append(payload))

    owner_update = {
        "update_id": 2002,
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": "Explain the full state engine architecture.",
        },
    }

    result = gateway.handle_update(owner_update)
    assert result is not None

    # Assert multiple chunks were sent, each <= 4096 chars
    assert len(sent_messages) >= 3
    for msg in sent_messages:
        assert msg["chat_id"] == owner_id
        assert len(msg["text"]) <= 4096

    # Verify no content was lost during chunking
    total_text = "\n\n".join(m["text"] for m in sent_messages)
    assert len(total_text) >= len(long_response.strip())


def test_stranger_message_gets_fixed_line_and_no_pi_turn(clean_locus_env: Path):
    """SPEC 10.S-1 line 18: "Until paired the bot answers every message with one fixed line (\"not configured\") and executes nothing."."""
    owner_id = 123456
    stranger_id = 999999
    pairing_mgr = PairingManager()
    pairing_mgr.save_owner_id(owner_id)

    pi_calls = []

    def fake_pi_runner(prompt: str, session_id: str | None = None, **kwargs):
        pi_calls.append(prompt)
        return "Pi should never run for stranger"

    gateway = TelegramGateway(pairing_manager=pairing_mgr, pi_runner=fake_pi_runner)
    gateway.initialize()

    sent_messages = []
    gateway.set_transport(lambda payload: sent_messages.append(payload))

    stranger_update = {
        "update_id": 2003,
        "message": {
            "from": {"id": stranger_id},
            "chat": {"id": stranger_id, "type": "private"},
            "text": "run rm -rf /",
        },
    }

    result = gateway.handle_update(stranger_update)
    assert result is not None
    assert result["text"] == "not configured"

    # Pi turn must NEVER have been called
    assert len(pi_calls) == 0

    # Stranger receives only the single fixed line
    assert len(sent_messages) == 1
    assert sent_messages[0]["chat_id"] == stranger_id
    assert sent_messages[0]["text"] == "not configured"


def test_disabled_telegram_gateway_suppresses_processing(clean_locus_env: Path):
    """SPEC 03 / 08 F-0125: "When a feature's enabled switch is false ... processes no messages"."""
    # Explicitly disable telegram in config
    cfg_path = clean_locus_env / "config.yaml"
    cfg_path.write_text(yaml.dump({"locus": {"channels": {"telegram": {"enabled": False}}}}), encoding="utf-8")

    owner_id = 123456
    pairing_mgr = PairingManager()
    pairing_mgr.save_owner_id(owner_id)

    pi_calls = []
    gateway = TelegramGateway(pairing_manager=pairing_mgr, pi_runner=lambda *a, **k: pi_calls.append(a))
    gateway.initialize()

    health = gateway.health_check()
    assert health["status"] == "degraded"
    assert health["enabled"] is False

    update = {
        "update_id": 2004,
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": "Hello?",
        },
    }

    res = gateway.handle_update(update)
    assert res is None
    assert len(pi_calls) == 0
    assert gateway.send_message(owner_id, "test") is False


def test_filter_groups_and_forwards_and_non_private(clean_locus_env: Path):
    """SPEC 10.S-1 line 22: "Messages from other ids, groups, forwards, and inline queries are ignored."."""
    owner_id = 123456
    pairing_mgr = PairingManager()
    pairing_mgr.save_owner_id(owner_id)

    pi_calls = []
    gateway = TelegramGateway(pairing_manager=pairing_mgr, pi_runner=lambda *a, **k: pi_calls.append(a))
    gateway.initialize()

    # Group message
    group_update = {
        "update_id": 2005,
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": -100123456789, "type": "group"},
            "text": "Group message",
        },
    }
    assert gateway.handle_update(group_update) is None

    # Forwarded message
    forward_update = {
        "update_id": 2006,
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "forward_from": {"id": 888888},
            "text": "Forwarded text",
        },
    }
    assert gateway.handle_update(forward_update) is None

    # Update without message (e.g. inline query or reaction)
    inline_update = {"update_id": 2007, "inline_query": {"id": "query123"}}
    assert gateway.handle_update(inline_update) is None

    assert len(pi_calls) == 0


def test_chunk_telegram_text_helper():
    """SPEC 17.1-17.11 line 3975: "MAX_MESSAGE_LENGTH = 4096 // Telegram limit"."""
    assert chunk_telegram_text("") == [""]
    assert chunk_telegram_text("Short message") == ["Short message"]

    text_5000 = "Line 1\n" * 700  # 4900 chars
    chunks = chunk_telegram_text(text_5000, max_len=1000)
    assert len(chunks) == 5
    for c in chunks:
        assert len(c) <= 1000
    assert "".join(chunks).replace("\n", "") == text_5000.replace("\n", "")
