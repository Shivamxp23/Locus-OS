import pytest
from datetime import datetime, timedelta, timezone
from sidecar.memory.spaced_repetition import (
    MIN_EASE_FACTOR,
    DEFAULT_EASE_FACTOR,
    MemoryNodeState,
    calculate_next_review,
    MemoryScheduler,
)


def test_initial_review_pass():
    now = datetime(2026, 10, 16, 12, 0, 0, tzinfo=timezone.utc)
    state = MemoryNodeState(node_id="n1")

    # Pass with effort (q = 3)
    updated = calculate_next_review(state, quality_grade=3, current_time=now)
    assert updated.repetition_count == 1
    assert updated.interval_days == 1
    assert updated.due_date == (now + timedelta(days=1)).isoformat()
    # EF changes slightly for q=3: 0.1 - (2)*(0.08 + 2*0.02) = 0.1 - 0.24 = -0.14
    assert updated.ease_factor == pytest.approx(DEFAULT_EASE_FACTOR - 0.14, rel=1e-3)


def test_second_review_ladder():
    now = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)
    state = MemoryNodeState(node_id="n1", repetition_count=1, interval_days=1, ease_factor=2.50)

    # Perfect recall (q = 5)
    updated = calculate_next_review(state, quality_grade=5, current_time=now)
    assert updated.repetition_count == 2
    assert updated.interval_days == 6
    assert updated.due_date == (now + timedelta(days=6)).isoformat()
    # q=5 increases EF: delta = 0.1 - 0 = +0.10 -> 2.60
    assert updated.ease_factor == pytest.approx(2.60, rel=1e-3)


def test_failed_recall_resets_ladder():
    now = datetime(2026, 10, 18, 12, 0, 0, tzinfo=timezone.utc)
    state = MemoryNodeState(node_id="n1", repetition_count=5, interval_days=25, ease_factor=2.60)

    # Incorrect recall (q = 1)
    updated = calculate_next_review(state, quality_grade=1, current_time=now)
    assert updated.repetition_count == 0
    assert updated.interval_days == 1
    assert updated.due_date == (now + timedelta(days=1)).isoformat()
    assert updated.ease_factor >= MIN_EASE_FACTOR


def test_memory_scheduler_due_querying():
    scheduler = MemoryScheduler()
    t0 = datetime(2026, 10, 16, 10, 0, 0, tzinfo=timezone.utc)
    scheduler.register_node("card1", initial_due=t0)
    scheduler.register_node("card2", initial_due=t0 + timedelta(days=5))

    due = scheduler.get_due_nodes(as_of=t0 + timedelta(hours=1))
    assert len(due) == 1
    assert due[0].node_id == "card1"

    # Review card1
    scheduler.record_review("card1", quality_grade=4, review_time=t0)
    due_after = scheduler.get_due_nodes(as_of=t0 + timedelta(hours=1))
    assert len(due_after) == 0
