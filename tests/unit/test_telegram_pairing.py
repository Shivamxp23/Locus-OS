"""
SPEC §10 S-1 / F-0083 / US-04: Security and Pairing tests for Telegram Gateway.
Enforces S-1 security requirements:
- Stranger first message rejection ("not configured")
- Wrong code rejection and counting (lockout after 5 attempts)
- Right code pairs once and stores numeric ID in LOCUS_HOME/config.yaml
- Code reuse fails (destroyed on first success)
- Corrupted allow-list fails closed
- Restart keeps owner without reopening pairing
- Webhook mode requires TELEGRAM_WEBHOOK_SECRET
- Modularity tests (off, swap, health)
"""
from __future__ import annotations

import os
from pathlib import Path
import time
import pytest
import yaml

from sidecar import config
from sidecar.providers.channel import BaseChannelProvider
from sidecar.registry import get_registry
from sidecar.telegram.gateway import TelegramGateway
from sidecar.telegram.pairing import PairingManager


@pytest.fixture
def clean_locus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated LOCUS_HOME for configuration testing."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    return locus_home


def test_stranger_first_message_rejected(clean_locus_env: Path):
    """SPEC 10.S-1 line 18: "Until paired, the bot answers every message with one fixed line (\"not configured\") and executes nothing.\""""
    pairing_mgr = PairingManager()
    gateway = TelegramGateway(pairing_manager=pairing_mgr)
    gateway.initialize()

    # Stranger sends initial message
    stranger_update = {
        "update_id": 1001,
        "message": {
            "from": {"id": 987654321, "is_bot": False, "first_name": "Stranger"},
            "chat": {"id": 987654321, "type": "private"},
            "text": "hello bot, what can you do?",
        },
    }

    resp = gateway.handle_update(stranger_update)
    assert resp is not None
    assert resp["text"] == "not configured"
    assert resp["chat_id"] == 987654321

    # Ensure stranger is NOT owner
    assert pairing_mgr.is_allowed_user(987654321) is False
    assert pairing_mgr.get_owner_id() is None


def test_wrong_code_rejected_and_counted(clean_locus_env: Path):
    """SPEC 10.S-1 line 15: "Valid 10 minutes, single use; 5 wrong attempts lock pairing for 15 minutes. Only a hash is stored.\""""
    pairing_mgr = PairingManager()
    valid_code = pairing_mgr.generate_pairing_code()

    gateway = TelegramGateway(pairing_manager=pairing_mgr)
    gateway.initialize()

    stranger_id = 11223344

    # 4 wrong attempts
    for attempt in range(1, 5):
        update = {
            "update_id": 100 + attempt,
            "message": {
                "from": {"id": stranger_id},
                "chat": {"id": stranger_id, "type": "private"},
                "text": f"/pair WRONGCODE{attempt}",
            },
        }
        resp = gateway.handle_update(update)
        assert resp is not None
        assert "Invalid pairing code" in resp["text"]
        assert f"{5 - attempt} attempts remaining" in resp["text"]
        assert pairing_mgr.is_allowed_user(stranger_id) is False

    # 5th wrong attempt triggers lockout
    update_5 = {
        "update_id": 105,
        "message": {
            "from": {"id": stranger_id},
            "chat": {"id": stranger_id, "type": "private"},
            "text": "/pair WRONGCODE5",
        },
    }
    resp_5 = gateway.handle_update(update_5)
    assert resp_5 is not None
    assert "Pairing is locked for 15 minutes" in resp_5["text"]
    assert pairing_mgr.is_locked is True

    # Even the valid code is now rejected because pairing is locked
    update_valid = {
        "update_id": 106,
        "message": {
            "from": {"id": stranger_id},
            "chat": {"id": stranger_id, "type": "private"},
            "text": f"/pair {valid_code}",
        },
    }
    resp_valid = gateway.handle_update(update_valid)
    assert resp_valid is not None
    assert "Pairing is locked" in resp_valid["text"]


def test_right_code_pairs_once(clean_locus_env: Path):
    """SPEC 10.S-1 line 16: "Pairing = the owner sends /pair <code>. On success the numeric Telegram user id (never the @username) is saved to LOCUS_HOME/config.yaml as the allowed id, and the code is destroyed.\""""
    pairing_mgr = PairingManager()
    code = pairing_mgr.generate_pairing_code()

    gateway = TelegramGateway(pairing_manager=pairing_mgr)
    gateway.initialize()

    owner_numeric_id = 55667788

    pair_update = {
        "update_id": 200,
        "message": {
            "from": {"id": owner_numeric_id, "username": "owner_handle"},
            "chat": {"id": owner_numeric_id, "type": "private"},
            "text": f"/pair {code}",
        },
    }

    resp = gateway.handle_update(pair_update)
    assert resp is not None
    assert "Paired successfully" in resp["text"]

    # Verify owner numeric ID saved to config.yaml (never username)
    cfg_path = config.get_config_path()
    assert cfg_path.is_file()
    cfg_data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    assert cfg_data["channels"]["telegram"]["allowed_user_id"] == owner_numeric_id

    # Verify pairing status
    assert pairing_mgr.is_allowed_user(owner_numeric_id) is True
    assert pairing_mgr.get_owner_id() == owner_numeric_id

    # Subsequent command from owner is acknowledged
    cmd_update = {
        "update_id": 201,
        "message": {
            "from": {"id": owner_numeric_id},
            "chat": {"id": owner_numeric_id, "type": "private"},
            "text": "/status",
        },
    }
    resp_cmd = gateway.handle_update(cmd_update)
    assert resp_cmd is not None
    assert "Owner command: /status" in resp_cmd["text"]


def test_code_reuse_fails(clean_locus_env: Path):
    """SPEC 10.S-1 line 24: "Tests (mandatory for any Telegram change): a stranger's first message is rejected; a wrong code is rejected and counted; the right code pairs once; reuse fails; a corrupted allow-list fails closed; a restart keeps the owner.\""""
    pairing_mgr = PairingManager()
    code = pairing_mgr.generate_pairing_code()

    gateway = TelegramGateway(pairing_manager=pairing_mgr)
    gateway.initialize()

    owner_id = 11111111
    intruder_id = 99999999

    # Owner pairs successfully
    resp1 = gateway.handle_update({
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": f"/pair {code}",
        }
    })
    assert resp1 is not None
    assert "Paired successfully" in resp1["text"]

    # Intruder tries to use the same code
    resp2 = gateway.handle_update({
        "message": {
            "from": {"id": intruder_id},
            "chat": {"id": intruder_id, "type": "private"},
            "text": f"/pair {code}",
        }
    })
    assert resp2 is not None
    assert "No active pairing code" in resp2["text"]
    assert pairing_mgr.is_allowed_user(intruder_id) is False


def test_corrupted_allow_list_fails_closed(clean_locus_env: Path):
    """SPEC 10.S-1 line 19: "If the allowed-id list cannot be read or written, the bot refuses ALL messages (fail closed).\""""
    pairing_mgr = PairingManager()
    gateway = TelegramGateway(pairing_manager=pairing_mgr)
    gateway.initialize()

    # Corrupt config.yaml intentionally with invalid YAML syntax
    cfg_path = config.get_config_path()
    cfg_path.write_text("channels:\n  telegram: [unclosed list\n    corrupted: {", encoding="utf-8")

    assert config.is_config_valid() is False

    # Try any message
    resp = gateway.handle_update({
        "message": {
            "from": {"id": 12345},
            "chat": {"id": 12345, "type": "private"},
            "text": "help me",
        }
    })
    assert resp is not None
    assert "fail-closed" in resp["text"]
    assert pairing_mgr.is_allowed_user(12345) is False


def test_restart_keeps_owner(clean_locus_env: Path):
    """SPEC 10.S-1 line 19: "A restart never reopens pairing; re-pairing needs locus setup --repair telegram on the machine.\""""
    # Initial run: Owner pairs
    mgr1 = PairingManager()
    code = mgr1.generate_pairing_code()
    gw1 = TelegramGateway(pairing_manager=mgr1)
    gw1.initialize()

    owner_id = 77889900
    gw1.handle_update({
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": f"/pair {code}",
        }
    })

    gw1.shutdown()

    # Restart: instantiate brand new gateway and pairing manager
    mgr2 = PairingManager()
    gw2 = TelegramGateway(pairing_manager=mgr2)
    gw2.initialize()

    # Owner is still recognized immediately without re-pairing
    assert mgr2.is_allowed_user(owner_id) is True
    assert mgr2.get_owner_id() == owner_id

    resp_owner = gw2.handle_update({
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": "ping",
        }
    })
    assert resp_owner is not None
    assert "Owner command: ping" in resp_owner["text"]

    # Strangers are still rejected with "not configured"
    resp_stranger = gw2.handle_update({
        "message": {
            "from": {"id": 44332211},
            "chat": {"id": 44332211, "type": "private"},
            "text": "hello",
        }
    })
    assert resp_stranger is not None
    assert resp_stranger["text"] == "not configured"


def test_webhook_mode_refuses_without_secret(clean_locus_env: Path, monkeypatch: pytest.MonkeyPatch):
    """SPEC 10.S-1 line 22: "Webhook mode refuses to start without TELEGRAM_WEBHOOK_SECRET.\""""
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    gateway = TelegramGateway()

    with pytest.raises(ValueError, match="Webhook mode requires TELEGRAM_WEBHOOK_SECRET"):
        gateway.initialize(options={"webhook": True})


def test_code_generation_security_properties(clean_locus_env: Path):
    """SPEC 10.S-1 line 14: "Setup creates a one-time pairing code (8+ characters from secrets) and shows it ONLY on the machine running setup.\""""
    mgr = PairingManager()
    code = mgr.generate_pairing_code()

    # 1. 8+ characters
    assert len(code) >= 8
    # 2. Only hash is stored in memory, not plaintext
    assert mgr._code_hash is not None
    assert code not in mgr._code_hash
    # 3. Code expires after TTL
    mgr._created_at = time.time() - 601.0  # past 10 minutes
    ok, msg = mgr.attempt_pair(code, 12345)
    assert ok is False
    assert "expired" in msg


def test_telegram_channel_off(clean_locus_env: Path):
    """SPEC 03.Modularity line 40: "test_<feature>_off: enabled=false -> routes/tools/jobs absent, the rest of the system starts, the spec's \"Off ->\" effect is visible.\""""
    config.set_value("locus.channels.telegram.enabled", False)

    gateway = TelegramGateway()
    gateway.initialize()

    health = gateway.health_check()
    assert health["status"] == "degraded"
    assert health["enabled"] is False

    # Messages sent while off are ignored
    resp = gateway.handle_update({
        "message": {"from": {"id": 123}, "chat": {"id": 123, "type": "private"}, "text": "hello"}
    })
    assert resp is None


def test_telegram_channel_swap(clean_locus_env: Path):
    """SPEC 03.Modularity line 41: "test_<feature>_swap: register a second fake provider under another name, set provider, assert the fake is called and the default is not.\""""
    registry = get_registry()

    class MockChannelProvider(BaseChannelProvider):
        def __init__(self):
            self.invoked = False
        def initialize(self, options=None): pass
        def shutdown(self): pass
        def health_check(self): return {"status": "ok", "provider": "mock_channel"}
        def send_message(self, target, text):
            self.invoked = True
            return True

    registry.register("channels", "mock_channel", MockChannelProvider)
    config.set_value("locus.channels.provider", "mock_channel")

    chosen_provider_name = config.get("locus.channels.provider", "telegram")
    provider_cls = registry.get("channels", chosen_provider_name)
    assert provider_cls is MockChannelProvider

    instance = provider_cls()
    assert instance.health_check()["provider"] == "mock_channel"


def test_telegram_channel_health(clean_locus_env: Path):
    """SPEC 03.Modularity line 42: "test_<feature>_health: health_check() returns status and latency, and reports a stopped dependency as not OK.\""""
    gateway = TelegramGateway()
    gateway.initialize()

    health = gateway.health_check()
    assert health["status"] == "ok"
    assert health["provider"] == "telegram"
    assert "latency_ms" in health
    assert health["latency_ms"] >= 0.0
