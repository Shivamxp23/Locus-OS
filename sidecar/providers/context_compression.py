"""
Base provider definitions for Context Window Management & Token Compression (SPEC §1.6 & §4.17, F-0006).
Defines contracts for token estimation, threshold-based compaction,
Cache-Compress-Retrieve (CCR) reversibility, and inflation guards.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CompressionMode(str, Enum):
    HEADROOM_CCR = "headroom-ccr"
    PI_DEFAULT = "pi-default"
    SIMPLE_SUMMARIZE = "simple-summarize"


@dataclass
class ContextMessage:
    role: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
        }


@dataclass
class CompactionResult:
    compressed_messages: List[Dict[str, Any]]
    original_tokens: int
    compressed_tokens: int
    ratio: float
    cached_keys: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    protected_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compressed_messages": self.compressed_messages,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "ratio": round(self.ratio, 3),
            "cached_keys": self.cached_keys,
            "summary": self.summary,
            "protected_count": self.protected_count,
        }


class BaseCompressionProvider(ABC):
    """Abstract contract for context window management and token compression."""

    @abstractmethod
    def estimate_tokens(self, text_or_messages: Any) -> int:
        """Estimate token count for a string or list of message objects."""
        raise NotImplementedError

    @abstractmethod
    def should_compact(self, current_tokens: int, threshold: int) -> bool:
        """Evaluate whether compaction threshold is reached."""
        raise NotImplementedError

    @abstractmethod
    def compact(
        self,
        messages: List[Dict[str, Any]],
        protect_first_n: int = 3,
        protect_last_n: int = 6,
        options: Optional[Dict[str, Any]] = None,
    ) -> CompactionResult:
        """
        Compact conversation history preserving first N and last N messages,
        compressing intermediate turns via CCR or summarization.
        """
        raise NotImplementedError

    @abstractmethod
    def compress_text(self, text: str, cache_key: Optional[str] = None) -> Dict[str, Any]:
        """Compress text with CCR caching and inflation guard."""
        raise NotImplementedError

    @abstractmethod
    def retrieve_original(self, cache_key: str) -> Optional[str]:
        """Retrieve original uncompressed text from CCR cache by key."""
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if context compression is enabled in configuration."""
        raise NotImplementedError
