"""
SPEC §4.10: Holographic Reduced Representations (HRR Memory Binding) Provider Interfaces.
Defines HRR vector representation, codebook data models, configuration, and associative memory provider.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class HRRVector:
    """
    SPEC §4.10 line 1185:
    HRRVector:
        dimension: int = 2048
        values: float[2048]   // Zero-mean, variance 1/D normal distribution
    """
    dimension: int = 2048
    values: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.values and len(self.values) != self.dimension:
            self.dimension = len(self.values)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "values": [float(x) for x in self.values],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HRRVector:
        dim = int(data.get("dimension", 2048))
        raw_vals = data.get("values", [])
        return cls(dimension=dim, values=[float(x) for x in raw_vals])

    def to_numpy(self) -> np.ndarray:
        return np.asarray(self.values, dtype=np.float64)

    @classmethod
    def from_numpy(cls, arr: np.ndarray) -> HRRVector:
        flat = np.asarray(arr, dtype=np.float64).flatten()
        return cls(dimension=int(len(flat)), values=flat.tolist())


@dataclass
class HolographicConfig:
    """
    SPEC §4.10 line 1240-1242:
    - codebook cache persisted at .locus/memory/hrr_codebook.bin
    - off switch locus.memory.hrr.enabled / locus.holographic_hrr.enabled
    - threshold tau >= 0.70
    """
    enabled: bool = True
    dimension: int = 2048
    similarity_threshold: float = 0.70
    codebook_cache_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseAssociativeMemoryProvider(ABC):
    """
    SPEC §4.10 line 1239:
    Provider Interface: AssociativeMemoryProvider
    """

    def __init__(self, name: str = "default", config: Optional[HolographicConfig] = None) -> None:
        self.name = name
        self.config = config or HolographicConfig()

    @abstractmethod
    def bind(self, a: HRRVector, b: HRRVector) -> HRRVector:
        """
        SPEC §4.10 line 1195:
        Circular Convolution (Binding: a ⊛ b)
        """
        pass

    @abstractmethod
    def unbind(self, c: HRRVector, b: HRRVector) -> HRRVector:
        """
        SPEC §4.10 line 1204:
        Circular Correlation (Unbinding: a ≈ c ⊙ b)
        """
        pass

    @abstractmethod
    def bundle(self, vectors: List[HRRVector]) -> HRRVector:
        """
        SPEC §4.10 line 1210:
        Vector Superposition (Bundling: s = a + b + c)
        """
        pass

    @abstractmethod
    def cleanup(self, noisy_vector: HRRVector, threshold: Optional[float] = None) -> Optional[str]:
        """
        SPEC §4.10 line 1215:
        Clean-Up Memory (Associative Recall)
        """
        pass

    @abstractmethod
    def encode_ephemeral_state(
        self,
        current_task: Any,
        active_mode: Any,
        stress_level: Any,
    ) -> HRRVector:
        """
        SPEC §4.10 line 1226:
        Fast Ephemeral State Composition Pipeline
        """
        pass

    @abstractmethod
    def get_or_create_symbol(self, symbol: str) -> HRRVector:
        """Fetch or deterministically initialize proto-vector for a symbol."""
        pass

    @abstractmethod
    def list_symbols(self) -> List[str]:
        """List all symbols currently in the codebook."""
        pass

    @abstractmethod
    def get_symbol_vector(self, symbol: str) -> Optional[HRRVector]:
        """Retrieve stored proto-vector for symbol if present."""
        pass

    def similarity(self, a: HRRVector, b: HRRVector) -> float:
        """Compute cosine similarity between two HRR vectors."""
        a_arr = a.to_numpy()
        b_arr = b.to_numpy()
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        if norm_a <= 1e-12 or norm_b <= 1e-12:
            return 0.0
        return float(np.dot(a_arr, b_arr) / (norm_a * norm_b))


# Backward-compatible alias
BaseHolographicProvider = BaseAssociativeMemoryProvider
