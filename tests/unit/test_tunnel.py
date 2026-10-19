"""
SPEC §04 / D-13 Option a / F-0085 / US-15: Unit Tests for SSH Tunnel Helper.
Tests:
- SSHTunnelManager builds valid SSH command with -N, -L port forwarding, host, user, and key.
- SSHTunnelManager lifecycle management (start, is_alive, stop).
- Launcher dispatch for 'tunnel' and 'connect'.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import pytest

from locus_cli.tunnel import SSHTunnelManager


def test_build_ssh_command_flags():
    """SPEC 04 line 14: SSHTunnelManager builds compliant port forwarding command."""
    mgr = SSHTunnelManager(
        host="vm.locus.internal",
        user="testuser",
        local_port=8420,
        remote_port=8420,
        ssh_port=22,
        ssh_key=Path("/fake/id_ed25519"),
    )
    cmd = mgr.build_command()
    assert "-N" in cmd
    assert "8420:127.0.0.1:8420" in cmd
    assert "testuser@vm.locus.internal" in cmd
    assert "-p" in cmd
    assert "22" in cmd
    assert "-i" in cmd
    assert "id_ed25519" in str(cmd)


def test_tunnel_manager_validation():
    """SPEC 04 line 14: SSHTunnelManager validates non-empty host and user."""
    with pytest.raises(ValueError):
        SSHTunnelManager(host="", user="ubuntu")

    with pytest.raises(ValueError):
        SSHTunnelManager(host="1.2.3.4", user="")


def test_tunnel_manager_lifecycle_with_mock():
    """SPEC 04 line 14: SSHTunnelManager starts and stops process."""
    class MockProcess:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None if not self.terminated else 0

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            pass

    mock_proc = MockProcess()
    mgr = SSHTunnelManager(host="localhost", user="user")
    mgr.start_tunnel(runner=lambda _: mock_proc)

    assert mgr.is_alive() is True
    mgr.stop_tunnel()
    assert mock_proc.terminated is True


def test_launcher_dispatch_tunnel_and_connect():
    """SPEC 04 line 14: locus.bat and locus.cmd dispatch tunnel and connect commands."""
    repo_root = Path(__file__).resolve().parents[2]
    bat_file = repo_root / "locus.bat"
    cmd_file = repo_root / "locus.cmd"

    bat_text = bat_file.read_text(encoding="utf-8")
    assert 'if "%1"=="tunnel"' in bat_text
    assert 'if "%1"=="connect"' in bat_text
    assert "locus_cli.tunnel" in bat_text

    cmd_text = cmd_file.read_text(encoding="utf-8")
    assert 'if "%1"=="tunnel"' in cmd_text
    assert 'if "%1"=="connect"' in cmd_text
    assert "locus_cli.tunnel" in cmd_text
