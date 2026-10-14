"""Unit tests for Pi Agent bridge (US-02 / F-0087).

Verifies:
- get_node_executable locates Node or raises informative error
- run_pi_turn strictly passes `--approve` and `--no-context-files`
- cwd defaults to the repository root
- --dangerously-skip-permissions is rejected
- cron_runner executes Pi turns exclusively via run_pi_turn
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sidecar.cron_runner import execute_cron_job, match_field, matches_schedule
from sidecar.pi_bridge import REPO_ROOT, PiTurnResult, get_node_executable, run_pi_turn


def test_get_node_executable():
    """Verify get_node_executable resolves an executable string."""
    with patch("shutil.which", return_value="/usr/bin/node"):
        exe = get_node_executable()
        assert exe == "/usr/bin/node"

    with patch("shutil.which", return_value=None), patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="Node.js executable not found"):
            get_node_executable()


def test_run_pi_turn_mandatory_security_flags_and_cwd():
    """Verify run_pi_turn passes --approve, --no-context-files, and repo root cwd."""
    mock_proc = MagicMock()
    mock_proc.stdout = "Turn completed successfully"
    mock_proc.stderr = ""
    mock_proc.returncode = 0

    with patch("subprocess.run", return_value=mock_proc) as mock_run, \
         patch("sidecar.pi_bridge.get_node_executable", return_value="node"):

        result = run_pi_turn("Summarize recent captures")

        assert isinstance(result, PiTurnResult)
        assert result.ok is True
        assert result.stdout == "Turn completed successfully"

        assert mock_run.called
        args, kwargs = mock_run.call_args
        cmd = args[0]

        # Security flag assertions (AGENTS.md Law 7 & S-3)
        assert "--approve" in cmd, "Mandatory flag --approve missing from Pi turn command"
        assert "--no-context-files" in cmd, "Mandatory flag --no-context-files missing from Pi turn command"

        # Working directory assertion
        assert kwargs["cwd"] == str(REPO_ROOT), f"Working folder must be repo root {REPO_ROOT}, got {kwargs['cwd']}"

        # Subprocess security guarantees
        assert kwargs["stdin"] == subprocess.DEVNULL, "stdin must be DEVNULL to prevent hang"
        assert kwargs["shell"] is False, "shell=True is forbidden"


def test_run_pi_turn_session_id_and_custom_cwd():
    """Verify session_id and custom cwd handling."""
    mock_proc = MagicMock()
    mock_proc.stdout = "Session turn ok"
    mock_proc.stderr = ""
    mock_proc.returncode = 0

    custom_cwd = REPO_ROOT / "vault"

    with patch("subprocess.run", return_value=mock_proc) as mock_run, \
         patch("sidecar.pi_bridge.get_node_executable", return_value="node"):

        result = run_pi_turn("Test prompt", cwd=custom_cwd, session_id="cron_job_42", timeout=120)

        assert result.ok is True
        args, kwargs = mock_run.call_args
        cmd = args[0]

        assert "--session" in cmd
        session_idx = cmd.index("--session")
        assert cmd[session_idx + 1] == "cron_job_42"
        assert kwargs["cwd"] == str(custom_cwd)
        assert kwargs["timeout"] == 120


def test_run_pi_turn_rejects_dangerously_skip_permissions():
    """Verify run_pi_turn actively rejects the dangerous permissions bypass."""
    with pytest.raises(ValueError, match="Forbidden security flag detected"):
        run_pi_turn("Do work", extra_args=["--dangerously-skip-permissions"])


def test_cron_runner_delegation_to_pi_bridge():
    """Verify cron_runner starts Pi turns exclusively through run_pi_turn with cron_ prefix."""
    with patch("sidecar.cron_runner.run_pi_turn") as mock_pi_turn:
        mock_pi_turn.return_value = PiTurnResult(stdout="Cron executed", stderr="", returncode=0)

        res = execute_cron_job(job_id="weather_scan", prompt="Check weather forecast", timeout=180)

        assert res.ok is True
        mock_pi_turn.assert_called_once_with(
            prompt="Check weather forecast",
            session_id="cron_weather_scan",
            timeout=180,
        )


def test_cron_expression_matching():
    """Verify cron schedule matching helper."""
    assert match_field(15, "15") is True
    assert match_field(15, "*/5") is True
    assert match_field(16, "*/5") is False
    assert match_field(3, "1-5") is True
    assert match_field(7, "1-5") is False

    dt = datetime(2026, 10, 14, 7, 30)  # Wednesday
    assert matches_schedule(dt, "30 7 * * *") is True
    assert matches_schedule(dt, "0 7 * * *") is False
