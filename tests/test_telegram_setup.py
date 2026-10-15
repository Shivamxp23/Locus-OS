"""tests/test_telegram_setup.py - Unit tests for Telegram setup and secret-reference flow.

Tests:
- R6, S-1: Secure pairing code generation (6-digit, 10-minute validity)
- Allowed user ID persistence to LOCUS_HOME/allowed_users.json and config.yaml
- Re-run safety: already paired detection
- Stranger rejection and fail-closed security
- R4, Spec section 18: Secret-reference flow
  - Opaque secret references (secret://...)
  - 5-minute timeout on pending references
  - Single-use consumption on persist
  - 15-minute cleanup of stale references
  - Secret persistence into LOCUS_HOME/.env (mode 0600)
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from locus_cli.setup import load_secret_env
from locus_cli.telegram_setup import (
    SecretReferenceManager,
    TelegramSetupWizard,
    load_allowed_users,
    run_telegram_setup,
    save_allowed_users,
)
from sidecar.telegram_pairing import (
    TelegramPairingManager,
    UNCONFIGURED_MESSAGE,
)


@pytest.fixture
def temp_locus_home(tmp_path: Path) -> Path:
    home = tmp_path / ".locus"
    home.mkdir(parents=True, exist_ok=True)
    return home


def test_allowed_users_persistence(temp_locus_home: Path):
    """Test saving and loading allowed users from allowed_users.json."""
    users_file = temp_locus_home / "allowed_users.json"
    assert not users_file.is_file()
    assert load_allowed_users(temp_locus_home) == []

    # Save allowed user ID
    save_allowed_users(temp_locus_home, [123456789])
    assert users_file.is_file()

    loaded = load_allowed_users(temp_locus_home)
    assert loaded == [123456789]

    # Verify JSON structure
    raw = json.loads(users_file.read_text(encoding="utf-8"))
    assert 123456789 in raw["allowed_user_ids"]

    # Support bare list format as well
    users_file.write_text(json.dumps([987654321]), encoding="utf-8")
    assert load_allowed_users(temp_locus_home) == [987654321]

    # Corrupted format fails closed
    users_file.write_text("{corrupt-json", encoding="utf-8")
    assert load_allowed_users(temp_locus_home) == []


def test_secret_reference_lifecycle():
    """Test opaque reference creation, fulfillment, and single-use consumption."""
    mgr = SecretReferenceManager(ttl_seconds=300.0)
    t0 = 1000.0

    # 1. Create opaque secret reference
    ref = mgr.create_secret_ref("ANTHROPIC_API_KEY", description="Test Key", now=t0)
    assert ref.startswith("secret://")
    assert len(ref) > 16

    meta = mgr.get_ref_metadata(ref)
    assert meta is not None
    assert meta[0] == "ANTHROPIC_API_KEY"
    assert meta[2] is False  # unfulfilled

    # Unfulfilled ref cannot be resolved or consumed
    assert mgr.resolve_secret_ref(ref, now=t0 + 10) is None
    assert mgr.consume_secret_ref(ref, now=t0 + 10) is None

    # 2. Fulfill ref
    ok = mgr.fulfill_secret_ref(ref, "sk-ant-test-secret-value", now=t0 + 50)
    assert ok is True

    # Cannot fulfill again
    assert mgr.fulfill_secret_ref(ref, "different-value", now=t0 + 60) is False

    # 3. Resolve ref
    resolved = mgr.resolve_secret_ref(ref, now=t0 + 70)
    assert resolved == "sk-ant-test-secret-value"

    # 4. Consume ref (single use on persist)
    consumed = mgr.consume_secret_ref(ref, now=t0 + 80)
    assert consumed == "sk-ant-test-secret-value"

    # Second consumption fails (already consumed and purged from memory)
    assert mgr.consume_secret_ref(ref, now=t0 + 85) is None
    assert mgr.resolve_secret_ref(ref, now=t0 + 85) is None


def test_secret_reference_expiration():
    """Test 5-minute timeout on pending references (R4)."""
    mgr = SecretReferenceManager(ttl_seconds=300.0)
    t0 = 2000.0

    ref = mgr.create_secret_ref("OPENAI_API_KEY", now=t0)

    # Fulfilling after 301 seconds fails due to expiration
    ok = mgr.fulfill_secret_ref(ref, "sk-test", now=t0 + 301.0)
    assert ok is False
    assert mgr.resolve_secret_ref(ref, now=t0 + 301.0) is None


def test_secret_reference_cleanup():
    """Test 15-minute cleanup of expired / stale references."""
    mgr = SecretReferenceManager(ttl_seconds=300.0, cleanup_age_seconds=900.0)
    t0 = 5000.0

    ref1 = mgr.create_secret_ref("KEY_1", now=t0)
    ref2 = mgr.create_secret_ref("KEY_2", now=t0 + 400.0)

    # Before 15 minutes, cleanup removes only expired refs (ref1 is past 300s TTL)
    purged = mgr.cleanup_expired(now=t0 + 350.0)
    assert purged == 1
    assert mgr.get_ref_metadata(ref1) is None
    assert mgr.get_ref_metadata(ref2) is not None

    # After 15 minutes (901s), everything is purged
    purged2 = mgr.cleanup_expired(now=t0 + 950.0)
    assert purged2 == 1
    assert mgr.get_ref_metadata(ref2) is None


def test_telegram_wizard_pairing_flow(temp_locus_home: Path):
    """
    Sprint Review Demo:
    Start telegram setup wizard; receive a 6-digit one-time code valid for 10 minutes.
    Send code from test bot: pairing succeeds and owner id is stored.
    Re-running with existing pairing reports already paired.
    """
    wizard = TelegramSetupWizard(locus_home=temp_locus_home)
    assert not wizard.is_already_paired()

    t0 = 10000.0
    # Step 1: Start wizard, receive 6-digit one-time code
    code = wizard.start_pairing_session(code_length=6, now=t0)
    assert len(code) == 6
    assert code.isdigit()

    # Stranger messages before pairing are rejected
    stranger_id = 999111
    auth, resp = wizard.handle_inbound_telegram_message(stranger_id, "Hello", now=t0 + 5)
    assert not auth
    assert resp == UNCONFIGURED_MESSAGE

    # Step 2: Owner sends /pair <code> from test bot
    owner_id = 777888999
    success, msg = wizard.handle_inbound_telegram_message(
        owner_id, f"/pair {code}", now=t0 + 30
    )
    assert success is True
    assert "Pairing successful" in msg

    # Verify owner id is stored in allowed_users.json and config.yaml
    assert wizard.is_already_paired()
    assert wizard.get_paired_owner_ids() == [owner_id]
    assert load_allowed_users(temp_locus_home) == [owner_id]

    # Re-pairing attempt is rejected (single use)
    success2, msg2 = wizard.handle_inbound_telegram_message(
        owner_id, f"/pair {code}", now=t0 + 40
    )
    assert "Already paired" in msg2 or "Pairing is closed" in msg2

    # Step 3: Re-running with existing pairing reports already paired (R8)
    res = run_telegram_setup(temp_locus_home)
    assert res["status"] == "already_paired"
    assert owner_id in res["allowed_users"]


def test_telegram_setup_secret_reference_flow(temp_locus_home: Path):
    """Test owner transmitting secrets via /setup and /secret (R4)."""
    wizard = TelegramSetupWizard(locus_home=temp_locus_home)
    t0 = 20000.0

    # Pre-pair owner
    save_allowed_users(temp_locus_home, [555444333])
    owner_id = 555444333
    stranger_id = 111000999

    # 1. Stranger attempting /setup is rejected
    auth, resp = wizard.handle_inbound_telegram_message(
        stranger_id, "/setup ANTHROPIC_API_KEY", now=t0
    )
    assert not auth
    assert resp == UNCONFIGURED_MESSAGE

    # 2. Owner sends /setup ANTHROPIC_API_KEY
    auth, resp = wizard.handle_inbound_telegram_message(
        owner_id, "/setup ANTHROPIC_API_KEY", now=t0
    )
    assert auth is True
    assert "secret://" in resp

    # Extract opaque reference token
    lines = resp.splitlines()
    ref_line = [line for line in lines if "secret://" in line][0]
    ref = [part for part in ref_line.split() if part.startswith("secret://")][0]

    # 3. Owner submits secret using reference: /secret <ref> <value>
    test_key_val = "sk-ant-api03-live-simulation-token"
    auth2, resp2 = wizard.handle_inbound_telegram_message(
        owner_id, f"/secret {ref} {test_key_val}", now=t0 + 45
    )
    assert auth2 is True
    assert "persisted successfully" in resp2
    assert test_key_val not in resp2  # Never echo the secret!

    # 4. Check secret was persisted to LOCUS_HOME/.env with mode 0600
    secrets_env = load_secret_env(temp_locus_home)
    assert secrets_env.get("ANTHROPIC_API_KEY") == test_key_val

    # 5. Subsequent reuse of consumed secret ref fails
    auth3, resp3 = wizard.handle_inbound_telegram_message(
        owner_id, f"/secret {ref} reuse-attempt", now=t0 + 60
    )
    assert not auth3
    assert "Invalid or expired" in resp3


def test_cli_run_telegram_setup(temp_locus_home: Path):
    """Test CLI runner output messages for unpaired and paired runs."""
    messages: list[str] = []

    def mock_print(msg: str):
        messages.append(msg)

    # 1. First run: generates code
    res1 = run_telegram_setup(temp_locus_home, print_fn=mock_print)
    assert res1["status"] == "pairing_started"
    assert "Your Locus pairing code is:" in messages[1]

    # Pair the bot
    wizard: TelegramSetupWizard = res1["wizard"]
    wizard.verify_pairing_attempt(123456, res1["pairing_code"])

    # 2. Second run: reports already paired
    messages.clear()
    res2 = run_telegram_setup(temp_locus_home, print_fn=mock_print)
    assert res2["status"] == "already_paired"
    assert any("already paired" in m for m in messages)
