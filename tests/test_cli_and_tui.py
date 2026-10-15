"""tests/test_cli_and_tui.py - Unit and integration tests for Locus CLI and TUI.

Tests:
- Interactive TUI lifecycle and command handling (/help, /status, /factions, /doctor, /vault, /memory, /subagents, /checkin, /exit)
- Batch execution (--print)
- Main CLI routing: default TUI launch when installed, auto-install fallback when not installed
- Subcommand routing: install, doctor, dashboard, tui, version, help
- Launchers configuration (install.bat, install.ps1, install.sh, locus.bat, locus.cmd, locus)
"""

from __future__ import annotations

import io
from pathlib import Path
import tempfile
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
import yaml

from locus_cli.main import init_locus_home, is_installed, main, run_installer
from locus_cli.tui import LocusTUI, run_tui

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def temp_locus_env() -> Generator[tuple[Path, Path], None, None]:
    """Provide isolated temporary directories for LOCUS_HOME and vault root."""
    with tempfile.TemporaryDirectory() as home_dir, tempfile.TemporaryDirectory() as vault_dir:
        yield Path(home_dir), Path(vault_dir)


def test_tui_initialization_and_welcome(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify LocusTUI initializes config, dashboard, and renders welcome banner."""
    home_dir, vault_dir = temp_locus_env
    init_locus_home(home_dir, vault_dir, mode="hybrid")

    fake_stdin = io.StringIO("/exit\n")
    fake_stdout = io.StringIO()

    tui = LocusTUI(locus_home=home_dir, stdin=fake_stdin, stdout=fake_stdout)
    exit_code = tui.run_repl()

    assert exit_code == 0
    output = fake_stdout.getvalue()
    assert "Autonomous Agent Operating System" in output
    assert "LOCUS OS DASHBOARD" in output
    assert "HYBRID" in output
    assert "Exiting Locus OS. Goodbye!" in output


def test_tui_slash_commands(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify all major slash commands execute and return expected outputs."""
    home_dir, vault_dir = temp_locus_env
    init_locus_home(home_dir, vault_dir, mode="local")

    commands = [
        "/help",
        "/status",
        "/factions",
        "/subagents",
        "/memory",
        "/vault",
        "/checkin",
        "/clear",
        "/exit",
    ]
    fake_stdin = io.StringIO("\n".join(commands) + "\n")
    fake_stdout = io.StringIO()

    tui = LocusTUI(locus_home=home_dir, stdin=fake_stdin, stdout=fake_stdout)
    tui.run_repl()

    output = fake_stdout.getvalue()
    assert "Commands:" in output  # /help
    assert "LOCUS OS DASHBOARD" in output  # /status
    assert "Life Factions Balance" in output  # /factions
    assert "Craft" in output or "Career" in output
    assert "Subagent Registry & Swarm Status" in output  # /subagents
    assert "Tri-Stack Memory Status" in output  # /memory
    assert "Obsidian Vault Inspection" in output  # /vault
    assert "Locus Autonomous Life Check-In" in output  # /checkin
    assert "screen cleared" in output  # /clear


def test_tui_doctor_command(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify /doctor command inside TUI executes diagnostics."""
    home_dir, vault_dir = temp_locus_env
    init_locus_home(home_dir, vault_dir, mode="local")

    fake_stdin = io.StringIO("/doctor\n/exit\n")
    fake_stdout = io.StringIO()

    tui = LocusTUI(locus_home=home_dir, stdin=fake_stdin, stdout=fake_stdout)
    with patch("locus_cli.doctor.run_doctor", return_value=0) as mock_doctor:
        tui.run_repl()
        assert mock_doctor.called


def test_tui_prompt_processing(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify freeform natural language prompts are processed cleanly."""
    home_dir, vault_dir = temp_locus_env
    init_locus_home(home_dir, vault_dir, mode="local")

    fake_stdin = io.StringIO("Review our upcoming sprint milestones\n/exit\n")
    fake_stdout = io.StringIO()

    tui = LocusTUI(locus_home=home_dir, stdin=fake_stdin, stdout=fake_stdout)
    tui.run_repl()

    output = fake_stdout.getvalue()
    assert "Locus Agent thinking..." in output
    assert "Review our upcoming sprint milestones" in output


def test_tui_oneshot_mode(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify batch one-shot execution via run_tui(query=...)."""
    home_dir, vault_dir = temp_locus_env
    init_locus_home(home_dir, vault_dir, mode="local")

    fake_stdout = io.StringIO()
    code = run_tui(locus_home=home_dir, query="Check system readiness", stdout=fake_stdout)
    assert code == 0
    output = fake_stdout.getvalue()
    assert "Check system readiness" in output


def test_is_installed_logic(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify is_installed correctly detects absence vs presence of config.yaml."""
    home_dir, vault_dir = temp_locus_env
    assert not is_installed(home_dir)

    init_locus_home(home_dir, vault_dir, mode="local")
    assert is_installed(home_dir)


def test_main_cli_routing_installed_runs_tui(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify locus without args launches TUI when installed."""
    home_dir, vault_dir = temp_locus_env
    init_locus_home(home_dir, vault_dir, mode="local")

    with patch.dict("os.environ", {"LOCUS_HOME": str(home_dir)}):
        with patch("locus_cli.tui.run_tui", return_value=0) as mock_tui:
            with pytest.raises(SystemExit) as exc:
                main([])
            assert exc.value.code == 0
            assert mock_tui.called


def test_main_cli_routing_uninstalled_runs_installer(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify locus without args runs installer when not yet installed."""
    home_dir, _ = temp_locus_env

    with patch.dict("os.environ", {"LOCUS_HOME": str(home_dir)}):
        with patch("locus_cli.main.run_installer", return_value=0) as mock_inst:
            with patch("locus_cli.tui.run_tui", return_value=0) as mock_tui:
                with pytest.raises(SystemExit) as exc:
                    main([])
                assert exc.value.code == 0
                assert mock_inst.called
                assert mock_tui.called


def test_main_cli_subcommands(temp_locus_env: tuple[Path, Path]) -> None:
    """Verify CLI subcommands dispatch correctly."""
    home_dir, vault_dir = temp_locus_env
    init_locus_home(home_dir, vault_dir, mode="local")

    with patch.dict("os.environ", {"LOCUS_HOME": str(home_dir)}):
        # install
        with patch("locus_cli.main.run_installer", return_value=0) as mock_inst:
            with pytest.raises(SystemExit) as exc:
                main(["install", "--yes"])
            assert exc.value.code == 0
            assert mock_inst.called

        # doctor
        with patch("locus_cli.doctor.run_doctor", return_value=0) as mock_doc:
            with pytest.raises(SystemExit) as exc:
                main(["doctor"])
            assert exc.value.code == 0
            assert mock_doc.called

        # dashboard
        with pytest.raises(SystemExit) as exc:
            main(["dashboard"])
        assert exc.value.code == 0

        # version
        with pytest.raises(SystemExit) as exc:
            main(["version"])
        assert exc.value.code == 0

        # help
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0


def test_launcher_scripts_wiring() -> None:
    """Verify launcher scripts wire to locus_cli.main properly."""
    ps1 = (REPO_ROOT / "install.ps1").read_text(encoding="utf-8")
    sh = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
    bat = (REPO_ROOT / "install.bat").read_text(encoding="utf-8")
    locus_bat = (REPO_ROOT / "locus.bat").read_text(encoding="utf-8")
    locus_cmd = (REPO_ROOT / "locus.cmd").read_text(encoding="utf-8")

    assert "locus_cli.main install" in ps1
    assert "locus_cli.main install" in sh
    assert "locus_cli.main install" in bat
    assert "locus_cli.main" in locus_bat
    assert "locus_cli.main" in locus_cmd
