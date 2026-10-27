"""
SPEC §25.12 lines 4801-4882: Unit tests for Goal Tracker 3-Layer Stack & Faction Balancer (F-0057 / US-90).
Tests:
- Validation of three-layer goal stack (Outcome -> Project -> Task)
- Orphan task and orphan project detection
- Faction balance constraint evaluation against targets (Craft 40%, Health 25%, Leverage 20%, Expression 15% ±5%)
- Greedy task assignment constraint gating under Step 4
- Six-step scheduler integration with faction balancer and goal stack
- Provider swappability and modular off-switches returning HTTP 503
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

import sidecar.config as config
from sidecar.life_os.faction_balancer import (
    SCHEDULER_FACTION_TARGETS,
    FactionBalancer,
    canonicalize_faction,
)
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)
from sidecar.life_os.scheduler import (
    CandidateTask,
    SixStepSchedulerEngine,
)
from sidecar.providers.goal_tracker import (
    BaseGoalTrackerProvider,
    DefaultGoalTrackerProvider,
)


def test_three_layer_goal_stack_hierarchy_validation() -> None:
    """SPEC §25.12 line 4874: "ASSERT t.project_id IS NOT NULL, error=\"Orphan task detected\"" """
    stack = ThreeLayerGoalStack()

    # Create valid tree: Outcome (Vision) -> Project (Milestone) -> Task (Daily)
    vision = GoalNode(id="vis-1", title="Master AI Systems", level=GoalStackLevel.VISION, faction="Craft")
    project = GoalNode(id="proj-1", title="Build Locus Sidecar", level=GoalStackLevel.MILESTONE, parent_id="vis-1")
    task = GoalNode(id="task-1", title="Implement Goal Tracker", level=GoalStackLevel.DAILY, parent_id="proj-1")

    stack.add_node(vision)
    stack.add_node(project)
    stack.add_node(task)

    valid, msg = stack.validate_task("task-1")
    assert valid is True
    assert "Valid" in msg

    # Orphan task test: remove parent project
    orphan_task = GoalNode(id="task-orphan", title="Unparented Task", level=GoalStackLevel.DAILY, parent_id=None)
    stack.add_node(orphan_task)
    v_orphan, msg_orphan = stack.validate_task("task-orphan")
    assert v_orphan is False
    assert "Orphan task detected" in msg_orphan


def test_orphan_project_detection() -> None:
    """SPEC §25.12 line 4875: "ASSERT Project(t.project_id).outcome_id IS NOT NULL, error=\"Orphan project detected\"" """
    stack = ThreeLayerGoalStack()

    # Project with no parent outcome
    orphan_proj = GoalNode(id="proj-orphan", title="Rogue Project", level=GoalStackLevel.MILESTONE, parent_id=None)
    sub_task = GoalNode(id="task-sub", title="Sub Task", level=GoalStackLevel.DAILY, parent_id="proj-orphan")

    stack.add_node(orphan_proj)
    stack.add_node(sub_task)

    valid, msg = stack.validate_task("task-sub")
    assert valid is False
    assert "Orphan project detected" in msg


def test_faction_balancer_weekly_distribution_evaluation() -> None:
    """SPEC §25.12 line 4845: "Craft Target 40% (Tolerance ±5%), Health Target 25%, Leverage Target 20%, Expression Target 15%" """
    balancer = FactionBalancer()

    # Perfect distribution for 100 hours (6000 mins):
    # Craft 40h (2400m), Health 25h (1500m), Leverage 20h (1200m), Expression 15h (900m)
    allocs = {
        "Craft": 2400.0,
        "Health": 1500.0,
        "Leverage": 1200.0,
        "Expression": 900.0,
    }

    report = balancer.evaluate_allocations(allocs)
    assert report.compliant is True
    assert len(report.under_represented) == 0
    assert len(report.over_represented) == 0
    assert report.actual_fractions["Craft"] == 0.40

    # Skewed distribution: Craft 80% (over-represented), Health 5% (under-represented)
    skewed_allocs = {
        "Craft": 4800.0,
        "Health": 300.0,
        "Leverage": 500.0,
        "Expression": 400.0,
    }
    skewed_report = balancer.evaluate_allocations(skewed_allocs)
    assert skewed_report.compliant is False
    assert "Craft" in skewed_report.over_represented
    assert "Health" in skewed_report.under_represented


def test_faction_balancer_assignment_rule_gating() -> None:
    """SPEC §25.12 line 4853: "Greedily assign highest TWS task to next open Deep block UNLESS assigning that task causes that faction's weekly allocated hours to exceed Target + Tolerance while an under-represented faction has eligible tasks waiting." """
    balancer = FactionBalancer()

    # Craft already heavily allocated: 50% of 1000m = 500m (target is 40% ± 5% -> max 45%)
    current_allocs = {
        "Craft": 500.0,
        "Health": 100.0,  # 10% vs 25% target -> severely under-represented
        "Leverage": 200.0,
        "Expression": 200.0,
    }

    # Propose another 90m Craft task while Health has eligible tasks waiting
    allowed, msg = balancer.is_assignment_allowed(
        candidate_faction="Craft",
        proposed_minutes=90.0,
        current_allocations=current_allocs,
        waiting_factions={"Health"},
    )
    assert allowed is False
    assert "blocked" in msg.lower()
    assert "Health" in msg

    # Propose Health task instead -> must be allowed
    allowed_health, _ = balancer.is_assignment_allowed(
        candidate_faction="Health",
        proposed_minutes=90.0,
        current_allocations=current_allocs,
        waiting_factions={"Craft"},
    )
    assert allowed_health is True


def test_six_step_scheduler_engine_with_balancer_and_goal_stack() -> None:
    """SPEC §25.12 lines 4801-4879: Six-step scheduler integrates operating mode, faction balance, ultradian buffers, and goal stack."""
    stack = ThreeLayerGoalStack()
    vision = GoalNode(id="v1", title="Health Master", level=GoalStackLevel.VISION, faction="Health")
    proj = GoalNode(id="p1", title="Cardio Routine", level=GoalStackLevel.MILESTONE, parent_id="v1")
    task_ok = GoalNode(id="t1", title="Morning Run", level=GoalStackLevel.DAILY, parent_id="p1")

    stack.add_node(vision)
    stack.add_node(proj)
    stack.add_node(task_ok)

    engine = SixStepSchedulerEngine(goal_stack=stack)

    candidates = [
        CandidateTask(
            id="t1",
            title="Morning Run",
            faction="Health",
            difficulty=3,
            leverage=6,
            urgency=8,
            consequence=7,
        )
    ]

    res = engine.generate_schedule(dcs=5.0, candidate_tasks=candidates, enforce_goal_stack=True)
    assert res["status"] == "ok"
    assert res["mode"] == "NORMAL"
    assert res["scheduled_tasks_count"] == 1
    assert res["goal_stack_validation"]["passed"] is True
    assert "faction_balance_evaluation" in res


def test_goal_tracker_provider_modular_off_switches() -> None:
    """SPEC §25.12: Modular off-switches returning HTTP 503."""
    provider = DefaultGoalTrackerProvider()

    assert provider.get_status()["status"] == "ok"

    # Test locus.goal_tracker_3_layer_stack.enabled
    config.set("locus.goal_tracker_3_layer_stack.enabled", False)
    res = provider.validate_task_hierarchy("task-1")
    assert res.get("status_code") == 503
    assert res.get("disabled") == "locus.goal_tracker_3_layer_stack.enabled"
    config.set("locus.goal_tracker_3_layer_stack.enabled", True)

    # Test locus.life_os.goal_tracker.enabled
    config.set("locus.life_os.goal_tracker.enabled", False)
    res2 = provider.evaluate_faction_balance({})
    assert res2.get("status_code") == 503
    assert res2.get("disabled") == "locus.life_os.goal_tracker.enabled"
    config.set("locus.life_os.goal_tracker.enabled", True)


def test_swappable_goal_tracker_provider_contract() -> None:
    """SPEC §25.12: Swappable Goal Tracker Provider contract."""
    class CustomGoalTrackerProvider(BaseGoalTrackerProvider):
        @property
        def name(self) -> str:
            return "custom_goal_tracker"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def validate_task_hierarchy(self, task_id: str) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def detect_orphans(self) -> dict[str, Any]:
            return {"status": "ok", "orphans": []}

        def evaluate_faction_balance(self, allocations_minutes: dict[str, float]) -> dict[str, Any]:
            return {"status": "ok"}

        def check_assignment_allowed(
            self,
            candidate_faction: str,
            proposed_minutes: float,
            current_allocations: dict[str, float],
            waiting_factions: list[str],
        ) -> dict[str, Any]:
            return {"status": "ok", "allowed": True}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "provider": self.name}

    custom = CustomGoalTrackerProvider()
    assert custom.name == "custom_goal_tracker"
    assert custom.validate_task_hierarchy("t")["custom"] is True
