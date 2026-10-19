"""
SPEC §1.11 / F-0011 / US-30: Title Generation Provider Contract.
Defines interfaces and data models for auto-generating session titles.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import threading
from typing import Any, Callable, Dict, Optional


@dataclass
class TitleGenerationRequest:
    user_message: str
    assistant_response: str
    timeout: float = 30.0
    fallback_title: str = "New Session"
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "timeout": self.timeout,
            "fallback_title": self.fallback_title,
            "extra_metadata": self.extra_metadata,
        }


@dataclass
class TitleGenerationResult:
    title: str
    raw_response: str = ""
    source: str = "llm"  # llm, fallback, user_override
    status: str = "success"  # success, fallback, disabled, error
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "raw_response": self.raw_response,
            "source": self.source,
            "status": self.status,
            "duration_ms": self.duration_ms,
        }


class BaseTitleGeneratorProvider(ABC):
    """Abstract base class for title generation provider."""

    @abstractmethod
    def generate_title(
        self,
        user_message: str,
        assistant_response: str,
        timeout: float = 30.0,
        llm_caller: Optional[Callable[[Dict[str, Any]], str]] = None,
    ) -> Optional[str]:
        """Synchronously generate a 3-7 word session title from first turn exchange."""
        pass

    @abstractmethod
    def clean_title(self, raw_title: str) -> str:
        """Clean artifacts (strip quotes, remove 'Title:' prefix, clamp to 80 chars)."""
        pass

    @abstractmethod
    def format_prompt(
        self, user_snippet: str, assistant_snippet: str
    ) -> Dict[str, Any]:
        """Assemble system prompt and user content messages."""
        pass

    @abstractmethod
    def generate_title_async(
        self,
        user_message: str,
        assistant_response: str,
        callback: Callable[[str], None],
        timeout: float = 30.0,
        failure_callback: Optional[Callable[[Exception], None]] = None,
        llm_caller: Optional[Callable[[Dict[str, Any]], str]] = None,
    ) -> threading.Thread:
        """Asynchronously dispatch title generation without blocking turn response."""
        pass
