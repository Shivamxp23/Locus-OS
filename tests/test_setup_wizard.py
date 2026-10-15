"""tests/test_setup_wizard.py - Unit tests for locus_cli.setup wizard.

Tests topology mode configuration (R2), key collection and live validation (R3),
secret storage in .env (mode 0600) with zero secrets in config.yaml (S-0),
and safe re-run preservation (R8).
"""

from __future__ import annotations

from pathlib import Path
import stat
import sys
import tempfile
from typing import Generator

import pytest
import yaml

from locus_cli.setup import (
    load_secret_env,
    run_setup_wizard,
    save_secret_env,
    update_config_mode,
    validate_key,
)


@pytest.fixture
def temp_locus_home() -> Generator[Path, None, None]:
    """Provide isolated temporary directory for LOCUS_HOME."""
    with tempfile.TemporaryDirectory() as home_dir:
        yield Path(home_dir)


def test_validate_key_with_custom_validator() -> None:
    """Verify live key validation logic using mock validator."""
    def mock_validator(provider: str, key: str) -> tuple[bool, str]:
        if key.startswith("sk-valid"):
            return True, f"{provider} valid"
        return False, "invalid key"

    # Empty key
    ok, msg = validate_key("anthropic", "  ")
    assert not ok
    assert "empty" in msg

    # Valid key
    ok, msg = validate_key("anthropic", "sk-valid-12345", custom_validator=mock_validator)
    assert ok
    assert "valid" in msg

    # Invalid key
    ok, msg = validate_key("openai", "bad-key", custom_validator=mock_validator)
    assert not ok
    assert "invalid" in msg


def test_save_and_load_secret_env(temp_locus_home: Path) -> None:
    """Verify secrets are saved to .env with 0600 permissions and round-trip cleanly (S-0)."""
    secrets = {
        "ANTHROPIC_API_KEY": "sk-ant-test123",
        "OPENAI_API_KEY": "sk-proj-test456",
        "COMPLEX_VAL": 'contains spaces and "quotes"',
    }

    env_path = save_secret_env(temp_locus_home, secrets)
    assert env_path.is_file()

    # Check permissions on POSIX
    if sys.platform != "win32":
        mode = stat.S_IMODE(env_path.stat().st_mode)
        assert mode == 0o600, f"Expected 0600 permissions, got {oct(mode)}"

    # Check round-trip load
    loaded = load_secret_env(temp_locus_home)
    assert loaded["ANTHROPIC_API_KEY"] == "sk-ant-test123"
    assert loaded["OPENAI_API_KEY"] == "sk-proj-test456"
    assert loaded["COMPLEX_VAL"] == 'contains spaces and "quotes"'

    # Verify updating one key preserves others
    save_secret_env(temp_locus_home, {"TELEGRAM_BOT_TOKEN": "123456:ABC-DEF"})
    updated = load_secret_env(temp_locus_home)
    assert updated["ANTHROPIC_API_KEY"] == "sk-ant-test123"
    assert updated["TELEGRAM_BOT_TOKEN"] == "123456:ABC-DEF"


def test_update_config_mode_preserves_existing_keys(temp_locus_home: Path) -> None:
    """Verify updating topology mode in config.yaml preserves all existing configuration (R2, R8)."""
    config_file = temp_locus_home / "config.yaml"
    initial_config = {
        "locus": {
            "version": "0.1.0",
            "mode": "local",
            "timezone": "Asia/Kolkata",
            "custom_setting": 42,
        }
    }
    config_file.write_text(yaml.dump(initial_config), encoding="utf-8")

    update_config_mode(config_file, "hybrid")

    loaded = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert loaded["locus"]["mode"] == "hybrid"
    assert loaded["locus"]["version"] == "0.1.0"
    assert loaded["locus"]["custom_setting"] == 42


def test_setup_wizard_key_collection_stores_in_env_not_config(temp_locus_home: Path) -> None:
    """Verify setup wizard saves API keys strictly into .env and NEVER into config.yaml (R3, S-0)."""
    inputs = ["local"]  # mode prompt response
    passwords = [
        "sk-valid-anthropic",  # Anthropic key
        "sk-valid-openai",     # OpenAI key
        "",                    # Google (skipped)
        "",                    # Telegram (skipped)
    ]

    def mock_input(prompt: str) -> str:
        return inputs.pop(0) if inputs else ""

    def mock_password(prompt: str) -> str:
        return passwords.pop(0) if passwords else ""

    def mock_validator(provider: str, key: str) -> tuple[bool, str]:
        return (True, f"{provider} ok") if key.startswith("sk-valid") else (False, "bad")

    res = run_setup_wizard(
        locus_home=temp_locus_home,
        input_fn=mock_input,
        prompt_password_fn=mock_password,
        custom_validator=mock_validator,
    )

    assert res["mode"] == "local"

    # Assert .env contains the secrets
    env_secrets = load_secret_env(temp_locus_home)
    assert env_secrets.get("ANTHROPIC_API_KEY") == "sk-valid-anthropic"
    assert env_secrets.get("OPENAI_API_KEY") == "sk-valid-openai"

    # Assert config.yaml contains NO secrets
    config_text = (temp_locus_home / "config.yaml").read_text(encoding="utf-8")
    assert "sk-valid-anthropic" not in config_text
    assert "sk-valid-openai" not in config_text
    assert "API_KEY" not in config_text


def test_setup_wizard_re_run_safety(temp_locus_home: Path) -> None:
    """Verify re-running setup wizard safely keeps existing values on Enter (R8)."""
    # Pre-populate .env and config.yaml
    save_secret_env(temp_locus_home, {"ANTHROPIC_API_KEY": "sk-existing-secret"})
    config_file = temp_locus_home / "config.yaml"
    config_file.write_text("locus:\n  mode: vm\n  timezone: UTC\n", encoding="utf-8")

    # Simulate user pressing Enter on all prompts (accepting existing values)
    def mock_input(prompt: str) -> str:
        return ""

    def mock_password(prompt: str) -> str:
        return ""

    res = run_setup_wizard(
        locus_home=temp_locus_home,
        input_fn=mock_input,
        prompt_password_fn=mock_password,
    )

    # Mode remains "vm"
    assert res["mode"] == "vm"
    loaded_config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert loaded_config["locus"]["mode"] == "vm"

    # Secret remains unchanged
    env_secrets = load_secret_env(temp_locus_home)
    assert env_secrets.get("ANTHROPIC_API_KEY") == "sk-existing-secret"


def test_setup_wizard_non_interactive_with_answers(temp_locus_home: Path) -> None:
    """Verify non-interactive setup with answers dictionary (R9)."""
    answers = {
        "mode": "hybrid",
        "ANTHROPIC_API_KEY": "sk-valid-answers-key",
    }

    def mock_validator(provider: str, key: str) -> tuple[bool, str]:
        return True, "verified"

    res = run_setup_wizard(
        locus_home=temp_locus_home,
        non_interactive=True,
        answers=answers,
        custom_validator=mock_validator,
    )

    assert res["mode"] == "hybrid"
    env_secrets = load_secret_env(temp_locus_home)
    assert env_secrets.get("ANTHROPIC_API_KEY") == "sk-valid-answers-key"
