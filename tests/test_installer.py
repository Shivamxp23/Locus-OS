"""tests/test_installer.py - Unit and integration tests for Locus installer.

Tests the thin launchers, non-interactive installation (--yes, --answers),
directory and vault bootstrapping, and re-run safety (R1, R8, R9, R10).
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Generator

import pytest
import yaml

from locus_cli.main import (
    CANONICAL_VAULT_DIRS,
    init_locus_home,
    load_answers,
    run_installer,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def temp_locus_env() -> Generator[tuple[Path, Path], None, None]:
    """Provide isolated temporary directories for LOCUS_HOME and vault root."""
    with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as vault_dir:
        yield Path(home_dir), Path(vault_dir)


def test_installer_launchers_exist_and_thin() -> None:
    """Verify install.ps1 and install.sh exist, are under 50 lines, and call locus_cli.main (R1, R10)."""
    ps1_path = REPO_ROOT / "install.ps1"
    sh_path = REPO_ROOT / "install.sh"
    bat_path = REPO_ROOT / "install.bat"
    locus_bat = REPO_ROOT / "locus.bat"
    locus_cmd = REPO_ROOT / "locus.cmd"

    assert ps1_path.is_file(), "install.ps1 must exist at repository root"
    assert sh_path.is_file(), "install.sh must exist at repository root"
    assert bat_path.is_file(), "install.bat must exist at repository root"
    assert locus_bat.is_file(), "locus.bat must exist at repository root"
    assert locus_cmd.is_file(), "locus.cmd must exist at repository root"

    ps1_lines = ps1_path.read_text(encoding="utf-8").splitlines()
    sh_lines = sh_path.read_text(encoding="utf-8").splitlines()

    assert len(ps1_lines) < 50, f"install.ps1 must be under 50 lines, found {len(ps1_lines)}"
    assert len(sh_lines) < 50, f"install.sh must be under 50 lines, found {len(sh_lines)}"

    assert any("locus_cli.main" in line for line in ps1_lines), "install.ps1 must invoke locus_cli.main"
    assert any("locus_cli.main" in line for line in sh_lines), "install.sh must invoke locus_cli.main"


def test_init_locus_home_creates_canonical_structure(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify init_locus_home creates LOCUS_HOME, jobs/, config.yaml, .env, and all 8 canonical vault folders."""
    home_dir, vault_dir = temp_locus_env

    result = init_locus_home(
        locus_home=home_dir,
        vault_root=vault_dir,
        mode="local",
    )

    assert result["config_created"] is True
    assert result["env_created"] is True

    # Check directories
    assert (home_dir / "jobs").is_dir(), "jobs/ folder must be created in LOCUS_HOME"
    assert (home_dir / "config.yaml").is_file(), "config.yaml must be created in LOCUS_HOME"
    assert (home_dir / ".env").is_file(), ".env must be created in LOCUS_HOME"

    # Check 8 canonical vault folders
    for d in CANONICAL_VAULT_DIRS:
        assert (vault_dir / d).is_dir(), f"Canonical vault folder {d} must be created"

    # Verify config content
    config_data = yaml.safe_load((home_dir / "config.yaml").read_text(encoding="utf-8"))
    assert config_data["locus"]["mode"] == "local"
    assert config_data["locus"]["scheduler"]["enabled"] is True


def test_installer_re_run_is_safe_and_preserves_config(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify installer re-run leaves existing config, .env, and vault files untouched (R8)."""
    home_dir, vault_dir = temp_locus_env

    # First run
    init_locus_home(home_dir, vault_dir, mode="local")
    config_file = home_dir / "config.yaml"

    # Modify config to simulate user modifications
    custom_config = {
        "locus": {
            "version": "0.1.0",
            "mode": "vm",
            "custom_user_key": "do_not_erase",
        }
    }
    config_file.write_text(yaml.dump(custom_config), encoding="utf-8")

    # Add a note in vault
    test_note = vault_dir / "01-Projects" / "Project_Alpha.md"
    test_note.write_text("# Project Alpha Note", encoding="utf-8")

    # Second run
    result2 = init_locus_home(home_dir, vault_dir, mode="hybrid")
    assert result2["config_created"] is False, "Second run must not create or overwrite config"
    assert result2["env_created"] is False, "Second run must not create or overwrite .env"

    # Assert user modifications were preserved
    loaded_config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert loaded_config["locus"]["mode"] == "vm"
    assert loaded_config["locus"]["custom_user_key"] == "do_not_erase"
    assert test_note.is_file(), "Existing vault files must be preserved"


def test_load_answers_json_and_yaml(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify loading answers from JSON and YAML files (R9)."""
    home_dir, _ = temp_locus_env

    # JSON answers
    json_path = home_dir / "answers.json"
    json_data = {"mode": "vm", "timezone": "UTC"}
    json_path.write_text(json.dumps(json_data), encoding="utf-8")
    loaded_json = load_answers(json_path)
    assert loaded_json == json_data

    # YAML answers
    yaml_path = home_dir / "answers.yaml"
    yaml_data = {"mode": "hybrid", "timezone": "Europe/London"}
    yaml_path.write_text(yaml.dump(yaml_data), encoding="utf-8")
    loaded_yaml = load_answers(yaml_path)
    assert loaded_yaml == yaml_data


def test_run_installer_cli_non_interactive(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify running the installer CLI with --yes and custom paths completes with exit code 0 (R9)."""
    home_dir, vault_dir = temp_locus_env

    exit_code = run_installer([
        "--yes",
        "--locus-home", str(home_dir),
        "--vault-root", str(vault_dir),
        "--mode", "hybrid",
    ])

    assert exit_code == 0
    config_data = yaml.safe_load((home_dir / "config.yaml").read_text(encoding="utf-8"))
    assert config_data["locus"]["mode"] == "hybrid"
    assert (home_dir / "jobs").is_dir()
    for d in CANONICAL_VAULT_DIRS:
        assert (vault_dir / d).is_dir()


def test_run_installer_with_answers_file(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify running the installer CLI with --answers flag overrides defaults."""
    home_dir, vault_dir = temp_locus_env

    answers_file = home_dir / "custom_answers.yaml"
    answers_content = {
        "mode": "vm",
        "timezone": "America/New_York",
        "vault_path": str(vault_dir).replace("\\", "/"),
    }
    answers_file.write_text(yaml.dump(answers_content), encoding="utf-8")

    exit_code = run_installer([
        "--yes",
        "--answers", str(answers_file),
        "--locus-home", str(home_dir),
    ])

    assert exit_code == 0
    config_data = yaml.safe_load((home_dir / "config.yaml").read_text(encoding="utf-8"))
    assert config_data["locus"]["mode"] == "vm"
    assert config_data["locus"]["timezone"] == "America/New_York"
