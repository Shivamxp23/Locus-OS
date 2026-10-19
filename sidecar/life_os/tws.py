"""
SPEC §25.4 line 4628 / D-1 Option A: Task Weight Score (TWS).
TWS = (P × 0.4) + (U × 0.4) + (D × 0.2)
    P = Priority (1-10), U = Urgency (1-10), D = Difficulty (1-10)
    Higher TWS = schedule first. This is the daily sort key.

LAG BONUS (applied AFTER base TWS):
    faction Lag Score > 3h  → all its tasks TWS + 2
    faction Lag Score > 6h  → all its tasks TWS + 4 (faction in crisis)
    faction ahead of target → its tasks TWS − 1

MULTI-SCALE ROLL-UP (D-3 Option a):
    Level 1 Vision / Level 2 Milestone roll up child constituent scores.

POST-TASK LOG: A (actual time), Q (quality 1-10), R (reason if |A − Est| > 50%)
"""
from __future__ import annotations

from typing import List, Optional
from sidecar.providers.life_os import (
    GoalStackLevel,
    PostTaskLog,
    TaskScoreInput,
    TaskScoreResult,
)


def calculate_tws(
    priority: int,
    urgency: int,
    difficulty: int,
    faction_lag_hours: float = 0.0,
    scale: GoalStackLevel = GoalStackLevel.DAILY,
    child_scores: Optional[List[float]] = None,
) -> TaskScoreResult:
    """
    Calculate Task Weight Score (TWS) according to D-1 Option A with lag bonus and multi-scale roll-up.
    """
    p = max(1, min(10, int(priority)))
    u = max(1, min(10, int(urgency)))
    d = max(1, min(10, int(difficulty)))

    # Base TWS formula: (P * 0.4) + (U * 0.4) + (D * 0.2)
    base_tws = round((p * 0.4) + (u * 0.4) + (d * 0.2), 2)

    # Lag bonus calculation
    lag_bonus = 0.0
    if faction_lag_hours > 6.0:
        lag_bonus = 4.0
    elif faction_lag_hours > 3.0:
        lag_bonus = 2.0
    elif faction_lag_hours < 0.0:
        lag_bonus = -1.0

    # Multi-scale roll-up (D-3 Option a)
    if scale in (GoalStackLevel.MILESTONE, GoalStackLevel.VISION) and child_scores:
        valid_children = [float(s) for s in child_scores if s is not None]
        if valid_children:
            child_component = max(valid_children) * 0.7 + (sum(valid_children) / len(valid_children)) * 0.3
            final_tws = round((base_tws * 0.7) + (child_component * 0.3) + lag_bonus, 2)
        else:
            final_tws = round(base_tws + lag_bonus, 2)
    else:
        final_tws = round(base_tws + lag_bonus, 2)

    return TaskScoreResult(
        base_tws=base_tws,
        lag_bonus=lag_bonus,
        final_tws=final_tws,
        scale=scale.value if isinstance(scale, GoalStackLevel) else str(scale),
        metadata={
            "inputs": {"p": p, "u": u, "d": d},
            "faction_lag_hours": faction_lag_hours,
            "child_count": len(child_scores) if child_scores else 0,
        },
    )


def calculate_tws_from_input(task_input: TaskScoreInput) -> TaskScoreResult:
    """Helper accepting TaskScoreInput data class."""
    return calculate_tws(
        priority=task_input.priority,
        urgency=task_input.urgency,
        difficulty=task_input.difficulty,
        faction_lag_hours=task_input.faction_lag_hours,
        scale=task_input.scale,
        child_scores=task_input.child_scores,
    )


def log_post_task(
    actual_time_minutes: int,
    estimated_time_minutes: int,
    quality: int,
    reason: Optional[str] = None,
) -> PostTaskLog:
    """
    SPEC §25.4 line 4646: Log post-task completion metrics.
    Enforces explanation reason if deviation |actual - estimated| / estimated > 50%.
    """
    actual = max(0, int(actual_time_minutes))
    est = max(1, int(estimated_time_minutes))
    q = max(1, min(10, int(quality)))

    ratio = abs(actual - est) / float(est)
    if ratio > 0.50 and not reason:
        raise ValueError(
            f"Reason required: actual time ({actual}m) deviated >50% from estimate ({est}m)"
        )

    return PostTaskLog(
        actual_time_minutes=actual,
        estimated_time_minutes=est,
        quality=q,
        reason=reason,
    )
