"""
SPEC §1.12 / R7, R5 / F-0082 / US-13: Unit Tests for Locus Doctor Diagnostics and Pi Pass-Through.
Tests:
- locus_cli/doctor.py executes diagnostic checks with one PASS/FAIL line per check and remediation advice.
- Diagnostic checks cover Python, Node, Git, Docker, port availability, vault writability, and keys.
- Exit code is 0 when all critical diagnostics pass, and non-zero when any check fails.
- locus.bat and locus.cmd pass through arguments to Pi TUI setup when requested, keeping Pi's setup working unchanged (R5).
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import pytest

from locus_cli.doctor import (
    DiagnosticResult,
    check_docker,
    check_environment_keys,
    check_git,
    check_node,
    check_port_free,
    check_python,
    check_registered_providers,
    check_sidecar_health,
    check_vault_writability,
    run_doctor,
)


def test_doctor_diagnostics_formatting_and_checks():
    """SPEC §1.12 / R7: locus doctor with one PASS/FAIL line per check with remediation advice."""
    res_pass = DiagnosticResult("test-check", True, "System component ready")
    assert res_pass.format_line() == "[PASS] test-check: System component ready"

    res_fail = DiagnosticResult("test-check", False, "Missing dependency", "Run installation command")
    assert res_fail.format_line() == "[FAIL] test-check: Missing dependency -> Fix: Run installation command"

    # Python check
    py_res = check_python()
    assert py_res.passed is True
    assert "python" in py_res.format_line().lower()

    # Node check
    node_res = check_node()
    assert node_res.passed is True
    assert "node" in node_res.format_line().lower()

    # Git check
    git_res = check_git()
    assert git_res.passed is True
    assert "git" in git_res.format_line().lower()

    # Docker check
    docker_res = check_docker()
    assert isinstance(docker_res.passed, bool)

    # Provider check
    prov_res = check_registered_providers()
    assert prov_res.passed is True


def test_doctor_vault_and_env_checks(tmp_path: Path):
    """SPEC §1.12 / R7: Diagnostic checks cover vault writability and environment keys present."""
    vault_test_dir = tmp_path / "test_vault"
    vault_res = check_vault_writability(vault_test_dir)
    assert vault_res.passed is True
    assert "writable" in vault_res.message

    # Env check on non-existent file
    missing_env = tmp_path / "missing.env"
    env_fail = check_environment_keys(missing_env)
    assert env_fail.passed is False
    assert "not found" in env_fail.message

    # Env check on valid .env
    valid_env = tmp_path / "valid.env"
    valid_env.write_text("LOCUS_HOME=" + str(tmp_path) + "\nTEST_KEY=123\n", encoding="utf-8")
    env_pass = check_environment_keys(valid_env)
    assert env_pass.passed is True
    assert "LOCUS_HOME" not in env_pass.message  # No missing error message


def test_doctor_exit_codes_and_criticality(monkeypatch, tmp_path: Path):
    """SPEC §1.12 / R7: Exit code is 0 when all critical diagnostics pass, and non-zero when any check fails."""
    valid_env = tmp_path / "doctor.env"
    valid_env.write_text("LOCUS_HOME=" + str(tmp_path) + "\n", encoding="utf-8")

    all_passed, results = run_doctor(vault_dir=tmp_path, env_file=valid_env, check_sidecar=False)
    assert all_passed is True

    # Mock a critical failure (e.g. Python check fails)
    monkeypatch.setattr("locus_cli.doctor.check_python", lambda: DiagnosticResult("python", False, "Python outdated", "Upgrade python", critical=True))
    crit_passed, crit_results = run_doctor(vault_dir=tmp_path, env_file=valid_env, check_sidecar=False)
    assert crit_passed is False


def test_launcher_doctor_dispatch_and_pi_passthrough():
    """SPEC §1.12 / R5: locus.bat and locus.cmd pass through arguments directly to Pi TUI setup when requested, keeping Pi's setup working unchanged."""
    repo_root = Path(__file__).resolve().parents[2]
    bat_file = repo_root / "locus.bat"
    cmd_file = repo_root / "locus.cmd"

    assert bat_file.is_file()
    assert cmd_file.is_file()

    bat_text = bat_file.read_text(encoding="utf-8")
    assert "locus_cli.doctor" in bat_text
    assert "setup" in bat_text
    assert "packages\\coding-agent\\dist\\cli.js" in bat_text

    cmd_text = cmd_file.read_text(encoding="utf-8")
    assert "locus_cli.doctor" in cmd_text
    assert "setup" in cmd_text
    assert "packages\\coding-agent\\dist\\cli.js" in cmd_text


def test_doctor_cli_run(tmp_path: Path):
    """SPEC §1.12 / US-13 demo: Run py -3 -m locus_cli.doctor: prints diagnostic lines with [PASS]/[FAIL] status for Python, Node, Git, and vault writability, exiting 0."""
    repo_root = Path(__file__).resolve().parents[2]
    target_env = tmp_path / ".env"
    target_env.write_text("LOCUS_HOME=" + str(tmp_path) + "\n", encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "locus_cli.doctor",
        "--vault-dir",
        str(tmp_path / "vault"),
        "--env-file",
        str(target_env),
    ]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    assert proc.returncode == 0, f"Doctor failed with stderr: {proc.stderr}\nstdout: {proc.stdout}"
    assert "[PASS] python:" in proc.stdout
    assert "[PASS] node:" in proc.stdout
    assert "[PASS] git:" in proc.stdout
    assert "[PASS] vault:" in proc.stdout
    assert "[OK] System is healthy" in proc.stdout
