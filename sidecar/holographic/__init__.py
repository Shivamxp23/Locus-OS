"""
SPEC §4.10: Holographic Reduced Representations (HRR) package.
Backward-compatible wrapper re-exporting memory HRR implementations.
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
from sidecar.providers.holographic import (
    BaseAssociativeMemoryProvider,
    BaseHolographicProvider,
    HolographicConfig,
    HRRVector,
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
    "BaseAssociativeMemoryProvider",
    "BaseHolographicProvider",
    "HolographicConfig",
    "HRRVector",
]
