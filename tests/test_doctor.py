"""tests/test_doctor.py - Unit tests for locus_cli.doctor and Pi TUI runner (R7, R5).

Tests diagnostic checks for Python, Node.js, CouchDB, config, and vault writability,
ensuring exactly one PASS/FAIL line is emitted with remediation advice.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from typing import Generator
from unittest.mock import patch

import pytest
import yaml

from locus_cli.doctor import (
    CheckResult,
    check_config_validity,
    check_couchdb_loopback,
    check_nodejs_version,
    check_python_version,
    check_sidecar_health,
    check_vault_writable,
    run_doctor,
    run_pi_tui,
)
from locus_cli.main import init_locus_home


@pytest.fixture
def temp_doctor_env() -> Generator[tuple[Path, Path], None, None]:
    """Provide isolated temporary directories for LOCUS_HOME and vault root."""
    with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as vault_dir:
        yield Path(home_dir), Path(vault_dir)


def test_check_python_version() -> None:
    """Verify check_python_version succeeds on Python >= 3.11."""
    res = check_python_version()
    assert res.passed is True
    assert "[PASS]" in res.format_line()


def test_check_nodejs_version() -> None:
    """Verify check_nodejs_version handles presence and missing node binary."""
    # When node is available
    res = check_nodejs_version()
    assert isinstance(res, CheckResult)
    assert "[PASS]" in res.format_line() or "[FAIL]" in res.format_line()

    # When node is missing
    missing_res = check_nodejs_version(node_bin="/nonexistent/bin/node")
    assert missing_res.passed is False
    assert "[FAIL]" in missing_res.format_line()
    assert "Fix: Install Node.js" in missing_res.format_line()


def test_check_config_validity(temp_doctor_env: tuple[Path, Path]) -> None:
    """Verify check_config_validity reports FAIL on missing config and PASS when valid."""
    home_dir, _ = temp_doctor_env

    # Missing config
    res_missing = check_config_validity(home_dir)
    assert res_missing.passed is False
    assert "[FAIL]" in res_missing.format_line()
    assert "Fix:" in res_missing.format_line()

    # Valid config
    cfg_file = home_dir / "config.yaml"
    cfg_file.write_text("locus:\n  mode: local\n", encoding="utf-8")
    res_valid = check_config_validity(home_dir)
    assert res_valid.passed is True
    assert "[PASS]" in res_valid.format_line()


def test_check_vault_writable(temp_doctor_env: tuple[Path, Path]) -> None:
    """Verify check_vault_writable reports FAIL if canonical folders are missing and PASS when complete."""
    _, vault_dir = temp_doctor_env

    # Empty directory (missing canonical folders)
    res_empty = check_vault_writable(vault_dir)
    assert res_empty.passed is False
    assert "[FAIL]" in res_empty.format_line()
    assert "Missing canonical folders" in res_empty.format_line()

    # Create canonical folders
    for d in ["00-System", "01-Projects", "02-Areas", "03-Resources", "04-Captures", "05-Daily", "06-Content", "07-Archives"]:
        (vault_dir / d).mkdir(parents=True, exist_ok=True)

    res_ok = check_vault_writable(vault_dir)
    assert res_ok.passed is True
    assert "[PASS]" in res_ok.format_line()


def test_check_couchdb_loopback_failure_remediation() -> None:
    """Verify check_couchdb_loopback outputs clear fix guidance when down (R7)."""
    # Probe unused port to guarantee connection failure
    res = check_couchdb_loopback(port=59999)
    assert res.passed is False
    formatted = res.format_line()
    assert "[FAIL] CouchDB connectivity" in formatted
    assert "Fix: Run 'docker compose up -d couchdb'" in formatted


def test_check_sidecar_health_failure_remediation() -> None:
    """Verify check_sidecar_health outputs clear fix guidance when down."""
    # Probe unused port to guarantee service unreachable
    res = check_sidecar_health(port=58420)
    assert res.passed is False
    formatted = res.format_line()
    assert "[FAIL] Sidecar service" in formatted
    assert "Fix: Start sidecar service" in formatted


def test_doctor_runs_with_one_line_per_check(temp_doctor_env: tuple[Path, Path], capsys: pytest.CaptureFixture) -> None:
    """Verify run_doctor prints exactly one PASS or FAIL line per diagnostic check."""
    home_dir, vault_dir = temp_doctor_env

    # Initialize environment
    init_locus_home(home_dir, vault_dir, mode="local")

    # Run doctor with mock unused ports for external services
    exit_code = run_doctor(
        locus_home=home_dir,
        vault_root=vault_dir,
        couchdb_port=59999,
        sidecar_port=58420,
    )

    captured = capsys.readouterr().out
    lines = [line.strip() for line in captured.splitlines() if line.strip() and not line.startswith("===")]

    assert len(lines) >= 5, "Doctor should run at least 5 diagnostic checks"
    for line in lines:
        assert line.startswith("[PASS]") or line.startswith("[FAIL]"), f"Line must start with [PASS] or [FAIL]: {line}"

    # Because CouchDB is simulated down, exit code is 1
    assert exit_code == 1


def test_pi_tui_runner_pass_through() -> None:
    """Verify run_pi_tui builds command targeting upstream packages/coding-agent without modifying flags (R5)."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        code = run_pi_tui(["--model", "gpt-4o", "--help"])
        assert code == 0
        assert mock_run.called
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert any("coding-agent" in str(part) for part in cmd)
        assert "--model" in cmd
        assert "gpt-4o" in cmd
        assert "--help" in cmd
