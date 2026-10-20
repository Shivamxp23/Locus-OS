"""
SPEC §4.12: STDP Reinforcement (Spike-Timing-Dependent Plasticity) Provider Interfaces.
Defines STDP constants, data structures, configuration, and GraphPlasticity provider.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# SPEC §4.12 lines 1265-1272: Canonical STDP Constants
A_PLUS: float = 0.15        # Max potentiation (strengthening)
A_MINUS: float = 0.12       # Max depression (weakening)
TAU_PLUS: float = 300.0     # Positive time constant (5 minutes in seconds)
TAU_MINUS: float = 600.0    # Negative time constant (10 minutes in seconds)
W_MIN: float = 0.05         # Minimum edge weight (prevents complete deletion)
W_MAX: float = 1.00         # Maximum edge weight saturation
PRUNE_THRESHOLD: float = 0.08  # Below this, edge is marked for archive/prune


@dataclass
class RetrievalEvent:
    """
    SPEC §4.12 line 1275:
    RetrievalEvent:
        node_id: string
        edge_id: string
        retrieved_at: float   // epoch timestamp
    """
    node_id: str
    edge_id: str
    retrieved_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RetrievalEvent:
        return cls(
            node_id=str(data.get("node_id", "")),
            edge_id=str(data.get("edge_id", "")),
            retrieved_at=float(data.get("retrieved_at", 0.0)),
        )


@dataclass
class OutcomeEvent:
    """
    SPEC §4.12 line 1280:
    OutcomeEvent:
        session_id: string
        turn_id: string
        success: bool         // 👍 reward, goal completion, or accepted suggestion
        occurred_at: float
    """
    session_id: str
    turn_id: str
    success: bool
    occurred_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OutcomeEvent:
        return cls(
            session_id=str(data.get("session_id", "")),
            turn_id=str(data.get("turn_id", "")),
            success=bool(data.get("success", True)),
            occurred_at=float(data.get("occurred_at", 0.0)),
        )


@dataclass
class TraversedEdgeRecord:
    """Record of an edge traversed during agent retrieval."""
    edge_id: str
    retrieval_event: RetrievalEvent
    initial_weight: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "retrieval_event": self.retrieval_event.to_dict(),
            "initial_weight": self.initial_weight,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TraversedEdgeRecord:
        raw_retrieval = data.get("retrieval_event", {})
        if isinstance(raw_retrieval, dict):
            retrieval = RetrievalEvent.from_dict(raw_retrieval)
        else:
            retrieval = raw_retrieval
        return cls(
            edge_id=str(data.get("edge_id", "")),
            retrieval_event=retrieval,
            initial_weight=float(data["initial_weight"]) if data.get("initial_weight") is not None else None,
        )


@dataclass
class TurnAuditLog:
    """
    SPEC §4.12 line 1307:
    turn_audit_log with traversed_edges and outcome.
    """
    session_id: str
    turn_id: str
    traversed_edges: List[TraversedEdgeRecord] = field(default_factory=list)
    outcome: Optional[OutcomeEvent] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "traversed_edges": [e.to_dict() for e in self.traversed_edges],
            "outcome": self.outcome.to_dict() if self.outcome else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TurnAuditLog:
        raw_edges = data.get("traversed_edges", [])
        edges = [TraversedEdgeRecord.from_dict(e) if isinstance(e, dict) else e for e in raw_edges]
        raw_outcome = data.get("outcome")
        outcome = OutcomeEvent.from_dict(raw_outcome) if isinstance(raw_outcome, dict) else raw_outcome
        return cls(
            session_id=str(data.get("session_id", "")),
            turn_id=str(data.get("turn_id", "")),
            traversed_edges=edges,
            outcome=outcome,
        )


@dataclass
class STDPConfig:
    """
    SPEC §4.12 lines 1265-1272, 1321:
    Configuration parameters and modular off-switch for STDP graph reinforcement.
    """
    enabled: bool = True
    a_plus: float = A_PLUS
    a_minus: float = A_MINUS
    tau_plus: float = TAU_PLUS
    tau_minus: float = TAU_MINUS
    w_min: float = W_MIN
    w_max: float = W_MAX
    prune_threshold: float = PRUNE_THRESHOLD
    storage_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseGraphPlasticityProvider(ABC):
    """
    SPEC §4.12 line 1319:
    Provider Interface: GraphPlasticityProvider
    """

    def __init__(self, name: str = "default", config: Optional[STDPConfig] = None) -> None:
        self.name = name
        self.config = config or STDPConfig()

    def clamp(self, weight: float) -> float:
        """Clamp edge weight within [W_MIN, W_MAX] bounds."""
        return max(self.config.w_min, min(self.config.w_max, float(weight)))

    @abstractmethod
    def apply_stdp_update(
        self,
        retrieval: RetrievalEvent,
        outcome: OutcomeEvent,
        current_weight: float,
    ) -> float:
        """
        SPEC §4.12 line 1286:
        Calculate new weight based on temporal delta and success outcome.
        """
        pass

    @abstractmethod
    def process_turn_stdp(self, turn_audit_log: TurnAuditLog) -> Dict[str, Any]:
        """
        SPEC §4.12 line 1307:
        Batch Graph Reinforcement Cycle over all traversed edges in a turn.
        """
        pass

    @abstractmethod
    def get_edge_weight(self, edge_id: str) -> float:
        """Fetch current weight of an edge."""
        pass

    @abstractmethod
    def set_edge_weight(self, edge_id: str, weight: float) -> None:
        """Update weight of an edge."""
        pass

    @abstractmethod
    def tag_edge_for_pruning(self, edge_id: str, reason: str = "STDP_DEPLETION") -> None:
        """Mark an edge whose weight has fallen below PRUNE_THRESHOLD for pruning."""
        pass

    @abstractmethod
    def list_prune_candidates(self) -> List[Dict[str, Any]]:
        """List all edges marked for pruning."""
        pass


# Aliases
BaseSTDPProvider = BaseGraphPlasticityProvider
