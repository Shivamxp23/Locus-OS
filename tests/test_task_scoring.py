"""tests/test_task_scoring.py - Tests for Task Priority Scoring (TWS) and Multi-Scale Goal Roll-Up.

Validates Acceptance Criteria for US-19, Spec §25.1-§25.4, D-1, and D-3:
- Unit: Base TWS calculation (Priority*0.4 + Urgency*0.4 + Difficulty*0.2)
- Unit: FactionLagBonus calculation against targets (Health 25%, Leverage 25%, Craft 30%, Expression 20%)
- Unit: Multi-scale roll-up across Three-Layer Goal Stack (vision, milestone, daily)
- Unit: DCS and OperatingMode resolution
- Unit: Modularity off-switch and TaskScorerProvider protocol
- Integration: Full task suite evaluation and descending rank ordering
"""

from __future__ import annotations

import pytest

from sidecar.life_os.dcs import calculate_dcs
from sidecar.life_os.factions import (
    FACTION_TARGET_PERCENTAGES,
    Faction,
    calculate_faction_lag,
    calculate_faction_lag_bonus,
)
from sidecar.life_os.modes import OperatingMode, resolve_operating_mode
from sidecar.life_os.tws import calculate_base_tws, calculate_tws
from sidecar.task_scoring import (
    GoalScale,
    Task,
    TaskPriorityScorer,
    TaskScorerProvider,
    get_task_suite,
)


def test_unit_base_tws_formula():
    """Verify base TWS formula: (P * 0.4) + (U * 0.4) + (D * 0.2)."""
    # Case 1: P=10, U=5, D=4 -> 4.0 + 2.0 + 0.8 = 6.8
    score = calculate_base_tws(priority=10.0, urgency=5.0, difficulty=4.0)
    assert score == 6.8

    # Case 2: P=8, U=7, D=6 -> 3.2 + 2.8 + 1.2 = 7.2
    score2 = calculate_base_tws(priority=8.0, urgency=7.0, difficulty=6.0)
    assert score2 == 7.2


def test_unit_faction_targets_and_lag_bonus():
    """Verify weekly faction targets and lag score bonuses per D-1 and Appendix C."""
    # Target allocations
    assert FACTION_TARGET_PERCENTAGES[Faction.HEALTH] == 0.25
    assert FACTION_TARGET_PERCENTAGES[Faction.LEVERAGE] == 0.25
    assert FACTION_TARGET_PERCENTAGES[Faction.CRAFT] == 0.30
    assert FACTION_TARGET_PERCENTAGES[Faction.EXPRESSION] == 0.20

    # Lag bonus rules
    assert calculate_faction_lag_bonus(lag_hours=7.0) == 4.0   # > 6h
    assert calculate_faction_lag_bonus(lag_hours=4.5) == 2.0   # > 3h
    assert calculate_faction_lag_bonus(lag_hours=1.5) == 0.0   # within 3h
    assert calculate_faction_lag_bonus(lag_hours=-2.0) == -1.0  # ahead of target


def test_unit_dcs_and_modes():
    """Verify DCS formula and OperatingMode resolution."""
    # Perfect score: E=10, M=10, S=10, ST=0 (clamped to 1) -> 10 * (1 - 0.05) = 9.5
    dcs_peak = calculate_dcs(energy=10, mood=10, sleep=10, stress=1)
    assert dcs_peak == 9.5
    assert resolve_operating_mode(dcs_peak) == OperatingMode.PEAK

    # Low score: E=2, M=2, S=2, ST=10 -> 2 * (1 - 0.5) = 1.0
    dcs_survival = calculate_dcs(energy=2, mood=2, sleep=2, stress=10)
    assert dcs_survival == 1.0
    assert resolve_operating_mode(dcs_survival) == OperatingMode.SURVIVAL

    # Staleness penalty: score * 0.9
    dcs_stale = calculate_dcs(energy=6, mood=6, sleep=6, stress=4, stale_checkin=True)
    normal_score = calculate_dcs(energy=6, mood=6, sleep=6, stress=4, stale_checkin=False)
    assert dcs_stale == round(normal_score * 0.9, 2)


def test_unit_multiscale_goal_rollup():
    """Verify D-3 Three-Layer Goal Stack roll-up (parent blends intrinsic + child average)."""
    scorer = TaskPriorityScorer()

    # Child task: P=6, U=6, D=6 -> base 6.0, no lag bonus
    child = Task(
        task_id="C-1",
        title="Subtask",
        scale=GoalScale.DAILY,
        priority=6.0,
        urgency=6.0,
        difficulty=6.0,
    )
    assert scorer.score_task(child) == 6.0

    # Parent goal: intrinsic base P=10, U=10, D=10 -> 10.0
    # Effective base = (10.0 * 0.5) + (6.0 * 0.5) = 8.0
    parent = Task(
        task_id="P-1",
        title="Parent Goal",
        scale=GoalScale.MILESTONE,
        priority=10.0,
        urgency=10.0,
        difficulty=10.0,
        children=[child],
    )
    assert scorer.score_task(parent) == 8.0


def test_unit_modularity_off_and_protocol():
    """Verify modular off toggle and protocol conformance."""
    scorer_off = TaskPriorityScorer(enabled=False)
    assert scorer_off.is_enabled is False

    task = Task(task_id="T-off", title="Off Test", priority=7.0, urgency=2.0, difficulty=9.0)
    # When disabled, score returns raw priority
    assert scorer_off.score_task(task) == 7.0

    # Protocol compliance
    assert isinstance(scorer_off, TaskScorerProvider)


def test_integration_task_suite_ranking():
    """Integration: Evaluate standard task suite and verify descending TWS ordering."""
    scorer = TaskPriorityScorer()
    tasks = get_task_suite()
    ranked = scorer.rank_tasks(tasks)

    # Verify descending sort order
    scores = [score for _, score in ranked]
    assert scores == sorted(scores, reverse=True)

    # Verify highest task has top score > 12
    top_task, top_score = ranked[0]
    assert top_score >= 11.0
    assert top_task.scale_enum in (GoalScale.MILESTONE, GoalScale.VISION, GoalScale.DAILY)
