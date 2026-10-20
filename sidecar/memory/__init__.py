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

from sidecar.memory.project_decay import (
    COLD_STORAGE_THRESHOLD,
    DEFAULT_HALF_LIFE,
    HALF_LIFE_DAYS,
    ProjectDecayEngine,
    ProjectNode,
    ProjectRecord,
    calculate_retention_strength,
)
from sidecar.memory.cold_archiver import (
    archive_cluster_to_cold_storage,
    list_cold_archives,
    load_cold_archive,
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
    "COLD_STORAGE_THRESHOLD",
    "DEFAULT_HALF_LIFE",
    "HALF_LIFE_DAYS",
    "ProjectDecayEngine",
    "ProjectNode",
    "ProjectRecord",
    "calculate_retention_strength",
    "archive_cluster_to_cold_storage",
    "list_cold_archives",
    "load_cold_archive",
]
