"""tests/test_life_os_advanced.py - Test suite for Life OS Advanced Mechanics.

Tests:
- GoalStackManager (§25.5)
- ActionGap (§25.6)
- Deferral (§25.7)
- FactionLag (§25.8)
- EmergencyInjector (§25.9)
- ExhaustionPredictor (§25.10)
- WeeklyFactionRebalance (§25.11)
- SixStepScheduler (§25.12)
- ReviewCadenceManager (§25.13)
- GoalStackEnforcer (§25.14)
- CrossFactionAllocator (§25.15)
- EmergencyProtocolEngine (§25.16)
- TagManager (§27.4)
"""

import pytest

from sidecar.life_os.factions import Faction
from sidecar.life_os.modes import OperatingMode
from sidecar.life_os.goal_stack import GoalStackManager, GoalTask, Project, Outcome, GoalStatus
from sidecar.life_os.action_gap import calculate_action_gap, evaluate_faction_action_gaps
from sidecar.life_os.deferral import DeferralTracker, DeferralAction, evaluate_deferral_thresholds
from sidecar.life_os.lag import calculate_lag_score, get_lag_tws_bonus, compute_all_faction_lags
from sidecar.life_os.emergency import EmergencyInjector, ScheduledTaskEntry
from sidecar.life_os.exhaustion import ExhaustionPredictor
from sidecar.life_os.rebalance import compute_weekly_rebalance, WeeklyFactionRebalancer
from sidecar.life_os.faction_balancer import FactionBalancer, SCHEDULER_FACTION_TARGETS
from sidecar.life_os.scheduler import SixStepScheduler, SchedulerProvider, calculate_scheduler_tws, BlockType
from sidecar.life_os.reviews import ReviewCadenceManager, ReviewCadenceType
from sidecar.life_os.goal_enforcement import GoalStackEnforcer
from sidecar.life_os.cross_faction import CrossFactionAllocator
from sidecar.life_os.emergency_protocol import EmergencyProtocolEngine, EmergencyLevel
from sidecar.vault.tag_manager import TagManager, validate_and_normalize_tags, lookup_domain_for_category


def test_goal_stack_ancestry_and_orphans():
    mgr = GoalStackManager()
    outcome = mgr.add_outcome("Master AI Systems", Faction.CRAFT)
    project = mgr.add_project("Build Locus OS", outcome_id=outcome.id)
    task = mgr.add_task("Implement Scheduler", project_id=project.id)

    valid, err = mgr.validate_task_ancestry(task.id)
    assert valid is True
    assert err is None
    assert len(mgr.get_orphan_tasks()) == 0

    # Create orphan task
    orphan = mgr.add_task("Random unattached idea")
    valid_o, err_o = mgr.validate_task_ancestry(orphan.id)
    assert valid_o is False
    assert "no parent project" in err_o
    assert len(mgr.get_orphan_tasks()) == 1

    # Reparent task
    mgr.reparent_task(orphan.id, project.id)
    valid_reparented, _ = mgr.validate_task_ancestry(orphan.id)
    assert valid_reparented is True
    assert len(mgr.get_orphan_tasks()) == 0


def test_action_gap_tracking():
    # If priority is 9.0, target is 10h, and actual is 2h (ratio 0.2 -> 2.0)
    # Gap = 9.0 - 2.0 = 7.0 (> 5.0 alert)
    gap = calculate_action_gap(declared_priority=9.0, actual_hours=2.0, target_hours=10.0)
    assert gap == 7.0

    metrics = {
        Faction.HEALTH: (9.0, 2.0, 10.0),
        Faction.CRAFT: (8.0, 10.0, 10.0),
    }
    alerts = evaluate_faction_action_gaps(metrics, threshold=5.0)
    assert len(alerts) == 1
    assert alerts[0].faction == Faction.HEALTH
    assert alerts[0].severity == "warning"


def test_deferral_thresholds_3_5_8():
    tracker = DeferralTracker()
    tid = "task-101"

    # 1st and 2nd deferral: normal
    r1 = tracker.record_deferral(tid, "Write Docs")
    assert r1.action == DeferralAction.NONE
    r2 = tracker.record_deferral(tid, "Write Docs")
    assert r2.action == DeferralAction.NONE

    # 3rd deferral: warn
    r3 = tracker.record_deferral(tid, "Write Docs")
    assert r3.action == DeferralAction.WARN
    assert r3.is_parked is False

    # 4th deferral: warn
    r4 = tracker.record_deferral(tid, "Write Docs")
    assert r4.action == DeferralAction.WARN

    # 5th deferral: escalate to weekly review
    r5 = tracker.record_deferral(tid, "Write Docs")
    assert r5.action == DeferralAction.ESCALATE
    assert tid in tracker.get_weekly_review_escalations()

    # 8th deferral: auto-park as phantom task
    for _ in range(3):
        r_last = tracker.record_deferral(tid, "Write Docs")
    assert r_last.action == DeferralAction.PARK_PHANTOM
    assert r_last.is_parked is True
    assert tracker.is_task_parked(tid) is True


def test_faction_lag_and_tws_bonus():
    # Target 10h, actual 3h -> lag 7h (>6h -> +4 crisis)
    lag = calculate_lag_score(10.0, 3.0)
    assert lag == 7.0
    assert get_lag_tws_bonus(lag) == 4.0

    # Lag 4h -> +2
    assert get_lag_tws_bonus(4.0) == 2.0
    # Lag 1h -> 0.0
    assert get_lag_tws_bonus(1.0) == 0.0
    # Ahead of schedule (lag -2h) -> -1.0
    assert get_lag_tws_bonus(-2.0) == -1.0


def test_emergency_task_injection():
    injector = EmergencyInjector(enabled=True)
    t1 = GoalTask(id="1", project_id=None, title="Normal Coding", difficulty=5.0)
    t2 = GoalTask(id="2", project_id=None, title="Health Emergency", difficulty=6.0)
    t3 = GoalTask(id="3", project_id=None, title="Leverage Outage", difficulty=7.0)

    normal = [ScheduledTaskEntry(task=t1, faction=Faction.CRAFT, tws=8.5)]
    emergencies = [
        ScheduledTaskEntry(task=t3, faction=Faction.LEVERAGE, tws=7.0, is_emergency=True),
        ScheduledTaskEntry(task=t2, faction=Faction.HEALTH, tws=6.5, is_emergency=True),
    ]

    ordered = injector.order_schedule(normal, emergencies)
    # Emergency tasks come first sorted by crisis hierarchy (Health > Leverage)
    assert ordered[0].task.id == "2"  # Health emergency first
    assert ordered[1].task.id == "3"  # Leverage emergency second
    assert ordered[2].task.id == "1"  # Normal task third


def test_exhaustion_predictor():
    predictor = ExhaustionPredictor(enabled=True)
    # High-D: 4h, Sleep deficit: 3h, Stress: 8.5
    # drop = (4/2)*0.6 + 3*0.8 + (8.5-6)*0.5 = 1.2 + 2.4 + 1.25 = 4.85 (>2.0 risk!)
    pred = predictor.predict(
        current_dcs=6.5,
        consecutive_high_d_hours=4.0,
        sleep_deficit_hours=3.0,
        stress_trend_score=8.5,
    )
    assert pred.is_at_risk is True
    assert pred.predicted_dcs_drop > 2.0
    assert pred.recommended_mode in (OperatingMode.SURVIVAL, OperatingMode.RECOVERY)


def test_weekly_faction_rebalance():
    actual_hours = {
        Faction.CRAFT: 35.0,     # Heavily over-allocated
        Faction.HEALTH: 2.0,     # Starved
        Faction.LEVERAGE: 5.0,   # Starved
        Faction.EXPRESSION: 8.0,
    }
    rebalancer = WeeklyFactionRebalancer(enabled=True)
    new_weights = rebalancer.rebalance(actual_hours)
    # Health and Leverage should see increased weight for next week
    assert new_weights[Faction.HEALTH] > SCHEDULER_FACTION_TARGETS[Faction.HEALTH]
    assert round(sum(new_weights.values()), 2) == 1.0


def test_six_step_scheduler_and_provider():
    mgr = GoalStackManager()
    out = mgr.add_outcome("Product Excellence", Faction.CRAFT)
    proj = mgr.add_project("Core Engine", outcome_id=out.id)
    t1 = mgr.add_task("High-pri Kernel Work", project_id=proj.id, difficulty=8.0, leverage=8.0, urgency=9.0, consequence=8.0)
    t2 = mgr.add_task("Refactoring", project_id=proj.id, difficulty=4.0, leverage=5.0, urgency=3.0, consequence=3.0)

    scheduler = SixStepScheduler(goal_manager=mgr)
    task_factions = {t1.id: Faction.CRAFT, t2.id: Faction.CRAFT}

    # At DCS 7.5 (DEEP_WORK mode):
    manifest = scheduler.generate_schedule(
        dcs=7.5,
        task_pool=[t1, t2],
        task_factions=task_factions,
    )
    assert manifest.operating_mode == OperatingMode.DEEP_WORK
    assert manifest.validation_passed is True
    # Should include Deep blocks and Recovery buffer
    deep_blocks = [b for b in manifest.blocks if b.block_type == BlockType.DEEP]
    recovery_blocks = [b for b in manifest.blocks if b.block_type == BlockType.RECOVERY]
    assert len(deep_blocks) >= 1
    assert len(recovery_blocks) >= 1

    # Test Provider interface
    prov = SchedulerProvider()
    prov_manifest = prov.plan_day(dcs=5.0, tasks=[t1, t2], task_factions=task_factions)
    assert prov_manifest.operating_mode == OperatingMode.NORMAL


def test_review_cadence_system():
    mgr = ReviewCadenceManager()
    briefing = mgr.get_morning_briefing_prompt(orphan_task_count=2)
    assert briefing is not None
    assert briefing.cadence == ReviewCadenceType.DAILY_STANDUP
    assert any("orphan" in c for c in briefing.check_items)

    retro = mgr.get_weekly_retro_prompt(escalated_tasks=["t1", "t2"])
    assert retro is not None
    assert retro.cadence == ReviewCadenceType.WEEKLY_RETROSPECTIVE
    assert len(retro.action_items) == 1


def test_goal_stack_enforcement():
    enforcer = GoalStackEnforcer(enabled=True)
    mgr = GoalStackManager()
    out = mgr.add_outcome("Health Milestone", Faction.HEALTH)
    proj = mgr.add_project("Marathon Training", outcome_id=out.id)
    good_task = mgr.add_task("10k Run", project_id=proj.id)
    orphan_task = mgr.add_task("Drifted Task", project_id=None)

    valid_good, err_good = enforcer.enforce_task(good_task, mgr)
    assert valid_good is True
    assert err_good is None

    valid_orphan, err_orphan = enforcer.enforce_task(orphan_task, mgr)
    assert valid_orphan is False
    assert "Violation" in err_orphan

    report = enforcer.audit_all(mgr)
    assert report.is_valid is False
    assert len(report.orphan_tasks) == 1


def test_cross_faction_allocator():
    allocator = CrossFactionAllocator(enabled=True, default_primary_ratio=0.7)
    alloc = allocator.allocate(
        task_id="cross-1",
        total_hours=10.0,
        primary_faction=Faction.CRAFT,
        secondary_faction=Faction.LEVERAGE,
    )
    assert alloc.primary_hours == 7.0
    assert alloc.secondary_hours == 3.0

    totals = allocator.accumulate_allocations([alloc])
    assert totals[Faction.CRAFT] == 7.0
    assert totals[Faction.LEVERAGE] == 3.0
    assert totals[Faction.HEALTH] == 0.0


def test_emergency_protocol_levels():
    proto = EmergencyProtocolEngine(enabled=True)

    # Level 1: Minor
    s1 = proto.trigger_emergency(EmergencyLevel.LEVEL_1_MINOR, "Minor alert")
    assert s1.schedule_action == "notify_user"
    assert proto.is_action_allowed(Faction.CRAFT) is True

    # Level 3: Severe crisis (Only Health & Leverage allowed)
    s3 = proto.trigger_emergency(EmergencyLevel.LEVEL_3_SEVERE, "Server outage", Faction.LEVERAGE)
    assert s3.schedule_action == "clear_discretionary_schedule"
    assert proto.is_action_allowed(Faction.LEVERAGE) is True
    assert proto.is_action_allowed(Faction.CRAFT) is False

    # Level 4: Catastrophic crisis (Only Health allowed, tool lock)
    s4 = proto.trigger_emergency(EmergencyLevel.LEVEL_4_CRISIS, "Medical emergency", Faction.HEALTH)
    assert s4.tool_lock_enabled is True
    assert proto.is_action_allowed(Faction.HEALTH) is True
    assert proto.is_action_allowed(Faction.LEVERAGE) is False

    # Resolve
    proto.resolve_emergency()
    assert proto.is_action_allowed(Faction.CRAFT) is True


def test_tag_manager_hierarchy():
    tags = [
        "#coding",
        "exercise",
        "#domain/leverage/automation",
        "#expression/writing/blog",
    ]
    normalized = validate_and_normalize_tags(tags)
    assert "#domain/craft/coding" in normalized
    assert "#domain/health/exercise" in normalized
    assert "#domain/leverage/automation" in normalized
    assert "#expression/writing/blog" in normalized

    tm = TagManager()
    norm2 = tm.normalize(["#music"])
    assert norm2 == ["#domain/expression/music"]


# -----------------------------------------------------------------------------
# Cross-Boundary Integration Tests
# -----------------------------------------------------------------------------

def test_six_step_scheduler_integration():
    """Integration test: Scheduler runs with FactionBalancer constraint solver over multi-day queue."""
    mgr = GoalStackManager()
    out_c = mgr.add_outcome("Engine", Faction.CRAFT)
    out_h = mgr.add_outcome("Fitness", Faction.HEALTH)
    p_c = mgr.add_project("Build Locus", outcome_id=out_c.id)
    p_h = mgr.add_project("Ironman", outcome_id=out_h.id)

    tasks = [
        mgr.add_task(f"Craft Task {i}", project_id=p_c.id, difficulty=7.0, leverage=8.0, urgency=6.0, consequence=6.0)
        for i in range(5)
    ] + [
        mgr.add_task(f"Health Task {i}", project_id=p_h.id, difficulty=5.0, leverage=6.0, urgency=5.0, consequence=5.0)
        for i in range(3)
    ]
    factions = {t.id: (Faction.CRAFT if "Craft" in t.title else Faction.HEALTH) for t in tasks}

    balancer = FactionBalancer()
    scheduler = SixStepScheduler(goal_manager=mgr, balancer=balancer)

    # Start with heavy craft skew
    history = {Faction.CRAFT: 25.0, Faction.HEALTH: 2.0, Faction.LEVERAGE: 5.0, Faction.EXPRESSION: 3.0}
    manifest = scheduler.generate_schedule(dcs=8.5, task_pool=tasks, task_factions=factions, current_weekly_hours=history)

    assert manifest.operating_mode == OperatingMode.PEAK
    assert manifest.validation_passed is True
    assert len(manifest.blocks) > 0


def test_emergency_injection_integration():
    """Integration test: Emergency injector interacting with full scheduler manifest and goal stack."""
    mgr = GoalStackManager()
    out = mgr.add_outcome("Emergency Response", Faction.HEALTH)
    proj = mgr.add_project("Disaster Recovery", outcome_id=out.id)
    e_task = mgr.add_task("Critical Health Event", project_id=proj.id, difficulty=6.0)
    normal_task = mgr.add_task("Routine Refactor", project_id=proj.id, difficulty=4.0)

    injector = EmergencyInjector(enabled=True)
    normal_entry = ScheduledTaskEntry(task=normal_task, faction=Faction.CRAFT, tws=9.0)
    emerg_entry = ScheduledTaskEntry(task=e_task, faction=Faction.HEALTH, tws=5.0, is_emergency=True)

    ordered = injector.order_schedule([normal_entry], [emerg_entry])
    assert ordered[0].task.id == e_task.id  # Preempts routine task


def test_exhaustion_integration():
    """Integration test: Exhaustion predictor output feeding directly into scheduler mode selection."""
    predictor = ExhaustionPredictor(enabled=True)
    report = predictor.predict(current_dcs=7.0, consecutive_high_d_hours=6.0, sleep_deficit_hours=3.5, stress_trend_score=9.0)
    assert report.is_at_risk is True
    assert report.recommended_mode is not None

    scheduler = SixStepScheduler()
    # Scheduler with recommended mode DCS
    manifest = scheduler.generate_schedule(dcs=report.predicted_dcs, task_pool=[], task_factions={})
    assert manifest.operating_mode in (OperatingMode.SURVIVAL, OperatingMode.RECOVERY)


def test_weekly_faction_rebalance_integration():
    """Integration test: Rebalance output updating FactionBalancer targets for scheduler constraints."""
    rebalancer = WeeklyFactionRebalancer(enabled=True)
    actuals = {Faction.CRAFT: 40.0, Faction.HEALTH: 1.0, Faction.LEVERAGE: 2.0, Faction.EXPRESSION: 2.0}
    new_weights = rebalancer.rebalance(actuals)

    balancer = FactionBalancer(targets=new_weights)
    # Health should have elevated target and prioritize Health tasks
    assert balancer.targets[Faction.HEALTH] > 0.25


def test_review_cadence_integration():
    """Integration test: Review cadence manager consuming deferral escalations and orphan audits."""
    cadence = ReviewCadenceManager()
    deferrals = DeferralTracker()
    for _ in range(5):
        deferrals.record_deferral("task-escalated", "Overdue Task")

    escalated = deferrals.get_weekly_review_escalations()
    prompt = cadence.get_weekly_retro_prompt(escalated_tasks=escalated)
    assert prompt is not None
    assert any("task-escalated" in act or "1 tasks" in act for act in prompt.action_items)


def test_goal_stack_enforcement_integration():
    """Integration test: Scheduler validating tasks via GoalStackEnforcer across hierarchy."""
    mgr = GoalStackManager()
    orphan = mgr.add_task("Free Floating Task")
    enforcer = GoalStackEnforcer(enabled=True)
    valid, err = enforcer.enforce_task(orphan, mgr)
    assert valid is False
    assert "Violation" in err


def test_cross_faction_integration():
    """Integration test: Cross-faction allocator feeding cumulative allocations to FactionBalancer."""
    allocator = CrossFactionAllocator(enabled=True)
    alloc = allocator.allocate("t1", 10.0, Faction.CRAFT, Faction.EXPRESSION, primary_ratio=0.8)
    totals = allocator.accumulate_allocations([alloc])

    balancer = FactionBalancer()
    can_assign = balancer.can_assign_task(Faction.CRAFT, 2.0, totals, {Faction.EXPRESSION})
    assert isinstance(can_assign, bool)


def test_emergency_protocol_integration():
    """Integration test: Emergency protocol locking non-essential factions and checking task eligibility."""
    proto = EmergencyProtocolEngine(enabled=True)
    proto.trigger_emergency(EmergencyLevel.LEVEL_3_SEVERE, "System crisis", Faction.LEVERAGE)
    assert proto.is_action_allowed(Faction.LEVERAGE) is True
    assert proto.is_action_allowed(Faction.CRAFT) is False


def test_tag_manager_integration():
    """Integration test: TagManager normalizes tags and associates them with domain taxonomy."""
    tm = TagManager()
    tags = ["#exercise", "coding", "#leverage/wealth/investing"]
    normalized = tm.normalize(tags)
    assert "#domain/health/exercise" in normalized
    assert "#domain/craft/coding" in normalized
    assert "#leverage/wealth/investing" in normalized

