"""
SPEC §18 / R4, R6 / F-0083 / US-14: Telegram Setup and Secret-Reference Flow Unit Tests.
Tests:
- Installer wizard offers interactive Telegram bot setup triggering pairing code generation via sidecar/pairing.py (R6, S-1).
- Telegram gateway implements /setup command initiating the Section 18 secret-reference flow for late key entry (R4).
- Secret reference token expires in 5 minutes, is cleaned up after 15 minutes, and is consumed upon successful persistence.
- Messages containing secrets are deleted via Telegram API immediately after receipt, never logged or echoed.
- Unit tests with mock Telegram transport test /setup flow, secret reference generation, expiration, message deletion request, and config persistence.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import time
import pytest
import yaml

from locus_cli.install import prompt_telegram_pairing, run_install
from sidecar import config
from sidecar.telegram.gateway import TelegramGateway
from sidecar.telegram.pairing import PairingManager
from sidecar.telegram.secret_manager import SecretReference, SecretReferenceManager


@pytest.fixture
def clean_locus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated LOCUS_HOME for configuration testing."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    return locus_home


def test_installer_wizard_telegram_pairing_trigger(clean_locus_env: Path, monkeypatch: pytest.MonkeyPatch):
    """SPEC 05 line 20: "Telegram setup includes SECURE pairing (10-security.md S-1): a one-time code shown on the machine, entered in the bot, valid 10 minutes; the owner id is stored in LOCUS_HOME; nobody else is ever paired automatically.\""""
    # Test prompt_telegram_pairing helper with explicit answer
    triggered = prompt_telegram_pairing({"telegram_pair": True})
    assert triggered is True

    # Test interactive prompt answering 'y'
    monkeypatch.setattr("builtins.input", lambda _: "y")
    inter_triggered = prompt_telegram_pairing({})
    assert inter_triggered is True

    # Test run_install with telegram_pair in answers
    res = run_install(target_dir=clean_locus_env, answers={"telegram_pair": True}, non_interactive=True)
    assert res["status"] == "installed"
    assert res["telegram_pairing_triggered"] is True


def test_setup_command_initiates_secret_reference_flow(clean_locus_env: Path):
    """SPEC 18 line 16: "An LLM on the VM may be finished later from Telegram with /setup: the key travels through the secret-reference flow (spec section 18: opaque secret reference, 5-minute timeout, 15-minute cleanup, consumed on persist)...\""""
    pairing_mgr = PairingManager()
    sec_mgr = SecretReferenceManager()
    gateway = TelegramGateway(pairing_manager=pairing_mgr, secret_manager=sec_mgr)
    gateway.initialize()

    # Pair owner
    code = pairing_mgr.generate_pairing_code()
    owner_id = 998877
    gateway.handle_update({
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": f"/pair {code}",
        }
    })

    # Owner requests setup without provider
    resp_usage = gateway.handle_update({
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": "/setup",
        }
    })
    assert resp_usage is not None
    assert "Usage: /setup <provider>" in resp_usage["text"]

    # Owner requests setup for anthropic
    resp_setup = gateway.handle_update({
        "message": {
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": "/setup anthropic",
        }
    })
    assert resp_setup is not None
    assert "Secret reference issued for provider 'anthropic'" in resp_setup["text"]
    ref_token = resp_setup.get("ref_token")
    assert ref_token is not None
    assert len(ref_token) == 32  # 16 bytes hex

    # Verify secret reference exists in manager
    ref_obj = sec_mgr.get_reference(ref_token)
    assert ref_obj is not None
    assert ref_obj.provider == "anthropic"
    assert ref_obj.is_consumed is False


def test_secret_reference_token_expiration_and_cleanup(clean_locus_env: Path):
    """SPEC 18 line 17: "...opaque secret reference, 5-minute timeout, 15-minute cleanup, consumed on persist); the message that carried it is deleted; it is never echoed or logged.\""""
    sec_mgr = SecretReferenceManager()
    ref_id = sec_mgr.create_secret_reference("openai")
    t0 = time.time()

    # Before 5 minutes (e.g. 290s) -> not expired
    ref = sec_mgr.get_reference(ref_id)
    assert ref is not None
    assert ref.is_expired(now=t0 + 290.0) is False

    # After 5 minutes (e.g. 301s) -> expired
    assert ref.is_expired(now=t0 + 301.0) is True

    # Consuming after 5 minutes fails with timeout message
    # guard:allow-secret (test key)
    test_key = "sk-mock-key-12345678"
    ok, msg = sec_mgr.consume_secret_reference(
        ref_id,
        test_key,
        env_file=clean_locus_env / ".env",
        now=t0 + 301.0,
    )
    assert ok is False
    assert "expired" in msg.lower()
    assert ref.is_consumed is False

    # Cleanup before 15 minutes preserves reference
    assert sec_mgr.cleanup(now=t0 + 890.0) == 0
    assert sec_mgr.get_reference(ref_id) is not None

    # Cleanup after 15 minutes purges reference
    assert sec_mgr.cleanup(now=t0 + 901.0) == 1
    assert sec_mgr.get_reference(ref_id) is None


def test_secret_transmission_message_deleted_and_consumed_to_env(clean_locus_env: Path):
    """SPEC 18 line 17: "...consumed on persist); the message that carried it is deleted; it is never echoed or logged.\""""
    pairing_mgr = PairingManager()
    sec_mgr = SecretReferenceManager()
    gateway = TelegramGateway(pairing_manager=pairing_mgr, secret_manager=sec_mgr)
    gateway.initialize()

    # Track deleted message payloads via custom transport
    transport_calls: list[dict] = []
    gateway.set_transport(lambda payload: transport_calls.append(payload))

    # Pair owner
    code = pairing_mgr.generate_pairing_code()
    owner_id = 445566
    gateway.handle_update({
        "message": {
            "message_id": 10,
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": f"/pair {code}",
        }
    })

    # Initiate /setup google
    resp_setup = gateway.handle_update({
        "message": {
            "message_id": 11,
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": "/setup google",
        }
    })
    ref_token = resp_setup["ref_token"]

    # Send /secret with key
    # guard:allow-secret (test key)
    fake_secret = "AIzaSyFakeKeyForTesting12345"
    resp_secret = gateway.handle_update({
        "message": {
            "message_id": 12,
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": f"/secret {ref_token} {fake_secret}",
        }
    })

    # Assert deleteMessage was invoked immediately for message_id 12
    assert resp_secret["deleted_message_id"] == 12
    deleted = [d for d in gateway._deleted_messages if d.get("message_id") == 12]
    assert len(deleted) == 1
    assert deleted[0]["method"] == "deleteMessage"
    assert deleted[0]["chat_id"] == owner_id

    # Assert secret is NEVER echoed in response
    assert fake_secret not in resp_secret["text"]
    assert "saved securely" in resp_secret["text"]

    # Assert secret is persisted to LOCUS_HOME/.env
    env_file = clean_locus_env / ".env"
    assert env_file.is_file()
    env_text = env_file.read_text(encoding="utf-8")
    assert f"GEMINI_API_KEY={fake_secret}" in env_text

    # Assert secret reference is consumed (cannot be reused)
    ref_obj = sec_mgr.get_reference(ref_token)
    assert ref_obj.is_consumed is True

    # Attempt reuse
    resp_reuse = gateway.handle_update({
        "message": {
            "message_id": 13,
            "from": {"id": owner_id},
            "chat": {"id": owner_id, "type": "private"},
            "text": f"/secret {ref_token} other_key",
        }
    })
    assert "already been consumed" in resp_reuse["text"]


def test_unpaired_user_cannot_access_setup_or_secret(clean_locus_env: Path):
    """SPEC 10 line 18: "Until paired, the bot answers every message with one fixed line (\"not configured\") and executes nothing.\""""
    pairing_mgr = PairingManager()
    sec_mgr = SecretReferenceManager()
    gateway = TelegramGateway(pairing_manager=pairing_mgr, secret_manager=sec_mgr)
    gateway.initialize()

    stranger_id = 999999

    # Stranger attempts /setup
    resp_setup = gateway.handle_update({
        "message": {
            "message_id": 50,
            "from": {"id": stranger_id},
            "chat": {"id": stranger_id, "type": "private"},
            "text": "/setup anthropic",
        }
    })
    assert resp_setup["text"] == "not configured"
    assert len(sec_mgr._references) == 0

    # Stranger attempts /secret with fake token
    # guard:allow-secret (test key)
    resp_sec = gateway.handle_update({
        "message": {
            "message_id": 51,
            "from": {"id": stranger_id},
            "chat": {"id": stranger_id, "type": "private"},
            "text": "/secret faketoken fakekey",
        }
    })
    assert resp_sec["text"] == "not configured"
    # Even for stranger, secret message is wiped immediately for safety
    assert resp_sec["deleted_message_id"] == 51
    assert any(d.get("message_id") == 51 for d in gateway._deleted_messages)
