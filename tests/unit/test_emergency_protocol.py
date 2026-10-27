"""
Unit tests for Four-Level Emergency Protocol (F-0117 / US-94).
"""
import pytest
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.emergency_protocol import (
    CRISIS_FACTION_ORDER,
    EmergencyAssessment,
    EmergencyLevel,
    EmergencyProtocolStatus,
    FourLevelEmergencyProtocol,
    ProtocolActivationResult,
    ProtocolDeactivationResult,
)
from sidecar.providers.emergency_protocol import (
    BaseFourLevelEmergencyProtocolProvider,
    DefaultFourLevelEmergencyProtocolProvider,
)


def test_emergency_levels_assessment():
    """
    SPEC §25.16 line 4926: "Level 1 (minor) -> Level 4 (crisis). Each level unlocks different tool permissions and overrides scheduling. Crisis hierarchy: Health > Leverage > Craft > Expression."
    """
    proto = FourLevelEmergencyProtocol()

    # Normal / Level 0
    a0 = proto.evaluate(disruption_hours=0.0)
    assert a0.level == 0
    assert a0.level_name == "LEVEL_0_NORMAL"
    assert a0.mode_override == "NORMAL"

    # Minor / Level 1 (lost 1-2 hours)
    a1 = proto.evaluate(disruption_hours=1.5)
    assert a1.level == 1
    assert a1.level_name == "LEVEL_1_MINOR"
    assert a1.mode_override == "NORMAL"
    assert a1.redistribution_window_days == 1

    # Moderate / Level 2 (lost a full day)
    a2 = proto.evaluate(disruption_days=1)
    assert a2.level == 2
    assert a2.level_name == "LEVEL_2_MODERATE"
    assert a2.mode_override == "LOW_DCS"

    # Major / Level 3 (lost 3+ days)
    a3 = proto.evaluate(disruption_days=3)
    assert a3.level == 3
    assert a3.level_name == "LEVEL_3_MAJOR"
    assert a3.mode_override == "SURVIVAL"
    assert a3.redistribution_window_days == 14  # 2 weeks minimum

    # Crisis / Level 4 (life event)
    a4 = proto.evaluate(is_life_event=True)
    assert a4.level == 4
    assert a4.level_name == "LEVEL_4_CRISIS"
    assert a4.mode_override == "CRISIS"
    assert a4.affected_factions["Expression/Explore"] == "SUSPENDED"
    assert a4.affected_factions["Health/Stability"] == "LOCKED_NON_NEGOTIABLE"


def test_level_4_crisis_hierarchy_and_expression_suspension():
    """
    SPEC §25.16 line 4926: "Level 1 (minor) -> Level 4 (crisis). Each level unlocks different tool permissions and overrides scheduling. Crisis hierarchy: Health > Leverage > Craft > Expression."
    """
    proto = FourLevelEmergencyProtocol()

    tasks = [
        {"id": "t1", "title": "Paint painting", "faction": "Expression/Explore", "tws": 9.5},
        {"id": "t2", "title": "Code feature", "faction": "Craft/Skills", "tws": 7.0},
        {"id": "t3", "title": "Client pitch", "faction": "Leverage/Money", "tws": 8.0},
        {"id": "t4", "title": "Cardio & sleep", "faction": "Health/Stability", "tws": 6.0},
    ]

    res = proto.apply_scheduling_overrides(tasks=tasks, level=4)
    assert res["overrides_applied"] is True
    assert res["mode"] == "CRISIS"

    # Expression must be suspended completely
    assert len(res["tasks_suspended"]) == 1
    assert res["tasks_suspended"][0]["id"] == "t1"

    # Retained tasks must be sorted strictly Health > Leverage > Craft
    retained_factions = [t["faction"] for t in res["tasks_retained"]]
    assert retained_factions == ["Health/Stability", "Leverage/Money", "Craft/Skills"]


def test_level_3_golden_rule_two_week_redistribution_and_review():
    """
    SPEC §25.16 line 4926: "Level 1 (minor) -> Level 4 (crisis). Each level unlocks different tool permissions and overrides scheduling. Crisis hierarchy: Health > Leverage > Craft > Expression."
    """
    proto = FourLevelEmergencyProtocol()

    act = proto.activate(level=3, reason="Flu outbreak")
    assert act.success is True
    assert act.level == 3
    assert act.mode_override == "SURVIVAL"
    assert act.redistribution_window_days == 14

    deact = proto.deactivate()
    assert deact.success is True
    assert deact.previous_level == 3
    assert deact.require_weekly_review is True
    assert deact.redistribution_window_days == 14


def test_tool_permissions_matrix():
    """
    SPEC §25.16 line 4926: "Level 1 (minor) -> Level 4 (crisis). Each level unlocks different tool permissions and overrides scheduling. Crisis hierarchy: Health > Leverage > Craft > Expression."
    """
    proto = FourLevelEmergencyProtocol()

    p0 = proto.get_tool_permissions(0)
    assert p0["task_create_discretionary"] is True
    assert p0["expression_work_allowed"] is True
    assert p0["survival_tools_only"] is False

    p2 = proto.get_tool_permissions(2)
    assert p2["task_create_discretionary"] is False
    assert p2["scheduling_override"] is True

    p3 = proto.get_tool_permissions(3)
    assert p3["survival_tools_only"] is True
    assert p3["expression_work_allowed"] is False

    p4 = proto.get_tool_permissions(4)
    assert p4["expression_work_allowed"] is False
    assert p4["recovery_window_planning"] is True


def test_scheduling_overrides_levels_1_and_2():
    """
    SPEC §25.16 line 4926: "Level 1 (minor) -> Level 4 (crisis). Each level unlocks different tool permissions and overrides scheduling. Crisis hierarchy: Health > Leverage > Craft > Expression."
    """
    proto = FourLevelEmergencyProtocol()

    tasks = [
        {"id": "t1", "title": "High task", "faction": "Craft/Skills", "tws": 8.0},
        {"id": "t2", "title": "Low task", "faction": "Expression/Explore", "tws": 2.0},
    ]

    # Level 1 moves lowest TWS task to tomorrow
    res1 = proto.apply_scheduling_overrides(tasks=tasks, level=1)
    assert len(res1["tasks_deferred"]) == 1
    assert res1["tasks_deferred"][0]["id"] == "t2"
    assert len(res1["tasks_retained"]) == 1
    assert res1["tasks_retained"][0]["id"] == "t1"

    # Level 2 marks low DCS and retains high/emergency
    res2 = proto.apply_scheduling_overrides(tasks=tasks, level=2)
    assert res2["mode"] == "LOW_DCS"
    assert len(res2["tasks_retained"]) == 1
    assert res2["tasks_retained"][0]["id"] == "t1"


def test_modular_subsystem_off_switch(monkeypatch):
    """
    SPEC §25.16 line 4930: "Swappable / off state: locus.life_os.emergency_protocol.enabled. Off -> no emergency overrides; standard scheduling always applies."
    """
    proto = FourLevelEmergencyProtocol()

    # Disable subsystem switch
    monkeypatch.setattr(config, "get", lambda key: "false" if key == proto.SWITCH_KEY else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == proto.SWITCH_KEY else True)

    assert proto.is_protocol_enabled() is False

    eval_res = proto.evaluate(disruption_days=4)
    assert eval_res.overrides_applied is False
    assert eval_res.enabled is False
    assert eval_res.level == 0

    act = proto.activate(level=4)
    assert act.overrides_applied is False
    assert act.level == 0

    tasks = [{"id": "t1", "title": "Any", "faction": "Expression/Explore", "tws": 1.0}]
    overrides = proto.apply_scheduling_overrides(tasks=tasks, level=4)
    assert overrides["overrides_applied"] is False
    assert overrides["tasks_retained"] == tasks


def test_provider_master_off_switch_503(monkeypatch):
    """
    SPEC §25.16 line 4926: "Registers as a provider in sidecar/providers/ with modular off-switch locus.four_level_emergency_protocol.enabled returning 503."
    """
    provider = DefaultFourLevelEmergencyProtocolProvider()

    switch = "locus.four_level_emergency_protocol.enabled"
    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    enabled, sw = provider.is_feature_enabled()
    assert enabled is False
    assert sw == switch

    res_eval = provider.evaluate_situation(disruption_hours=2.0)
    assert res_eval.get("status_code") == 503

    res_act = provider.activate_protocol(level=2)
    assert res_act.get("status_code") == 503

    res_deact = provider.deactivate_protocol()
    assert res_deact.get("status_code") == 503

    res_ov = provider.apply_scheduling_overrides(tasks=[])
    assert res_ov.get("status_code") == 503

    res_st = provider.get_status()
    assert res_st.get("status_code") == 503


def test_provider_swap_polymorphism():
    """
    SPEC §25.16 line 4926: "Registers as a provider in sidecar/providers/ with modular off-switch locus.four_level_emergency_protocol.enabled returning 503."
    """
    class MockCustomEmergencyProvider(BaseFourLevelEmergencyProtocolProvider):
        @property
        def name(self) -> str:
            return "mock_custom_emergency_provider"

        def is_feature_enabled(self) -> Tuple[bool, str]:
            return True, ""

        def evaluate_situation(
            self,
            disruption_hours: float = 0.0,
            disruption_days: int = 0,
            is_life_event: bool = False,
            trigger_reason: str = "",
        ) -> Dict[str, Any]:
            return {"mock": True, "level": 1}

        def activate_protocol(self, level: int, reason: str = "") -> Dict[str, Any]:
            return {"mock": True, "activated": level}

        def deactivate_protocol(self) -> Dict[str, Any]:
            return {"mock": True, "active": False}

        def apply_scheduling_overrides(
            self, tasks: List[Dict[str, Any]], level: Optional[int] = None
        ) -> Dict[str, Any]:
            return {"mock": True, "tasks": tasks}

        def get_status(self) -> Dict[str, Any]:
            return {"mock": True, "name": self.name}

    prov: BaseFourLevelEmergencyProtocolProvider = MockCustomEmergencyProvider()
    assert prov.name == "mock_custom_emergency_provider"
    assert prov.evaluate_situation()["mock"] is True
    assert prov.activate_protocol(level=2)["activated"] == 2
