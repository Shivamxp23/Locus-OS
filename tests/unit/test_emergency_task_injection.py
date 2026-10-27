"""
SPEC §25.9 lines 4740-4758: Unit tests for Emergency Task Injection (F-0111 / US-87).
Tests:
- Emergency tasks bypass TWS ordering and insert at top
- Multiple emergency tasks sorted by Faction Crisis Hierarchy (Health > Leverage > Craft > Expression)
- Disabled bypass sorts strictly by TWS
- Timeline injection functionality
- Swappable provider interface and modular HTTP 503 off-switches
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

import sidecar.config as config
from sidecar.life_os.emergency import (
    CRISIS_FACTION_ORDER,
    EmergencyTask,
    EmergencyTaskInjector,
)
from sidecar.providers.emergency import (
    BaseEmergencyTaskProvider,
    DefaultEmergencyTaskProvider,
)


def test_emergency_tasks_bypass_tws_ordering() -> None:
    """SPEC §25.9 line 4749: "EMERGENCY INJECTION: tasks tagged EMERGENCY bypass TWS ordering and are inserted at the top of the schedule, respecting only faction crisis hierarchy." """
    injector = EmergencyTaskInjector()

    tasks = [
        EmergencyTask(id="norm-high-tws", title="High Priority Normal Task", faction="Craft", tws=9.5, is_emergency=False),
        EmergencyTask(id="norm-med-tws", title="Medium Priority Normal Task", faction="Leverage", tws=6.0, is_emergency=False),
        EmergencyTask(id="em-low-tws", title="Urgent Server Outage Fix", faction="Health", tws=3.0, is_emergency=True),
    ]

    # Prioritize with bypass_tws=True
    sorted_tasks = injector.prioritize_tasks(tasks, bypass_tws=True)
    assert len(sorted_tasks) == 3
    # Emergency task with TWS 3.0 must appear FIRST before normal task with TWS 9.5
    assert sorted_tasks[0].id == "em-low-tws"
    assert sorted_tasks[1].id == "norm-high-tws"
    assert sorted_tasks[2].id == "norm-med-tws"


def test_emergency_tasks_faction_crisis_hierarchy() -> None:
    """SPEC §25.9 line 4749: "respecting only faction crisis hierarchy." """
    injector = EmergencyTaskInjector()

    tasks = [
        EmergencyTask(id="em-craft", title="Craft Emergency", faction="Craft/Skills", tws=8.0, is_emergency=True),
        EmergencyTask(id="em-health", title="Health Crisis", faction="Health/Stability", tws=2.0, is_emergency=True),
        EmergencyTask(id="em-expression", title="Expression Emergency", faction="Expression/Explore", tws=9.0, is_emergency=True),
        EmergencyTask(id="em-leverage", title="Leverage Emergency", faction="Leverage/Money", tws=5.0, is_emergency=True),
    ]

    sorted_tasks = injector.prioritize_tasks(tasks, bypass_tws=True)
    # Expected crisis order: Health (0) -> Leverage (1) -> Craft (2) -> Expression (3)
    assert [t.id for t in sorted_tasks] == [
        "em-health",
        "em-leverage",
        "em-craft",
        "em-expression",
    ]


def test_emergency_bypass_off_state() -> None:
    """SPEC §25.9 line 4755: "Off → emergency-tagged tasks sort by TWS like everything else." """
    injector = EmergencyTaskInjector()

    tasks = [
        EmergencyTask(id="em-low-tws", title="Low TWS Emergency", faction="Health", tws=2.0, is_emergency=True),
        EmergencyTask(id="norm-high-tws", title="High TWS Normal", faction="Craft", tws=8.5, is_emergency=False),
        EmergencyTask(id="em-mid-tws", title="Mid TWS Emergency", faction="Craft", tws=5.0, is_emergency=True),
    ]

    # When bypass_tws is False, tasks sort strictly by TWS descending
    sorted_tasks = injector.prioritize_tasks(tasks, bypass_tws=False)
    assert [t.id for t in sorted_tasks] == [
        "norm-high-tws",
        "em-mid-tws",
        "em-low-tws",
    ]


def test_emergency_timeline_injection() -> None:
    """SPEC §25.9 line 4749: "inserted at the top of the schedule" """
    injector = EmergencyTaskInjector()

    timeline = [
        {"block_type": "deep", "duration_minutes": 90, "task_id": "scheduled-1"},
        {"block_type": "light", "duration_minutes": 30, "task_id": "scheduled-2"},
    ]
    emergency = EmergencyTask(
        id="em-immediate",
        title="Production Incident",
        faction="Health",
        estimated_minutes=60,
        is_emergency=True,
    )

    injected = injector.inject_into_schedule(timeline, emergency, at_index=0)
    assert len(injected) == 3
    assert injected[0]["task_id"] == "em-immediate"
    assert "[EMERGENCY]" in injected[0]["task_title"]
    assert injected[1]["task_id"] == "scheduled-1"


def test_emergency_provider_swappability_and_off_switches() -> None:
    """SPEC §25.9 line 4755: "Swappable / off state: locus.life_os.emergency.enabled." """
    # Swappability verification
    class CustomEmergencyProvider(BaseEmergencyTaskProvider):
        @property
        def name(self) -> str:
            return "custom_emergency"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def prioritize_tasks(self, tasks: list[dict[str, Any]], bypass_tws: bool | None = None) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def inject_task(self, timeline: list[dict[str, Any]], task: dict[str, Any], at_index: int = 0) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "custom_active": True}

    custom = CustomEmergencyProvider()
    assert custom.name == "custom_emergency"
    assert custom.get_status()["custom_active"] is True

    # DefaultEmergencyTaskProvider off-switches
    provider = DefaultEmergencyTaskProvider()

    old_get = config.get
    try:
        # Disable master emergency switch
        config.get = lambda k, default=None: False if k == "locus.emergency_task_injection.enabled" else old_get(k, default)
        res1 = provider.prioritize_tasks([])
        assert res1.get("status_code") == 503
        assert res1["disabled"] == "locus.emergency_task_injection.enabled"

        # Disable life_os emergency switch
        config.get = lambda k, default=None: False if k == "locus.life_os.emergency.enabled" else old_get(k, default)
        res2 = provider.inject_task([], {})
        assert res2.get("status_code") == 503
        assert res2["disabled"] == "locus.life_os.emergency.enabled"
    finally:
        config.get = old_get
