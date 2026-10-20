"""
SPEC §4.10: Holographic Reduced Representations (HRR Memory Binding).
`sidecar/memory/hrr.py`
High-performance NumPy implementation of circular convolution, circular correlation,
vector superposition, clean-up memory associative recall, and fast ephemeral state bundling.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from sidecar.memory.hrr_codebook import HRRCodebook, generate_unitary_vector
from sidecar.providers.holographic import (
    BaseAssociativeMemoryProvider,
    HolographicConfig,
    HRRVector,
)

logger = logging.getLogger(__name__)


def normalize(v: np.ndarray) -> np.ndarray:
    """
    SPEC §4.10 line 1200:
    Normalize vector to unit L2 norm.
    """
    norm = np.linalg.norm(v)
    if norm > 1e-12:
        return v / norm
    return v


def invert_axes(b: np.ndarray) -> np.ndarray:
    """
    SPEC §4.10 line 1205:
    b_inv = invert_axes(b.values)  // b*(-t)
    In discrete circular correlation, b*(-t) rolls the reversed array by 1:
    b_inv[0] = b[0], b_inv[i] = b[D - i].
    """
    return np.roll(b[::-1], 1)


def circular_convolution(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    SPEC §4.10 line 1195:
    Circular Convolution (Binding: a ⊛ b):
    A_fft = FFT(a.values)
    B_fft = FFT(b.values)
    C_fft = A_fft * B_fft
    c_vals = Real(IFFT(C_fft))
    RETURN normalize(c_vals)
    """
    dim = len(a)
    A_fft = np.fft.rfft(a)
    B_fft = np.fft.rfft(b)
    C_fft = A_fft * B_fft
    c_vals = np.fft.irfft(C_fft, n=dim)
    return normalize(c_vals)


def circular_correlation(c: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    SPEC §4.10 line 1204:
    Circular Correlation (Unbinding: a ≈ c ⊙ b):
    b_inv = invert_axes(b.values)  // b*(-t)
    RETURN bind(c, b_inv)
    """
    b_inv = invert_axes(b)
    return circular_convolution(c, b_inv)


def superposition_bundle(vectors: List[np.ndarray]) -> np.ndarray:
    """
    SPEC §4.10 line 1210:
    Vector Superposition (Bundling: s = a + b + c):
    s_vals = sum([v.values for v in vectors])
    RETURN normalize(s_vals)
    """
    if not vectors:
        raise ValueError("Cannot bundle empty vector list")
    stacked = np.stack(vectors, axis=0)
    s_vals = np.sum(stacked, axis=0)
    return normalize(s_vals)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a <= 1e-12 or norm_b <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def cleanup_memory(
    noisy_vector: np.ndarray,
    codebook: HRRCodebook,
    threshold: float = 0.70,
) -> Tuple[Optional[str], float]:
    """
    SPEC §4.10 line 1215:
    Clean-Up Memory (Associative Recall):
    best_symbol = null
    max_sim = -1.0
    FOR EACH symbol, proto_vec IN codebook.symbols:
        sim = cosine_similarity(noisy_vector.values, proto_vec.values)
        IF sim > max_sim AND sim >= threshold:
            max_sim = sim
            best_symbol = symbol
    RETURN best_symbol
    """
    best_symbol: Optional[str] = None
    max_sim = -1.0
    symbols = codebook.list_symbols()
    for symbol in symbols:
        proto_vec = codebook.get(symbol)
        if proto_vec is None:
            continue
        sim = cosine_similarity(noisy_vector, proto_vec)
        if sim > max_sim and sim >= threshold:
            max_sim = sim
            best_symbol = symbol
    return best_symbol, max_sim


class HolographicMemory(BaseAssociativeMemoryProvider):
    """
    SPEC §4.10: Holographic Memory Provider.
    Implements BaseAssociativeMemoryProvider with HRR circular convolution,
    circular correlation unbinding, superposition bundling, cleanup associative recall,
    and fast ephemeral state encoding.
    """

    def __init__(
        self,
        config: Optional[HolographicConfig] = None,
        codebook: Optional[HRRCodebook] = None,
    ) -> None:
        self.config = config or HolographicConfig()
        self.dimension = self.config.dimension
        self.threshold = self.config.similarity_threshold
        self.codebook = codebook or HRRCodebook(
            dimension=self.dimension,
            cache_path=self.config.codebook_cache_path,
        )

    def bind(self, a: HRRVector, b: HRRVector) -> HRRVector:
        """
        SPEC §4.10 line 1195:
        Circular Convolution (Binding: a ⊛ b)
        """
        a_arr = a.to_numpy()
        b_arr = b.to_numpy()
        if len(a_arr) != len(b_arr):
            raise ValueError(f"Vector dimensions do not match: {len(a_arr)} vs {len(b_arr)}")
        c_arr = circular_convolution(a_arr, b_arr)
        return HRRVector.from_numpy(c_arr)

    def unbind(self, c: HRRVector, b: HRRVector) -> HRRVector:
        """
        SPEC §4.10 line 1204:
        Circular Correlation (Unbinding: a ≈ c ⊙ b)
        """
        c_arr = c.to_numpy()
        b_arr = b.to_numpy()
        if len(c_arr) != len(b_arr):
            raise ValueError(f"Vector dimensions do not match: {len(c_arr)} vs {len(b_arr)}")
        a_arr = circular_correlation(c_arr, b_arr)
        return HRRVector.from_numpy(a_arr)

    def bundle(self, vectors: List[HRRVector]) -> HRRVector:
        """
        SPEC §4.10 line 1210:
        Vector Superposition (Bundling: s = a + b + c)
        """
        if not vectors:
            raise ValueError("Cannot bundle empty vector list")
        arrs = [v.to_numpy() for v in vectors]
        s_arr = superposition_bundle(arrs)
        return HRRVector.from_numpy(s_arr)

    def cleanup(self, noisy_vector: HRRVector, threshold: Optional[float] = None) -> Optional[str]:
        """
        SPEC §4.10 line 1215:
        Clean-Up Memory (Associative Recall)
        """
        th = self.threshold if threshold is None else threshold
        best_symbol, _ = cleanup_memory(noisy_vector.to_numpy(), self.codebook, threshold=th)
        return best_symbol

    def cleanup_with_score(
        self,
        noisy_vector: HRRVector,
        threshold: Optional[float] = None,
    ) -> Tuple[Optional[str], float]:
        """
        Associative recall returning both symbol and cosine similarity score.
        """
        th = self.threshold if threshold is None else threshold
        return cleanup_memory(noisy_vector.to_numpy(), self.codebook, threshold=th)

    def encode_ephemeral_state(
        self,
        current_task: Any,
        active_mode: Any,
        stress_level: Any,
    ) -> HRRVector:
        """
        SPEC §4.10 line 1226:
        FAST EPHEMERAL STATE COMPOSITION PIPELINE:
            task_bound = bind(codebook.get("ROLE:TASK"), codebook.get(current_task.id))
            mode_bound = bind(codebook.get("ROLE:MODE"), codebook.get(active_mode.name))
            stress_bound = bind(codebook.get("ROLE:STRESS"), codebook.get(stress_level.category))
            state_bundle = bundle([task_bound, mode_bound, stress_bound])
            RETURN state_bundle
        """
        task_id = self._extract_field(current_task, "id")
        mode_name = self._extract_field(active_mode, "name")
        stress_cat = self._extract_field(stress_level, "category")

        role_task = self.codebook.get_or_create("ROLE:TASK")
        val_task = self.codebook.get_or_create(f"TASK:{task_id}")
        task_bound = circular_convolution(role_task, val_task)

        role_mode = self.codebook.get_or_create("ROLE:MODE")
        val_mode = self.codebook.get_or_create(f"MODE:{mode_name}")
        mode_bound = circular_convolution(role_mode, val_mode)

        role_stress = self.codebook.get_or_create("ROLE:STRESS")
        val_stress = self.codebook.get_or_create(f"STRESS:{stress_cat}")
        stress_bound = circular_convolution(role_stress, val_stress)

        state_arr = superposition_bundle([task_bound, mode_bound, stress_bound])
        return HRRVector.from_numpy(state_arr)

    def get_or_create_symbol(self, symbol: str) -> HRRVector:
        """
        Retrieve or generate vector for symbol.
        """
        arr = self.codebook.get_or_create(symbol)
        return HRRVector.from_numpy(arr)

    def list_symbols(self) -> List[str]:
        """
        List all symbols in codebook.
        """
        return self.codebook.list_symbols()

    def get_symbol_vector(self, symbol: str) -> Optional[HRRVector]:
        """
        Get vector for symbol if known.
        """
        arr = self.codebook.get(symbol)
        if arr is None:
            return None
        return HRRVector.from_numpy(arr)

    def similarity(self, a: HRRVector, b: HRRVector) -> float:
        """
        Cosine similarity between two HRR vectors.
        """
        return cosine_similarity(a.to_numpy(), b.to_numpy())

    @staticmethod
    def _extract_field(obj: Any, field_name: str) -> str:
        """
        Helper extracting string identity from object or dict or scalar.
        """
        if obj is None:
            return "unknown"
        if isinstance(obj, dict):
            return str(obj.get(field_name, obj.get("val", str(obj))))
        if hasattr(obj, field_name):
            val = getattr(obj, field_name)
            return str(val() if callable(val) else val)
        return str(obj)


# Aliases for backward compatibility
HolographicMemoryBackend = HolographicMemory
