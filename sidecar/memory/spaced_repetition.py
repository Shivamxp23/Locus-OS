"""
SPEC §4.13: Spaced Repetition Memory Consolidation (FSRS / SM-2).
Implements the SuperMemo SM-2 interval & ease algorithm, FSRS stability scaling,
and node state transitions per SPEC §4.13 lines 1341-1400.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, Optional

from sidecar.providers.spaced_repetition import (
    CORE_FACT_MIN_EASE,
    CORE_FACT_MIN_REPETITIONS,
    DEFAULT_EASE_FACTOR,
    DEFAULT_STABILITY,
    INITIAL_INTERVAL_FIRST,
    INITIAL_INTERVAL_SECOND,
    MIN_EASE_FACTOR,
    MemoryNodeState,
    SpacedRepetitionConfig,
)

SECONDS_PER_DAY: float = 86400.0


def calculate_next_review(
    state: MemoryNodeState,
    quality_grade: int,
    timestamp: Optional[float] = None,
    config: Optional[SpacedRepetitionConfig] = None,
) -> MemoryNodeState:
    """
    SPEC §4.13 lines 1354-1379:
    SM-2 INTERVAL & EASE ALGORITHM:
        calculate_next_review(state: MemoryNodeState, quality_grade: int) -> MemoryNodeState
        quality_grade: 0 = Blackout, 1 = Incorrect, 2 = Hard recall,
                       3 = Pass with effort, 4 = Good recall, 5 = Perfect/Reflexive
    """
    cfg = config or SpacedRepetitionConfig()
    grade = max(0, min(5, int(quality_grade)))
    current_time = float(time.time() if timestamp is None else timestamp)

    new_state = MemoryNodeState(
        node_id=state.node_id,
        repetition_count=state.repetition_count,
        ease_factor=state.ease_factor,
        interval_days=state.interval_days,
        stability=state.stability,
        last_reviewed_at=current_time,
        due_date=current_time,
        lapses=state.lapses,
        is_core_fact=state.is_core_fact,
        metadata=dict(state.metadata),
    )

    if grade >= 3:
        # SPEC §4.13 lines 1359-1366: Repetition progression
        if new_state.repetition_count == 0:
            new_state.interval_days = cfg.initial_interval_first
        elif new_state.repetition_count == 1:
            new_state.interval_days = cfg.initial_interval_second
        else:
            new_state.interval_days = max(1, int(round(new_state.interval_days * new_state.ease_factor)))
        new_state.repetition_count += 1

        # FSRS Stability increase
        stability_multiplier = 1.0 + 0.19 * (grade - 2.0) * (new_state.ease_factor / cfg.default_ease_factor)
        new_state.stability = round(max(0.5, new_state.stability * stability_multiplier), 4)
    else:
        # SPEC §4.13 lines 1367-1370: Recall failed — reset repetition ladder
        new_state.repetition_count = 0
        new_state.interval_days = cfg.initial_interval_first
        new_state.lapses += 1
        new_state.stability = round(max(0.20, new_state.stability * 0.50), 4)

    # SPEC §4.13 lines 1373-1375: Update Ease Factor (EF)
    # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    diff = 5 - grade
    delta_ef = 0.1 - diff * (0.08 + diff * 0.02)
    new_state.ease_factor = round(max(cfg.min_ease_factor, new_state.ease_factor + delta_ef), 4)

    # Calculate due date
    new_state.last_reviewed_at = current_time
    new_state.due_date = current_time + (new_state.interval_days * SECONDS_PER_DAY)

    # SPEC §4.13 lines 1397-1399: Promote to CORE_FACT
    # IF updated_state.repetition_count >= 5 AND updated_state.ease_factor >= 2.5: CORE_FACT
    if (
        new_state.repetition_count >= cfg.core_fact_min_repetitions
        and new_state.ease_factor >= cfg.core_fact_min_ease
    ):
        new_state.is_core_fact = True
    elif grade < 3:
        # If lapsed, does not retain active core fact status
        new_state.is_core_fact = False

    return new_state


def calculate_retention_probability(stability: float, elapsed_days: float) -> float:
    """
    FSRS Exponential Retention Formula:
    R(t) = exp(-t / S) where t is elapsed days and S is memory stability.
    """
    if stability <= 0.0:
        return 0.0
    if elapsed_days <= 0.0:
        return 1.0
    return round(math.exp(-elapsed_days / max(0.1, stability)), 4)


def evaluate_node_retention(
    node_state: MemoryNodeState,
    context: Optional[Dict[str, Any]] = None,
    current_timestamp: Optional[float] = None,
) -> int:
    """
    SPEC §4.13 line 1393:
    Evaluate memory retention via implicit conversational mentions or Inner Loop verification.
    Grades:
        0 = Blackout / Completely unmentioned
        1 = Incorrect recall
        2 = Hard recall (long overdue, mention required prompt)
        3 = Pass with effort (default on-time review)
        4 = Good recall (recently mentioned in journal/chat)
        5 = Perfect / Reflexive (actively reinforced multiple times)
    """
    ctx = context or {}
    now = float(time.time() if current_timestamp is None else current_timestamp)

    # If explicit simulated grade provided in context, respect it
    if "quality_grade" in ctx:
        return max(0, min(5, int(ctx["quality_grade"])))

    # Check for recent mentions in user journal or chat
    mention_count = int(ctx.get("mention_count", 0))
    positive_reaction = bool(ctx.get("positive_reaction", False))

    if mention_count >= 3 or (mention_count >= 1 and positive_reaction):
        return 5
    if mention_count == 2:
        return 4
    if mention_count == 1:
        return 3

    # Check how overdue the node is
    if node_state.due_date > 0.0 and now > node_state.due_date:
        overdue_days = (now - node_state.due_date) / SECONDS_PER_DAY
        if overdue_days > (node_state.interval_days * 2.0):
            return 1
        if overdue_days > node_state.interval_days:
            return 2

    # Default passing grade on schedule
    return 3
