"""
SPEC §8.1-8.10 lines 5464-5526, 5598-5606: Unit tests for CLI Commands, Doctor Diagnostics, and Multi-Surface Configuration.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import pytest

from locus_cli.config import (
    check_config_integrity,
    export_config,
    get_config,
    get_secret,
    set_config,
)
from locus_cli.gateway_service import GatewayServiceManager
from locus_cli.main import (
    create_locus_argparser,
    exec_pi_tui,
    locus_cli_entrypoint,
)
from sidecar.providers.cli_doctor_diagnostics import (
    BaseCLIDoctorDiagnosticsProvider,
    DefaultCLIDoctorDiagnosticsProvider,
)


def test_create_locus_argparser_subcommands() -> None:
    """SPEC §8.1-8.10 line 5466: "parser = create_locus_argparser()" """
    parser = create_locus_argparser()
    assert parser.prog == "locus"

    # Verify parse of config subcommand
    args = parser.parse_args(["config", "get", "locus.topology"])
    assert args.subcommand == "config"
    assert args.action == "get"
    assert args.key == "locus.topology"

    # Verify parse of doctor subcommand
    doc_args = parser.parse_args(["doctor", "--full", "--json"])
    assert doc_args.subcommand == "doctor"
    assert doc_args.full is True
    assert doc_args.json is True

    # Verify parse of gateway subcommand
    gw_args = parser.parse_args(["gateway", "status"])
    assert gw_args.subcommand == "gateway"
    assert gw_args.cmd == "status"


def test_locus_cli_entrypoint_run_and_subcommands(capsys: pytest.CaptureFixture[str]) -> None:
    """SPEC §8.1-8.10 line 5469: "IF argv.length == 0 OR argv[0] == 'run': RETURN exec_pi_tui(args=argv, extension='locus-extension')" """
    # Run with empty args or 'run' defaults to pi tui execution
    code = locus_cli_entrypoint([])
    assert code == 0

    code_run = locus_cli_entrypoint(["run"])
    assert code_run == 0

    # Test config subcommand via entrypoint
    code_cfg = locus_cli_entrypoint(["config", "check"])
    assert code_cfg in (0, 1)
    captured = capsys.readouterr()
    assert "[OK] Config integrity:" in captured.out

    # Test life subcommand via entrypoint
    code_life = locus_cli_entrypoint(["life", "dcs"])
    assert code_life == 0
    captured_life = capsys.readouterr()
    assert "DCS:" in captured_life.out

    # Test gateway status via entrypoint
    code_gw = locus_cli_entrypoint(["gateway", "status"])
    assert code_gw == 0
    captured_gw = capsys.readouterr()
    assert "locus-gateway" in captured_gw.out


def test_config_get_set_export_operations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §8.1-8.10 line 5481: "CASE 'config': action = parser.get('action') // get, set, check, export" """
    test_locus_home = tmp_path / ".locus"
    test_locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(test_locus_home))

    assert check_config_integrity() is True

    set_config("locus.topology", "hybrid")
    set_config("locus.providers.llm.provider", "deepseek-flash")

    assert get_config("locus.topology") == "hybrid"
    assert get_config("locus.providers.llm.provider") == "deepseek-flash"
    assert get_config("locus.nonexistent", "default_val") == "default_val"

    exported = export_config()
    assert "locus" in exported
    assert exported["locus"]["topology"] == "hybrid"


def test_gateway_service_manager_lifecycle() -> None:
    """SPEC §8.1-8.10 line 5495: "cmd = parser.get('cmd') // run, start, stop, restart, status" """
    mgr = GatewayServiceManager("test-gateway")
    st = mgr.status()
    assert st["service"] == "test-gateway"
    assert st["active"] is False

    started = mgr.start()
    assert started["status"] == "started"
    assert started["active"] is True

    stopped = mgr.stop()
    assert stopped["status"] == "stopped"
    assert stopped["active"] is False

    restarted = mgr.restart()
    assert restarted["status"] == "started"


def test_cli_doctor_diagnostics_provider() -> None:
    """SPEC §8.1-8.10 line 5488: "probe_results = run_full_diagnostics(verbose=parser.has_flag('--full'))" """
    provider = DefaultCLIDoctorDiagnosticsProvider()
    assert provider.is_available() is True

    diag = provider.run_diagnostics(full=False)
    assert "overall_pass" in diag
    assert "checks" in diag
    assert isinstance(diag["checks"], list)
    assert len(diag["checks"]) >= 5

    reload_res = provider.reload_subsystem("memory")
    assert reload_res["status"] == "reloaded"
    assert reload_res["subsystem"] == "memory"

    cfg_res = provider.set_config("locus.test_key", 12345)
    assert cfg_res["status"] == "updated"
    assert provider.get_config("locus.test_key") == 12345


def test_cli_doctor_diagnostics_provider_off_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §8.1-8.10 line 5444: "Provider Interface: MultiSurfaceCLI / Off-switch: locus.cli_doctor_diagnostics.enabled" """
    provider = DefaultCLIDoctorDiagnosticsProvider()
    assert provider.is_available() is True

    monkeypatch.setattr(
        "sidecar.config.get",
        lambda key, default=None: False if key == "locus.cli_doctor_diagnostics.enabled" else default,
    )
    assert provider.is_available() is False

    with pytest.raises(RuntimeError, match="disabled"):
        provider.run_diagnostics()

    with pytest.raises(RuntimeError, match="disabled"):
        provider.reload_subsystem("memory")

    with pytest.raises(RuntimeError, match="disabled"):
        provider.get_config()

    with pytest.raises(RuntimeError, match="disabled"):
        provider.set_config("key", "val")
