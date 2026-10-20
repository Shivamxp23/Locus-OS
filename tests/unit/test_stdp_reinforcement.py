"""
tests/unit/test_stdp_reinforcement.py
Unit tests for STDP Reinforcement (Spike-Timing-Dependent Plasticity) per SPEC §4.12 / F-0023.
"""
from __future__ import annotations

import math
import os
import tempfile
import pytest

from sidecar.memory.graph_reinforcement import GraphPlasticityProvider
from sidecar.memory.stdp_updater import apply_stdp_update, calculate_delta_w
from sidecar.providers.stdp_reinforcement import (
    A_MINUS,
    A_PLUS,
    PRUNE_THRESHOLD,
    TAU_MINUS,
    TAU_PLUS,
    W_MAX,
    W_MIN,
    OutcomeEvent,
    RetrievalEvent,
    STDPConfig,
    TraversedEdgeRecord,
    TurnAuditLog,
)


def test_stdp_constants_and_data_structures() -> None:
    """
    SPEC §4.12 line 1265: "A_plus = 0.15 // Max potentiation (strengthening)"
    SPEC §4.12 line 1267: "A_minus = 0.12 // Max depression (weakening)"
    SPEC §4.12 line 1270: "W_MIN = 0.05 // Minimum edge weight (prevents complete deletion)"
    SPEC §4.12 line 1271: "W_MAX = 1.00 // Maximum edge weight saturation"
    SPEC §4.12 line 1272: "PRUNE_THRESHOLD = 0.08 // Below this, edge is marked for archive/prune"
    """
    cfg = STDPConfig()
    assert cfg.a_plus == 0.15
    assert cfg.a_minus == 0.12
    assert cfg.tau_plus == 300.0
    assert cfg.tau_minus == 600.0
    assert cfg.w_min == 0.05
    assert cfg.w_max == 1.00
    assert cfg.prune_threshold == 0.08

    retrieval = RetrievalEvent(node_id="node_1", edge_id="edge_1", retrieved_at=100.0)
    assert retrieval.node_id == "node_1"
    assert retrieval.retrieved_at == 100.0

    outcome = OutcomeEvent(session_id="s1", turn_id="t1", success=True, occurred_at=150.0)
    assert outcome.success is True
    assert outcome.occurred_at == 150.0


def test_stdp_causality_violation() -> None:
    """
    SPEC §4.12 line 1289: "IF delta_t <= 0: // Retrieval happened AFTER outcome — causality violation, ignore RETURN current_weight"
    """
    # Outcome happened before retrieval: delta_t = 100 - 150 = -50 <= 0
    retrieval = RetrievalEvent(node_id="n1", edge_id="e1", retrieved_at=150.0)
    outcome = OutcomeEvent(session_id="s1", turn_id="t1", success=True, occurred_at=100.0)
    current_w = 0.50

    updated_w = apply_stdp_update(retrieval, outcome, current_w)
    assert updated_w == current_w

    # delta_t == 0
    outcome_same_time = OutcomeEvent(session_id="s1", turn_id="t1", success=True, occurred_at=150.0)
    updated_w_zero = apply_stdp_update(retrieval, outcome_same_time, current_w)
    assert updated_w_zero == current_w


def test_stdp_long_term_potentiation() -> None:
    """
    SPEC §4.12 line 1293: "IF outcome.success: delta_w = A_plus * exp(-delta_t / tau_plus) new_weight = current_weight + delta_w"
    """
    retrieval = RetrievalEvent(node_id="n1", edge_id="e1", retrieved_at=1000.0)
    # Outcome happened 60s later (within 5min tau_plus=300s window)
    outcome = OutcomeEvent(session_id="s1", turn_id="t1", success=True, occurred_at=1060.0)
    current_w = 0.50

    delta_t = 60.0
    expected_delta = 0.15 * math.exp(-60.0 / 300.0)
    expected_w = min(1.00, 0.50 + expected_delta)

    updated_w = apply_stdp_update(retrieval, outcome, current_w)
    assert pytest.approx(updated_w, rel=1e-5) == expected_w
    assert updated_w > current_w


def test_stdp_long_term_depression() -> None:
    """
    SPEC §4.12 line 1297: "ELSE: delta_w = A_minus * exp(-delta_t / tau_minus) new_weight = current_weight - delta_w"
    """
    retrieval = RetrievalEvent(node_id="n1", edge_id="e1", retrieved_at=1000.0)
    # Failure outcome happened 120s later
    outcome = OutcomeEvent(session_id="s1", turn_id="t1", success=False, occurred_at=1120.0)
    current_w = 0.50

    delta_t = 120.0
    expected_delta = 0.12 * math.exp(-120.0 / 600.0)
    expected_w = max(0.05, 0.50 - expected_delta)

    updated_w = apply_stdp_update(retrieval, outcome, current_w)
    assert pytest.approx(updated_w, rel=1e-5) == expected_w
    assert updated_w < current_w


def test_stdp_boundary_clamping() -> None:
    """
    SPEC §4.12 line 1303: "new_weight = clamp(new_weight, W_MIN, W_MAX)"
    """
    retrieval = RetrievalEvent(node_id="n1", edge_id="e1", retrieved_at=1000.0)
    outcome_succ = OutcomeEvent(session_id="s1", turn_id="t1", success=True, occurred_at=1001.0)
    outcome_fail = OutcomeEvent(session_id="s1", turn_id="t1", success=False, occurred_at=1001.0)

    # Upper clamp saturation at 1.00
    saturated = apply_stdp_update(retrieval, outcome_succ, current_weight=0.98)
    assert saturated == 1.00

    # Lower clamp floor at 0.05
    depleted = apply_stdp_update(retrieval, outcome_fail, current_weight=0.06)
    assert depleted == 0.05


def test_batch_process_turn_stdp_and_prune_tagging() -> None:
    """
    SPEC §4.12 line 1307: "FUNCTION process_turn_stdp(turn_audit_log): FOR EACH edge IN turn_audit_log.traversed_edges: current_w = neo4j.get_edge_weight(edge.id) updated_w = apply_stdp_update(...) IF updated_w <= PRUNE_THRESHOLD: neo4j.tag_edge_for_pruning(edge.id, reason='STDP_DEPLETION')"
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "stdp.db")
        provider = GraphPlasticityProvider(db_path=db_path)

        edge1 = TraversedEdgeRecord(
            edge_id="edge_succ",
            retrieval_event=RetrievalEvent(node_id="n1", edge_id="edge_succ", retrieved_at=1000.0),
            initial_weight=0.50,
        )
        edge2 = TraversedEdgeRecord(
            edge_id="edge_fail_deplete",
            retrieval_event=RetrievalEvent(node_id="n2", edge_id="edge_fail_deplete", retrieved_at=1000.0),
            initial_weight=0.12,  # 0.12 - ~0.119 <= 0.08 (prune threshold)
        )

        # Failure turn
        outcome = OutcomeEvent(session_id="s_audit", turn_id="t_audit", success=False, occurred_at=1005.0)
        turn_log = TurnAuditLog(
            session_id="s_audit",
            turn_id="t_audit",
            traversed_edges=[edge1, edge2],
            outcome=outcome,
        )

        res = provider.process_turn_stdp(turn_log)
        assert res["session_id"] == "s_audit"
        assert len(res["updated_edges"]) == 2

        # edge_fail_deplete dropped <= 0.08 and got tagged for pruning
        w2 = provider.get_edge_weight("edge_fail_deplete")
        assert w2 <= PRUNE_THRESHOLD
        assert "edge_fail_deplete" in res["pruned_tags"]

        candidates = provider.list_prune_candidates()
        candidate_ids = [c["edge_id"] for c in candidates]
        assert "edge_fail_deplete" in candidate_ids


def test_decay_cycle() -> None:
    """
    SPEC §4.12 line 1259: "Manages relationship weight clamping [0.05, 1.0], decay cycles, and low-weight relationship pruning"
    """
    provider = GraphPlasticityProvider()
    provider.set_edge_weight("active_edge", 0.80)
    provider.set_edge_weight("low_edge", 0.09)

    decayed = provider.apply_decay_cycle(decay_rate=0.20)
    assert decayed["active_edge"] == pytest.approx(0.64, rel=1e-3)
    assert decayed["low_edge"] <= PRUNE_THRESHOLD

    # Clamping floor persists during decay
    provider.set_edge_weight("floor_edge", 0.05)
    decayed_floor = provider.apply_decay_cycle(decay_rate=0.50)
    assert decayed_floor["floor_edge"] == 0.05
