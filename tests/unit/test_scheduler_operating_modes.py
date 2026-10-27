"""
SPEC §25.5-25.8 & §25.12: Unit tests for Operating Modes / Scheduler (F-0056 / US-86).
Tests:
- §25.5: Three-Layer Goal Stack (Outcome -> Project -> Task) and orphan detection
- §25.6: Action Gap Tracking and neglect alerts
- §25.7: Deferral Detection (3/5/8+ thresholds) and auto-parking
- §25.8: Lag Score and TWS Lag Bonuses
- §25.12: Six-Step Scheduling Algorithm with capacity filters & ultradian recovery buffers
- Modular off-switches and swappable provider interface
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

import sidecar.config as config
from sidecar.life_os.action_gap import (
    calculate_action_gap,
    evaluate_faction_action_gaps,
)
from sidecar.life_os.deferral import (
    DeferralAction,
    DeferralTracker,
)
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)
from sidecar.life_os.lag import (
    calculate_lag_score,
    calculate_tws_lag_bonus,
    compute_faction_lag_report,
)
from sidecar.life_os.scheduler import (
    CandidateTask,
    ScheduledBlock,
    SchedulerOperatingMode,
    SixStepSchedulerEngine,
)
from sidecar.providers.scheduler import (
    BaseSchedulerProvider,
    DefaultSchedulerProvider,
)


def test_three_layer_goal_stack_enforcement() -> None:
    """SPEC §25.5 line 4669: "Enforcement: every task MUST parent to a project; every project MUST parent to an outcome." """
    stack = ThreeLayerGoalStack()

    # Create root outcome
    vision = GoalNode(
        id="v-1",
        title="Master Autonomous Coding Agent Architecture",
        level=GoalStackLevel.VISION,
        faction="Craft",
    )
    # Create project
    milestone = GoalNode(
        id="p-1",
        title="Complete Operating Modes & Scheduler Subsystem",
        level=GoalStackLevel.MILESTONE,
        parent_id="v-1",
    )
    # Create concrete daily task
    task = GoalNode(
        id="t-1",
        title="Implement 6-step scheduler engine",
        level=GoalStackLevel.DAILY,
        parent_id="p-1",
    )
    stack.add_node(vision)
    stack.add_node(milestone)
    stack.add_node(task)

    # Valid task verification
    ok, msg = stack.validate_task("t-1")
    assert ok is True
    assert "Valid" in msg

    # Hierarchy validation
    report = stack.validate_hierarchy()
    assert report["valid"] is True
    assert report["orphan_count"] == 0

    # Add orphan daily task (no parent)
    orphan_task = GoalNode(
        id="t-orphan",
        title="Unparented floating task",
        level=GoalStackLevel.DAILY,
        parent_id=None,
    )
    stack.add_node(orphan_task)

    val_ok, val_err = stack.validate_task("t-orphan")
    assert val_ok is False
    assert "Orphan task detected" in val_err

    # Detect orphan tasks surfaces unparented node
    orphans = stack.detect_orphan_tasks()
    assert len(orphans) == 1
    assert orphans[0]["node_id"] == "t-orphan"
    assert orphans[0]["issue"] == "missing_milestone_parent"

    # Reparent orphan to milestone
    assert stack.reparent("t-orphan", "p-1") is True
    assert len(stack.detect_orphan_tasks()) == 0


def test_action_gap_tracking_and_alerts() -> None:
    """SPEC §25.6 line 4688: "ACTION GAP = declared_priority − (actual_hrs / target_hrs × 10)" """
    # Normal faction: declared 8.0, actual 16.0 / target 20.0 (ratio 0.8 * 10 = 8.0 -> gap = 0.0)
    gap_normal = calculate_action_gap(declared_priority=8.0, actual_hours=16.0, target_hours=20.0)
    assert round(gap_normal, 2) == 0.0

    # Neglected faction: declared 9.0, actual 2.0 / target 20.0 (ratio 0.1 * 10 = 1.0 -> gap = 8.0)
    gap_neglected = calculate_action_gap(declared_priority=9.0, actual_hours=2.0, target_hours=20.0)
    assert round(gap_neglected, 2) == 8.0

    # Batch faction evaluation with alerts (> 5.0)
    factions_input = {
        "Craft": {"declared_priority": 8.0, "actual_hours": 18.0, "target_hours": 20.0},
        "Health": {"declared_priority": 9.0, "actual_hours": 3.0, "target_hours": 15.0},  # gap: 9 - 2 = 7.0 (ALERT)
        "Leverage": {"declared_priority": 6.0, "actual_hours": 10.0, "target_hours": 10.0},
        "Expression": {"declared_priority": 5.0, "actual_hours": 2.0, "target_hours": 10.0},  # gap: 5 - 2 = 3.0 (OK)
    }
    reports = evaluate_faction_action_gaps(factions_input)
    assert len(reports) == 4

    health_report = next(r for r in reports if r.faction == "Health")
    assert health_report.alert is True
    assert health_report.action_gap == 7.0
    assert "ALERT" in health_report.message

    craft_report = next(r for r in reports if r.faction == "Craft")
    assert craft_report.alert is False


def test_deferral_detection_escalation_thresholds() -> None:
    """SPEC §25.7 line 4707: "3× defer → warn: 'Consider dropping or delegating'; 5× defer → escalate: surfaced at weekly review; 8× defer → flag as phantom task: auto-parked with review note" """
    tracker = DeferralTracker()
    task_id = "task-stubborn-1"

    # 1st and 2nd deferral -> Normal
    r1 = tracker.record_deferral(task_id, reason="busy with fires")
    assert r1.deferral_count == 1
    assert r1.action == DeferralAction.NORMAL
    assert r1.is_parked is False

    r2 = tracker.record_deferral(task_id, reason="postponed")
    assert r2.deferral_count == 2
    assert r2.action == DeferralAction.NORMAL

    # 3rd deferral -> Warn
    r3 = tracker.record_deferral(task_id, reason="postponed again")
    assert r3.deferral_count == 3
    assert r3.action == DeferralAction.WARN
    assert "Consider dropping or delegating" in r3.message

    # 5th deferral -> Escalate
    tracker.record_deferral(task_id)  # 4th
    r5 = tracker.record_deferral(task_id, reason="missed deadline")
    assert r5.deferral_count == 5
    assert r5.action == DeferralAction.ESCALATE
    assert "surfaced at weekly review" in r5.message
    assert r5.is_parked is False

    # 8th deferral -> Phantom park
    tracker.record_deferral(task_id)  # 6th
    tracker.record_deferral(task_id)  # 7th
    r8 = tracker.record_deferral(task_id, reason="chronic avoidance")
    assert r8.deferral_count == 8
    assert r8.action == DeferralAction.PHANTOM_PARK
    assert r8.is_parked is True
    assert "phantom task" in r8.message

    parked = tracker.list_parked_tasks()
    assert len(parked) == 1
    assert parked[0]["task_id"] == task_id


def test_lag_score_and_tws_lag_bonus() -> None:
    """SPEC §25.8 line 4728: "LAG SCORE = cumulative hours a faction is behind its weekly target." """
    # Lag > 6h -> Crisis (+4.0)
    crisis_rep = compute_faction_lag_report("Craft", target_hours=20.0, actual_hours=13.0)
    assert crisis_rep.lag_hours == 7.0
    assert crisis_rep.tws_lag_bonus == 4.0
    assert crisis_rep.is_crisis is True

    # Lag > 3h and <= 6h -> (+2.0)
    moderate_rep = compute_faction_lag_report("Health", target_hours=15.0, actual_hours=11.0)
    assert moderate_rep.lag_hours == 4.0
    assert moderate_rep.tws_lag_bonus == 2.0
    assert moderate_rep.is_crisis is False

    # Ahead of target (actual > target) -> (-1.0)
    ahead_rep = compute_faction_lag_report("Leverage", target_hours=10.0, actual_hours=12.0)
    assert ahead_rep.lag_hours == -2.0
    assert ahead_rep.tws_lag_bonus == -1.0
    assert ahead_rep.is_ahead is True

    # On target / within 0 to 3h -> (0.0)
    neutral_rep = compute_faction_lag_report("Expression", target_hours=10.0, actual_hours=8.0)
    assert neutral_rep.lag_hours == 2.0
    assert neutral_rep.tws_lag_bonus == 0.0


def test_six_step_scheduler_engine_pipeline() -> None:
    """SPEC §25.12 line 4818: "STEP 1: Operating Mode Capacity Filter; STEP 2: Task Weight Score (TWS) Ranking; STEP 3: Operating Mode Time-Block Grid Allocation" """
    stack = ThreeLayerGoalStack()
    v = GoalNode(id="v1", title="Vision", level=GoalStackLevel.VISION, faction="Craft")
    p = GoalNode(id="p1", title="Project", level=GoalStackLevel.MILESTONE, parent_id="v1")
    t1 = GoalNode(id="t1", title="Task 1", level=GoalStackLevel.DAILY, parent_id="p1")
    t2 = GoalNode(id="t2", title="Task 2", level=GoalStackLevel.DAILY, parent_id="p1")
    t3 = GoalNode(id="t3", title="Task 3", level=GoalStackLevel.DAILY, parent_id="p1")
    for n in (v, p, t1, t2, t3):
        stack.add_node(n)

    engine = SixStepSchedulerEngine(goal_stack=stack)

    candidates = [
        CandidateTask(id="t1", title="Fix critical database index", difficulty=8, leverage=9, urgency=8, project_id="p1"),
        CandidateTask(id="t2", title="Review design document", difficulty=5, leverage=6, urgency=5, project_id="p1"),
        CandidateTask(id="t3", title="Trivial typo fix", difficulty=2, leverage=2, urgency=3, project_id="p1"),
    ]

    # Test DEEP_WORK mode (DCS 7.5): max diff 9, all 3 tasks eligible
    res_deep = engine.generate_schedule(dcs=7.5, candidate_tasks=candidates, enforce_goal_stack=True)
    assert res_deep["mode"] == "DEEP_WORK"
    assert res_deep["max_difficulty"] == 9
    assert res_deep["eligible_tasks"] == 3
    assert res_deep["goal_stack_validation"]["passed"] is True

    # Verify ultradian buffers are inserted
    deep_blocks = [b for b in res_deep["timeline"] if b["block_type"] == "deep"]
    recovery_blocks = [b for b in res_deep["timeline"] if b["block_type"] == "recovery"]
    assert len(deep_blocks) == 3
    assert len(recovery_blocks) == 3
    assert all(b["duration_minutes"] == 20 for b in recovery_blocks)

    # Test SURVIVAL mode (DCS 1.5): max diff 2, only t3 eligible
    res_survival = engine.generate_schedule(dcs=1.5, candidate_tasks=candidates, enforce_goal_stack=False)
    assert res_survival["mode"] == "SURVIVAL"
    assert res_survival["max_difficulty"] == 2
    assert res_survival["eligible_tasks"] == 1
    assert res_survival["scheduled_tasks_count"] == 1


def test_scheduler_provider_swappability_and_off_switches() -> None:
    """SPEC §25.5 line 4675: "locus.life_os.goal_stack.enabled. Off → no goal enforcement; tasks are free-floating." """
    # Verify swappability with custom provider
    class CustomSchedulerProvider(BaseSchedulerProvider):
        @property
        def name(self) -> str:
            return "custom_scheduler"

        def is_feature_enabled(self, feature: str = "scheduler") -> tuple[bool, str]:
            return True, ""

        def validate_goal_stack(self) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def evaluate_action_gaps(self, factions_data: dict[str, dict[str, float]]) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def record_deferral(self, task_id: str, reason: str = "") -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def compute_lag_bonus(self, lag_hours: float) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def generate_schedule(self, dcs: float, candidate_tasks: list[dict[str, Any]], enforce_goal_stack: bool = True) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "custom_active": True}

    custom = CustomSchedulerProvider()
    assert custom.name == "custom_scheduler"
    assert custom.validate_goal_stack()["custom"] is True

    # Test DefaultSchedulerProvider off-switch enforcement
    provider = DefaultSchedulerProvider()

    # Disable master scheduler switch
    old_get = config.get
    try:
        config.get = lambda k, default=None: False if k == "locus.operating_modes_scheduler.enabled" else old_get(k, default)
        res = provider.get_status()
        assert res.get("status_code") == 503
        assert res["disabled"] == "locus.operating_modes_scheduler.enabled"

        # Disable goal_stack sub-switch
        config.get = lambda k, default=None: False if k == "locus.life_os.goal_stack.enabled" else old_get(k, default)
        res_gs = provider.validate_goal_stack()
        assert res_gs.get("status_code") == 503
        assert res_gs["disabled"] == "locus.life_os.goal_stack.enabled"

        # Disable action_gap sub-switch
        config.get = lambda k, default=None: False if k == "locus.life_os.action_gap.enabled" else old_get(k, default)
        res_ag = provider.evaluate_action_gaps({})
        assert res_ag.get("status_code") == 503
        assert res_ag["disabled"] == "locus.life_os.action_gap.enabled"

        # Disable deferral sub-switch
        config.get = lambda k, default=None: False if k == "locus.life_os.deferral.enabled" else old_get(k, default)
        res_def = provider.record_deferral("t1")
        assert res_def.get("status_code") == 503
        assert res_def["disabled"] == "locus.life_os.deferral.enabled"
    finally:
        config.get = old_get
