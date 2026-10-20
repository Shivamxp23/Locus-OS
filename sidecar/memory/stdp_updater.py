"""
SPEC §4.12: STDP Reinforcement (Spike-Timing-Dependent Plasticity).
`sidecar/memory/stdp_updater.py`
Applies asymmetric temporal STDP learning rule to Neo4j graph edge weights
based on retrieval-to-outcome time deltas.
"""
from __future__ import annotations

import math
from typing import Optional

from sidecar.providers.stdp_reinforcement import (
    A_MINUS,
    A_PLUS,
    OutcomeEvent,
    PRUNE_THRESHOLD,
    RetrievalEvent,
    STDPConfig,
    TAU_MINUS,
    TAU_PLUS,
    W_MAX,
    W_MIN,
)


def calculate_delta_w(
    delta_t: float,
    success: bool,
    a_plus: float = A_PLUS,
    a_minus: float = A_MINUS,
    tau_plus: float = TAU_PLUS,
    tau_minus: float = TAU_MINUS,
) -> float:
    """
    Calculate raw weight update delta_w based on temporal difference.
    If delta_t <= 0 (causality violation), delta_w is 0.0.
    """
    if delta_t <= 0.0:
        return 0.0
    if success:
        # Long-Term Potentiation (LTP)
        return float(a_plus * math.exp(-delta_t / tau_plus))
    else:
        # Long-Term Depression (LTD)
        return -float(a_minus * math.exp(-delta_t / tau_minus))


def apply_stdp_update(
    retrieval: RetrievalEvent,
    outcome: OutcomeEvent,
    current_weight: float,
    config: Optional[STDPConfig] = None,
) -> float:
    """
    SPEC §4.12 line 1286:
    FUNCTION apply_stdp_update(retrieval: RetrievalEvent, outcome: OutcomeEvent, current_weight: float) -> float:
        delta_t = outcome.occurred_at - retrieval.retrieved_at   // in seconds
        
        IF delta_t <= 0:
            // Retrieval happened AFTER outcome — causality violation, ignore
            RETURN current_weight
            
        IF outcome.success:
            // Long-Term Potentiation (LTP): Retrieved memory contributed to success
            delta_w = A_plus * exp(-delta_t / tau_plus)
            new_weight = current_weight + delta_w
        ELSE:
            // Long-Term Depression (LTD): Retrieved memory led to hallucination, rejection, or error
            delta_w = A_minus * exp(-delta_t / tau_minus)
            new_weight = current_weight - delta_w
            
        // Clamp to valid boundary
        new_weight = clamp(new_weight, W_MIN, W_MAX)
        RETURN new_weight
    """
    cfg = config or STDPConfig()
    delta_t = float(outcome.occurred_at - retrieval.retrieved_at)

    if delta_t <= 0.0:
        # Causality violation: outcome preceded retrieval
        return float(current_weight)

    delta_w = calculate_delta_w(
        delta_t=delta_t,
        success=outcome.success,
        a_plus=cfg.a_plus,
        a_minus=cfg.a_minus,
        tau_plus=cfg.tau_plus,
        tau_minus=cfg.tau_minus,
    )

    new_weight = float(current_weight + delta_w)

    # Clamp within [w_min, w_max]
    clamped = max(cfg.w_min, min(cfg.w_max, new_weight))
    return float(clamped)
