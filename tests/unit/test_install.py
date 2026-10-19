"""
SPEC §1.12 / R1, R9, R10 / F-0082 / US-11: Unit Tests for Unified Installer and Thin Launchers.
Tests:
- install.ps1, install.sh, install.bat, locus.bat, locus.cmd exist at the repo root and act as thin launchers.
- locus_cli/install.py validates prerequisites: Python 3.10+, Node 18+, Git, and Docker.
- Non-interactive install creates target directory, config.yaml, and canonical vault folders.
- Running the installer twice is idempotent and preserves existing configuration.
- CLI invocation via --yes --answers works cleanly.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import pytest
import yaml

from locus_cli.install import (
    CANONICAL_VAULT_DIRS,
    check_docker,
    check_git,
    check_node,
    check_prerequisites,
    check_python,
    run_install,
)


def test_launchers_exist_at_repo_root_and_reference_installer():
    """SPEC §1.12 / R1, R9: install.ps1 and install.sh exist at the repo root and act as thin launchers checking Python 3.10+ and executing locus_cli/install.py."""
    repo_root = Path(__file__).resolve().parents[2]

    ps1_file = repo_root / "install.ps1"
    sh_file = repo_root / "install.sh"
    bat_file = repo_root / "install.bat"
    locus_bat = repo_root / "locus.bat"
    locus_cmd = repo_root / "locus.cmd"

    assert ps1_file.is_file(), "install.ps1 missing at repo root"
    assert sh_file.is_file(), "install.sh missing at repo root"
    assert bat_file.is_file(), "install.bat missing at repo root"
    assert locus_bat.is_file(), "locus.bat missing at repo root"
    assert locus_cmd.is_file(), "locus.cmd missing at repo root"

    ps1_text = ps1_file.read_text(encoding="utf-8")
    assert "locus_cli.install" in ps1_text
    assert "python" in ps1_text.lower()

    sh_text = sh_file.read_text(encoding="utf-8")
    assert "locus_cli.install" in sh_text
    assert "python" in sh_text.lower()


def test_prerequisites_validation():
    """SPEC §1.12 / R10: Validates prerequisites: Python 3, Node 18+, Docker (if mode requires it), and git."""
    py_ok, py_msg = check_python()
    assert py_ok is True
    assert "Python" in py_msg

    git_ok, git_msg = check_git()
    assert git_ok is True
    assert "git" in git_msg.lower()

    node_ok, node_msg = check_node()
    assert node_ok is True
    assert "Node" in node_msg

    all_passed, results = check_prerequisites(require_docker=False)
    assert all_passed is True
    assert "python" in results
    assert "node" in results
    assert "git" in results


def test_non_interactive_install_creates_directories_and_config(tmp_path: Path):
    """SPEC §1.12 / R1: locus_cli/install.py supports non-interactive mode via --yes --answers <file.json>; creates ~/.locus/ and ~/.locus/config.yaml using defaults."""
    target_dir = tmp_path / "locus_test_env"
    answers = {
        "topology": "local",
        "telegram_enabled": True,
        "scheduler_enabled": True,
        "allowed_user_id": 12345678,
    }

    report = run_install(target_dir=target_dir, answers=answers, non_interactive=True)
    assert report["status"] == "installed"

    # Check directories
    assert target_dir.is_dir()
    assert (target_dir / "jobs").is_dir()
    assert (target_dir / "logs").is_dir()
    assert (target_dir / "data").is_dir()
    assert (target_dir / "vault").is_dir()

    # Check canonical vault subfolders
    for folder in CANONICAL_VAULT_DIRS:
        assert (target_dir / "vault" / folder).is_dir()

    # Check config.yaml
    config_file = target_dir / "config.yaml"
    assert config_file.is_file()
    cfg = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert cfg["locus"]["topology"] == "local"
    assert cfg["locus"]["channels"]["telegram"]["enabled"] is True
    assert cfg["locus"]["channels"]["telegram"]["allowed_user_id"] == 12345678
    assert cfg["locus"]["scheduler"]["enabled"] is True

    # Check .env file
    env_file = target_dir / ".env"
    assert env_file.is_file()


def test_installer_is_idempotent(tmp_path: Path):
    """SPEC R1 / docs/agent/08: Run the installer twice and show both outputs; the second run must change nothing."""
    target_dir = tmp_path / "idempotent_env"
    answers = {"topology": "local", "telegram_enabled": True}

    # First run
    report1 = run_install(target_dir=target_dir, answers=answers)
    config_file = target_dir / "config.yaml"
    content_first = config_file.read_text(encoding="utf-8")

    # Second run
    report2 = run_install(target_dir=target_dir, answers=answers)
    content_second = config_file.read_text(encoding="utf-8")

    assert content_first == content_second
    assert report1["status"] == report2["status"]


def test_cli_invocation_with_answers_file(tmp_path: Path):
    """SPEC §1.12 / US-11 demo: Run py -3 -m locus_cli.install --yes --answers tests/fixtures/install_answers.json --target-dir <temp_dir>: creates config.yaml and exits 0."""
    target_dir = tmp_path / "cli_target"
    repo_root = Path(__file__).resolve().parents[2]
    answers_fixture = repo_root / "tests" / "fixtures" / "install_answers.json"
    assert answers_fixture.is_file()

    cmd = [
        sys.executable,
        "-m",
        "locus_cli.install",
        "--yes",
        "--answers",
        str(answers_fixture),
        "--target-dir",
        str(target_dir),
    ]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    assert proc.returncode == 0, f"Installer failed with stderr: {proc.stderr}\nstdout: {proc.stdout}"

    config_file = target_dir / "config.yaml"
    assert config_file.is_file()
    cfg = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    assert cfg["locus"]["topology"] == "local"
