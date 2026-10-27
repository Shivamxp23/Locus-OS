"""
Unit tests for Dual Interface, 4 Daily Check-ins, and Cost Budget Engine (F-0064 / US-101).
SPEC §28.1-28.6 lines 7380-7432.
"""
from __future__ import annotations

import pytest

from sidecar import config
from sidecar.gateway.dual_interface import (
    CheckInRecord,
    CheckInSlot,
    DualInterfaceEngine,
    SessionMessage,
)
from sidecar.providers.dual_interface import (
    BaseDualInterfaceProvider,
    DefaultDualInterfaceProvider,
)


@pytest.fixture(autouse=True)
def reset_config():
    """Ensure clean config state for tests."""
    config.set("locus.dual_interface_checkins.enabled", True)
    config.set("locus.gateway.dual_interface.enabled", True)
    yield
    config.set("locus.dual_interface_checkins.enabled", True)
    config.set("locus.gateway.dual_interface.enabled", True)


def test_session_unification():
    """SPEC §28.1: Both Telegram and TUI messages unify into shared session timeline."""
    engine = DualInterfaceEngine(daily_budget_usd=1.0)
    session_id = "unified-session-001"

    # Telegram message
    res_tg = engine.route_message(channel="telegram", session_id=session_id, content="Status update via Telegram", sender="user")
    assert res_tg["status"] == "BRIDGED"
    assert res_tg["total_messages"] == 1

    # TUI message to same session
    res_tui = engine.route_message(channel="tui", session_id=session_id, content="Follow-up from local TUI", sender="user")
    assert res_tui["status"] == "BRIDGED"
    assert res_tui["total_messages"] == 2

    # Check history
    history = engine.get_session_history(session_id)
    assert len(history) == 2
    assert history[0]["channel"] == "telegram"
    assert history[1]["channel"] == "tui"
    assert "Telegram" in history[0]["content"]
    assert "TUI" in history[1]["content"]


def test_checkin_keyboards():
    """SPEC §28.2: 4 Daily Structured Check-Ins generate correct keyboard layouts."""
    engine = DualInterfaceEngine()

    # 07:30 Morning
    kb_morning = engine.get_keyboard_for_slot("07:30_MORNING")
    assert len(kb_morning) >= 3
    assert any("Energy:" in btn["text"] for row in kb_morning for btn in row)
    assert any("Stress:" in btn["text"] for row in kb_morning for btn in row)

    # 13:00 Afternoon
    kb_afternoon = engine.get_keyboard_for_slot("13:00_AFTERNOON")
    assert any("On Track" in btn["text"] for row in kb_afternoon for btn in row)

    # 18:00 Evening
    kb_evening = engine.get_keyboard_for_slot("18:00_EVENING")
    assert any("All Done" in btn["text"] for row in kb_evening for btn in row)

    # 22:00 Night
    kb_night = engine.get_keyboard_for_slot("22:00_NIGHT")
    assert any("Grateful" in btn["text"] for row in kb_night for btn in row)


def test_dcs_calculation_formula():
    """
    SPEC §28.2:
    dcs = (energy * 0.4) + ((10 - stress) * 0.3) + (((mood + 1) * 5) * 0.3)
    """
    engine = DualInterfaceEngine()

    # High state: Energy=9, Stress=2, Mood=0.8
    # dcs = (9 * 0.4) + (8 * 0.3) + (1.8 * 5 * 0.3) = 3.6 + 2.4 + 2.7 = 8.7 -> FLOW
    dcs, mode = engine.calculate_dcs(energy=9.0, stress=2.0, mood=0.8)
    assert dcs == 8.7
    assert mode == "FLOW"

    # Moderate state: Energy=6, Stress=5, Mood=0.0
    # dcs = (6 * 0.4) + (5 * 0.3) + (1.0 * 5 * 0.3) = 2.4 + 1.5 + 1.5 = 5.4 -> BALANCED
    dcs, mode = engine.calculate_dcs(energy=6.0, stress=5.0, mood=0.0)
    assert dcs == 5.4
    assert mode == "BALANCED"

    # Depleted state: Energy=3, Stress=8, Mood=-0.5
    # dcs = (3 * 0.4) + (2 * 0.3) + (0.5 * 5 * 0.3) = 1.2 + 0.6 + 0.75 = 2.55 -> MINIMAL
    dcs, mode = engine.calculate_dcs(energy=3.0, stress=8.0, mood=-0.5)
    assert dcs == 2.55
    assert mode == "MINIMAL"


def test_record_checkin():
    """SPEC §28.2: Record structured daily check-in."""
    engine = DualInterfaceEngine()
    rec = engine.record_checkin(
        slot="07:30_MORNING",
        energy=8.0,
        stress=3.0,
        mood=0.6,
        readiness="Ready to conquer the sprint",
        notes="Slept 8 hours",
    )
    assert rec.slot == "07:30_MORNING"
    assert rec.operating_mode == "FLOW"
    assert rec.dcs_score > 7.5

    status = engine.get_status()
    assert status["total_checkins_count"] == 1


def test_zero_cost_budget_tracking():
    """SPEC §28.3: Inner loop skips run if >80% daily budget used."""
    budget = 0.001  # small budget for testing
    engine = DualInterfaceEngine(daily_budget_usd=budget)

    # Initial budget status
    st0 = engine.check_budget_status()
    assert st0["skip_inner_loop_recommended"] is False

    # Simulate heavy usage (over 80% of $0.001)
    engine.record_usage(tokens=10000, cost_usd=0.00085)
    st1 = engine.check_budget_status()
    assert st1["budget_usage_pct"] >= 80.0
    assert st1["skip_inner_loop_recommended"] is True


def test_subsystem_off_switch():
    """Subsystem toggle locus.gateway.dual_interface.enabled."""
    engine = DualInterfaceEngine()
    config.set("locus.gateway.dual_interface.enabled", False)

    res = engine.route_message("telegram", "test-sess", "Hello")
    assert res["status"] == "DISABLED"
    assert res["status_code"] == 503


def test_provider_modular_off_switch():
    """Provider master off-switch locus.dual_interface_checkins.enabled."""
    provider = DefaultDualInterfaceProvider()
    config.set("locus.dual_interface_checkins.enabled", False)

    res_msg = provider.route_interface_message("telegram", "sess-1", "Hello")
    assert res_msg["status_code"] == 503
    assert res_msg["disabled"] == "locus.dual_interface_checkins.enabled"

    res_kb = provider.get_checkin_keyboard("07:30_MORNING")
    assert res_kb["status_code"] == 503

    res_chk = provider.submit_checkin("07:30_MORNING")
    assert res_chk["status_code"] == 503

    res_bgt = provider.get_budget_status()
    assert res_bgt["status_code"] == 503

    res_st = provider.get_status()
    assert res_st["status_code"] == 503


def test_provider_normal_delegation():
    """Provider delegates properly when enabled."""
    provider = DefaultDualInterfaceProvider()
    config.set("locus.dual_interface_checkins.enabled", True)

    res_msg = provider.route_interface_message("tui", "sess-test", "Message 1")
    assert res_msg["status_code"] == 200

    res_kb = provider.get_checkin_keyboard("13:00_AFTERNOON")
    assert res_kb["status_code"] == 200
    assert "keyboard" in res_kb

    res_chk = provider.submit_checkin("13:00_AFTERNOON", energy=7.0, stress=4.0, mood=0.2)
    assert res_chk["status_code"] == 200
    assert res_chk["operating_mode"] in ("FLOW", "BALANCED", "RECOVERY", "MINIMAL")

    res_bgt = provider.get_budget_status()
    assert res_bgt["status_code"] == 200
    assert "budget_usage_pct" in res_bgt


def test_provider_polymorphism():
    """BaseDualInterfaceProvider polymorphic contract compliance."""
    class CustomDualInterfaceProvider(BaseDualInterfaceProvider):
        @property
        def name(self) -> str:
            return "custom_dual_interface"

        def is_feature_enabled(self):
            return True, ""

        def route_interface_message(self, channel: str, session_id: str, content: str, sender: str = "user"):
            return {"status": "CUSTOM_BRIDGED", "status_code": 200}

        def get_checkin_keyboard(self, slot: str):
            return {"slot": slot, "keyboard": [], "status_code": 200}

        def submit_checkin(self, slot: str, energy: float = 7.0, stress: float = 3.0, mood: float = 0.5, readiness: str = "Ready to go!", notes: str = ""):
            return {"slot": slot, "dcs_score": 9.9, "operating_mode": "FLOW", "status_code": 200}

        def get_budget_status(self):
            return {"daily_cost_usd": 0.0, "status_code": 200}

        def get_status(self):
            return {"custom": True, "status_code": 200}

    prov = CustomDualInterfaceProvider()
    assert prov.name == "custom_dual_interface"
    assert prov.route_interface_message("telegram", "s", "c")["status"] == "CUSTOM_BRIDGED"
