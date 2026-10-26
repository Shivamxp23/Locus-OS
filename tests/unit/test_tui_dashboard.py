"""
SPEC §7.1-7.9: Unit tests for TUI / Dashboard Engine & Provider (F-0030 / US-61).
"""
from __future__ import annotations

from pathlib import Path
import pytest

from sidecar.display.dashboard import (
    DashboardState,
    LocusDashboardRenderer,
    TUIDashboardEngine,
)
from locus_cli.curses_ui import CursesDashboard
from sidecar.providers.tui_dashboard import (
    BaseTUIDashboardProvider,
    DefaultTUIDashboardProvider,
)
import sidecar.config as config


def test_dashboard_state_data_structure() -> None:
    """SPEC §7.1 line 5840: "DashboardState data structure" """
    state = DashboardState(
        dcs=7.5,
        mode="DEEP WORK",
        active_faction="Craft",
        neo4j_nodes=120,
        neo4j_edges=340,
        livesync_status="OK",
        sidecar_latency_ms=12,
        model_name="claude-3-7-sonnet",
    )
    d = state.to_dict()
    assert d["dcs"] == 7.5
    assert d["mode"] == "DEEP WORK"
    assert d["active_faction"] == "Craft"
    assert d["neo4j_nodes"] == 120
    assert d["neo4j_edges"] == 340
    assert d["livesync_status"] == "OK"
    assert d["sidecar_latency_ms"] == 12
    assert d["model_name"] == "claude-3-7-sonnet"

    recovered = DashboardState.from_dict(d)
    assert recovered.dcs == 7.5
    assert recovered.mode == "DEEP WORK"
    assert recovered.neo4j_nodes == 120


def test_dashboard_renderer_three_column_layout() -> None:
    """SPEC §7.1 line 5849: "left_col = f'DCS:{state.dcs} [{state.mode}] Faction:{state.active_faction}'" """
    state = DashboardState(
        dcs=6.2,
        mode="NORMAL",
        active_faction="Leverage",
        neo4j_nodes=45,
        neo4j_edges=88,
        livesync_status="SYNCING",
        sidecar_latency_ms=8,
        model_name="deepseek-v3",
    )
    footer = LocusDashboardRenderer.render_footer(state, width=100)
    assert "DCS:6.2" in footer
    assert "[NORMAL]" in footer
    assert "Faction:Leverage" in footer
    assert "Mem:45n / 88e" in footer
    assert "LiveSync:SYNCING" in footer
    assert "Sidecar:8ms" in footer
    assert "deepseek-v3" in footer

    # Narrow width handling
    narrow = LocusDashboardRenderer.render_footer(state, width=40)
    assert len(narrow) <= 45
    assert "DCS" in narrow


def test_dashboard_renderer_full_panel() -> None:
    """SPEC §7.1 line 5845: "Format an expanded terminal dashboard status panel" """
    state = DashboardState(dcs=8.1, mode="PEAK", active_faction="Health")
    panel = LocusDashboardRenderer.render_full_dashboard(state, width=70)
    assert "LOCUS OS DASHBOARD :: STATE MONITOR" in panel
    assert "Dynamic Capacity Score (DCS) : 8.10" in panel
    assert "Current Operating Mode       : PEAK" in panel
    assert "Active Faction               : Health" in panel


def test_curses_dashboard_headless_mode() -> None:
    """SPEC §7.1 line 5805: "Curses / terminal dashboard interface for monitoring Locus state" """
    state = DashboardState(dcs=4.0, mode="RECOVERY")
    dash = CursesDashboard(state=state)
    assert dash.run(headless=True) == 0
    snapshot = dash.render_snapshot(width=60)
    assert "RECOVERY" in snapshot
    assert "DCS" in snapshot


def test_tui_dashboard_engine_state_collection() -> None:
    """SPEC §7.1 line 5847: "Coordinates dashboard state gathering, sidecar metric polling, and layout generation" """
    engine = TUIDashboardEngine()
    state = engine.get_state()
    assert isinstance(state, DashboardState)

    custom_state = DashboardState(dcs=9.0, mode="PEAK", active_faction="Expression")
    engine.update_state(custom_state)
    footer = engine.format_footer(width=90)
    assert "PEAK" in footer
    assert "Expression" in footer

    full = engine.format_dashboard(width=80)
    assert "LOCUS OS DASHBOARD" in full


def test_tui_dashboard_provider_off_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §7.1 line 5808: "Swappable / off state: locus.tui_dashboard.enabled" """
    provider = DefaultTUIDashboardProvider()
    assert provider.is_available() is True

    # When enabled, returns valid state and formatted footer
    st = provider.get_dashboard_state()
    assert st.dcs >= 0.0
    footer = provider.format_footer(width=80)
    assert len(footer) > 0

    # Turn off via config
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "tui_dashboard" in key else default)
    assert provider.is_available() is False
    assert provider.format_footer(width=80) == ""
    assert provider.format_dashboard(width=80) == ""
    off_state = provider.get_dashboard_state()
    assert off_state.mode == "OFF"
