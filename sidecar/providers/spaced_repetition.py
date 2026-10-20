"""
SPEC §4.13: Spaced Repetition Memory Consolidation (FSRS / SM-2) Provider Interfaces.
Defines SM-2 / FSRS constants, data structures, configuration, and MemoryConsolidationProvider.
"""
from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

# SPEC §4.13 lines 1348-1350: Canonical SM-2 and FSRS Constants
DEFAULT_EASE_FACTOR: float = 2.50   # SM-2 default initial ease factor
MIN_EASE_FACTOR: float = 1.30       # SM-2 minimum ease factor clamp
DEFAULT_STABILITY: float = 1.0      # Initial FSRS stability score (in days)
INITIAL_INTERVAL_FIRST: int = 1     # First interval in days
INITIAL_INTERVAL_SECOND: int = 6    # Second interval in days
CORE_FACT_MIN_REPETITIONS: int = 5  # Repetitions threshold for core fact promotion
CORE_FACT_MIN_EASE: float = 2.50    # Ease factor threshold for core fact promotion


@dataclass
class MemoryNodeState:
    """
    SPEC §4.13 lines 1344-1352:
    MemoryNodeState:
        node_id: string
        repetition_count: int = 0
        ease_factor: float = 2.50      // SM-2 default (min 1.30)
        interval_days: int = 1
        stability: float = 1.0         // FSRS memory stability
        last_reviewed_at: timestamp
        due_date: timestamp
    """
    node_id: str
    repetition_count: int = 0
    ease_factor: float = DEFAULT_EASE_FACTOR
    interval_days: int = INITIAL_INTERVAL_FIRST
    stability: float = DEFAULT_STABILITY
    last_reviewed_at: float = 0.0
    due_date: float = 0.0
    lapses: int = 0
    is_core_fact: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryNodeState:
        return cls(
            node_id=str(data.get("node_id", "")),
            repetition_count=int(data.get("repetition_count", 0)),
            ease_factor=float(data.get("ease_factor", DEFAULT_EASE_FACTOR)),
            interval_days=int(data.get("interval_days", INITIAL_INTERVAL_FIRST)),
            stability=float(data.get("stability", DEFAULT_STABILITY)),
            last_reviewed_at=float(data.get("last_reviewed_at", 0.0)),
            due_date=float(data.get("due_date", 0.0)),
            lapses=int(data.get("lapses", 0)),
            is_core_fact=bool(data.get("is_core_fact", False)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class SpacedRepetitionConfig:
    """
    SPEC §4.13 line 1406:
    Configuration parameters and modular off-switch for spaced repetition memory consolidation.
    """
    enabled: bool = True
    default_ease_factor: float = DEFAULT_EASE_FACTOR
    min_ease_factor: float = MIN_EASE_FACTOR
    initial_interval_first: int = INITIAL_INTERVAL_FIRST
    initial_interval_second: int = INITIAL_INTERVAL_SECOND
    core_fact_min_repetitions: int = CORE_FACT_MIN_REPETITIONS
    core_fact_min_ease: float = CORE_FACT_MIN_EASE
    max_batch_size: int = 50
    storage_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryConsolidationProvider(ABC):
    """
    SPEC §4.13 line 1404:
    Provider Interface: MemoryConsolidationProvider
    """

    def __init__(self, name: str = "default", config: Optional[SpacedRepetitionConfig] = None) -> None:
        self.name = name
        self.config = config or SpacedRepetitionConfig()

    @abstractmethod
    def calculate_next_review(
        self,
        state: MemoryNodeState,
        quality_grade: int,
        timestamp: Optional[float] = None,
    ) -> MemoryNodeState:
        """
        SPEC §4.13 lines 1354-1379:
        Calculate the next interval, ease factor, stability, and due date.
        """
        pass

    @abstractmethod
    def get_node_state(self, node_id: str) -> Optional[MemoryNodeState]:
        """Fetch current spaced repetition state for a memory node."""
        pass

    @abstractmethod
    def save_node_state(self, state: MemoryNodeState) -> None:
        """Persist spaced repetition state for a memory node."""
        pass

    @abstractmethod
    def record_review(
        self,
        node_id: str,
        quality_grade: int,
        timestamp: Optional[float] = None,
    ) -> MemoryNodeState:
        """Record an explicit review outcome for a memory node and update state."""
        pass

    @abstractmethod
    def get_due_nodes(self, limit: int = 50, timestamp: Optional[float] = None) -> List[MemoryNodeState]:
        """
        SPEC §4.13 line 1383-1389:
        Query nodes where due_date <= now() or due_date is unset/0.
        """
        pass

    @abstractmethod
    def run_consolidation(
        self,
        limit: int = 50,
        simulated_grades: Optional[Dict[str, int]] = None,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        SPEC §4.13 lines 1381-1400:
        Nightly memory consolidation worker evaluating due nodes and promoting core facts.
        """
        pass

    @abstractmethod
    def list_core_facts(self) -> List[MemoryNodeState]:
        """Retrieve all nodes promoted to permanent CORE_FACT status."""
        pass


# Aliases for provider naming consistency
BaseSpacedRepetitionProvider = MemoryConsolidationProvider
