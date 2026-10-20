"""
SPEC §4.12: Hebbian learning and STDP graph reinforcement bridge.
`sidecar/patterns/hebbian.py`
Re-exports GraphPlasticityProvider and apply_stdp_update.
"""
from sidecar.memory.graph_reinforcement import (
    DEFAULT_EDGE_WEIGHT,
    GraphPlasticityProvider,
    HebbianManager,
    STDPUpdater,
)
from sidecar.memory.stdp_updater import (
    apply_stdp_update,
    calculate_delta_w,
)
from sidecar.providers.stdp_reinforcement import (
    A_MINUS,
    A_PLUS,
    BaseGraphPlasticityProvider,
    BaseSTDPProvider,
    OutcomeEvent,
    PRUNE_THRESHOLD,
    RetrievalEvent,
    STDPConfig,
    TAU_MINUS,
    TAU_PLUS,
    TraversedEdgeRecord,
    TurnAuditLog,
    W_MAX,
    W_MIN,
)

__all__ = [
    "A_MINUS",
    "A_PLUS",
    "BaseGraphPlasticityProvider",
    "BaseSTDPProvider",
    "DEFAULT_EDGE_WEIGHT",
    "GraphPlasticityProvider",
    "HebbianManager",
    "OutcomeEvent",
    "PRUNE_THRESHOLD",
    "RetrievalEvent",
    "STDPConfig",
    "STDPUpdater",
    "TAU_MINUS",
    "TAU_PLUS",
    "TraversedEdgeRecord",
    "TurnAuditLog",
    "W_MAX",
    "W_MIN",
    "apply_stdp_update",
    "calculate_delta_w",
]
