"""
SPEC §4.16: Context Compression (F-0110 / US-55).
Defines the CompactionProvider and ContextEngine contracts adapting Hermes context_engine.py
and conversation_compression.py to Locus's swappable provider architecture.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CompactionConfig:
    """
    Configuration parameters for context compression and Hermes context engine.
    SPEC §4.16 line 3951-3953:
      - threshold_percent: float = 0.75 (compress at 75% usage)
      - protect_first_n: int = 3 (keep first 3 non-system messages)
      - protect_last_n: int = 6 (keep last 6 messages)
    """
    enabled: bool = True
    threshold_percent: float = 0.75
    protect_first_n: int = 3
    protect_last_n: int = 6
    default_context_length: int = 128000
    auxiliary_model: str = "deepseek-v4-flash"
    lock_timeout_seconds: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CompactionConfig:
        return cls(
            enabled=bool(data.get("enabled", True)),
            threshold_percent=float(data.get("threshold_percent", 0.75)),
            protect_first_n=int(data.get("protect_first_n", 3)),
            protect_last_n=int(data.get("protect_last_n", 6)),
            default_context_length=int(data.get("default_context_length", 128000)),
            auxiliary_model=str(data.get("auxiliary_model", "deepseek-v4-flash")),
            lock_timeout_seconds=float(data.get("lock_timeout_seconds", 30.0)),
        )


class ContextEngine(ABC):
    """
    SPEC §4.16 lines 3940-3970:
    Hermes-compatible abstract base class for context management engines.
    Tracks token consumption, evaluates compaction thresholds, and executes
    multi-stage context compression.
    """

    def __init__(
        self,
        name: str = "compressor",
        context_length: int = 128000,
        threshold_percent: float = 0.75,
        protect_first_n: int = 3,
        protect_last_n: int = 6,
    ) -> None:
        self.name = name
        self.context_length = context_length
        self.threshold_percent = threshold_percent
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n
        self.threshold_tokens = int(context_length * threshold_percent)
        self.last_prompt_tokens: int = 0
        self.compression_count: int = 0

    @abstractmethod
    def update_from_response(self, usage: Dict[str, Any]) -> None:
        """Called after every LLM call to update token tracking counters."""
        raise NotImplementedError

    @abstractmethod
    def should_compress(self, prompt_tokens: int) -> bool:
        """Check if context compaction threshold is reached."""
        raise NotImplementedError

    @abstractmethod
    def compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: int,
        focus_topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute context compaction on message history."""
        raise NotImplementedError

    @abstractmethod
    def on_session_start(self, session_id: str) -> None:
        """Lifecycle hook: initialize state on session start."""
        raise NotImplementedError

    @abstractmethod
    def on_session_end(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        """Lifecycle hook: clean up or record metrics on session end."""
        raise NotImplementedError

    @abstractmethod
    def on_session_reset(self) -> None:
        """Reset internal counters and session trackers."""
        raise NotImplementedError

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Optional tools exposed by this context engine."""
        return []

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> str:
        """Handle execution of tool calls exposed by this engine."""
        return "{}"

    def update_model(
        self,
        model: str,
        context_length: int,
        threshold_percent: Optional[float] = None,
    ) -> None:
        """Recalculate threshold tokens when model or context window switches."""
        self.context_length = context_length
        if threshold_percent is not None:
            self.threshold_percent = threshold_percent
        self.threshold_tokens = int(self.context_length * self.threshold_percent)


class MemoryProviderHook(ABC):
    """
    Hook interface for memory providers participating in pre-compaction extraction
    and session rotation per SPEC §4.16 lines 3986-3990 & 4014-4015.
    """

    @abstractmethod
    def on_pre_compress(self, messages_to_discard: List[Dict[str, Any]]) -> Optional[str]:
        """Extract insights from messages about to be compressed/lost."""
        raise NotImplementedError

    @abstractmethod
    def on_session_switch(self, new_session_id: str, parent_session_id: str) -> None:
        """Handle session rotation upon compaction."""
        raise NotImplementedError


class CompactionProvider(ABC):
    """
    SPEC §4.16 line 4024:
    Provider Interface: CompactionProvider
    Wraps both Pi's native compaction and Hermes's ContextEngine architecture.
    """

    def __init__(self, name: str = "default", config: Optional[CompactionConfig] = None) -> None:
        self.name = name
        self.config = config or CompactionConfig()

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if context compression is enabled."""
        raise NotImplementedError

    @abstractmethod
    def get_engine(self) -> ContextEngine:
        """Return the active ContextEngine instance."""
        raise NotImplementedError

    @abstractmethod
    def compress_context(
        self,
        messages: List[Dict[str, Any]],
        focus_topic: Optional[str] = None,
        memory_providers: Optional[List[MemoryProviderHook]] = None,
        old_session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute 7-step compression flow returning compressed messages,
        new session_id, and compression statistics.
        """
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Diagnostic health check."""
        raise NotImplementedError
