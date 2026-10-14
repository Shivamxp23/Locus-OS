"""
tests/test_telegram_pairing.py - Security tests for S-1 Telegram access: no first-touch pairing.

Covers all six mandatory tests from docs/agent/10-security.md S-1:
1. Stranger's first message is rejected
2. Wrong code is rejected and counted (5 wrong attempts lock pairing for 15 minutes)
3. Right code pairs once
4. Reuse of code fails
5. Corrupted allow-list fails closed
6. Restart keeps owner
Plus webhook fail-closed and code expiration tests.
"""

import time
from pathlib import Path
import pytest

from sidecar.telegram_pairing import (
    TelegramPairingManager,
    generate_pairing_code,
    hash_pairing_code,
    validate_webhook_config,
    UNCONFIGURED_MESSAGE,
    PairingStorageError,
)


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Fixture providing an isolated temporary config path."""
    return tmp_path / "config.yaml"


@pytest.fixture
def manager(temp_config: Path) -> TelegramPairingManager:
    """Fixture providing a fresh TelegramPairingManager."""
    return TelegramPairingManager(config_path=temp_config)


def test_code_generation_properties():
    """Verify pairing code is at least 8 chars and uses secure random generation."""
    code1 = generate_pairing_code(10)
    code2 = generate_pairing_code(10)
    assert len(code1) == 10
    assert len(code2) == 10
    assert code1 != code2
    # Reject codes shorter than 8 chars
    with pytest.raises(ValueError):
        generate_pairing_code(7)


def test_stranger_first_message_rejected(manager: TelegramPairingManager):
    """
    Test 1 (S-1): A stranger's first message is rejected.
    Nobody becomes owner simply by messaging the bot first.
    """
    stranger_id = 987654321
    # Plain text message
    authorized, response = manager.handle_inbound_message(stranger_id, "Hello bot")
    assert not authorized
    assert response == UNCONFIGURED_MESSAGE

    # Command like /start
    authorized, response = manager.handle_inbound_message(stranger_id, "/start")
    assert not authorized
    assert response == UNCONFIGURED_MESSAGE

    # Still unconfigured and unallowed
    assert not manager.is_configured()
    assert not manager.is_allowed(stranger_id)


def test_wrong_code_rejected_and_counted(manager: TelegramPairingManager):
    """
    Test 2 (S-1): A wrong code is rejected and counted.
    5 wrong attempts lock pairing for 15 minutes.
    """
    code = manager.start_pairing()
    stranger_id = 111222333

    # 4 wrong attempts
    for attempt in range(1, 5):
        authorized, response = manager.handle_inbound_message(stranger_id, f"/pair WRONG{attempt}")
        assert not authorized
        assert "Invalid pairing code" in response
        assert manager.wrong_attempts == attempt
        assert not manager.is_locked()

    # 5th wrong attempt triggers lockout
    authorized, response = manager.handle_inbound_message(stranger_id, "/pair WRONG5")
    assert not authorized
    assert "Too many failed attempts" in response
    assert manager.is_locked()

    # 6th attempt even with correct code is refused during lockout
    authorized, response = manager.handle_inbound_message(stranger_id, f"/pair {code}")
    assert not authorized
    assert "locked" in response.lower()
    assert not manager.is_allowed(stranger_id)


def test_right_code_pairs_once(manager: TelegramPairingManager):
    """
    Test 3 (S-1): The right code pairs once and destroys the code.
    Owner numeric ID is saved to config.yaml.
    """
    code = manager.start_pairing()
    owner_id = 555666777

    authorized, response = manager.handle_inbound_message(owner_id, f"/pair {code}")
    assert authorized
    assert "Paired successfully" in response
    assert manager.is_allowed(owner_id)
    assert manager.is_configured()

    # Code is destroyed immediately
    assert not manager.is_code_active()

    # Subsequent normal messages from owner are authorized
    auth, resp = manager.handle_inbound_message(owner_id, "What is my task?")
    assert auth
    assert resp == "AUTHORIZED"


def test_reuse_of_code_fails(manager: TelegramPairingManager):
    """
    Test 4 (S-1): Reuse of the pairing code fails.
    A second person cannot use the same code or become a second owner.
    """
    code = manager.start_pairing()
    owner_id = 555666777
    intruder_id = 999888777

    # Owner pairs successfully
    authorized, _ = manager.handle_inbound_message(owner_id, f"/pair {code}")
    assert authorized

    # Intruder attempts to use the same code
    auth2, resp2 = manager.handle_inbound_message(intruder_id, f"/pair {code}")
    assert not auth2
    assert "Pairing is closed" in resp2 or resp2 == UNCONFIGURED_MESSAGE
    assert not manager.is_allowed(intruder_id)


def test_corrupted_allow_list_fails_closed(manager: TelegramPairingManager, temp_config: Path):
    """
    Test 5 (S-1): A corrupted allow-list fails closed.
    If config.yaml cannot be parsed or read, ALL messages are refused.
    """
    # First, pair an owner
    code = manager.start_pairing()
    owner_id = 123456789
    manager.handle_inbound_message(owner_id, f"/pair {code}")
    assert manager.is_allowed(owner_id)

    # Corrupt the config.yaml file
    temp_config.write_text("locus: [corrupted yaml invalid: {{{{", encoding="utf-8")

    # Manager fails closed
    assert not manager.is_allowed(owner_id)
    assert not manager.is_configured()
    with pytest.raises(PairingStorageError):
        manager.get_allowed_user_ids()

    # Inbound messages from anyone (including former owner) are refused
    auth, resp = manager.handle_inbound_message(owner_id, "Do something")
    assert not auth
    assert resp == UNCONFIGURED_MESSAGE


def test_restart_keeps_owner(temp_config: Path):
    """
    Test 6 (S-1): A restart keeps the owner.
    A new manager instance pointing at the same config recognizes the owner and rejects strangers.
    """
    owner_id = 42424242
    stranger_id = 84848484

    # Session 1: Pair owner
    manager1 = TelegramPairingManager(config_path=temp_config)
    code = manager1.start_pairing()
    auth, _ = manager1.handle_inbound_message(owner_id, f"/pair {code}")
    assert auth

    # Session 2: "Restart" with fresh manager instance
    manager2 = TelegramPairingManager(config_path=temp_config)
    assert manager2.is_configured()
    assert manager2.is_allowed(owner_id)
    assert not manager2.is_allowed(stranger_id)

    # Owner message authorized
    auth_owner, resp_owner = manager2.handle_inbound_message(owner_id, "Status report")
    assert auth_owner
    assert resp_owner == "AUTHORIZED"

    # Stranger message rejected
    auth_stranger, resp_stranger = manager2.handle_inbound_message(stranger_id, "Hey")
    assert not auth_stranger
    assert resp_stranger == UNCONFIGURED_MESSAGE


def test_webhook_mode_refuses_without_secret():
    """
    Webhook mode must fail closed if TELEGRAM_WEBHOOK_SECRET is missing.
    """
    # When webhook_url is unset, passes
    assert validate_webhook_config(None, None)
    assert validate_webhook_config("", "")

    # When webhook_url is set but secret is missing, raises ValueError
    with pytest.raises(ValueError, match="TELEGRAM_WEBHOOK_SECRET is required"):
        validate_webhook_config("https://example.com/webhook", "")

    with pytest.raises(ValueError, match="TELEGRAM_WEBHOOK_SECRET is required"):
        validate_webhook_config("https://example.com/webhook", None)

    # When secret is provided, passes
    assert validate_webhook_config("https://example.com/webhook", "valid_secret_key")


def test_code_expiry_after_10_minutes(manager: TelegramPairingManager):
    """
    Pairing code expires after 10 minutes (600s).
    """
    t0 = 1000000.0
    code = manager.start_pairing(now=t0)
    # At 9 minutes (540s), still active
    assert manager.is_code_active(now=t0 + 540.0)

    # At 11 minutes (660s), expired
    assert not manager.is_code_active(now=t0 + 660.0)

    # Attempt to pair with expired code
    auth, resp = manager.handle_pairing_attempt(12345, code, now=t0 + 660.0)
    assert not auth
    assert "expired" in resp.lower()


def test_non_direct_messages_ignored(manager: TelegramPairingManager):
    """
    Messages from group chats, forwards, and channels (is_direct=False) are ignored.
    """
    code = manager.start_pairing()
    auth, resp = manager.handle_inbound_message(12345, f"/pair {code}", is_direct=False)
    assert not auth
    assert resp == ""
