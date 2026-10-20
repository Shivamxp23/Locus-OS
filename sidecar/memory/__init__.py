"""
SPEC §4.10: Memory modules package.
Exposes HRR holographic representations and codebook symbols.
"""
from sidecar.memory.hrr import (
    HolographicMemory,
    HolographicMemoryBackend,
    circular_convolution,
    circular_correlation,
    superposition_bundle,
    cosine_similarity,
    cleanup_memory,
)
from sidecar.memory.hrr_codebook import (
    HRRCodebook,
    generate_unitary_vector,
)

from sidecar.memory.spaced_repetition import (
    calculate_next_review,
    calculate_retention_probability,
    evaluate_node_retention,
)
from sidecar.memory.memory_scheduler import (
    SpacedRepetitionMemoryScheduler,
    MemoryScheduler,
)
from sidecar.providers.spaced_repetition import (
    MemoryNodeState,
    SpacedRepetitionConfig,
    MemoryConsolidationProvider,
)

__all__ = [
    "HolographicMemory",
    "HolographicMemoryBackend",
    "circular_convolution",
    "circular_correlation",
    "superposition_bundle",
    "cosine_similarity",
    "cleanup_memory",
    "HRRCodebook",
    "generate_unitary_vector",
    "calculate_next_review",
    "calculate_retention_probability",
    "evaluate_node_retention",
    "SpacedRepetitionMemoryScheduler",
    "MemoryScheduler",
    "MemoryNodeState",
    "SpacedRepetitionConfig",
    "MemoryConsolidationProvider",
]
