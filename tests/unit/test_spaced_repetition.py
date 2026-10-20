"""
SPEC §4.13: Spaced Repetition Memory Consolidation (FSRS / SM-2) Unit Tests.
Verifies SM-2 repetition ladder, ease factor scaling and clamping, FSRS stability,
SQLite storage persistence, due node queries, and core fact promotions.
"""
from __future__ import annotations

import math
import tempfile
import time
from pathlib import Path

import pytest

from sidecar.brain.inner_loop import ProactiveInnerLoopMemoryBridge
from sidecar.memory.memory_scheduler import SpacedRepetitionMemoryScheduler
from sidecar.memory.spaced_repetition import (
    calculate_next_review,
    calculate_retention_probability,
    evaluate_node_retention,
)
from sidecar.providers.spaced_repetition import (
    DEFAULT_EASE_FACTOR,
    DEFAULT_STABILITY,
    INITIAL_INTERVAL_FIRST,
    INITIAL_INTERVAL_SECOND,
    MIN_EASE_FACTOR,
    MemoryNodeState,
    SpacedRepetitionConfig,
)


def test_initial_state_defaults() -> None:
    """SPEC §4.13 line 1344: "MemoryNodeState: repetition_count: int = 0, ease_factor: float = 2.50, interval_days: int = 1, stability: float = 1.0"."""
    state = MemoryNodeState(node_id="concept:transformer")
    assert state.node_id == "concept:transformer"
    assert state.repetition_count == 0
    assert state.ease_factor == DEFAULT_EASE_FACTOR
    assert state.interval_days == INITIAL_INTERVAL_FIRST
    assert state.stability == DEFAULT_STABILITY
    assert state.lapses == 0
    assert not state.is_core_fact


def test_repetition_ladder_progression() -> None:
    """SPEC §4.13 line 1359: "IF quality_grade >= 3: IF state.repetition_count == 0: state.interval_days = 1 ELIF state.repetition_count == 1: state.interval_days = 6 ELSE: state.interval_days = round(state.interval_days * state.ease_factor)"."""
    base_time = 1000000.0
    state = MemoryNodeState(node_id="fact:attention")

    # First repetition with grade 4 (Good recall)
    s1 = calculate_next_review(state, quality_grade=4, timestamp=base_time)
    assert s1.repetition_count == 1
    assert s1.interval_days == 1
    assert s1.due_date == base_time + (1 * 86400.0)

    # Second repetition with grade 4
    s2 = calculate_next_review(s1, quality_grade=4, timestamp=base_time + 86400.0)
    assert s2.repetition_count == 2
    assert s2.interval_days == 6
    assert s2.due_date == (base_time + 86400.0) + (6 * 86400.0)

    # Third repetition with grade 4 (ease is 2.50, interval = round(6 * 2.50) = 15)
    s3 = calculate_next_review(s2, quality_grade=4, timestamp=base_time + 7 * 86400.0)
    assert s3.repetition_count == 3
    assert s3.interval_days == 15


def test_recall_failure_resets_ladder_and_increments_lapses() -> None:
    """SPEC §4.13 line 1367: "ELSE: state.repetition_count = 0 state.interval_days = 1 // Recall failed — reset repetition ladder"."""
    state = MemoryNodeState(
        node_id="fact:euler",
        repetition_count=4,
        interval_days=30,
        ease_factor=2.40,
        stability=12.0,
    )
    failed = calculate_next_review(state, quality_grade=2, timestamp=2000000.0)
    assert failed.repetition_count == 0
    assert failed.interval_days == 1
    assert failed.lapses == 1
    assert failed.stability < 12.0


def test_ease_factor_update_and_clamping() -> None:
    """SPEC §4.13 line 1373: "state.ease_factor = state.ease_factor + (0.1 - (5 - quality_grade) * (0.08 + (5 - quality_grade) * 0.02)) state.ease_factor = max(1.30, state.ease_factor)"."""
    state = MemoryNodeState(node_id="fact:quantum", ease_factor=2.50)

    # Perfect recall (grade 5): 5-5=0 -> delta = +0.10 -> ease = 2.60
    p5 = calculate_next_review(state, quality_grade=5, timestamp=1000.0)
    assert math.isclose(p5.ease_factor, 2.60, abs_tol=1e-3)

    # Good recall (grade 4): 5-4=1 -> delta = 0.1 - 1*(0.08+0.02) = 0.0 -> ease = 2.50
    p4 = calculate_next_review(state, quality_grade=4, timestamp=1000.0)
    assert math.isclose(p4.ease_factor, 2.50, abs_tol=1e-3)

    # Hard recall (grade 3): 5-3=2 -> delta = 0.1 - 2*(0.08+0.04) = 0.1 - 0.24 = -0.14 -> ease = 2.36
    p3 = calculate_next_review(state, quality_grade=3, timestamp=1000.0)
    assert math.isclose(p3.ease_factor, 2.36, abs_tol=1e-3)

    # Repeated blackouts (grade 0): delta = 0.1 - 5*(0.08+0.10) = 0.1 - 0.90 = -0.80
    # Must clamp at minimum 1.30
    curr = state
    for _ in range(5):
        curr = calculate_next_review(curr, quality_grade=0, timestamp=1000.0)
    assert math.isclose(curr.ease_factor, MIN_EASE_FACTOR, abs_tol=1e-3)


def test_core_fact_promotion() -> None:
    """SPEC §4.13 line 1397: "IF updated_state.repetition_count >= 5 AND updated_state.ease_factor >= 2.5: neo4j.add_label(node.id, "CORE_FACT")"."""
    state = MemoryNodeState(
        node_id="fact:speed_of_light",
        repetition_count=4,
        ease_factor=2.60,
        interval_days=15,
    )
    promoted = calculate_next_review(state, quality_grade=5, timestamp=1000.0)
    assert promoted.repetition_count == 5
    assert promoted.ease_factor >= 2.50
    assert promoted.is_core_fact is True


def test_fsrs_retention_probability() -> None:
    """SPEC §4.13 line 1350: "stability: float = 1.0 // FSRS memory stability"."""
    # At elapsed = 0, retention is 100%
    assert calculate_retention_probability(stability=10.0, elapsed_days=0.0) == 1.0
    # At elapsed = stability, retention is exp(-1) ~= 0.3679
    r_half = calculate_retention_probability(stability=10.0, elapsed_days=10.0)
    assert math.isclose(r_half, math.exp(-1.0), abs_tol=1e-3)


def test_sqlite_scheduler_persistence() -> None:
    """SPEC §4.13 line 1395: "neo4j.save_node_state(node.id, updated_state)"."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_sr.db")
        scheduler = SpacedRepetitionMemoryScheduler(db_path=db_path)

        state = MemoryNodeState(node_id="fact:dna", repetition_count=1, interval_days=6, ease_factor=2.50)
        scheduler.save_node_state(state)

        fetched = scheduler.get_node_state("fact:dna")
        assert fetched is not None
        assert fetched.node_id == "fact:dna"
        assert fetched.repetition_count == 1
        assert fetched.interval_days == 6
        assert fetched.ease_factor == 2.50

        # Review and verify update in database
        updated = scheduler.record_review("fact:dna", quality_grade=4, timestamp=10000.0)
        assert updated.repetition_count == 2
        assert updated.interval_days == 6

        re_fetched = scheduler.get_node_state("fact:dna")
        assert re_fetched is not None
        assert re_fetched.repetition_count == 2


def test_scheduler_get_due_nodes_and_consolidation() -> None:
    """SPEC §4.13 line 1383: "WHERE e.due_date <= datetime() OR e.due_date IS NULL RETURN e ORDER BY e.due_date ASC LIMIT 50"."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_consolidation.db")
        scheduler = SpacedRepetitionMemoryScheduler(db_path=db_path)

        now = 100000.0
        # Node 1: Overdue
        n1 = MemoryNodeState(node_id="node:1", due_date=now - 500.0, repetition_count=0)
        # Node 2: Never reviewed (due_date=0)
        n2 = MemoryNodeState(node_id="node:2", due_date=0.0, repetition_count=0)
        # Node 3: Due in future
        n3 = MemoryNodeState(node_id="node:3", due_date=now + 50000.0, repetition_count=0)

        scheduler.save_node_state(n1)
        scheduler.save_node_state(n2)
        scheduler.save_node_state(n3)

        due = scheduler.get_due_nodes(limit=10, timestamp=now)
        due_ids = [n.node_id for n in due]
        assert "node:1" in due_ids
        assert "node:2" in due_ids
        assert "node:3" not in due_ids

        # Run consolidation with simulated grades
        res = scheduler.run_consolidation(
            limit=10,
            simulated_grades={"node:1": 5, "node:2": 3},
            timestamp=now,
        )
        assert res["processed_count"] == 2
        assert len(res["nodes"]) == 2

        updated_n1 = scheduler.get_node_state("node:1")
        assert updated_n1 is not None
        assert updated_n1.repetition_count == 1
        assert updated_n1.due_date > now


def test_inner_loop_bridge_observation_and_engagement() -> None:
    """SPEC §30.5 step 3-5: "STEP 3: Spaced Repetition Observation Assembly STEP 5: Engagement Feedback Handling"."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_bridge.db")
        scheduler = SpacedRepetitionMemoryScheduler(db_path=db_path)
        bridge = ProactiveInnerLoopMemoryBridge(scheduler=scheduler)

        node = MemoryNodeState(node_id="concept:async_io", interval_days=6, repetition_count=2)
        obs = bridge.assemble_repetition_observation(node, connected_projects_count=3)
        assert obs["observation_type"] == "SPACED_REPETITION_PROMPT"
        assert "concept:async_io" in obs["prompt"]
        assert "3 active projects" in obs["prompt"]

        # Positive user engagement reinforces
        updated = bridge.process_user_engagement(node_id="concept:async_io", user_reacted=True, timestamp=5000.0)
        assert updated.repetition_count >= 1
        assert updated.last_reviewed_at == 5000.0


def test_config_off_switch() -> None:
    """SPEC §4.13 line 1406: "Swappable / off state: locus.memory.spaced_repetition.enabled. Off -> nodes do not decay or schedule reviews"."""
    cfg = SpacedRepetitionConfig(enabled=False)
    assert not cfg.enabled
    d = cfg.to_dict()
    assert d["enabled"] is False
    assert d["default_ease_factor"] == DEFAULT_EASE_FACTOR
