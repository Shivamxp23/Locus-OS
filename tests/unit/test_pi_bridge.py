"""
SPEC F-0084 / S-3: Pi launcher bridge tests.
Asserts that run_pi_turn builds command line with --approve, --no-context-files, repo root cwd,
and that --dangerously-skip-permissions is never passed.
"""
import pathlib
import subprocess
import sys
import pytest
from unittest.mock import patch, MagicMock

from sidecar.pi_bridge import get_node_executable, run_pi_turn, get_repo_root


def test_get_repo_root():
    """Verify that get_repo_root resolves to the repository root."""
    root = get_repo_root()
    assert (root / "tools" / "guard" / "guard.toml").exists()


def test_get_node_executable():
    """Verify get_node_executable returns a valid node path."""
    node_bin = get_node_executable()
    assert node_bin is not None
    assert "node" in node_bin.lower()


def test_run_pi_turn_flags_and_cwd():
    """
    Verify run_pi_turn always includes --approve, --no-context-files,
    runs with repo root as working directory, and never uses --dangerously-skip-permissions.
    """
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="pi success", stderr=""
        )

        res = run_pi_turn("hello pi", session_id="test_session_1")

        assert mock_run.called
        call_args, call_kwargs = mock_run.call_args

        cmd = call_args[0]
        # Must include security and headless flags
        assert "--approve" in cmd, f"--approve missing in {cmd}"
        assert "--no-context-files" in cmd, f"--no-context-files missing in {cmd}"
        assert "--dangerously-skip-permissions" not in cmd

        # Working directory must be repo root
        assert call_kwargs.get("cwd") == str(get_repo_root())
        assert call_kwargs.get("stdin") == subprocess.DEVNULL
        assert call_kwargs.get("shell") is False


def test_run_pi_turn_custom_executable():
    """Verify run_pi_turn works with a custom executable."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="fake output", stderr=""
        )

        fake_pi = "fake_pi_bin"
        run_pi_turn("prompt text", pi_executable=fake_pi)

        call_args, _ = mock_run.call_args
        cmd = call_args[0]
        assert cmd[0] == fake_pi
        assert "--approve" in cmd
        assert "--no-context-files" in cmd
