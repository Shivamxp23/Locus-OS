"""STDP Reinforcement (Spike-Timing-Dependent Plasticity) (§4.12).

Applies an asymmetric temporal STDP learning rule to Neo4j graph edge weights
based on retrieval-to-outcome time deltas and success/error feedback.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

# Canonical STDP Parameters (§4.12)
A_PLUS: float = 0.15       # Max potentiation (strengthening)
A_MINUS: float = 0.12      # Max depression (weakening)
TAU_PLUS: float = 300.0    # Positive time constant (5 minutes in seconds)
TAU_MINUS: float = 600.0   # Negative time constant (10 minutes in seconds)
W_MIN: float = 0.05        # Minimum edge weight
W_MAX: float = 1.00        # Maximum edge weight saturation
PRUNE_THRESHOLD: float = 0.08  # Below this, edge is marked for archive/prune


def clamp_weight(w: float) -> float:
    return max(W_MIN, min(W_MAX, w))


@dataclass
class RetrievalEvent:
    node_id: str
    edge_id: str
    retrieved_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OutcomeEvent:
    session_id: str
    turn_id: str
    success: bool
    occurred_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TurnAuditLog:
    session_id: str
    turn_id: str
    outcome: OutcomeEvent
    traversed_edges: List[RetrievalEvent] = field(default_factory=list)


def apply_stdp_update(
    retrieval: RetrievalEvent,
    outcome: OutcomeEvent,
    current_weight: float,
) -> float:
    """Compute updated edge weight under asymmetric temporal STDP."""
    delta_t = outcome.occurred_at - retrieval.retrieved_at

    # Causality violation (retrieval happened after outcome)
    if delta_t <= 0:
        return clamp_weight(current_weight)

    if outcome.success:
        # Long-Term Potentiation (LTP)
        delta_w = A_PLUS * math.exp(-delta_t / TAU_PLUS)
        new_w = current_weight + delta_w
    else:
        # Long-Term Depression (LTD)
        delta_w = A_MINUS * math.exp(-delta_t / TAU_MINUS)
        new_w = current_weight - delta_w

    return clamp_weight(new_w)


class STDPManager:
    """Manages edge weights, STDP updates, and low-weight relationship pruning."""

    def __init__(self, default_weight: float = 0.50) -> None:
        self.default_weight = default_weight
        self.edge_weights: Dict[str, float] = {}
        self.pruned_edges: Set[str] = set()

    def get_edge_weight(self, edge_id: str) -> float:
        if edge_id in self.pruned_edges:
            return 0.0
        return self.edge_weights.get(edge_id, self.default_weight)

    def set_edge_weight(self, edge_id: str, weight: float) -> float:
        clamped = clamp_weight(weight)
        self.edge_weights[edge_id] = clamped
        if clamped <= PRUNE_THRESHOLD:
            self.pruned_edges.add(edge_id)
        elif edge_id in self.pruned_edges:
            self.pruned_edges.remove(edge_id)
        return clamped

    def process_turn_stdp(self, turn_audit_log: TurnAuditLog) -> Dict[str, float]:
        """Update weights for all edges traversed in this turn."""
        results: Dict[str, float] = {}
        for retrieval in turn_audit_log.traversed_edges:
            cur_w = self.get_edge_weight(retrieval.edge_id)
            updated_w = apply_stdp_update(
                retrieval=retrieval,
                outcome=turn_audit_log.outcome,
                current_weight=cur_w,
            )
            self.set_edge_weight(retrieval.edge_id, updated_w)
            results[retrieval.edge_id] = updated_w
        return results

    def apply_passive_decay(self, elapsed_seconds: float, decay_rate: float = 0.00005) -> int:
        """Apply passive time decay to all unreinforced active edges."""
        pruned_count = 0
        for edge_id in list(self.edge_weights.keys()):
            if edge_id in self.pruned_edges:
                continue
            cur = self.edge_weights[edge_id]
            decayed = cur * math.exp(-decay_rate * elapsed_seconds)
            self.set_edge_weight(edge_id, decayed)
            if edge_id in self.pruned_edges:
                pruned_count += 1
        return pruned_count
