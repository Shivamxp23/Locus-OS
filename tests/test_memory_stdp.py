import pytest
import time
from sidecar.memory.stdp import (
    A_PLUS,
    A_MINUS,
    TAU_PLUS,
    TAU_MINUS,
    W_MIN,
    W_MAX,
    PRUNE_THRESHOLD,
    RetrievalEvent,
    OutcomeEvent,
    TurnAuditLog,
    apply_stdp_update,
    clamp_weight,
    STDPManager,
)


def test_clamp_boundaries():
    assert clamp_weight(0.01) == W_MIN
    assert clamp_weight(1.50) == W_MAX
    assert clamp_weight(0.50) == 0.50


def test_stdp_potentiation_on_success():
    now = time.time()
    retrieval = RetrievalEvent(node_id="n1", edge_id="e1", retrieved_at=now - 60)
    outcome = OutcomeEvent(session_id="s1", turn_id="t1", success=True, occurred_at=now)

    initial_w = 0.50
    updated_w = apply_stdp_update(retrieval, outcome, initial_w)

    assert updated_w > initial_w
    # LTP formula: delta_w = 0.15 * exp(-60 / 300) ≈ 0.15 * 0.8187 ≈ 0.1228
    expected_delta = A_PLUS * 0.81873
    assert updated_w == pytest.approx(initial_w + expected_delta, rel=1e-3)


def test_stdp_depression_on_failure():
    now = time.time()
    retrieval = RetrievalEvent(node_id="n1", edge_id="e1", retrieved_at=now - 60)
    outcome = OutcomeEvent(session_id="s1", turn_id="t1", success=False, occurred_at=now)

    initial_w = 0.50
    updated_w = apply_stdp_update(retrieval, outcome, initial_w)

    assert updated_w < initial_w
    assert updated_w >= W_MIN


def test_causality_violation_ignored():
    now = time.time()
    retrieval = RetrievalEvent(node_id="n1", edge_id="e1", retrieved_at=now + 10)
    outcome = OutcomeEvent(session_id="s1", turn_id="t1", success=True, occurred_at=now)

    # Retrieval after outcome should not change weight
    assert apply_stdp_update(retrieval, outcome, 0.55) == 0.55


def test_stdp_manager_turn_processing_and_pruning():
    mgr = STDPManager(default_weight=0.10)
    now = time.time()
    turn_log = TurnAuditLog(
        session_id="s1",
        turn_id="t1",
        outcome=OutcomeEvent(session_id="s1", turn_id="t1", success=False, occurred_at=now),
        traversed_edges=[
            RetrievalEvent(node_id="n1", edge_id="weak_edge", retrieved_at=now - 10)
        ],
    )
    # Edge at 0.10 receiving depression should drop below PRUNE_THRESHOLD (0.08)
    res = mgr.process_turn_stdp(turn_log)
    assert res["weak_edge"] <= PRUNE_THRESHOLD
    assert "weak_edge" in mgr.pruned_edges
    assert mgr.get_edge_weight("weak_edge") == 0.0
