"""Holographic Reduced Representations (HRR Memory Binding) (§4.10).

Encodes high-dimensional distributed representations of ephemeral system states,
role-filler bindings, and composite situational contexts using circular convolution
and correlation (Plate, 2003).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class HRRVector:
    values: np.ndarray
    dim: int = 1024

    def __post_init__(self) -> None:
        if isinstance(self.values, list):
            self.values = np.array(self.values, dtype=np.float64)
        if self.values.shape[0] != self.dim:
            self.dim = self.values.shape[0]

    def norm(self) -> float:
        return float(np.linalg.norm(self.values))

    def normalize(self) -> HRRVector:
        n = self.norm()
        if n > 1e-12:
            self.values = self.values / n
        return self

    def to_list(self) -> List[float]:
        return self.values.tolist()


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Compute cosine similarity between two 1D vectors."""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-12 or n2 < 1e-12:
        return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))


class Codebook:
    """Manages unique HRR symbol vectors drawn from zero-mean, 1/D variance normal distributions."""

    def __init__(self, dim: int = 1024, seed: Optional[int] = 42) -> None:
        self.dim = dim
        self.rng = np.random.default_rng(seed)
        self.symbols: Dict[str, HRRVector] = {}

    def get_or_create(self, symbol: str) -> HRRVector:
        if symbol not in self.symbols:
            scale = 1.0 / math.sqrt(self.dim)
            raw = self.rng.normal(loc=0.0, scale=scale, size=self.dim)
            vec = HRRVector(values=raw, dim=self.dim).normalize()
            self.symbols[symbol] = vec
        return self.symbols[symbol]

    def has_symbol(self, symbol: str) -> bool:
        return symbol in self.symbols


def bind(a: HRRVector, b: HRRVector) -> HRRVector:
    """Circular convolution (a ⊛ b) using FFT."""
    if a.dim != b.dim:
        raise ValueError(f"HRR dimension mismatch: {a.dim} vs {b.dim}")
    a_fft = np.fft.fft(a.values)
    b_fft = np.fft.fft(b.values)
    c_fft = a_fft * b_fft
    c_vals = np.real(np.fft.ifft(c_fft))
    return HRRVector(values=c_vals, dim=a.dim).normalize()


def unbind(c: HRRVector, b: HRRVector) -> HRRVector:
    """Circular correlation (c ⊙ b) using involution of b."""
    if c.dim != b.dim:
        raise ValueError(f"HRR dimension mismatch: {c.dim} vs {b.dim}")
    # involution: b_inv[i] = b[(-i) % D]
    b_inv_vals = np.roll(b.values[::-1], 1)
    b_inv = HRRVector(values=b_inv_vals, dim=b.dim)
    return bind(c, b_inv)


def bundle(vectors: List[HRRVector]) -> HRRVector:
    """Vector superposition (s = a + b + c + ...) normalized."""
    if not vectors:
        raise ValueError("Cannot bundle empty vector list")
    dim = vectors[0].dim
    accum = np.zeros(dim, dtype=np.float64)
    for v in vectors:
        if v.dim != dim:
            raise ValueError(f"HRR dimension mismatch in bundle: {v.dim} vs {dim}")
        accum += v.values
    return HRRVector(values=accum, dim=dim).normalize()


def cleanup(
    noisy_vector: HRRVector,
    codebook: Codebook,
    threshold: float = 0.30,
) -> Optional[str]:
    """Associative recall: match noisy unbind result against known symbols in codebook."""
    best_symbol: Optional[str] = None
    max_sim = -1.0

    for sym, proto in codebook.symbols.items():
        sim = cosine_similarity(noisy_vector.values, proto.values)
        if sim > max_sim and sim >= threshold:
            max_sim = sim
            best_symbol = sym

    return best_symbol


def encode_ephemeral_state(
    current_task: str,
    active_mode: str,
    stress_level: str,
    codebook: Codebook,
) -> HRRVector:
    """Encode situational state bundle: TASK*current_task + MODE*active_mode + STRESS*stress_level."""
    k_task = codebook.get_or_create("KEY_TASK")
    v_task = codebook.get_or_create(f"TASK:{current_task}")
    pair_task = bind(k_task, v_task)

    k_mode = codebook.get_or_create("KEY_MODE")
    v_mode = codebook.get_or_create(f"MODE:{active_mode}")
    pair_mode = bind(k_mode, v_mode)

    k_stress = codebook.get_or_create("KEY_STRESS")
    v_stress = codebook.get_or_create(f"STRESS:{stress_level}")
    pair_stress = bind(k_stress, v_stress)

    return bundle([pair_task, pair_mode, pair_stress])


def decode_ephemeral_state(
    state_vector: HRRVector,
    key_name: str,
    codebook: Codebook,
    threshold: float = 0.25,
) -> Optional[str]:
    """Retrieve attribute value by unbinding with key vector and cleaning up."""
    key_vec = codebook.get_or_create(f"KEY_{key_name.upper()}")
    noisy = unbind(state_vector, key_vec)
    matched = cleanup(noisy, codebook, threshold=threshold)
    if matched and ":" in matched:
        return matched.split(":", 1)[1]
    return matched


class HolographicMemory:
    """Holographic memory manager for high-dimensional episodic state binding."""

    def __init__(self, dim: int = 1024, seed: int = 42) -> None:
        self.dim = dim
        self.codebook = Codebook(dim=dim, seed=seed)
        self.stored_states: Dict[str, HRRVector] = {}

    def store_state(
        self,
        state_id: str,
        current_task: str,
        active_mode: str,
        stress_level: str,
    ) -> HRRVector:
        vec = encode_ephemeral_state(
            current_task=current_task,
            active_mode=active_mode,
            stress_level=stress_level,
            codebook=self.codebook,
        )
        self.stored_states[state_id] = vec
        return vec

    def query_state_attribute(
        self,
        state_id: str,
        attribute_key: str,
        threshold: float = 0.25,
    ) -> Optional[str]:
        vec = self.stored_states.get(state_id)
        if not vec:
            return None
        return decode_ephemeral_state(
            state_vector=vec,
            key_name=attribute_key,
            codebook=self.codebook,
            threshold=threshold,
        )
