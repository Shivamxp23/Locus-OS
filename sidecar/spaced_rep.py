"""
SPEC §4.13: Spaced Repetition legacy claim path compatibility.
Re-exports SM-2 interval algorithms, MemoryNodeState, and MemoryScheduler.
"""
from __future__ import annotations

from sidecar.memory.memory_scheduler import (
    MemoryScheduler,
    SpacedRepetitionMemoryScheduler,
)
from sidecar.memory.spaced_repetition import (
    calculate_next_review,
    calculate_retention_probability,
    evaluate_node_retention,
)
from sidecar.providers.spaced_repetition import (
    BaseSpacedRepetitionProvider,
    MemoryConsolidationProvider,
    MemoryNodeState,
    SpacedRepetitionConfig,
)

__all__ = [
    "MemoryNodeState",
    "SpacedRepetitionConfig",
    "MemoryConsolidationProvider",
    "BaseSpacedRepetitionProvider",
    "calculate_next_review",
    "calculate_retention_probability",
    "evaluate_node_retention",
    "SpacedRepetitionMemoryScheduler",
    "MemoryScheduler",
]
