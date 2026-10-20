"""
SPEC §4.10 line 1178:
`sidecar/memory/hrr_codebook.py`
Orthogonal random vector dictionary mapping symbols (roles, entities, attributes)
to fixed D=2048 dimensional vectors. Supports deterministic SHA-256 generation
and persistence caching at .locus/memory/hrr_codebook.bin.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
from pathlib import Path
import threading
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


def generate_unitary_vector(symbol: str, dimension: int = 2048) -> np.ndarray:
    """
    SPEC §4.10 lines 1185-1188, 1242:
    Generate deterministic unit-norm vector with zero-mean, variance 1/D.
    Uses SHA-256 seed and frequency-domain unitary normalization so that
    binding / unbinding retains high fidelity and exact invertibility.
    """
    seed = int.from_bytes(hashlib.sha256(symbol.encode("utf-8")).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    vec = rng.normal(0.0, 1.0 / np.sqrt(dimension), dimension)

    # Unitary in frequency domain
    X = np.fft.rfft(vec)
    mag = np.abs(X)
    mag[mag == 0] = 1.0
    vec_u = np.fft.irfft(X / mag, n=dimension)
    norm = np.linalg.norm(vec_u)
    if norm > 0:
        vec_u = vec_u / norm
    return vec_u.astype(np.float64)


class HRRCodebook:
    """
    SPEC §4.10 line 1189:
    Codebook:
        symbols: Dict[string -> HRRVector]
    """

    def __init__(
        self,
        dimension: int = 2048,
        cache_path: Optional[str] = None,
    ) -> None:
        self.dimension = dimension
        self.cache_path = cache_path or ".locus/memory/hrr_codebook.bin"
        self._symbols: Dict[str, np.ndarray] = {}
        self._lock = threading.RLock()

        if self.cache_path and os.path.exists(self.cache_path):
            try:
                self.load(self.cache_path)
            except Exception as e:
                logger.warning(f"Failed to load HRR codebook from {self.cache_path}: {e}")

    def get_or_create(self, symbol: str) -> np.ndarray:
        """
        Retrieve existing symbol vector or deterministically generate a new one.
        """
        with self._lock:
            if symbol not in self._symbols:
                vec = generate_unitary_vector(symbol, self.dimension)
                self._symbols[symbol] = vec
            return self._symbols[symbol]

    def get(self, symbol: str) -> Optional[np.ndarray]:
        """
        Get vector for symbol if present.
        """
        with self._lock:
            return self._symbols.get(symbol)

    def set(self, symbol: str, vector: np.ndarray) -> None:
        """
        Register a specific vector for a symbol.
        """
        with self._lock:
            vec = np.asarray(vector, dtype=np.float64).flatten()
            if len(vec) != self.dimension:
                raise ValueError(
                    f"Vector dimension {len(vec)} does not match codebook dimension {self.dimension}"
                )
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            self._symbols[symbol] = vec

    def list_symbols(self) -> List[str]:
        """
        List all registered symbols.
        """
        with self._lock:
            return sorted(list(self._symbols.keys()))

    def save(self, path: Optional[str] = None) -> None:
        """
        SPEC §4.10 line 1240:
        Persist codebook cache to .locus/memory/hrr_codebook.bin.
        """
        target = path or self.cache_path
        if not target:
            return
        with self._lock:
            p = Path(target)
            p.parent.mkdir(parents=True, exist_ok=True)
            # Save using np.savez_compressed into target path
            arrays_to_save = {k: v for k, v in self._symbols.items()}
            np.savez_compressed(target, **arrays_to_save)

    def load(self, path: Optional[str] = None) -> None:
        """
        Load codebook cache from disk.
        """
        target = path or self.cache_path
        if not target or not os.path.exists(target):
            return
        with self._lock:
            loaded = np.load(target)
            for k in loaded.files:
                arr = loaded[k]
                if len(arr) == self.dimension:
                    self._symbols[k] = arr.astype(np.float64)
