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
]
