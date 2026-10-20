"""
SPEC §2.6a / F-0097 / US-36: Streaming (SSE) Provider Contract.
Defines interfaces and data structures for Server-Sent Events (SSE) streaming,
chunk formatting, heartbeats, and client reconnect event handling.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import time
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Union


@dataclass
class SSEEvent:
    """
    Representation of a Server-Sent Event frame.
    """
    data: str
    event: Optional[str] = None
    id: Optional[str] = None
    retry: Optional[int] = None

    def encode(self) -> str:
        """Encode to valid SSE wire format."""
        lines = []
        if self.id is not None:
            lines.append(f"id: {self.id}")
        if self.event is not None:
            lines.append(f"event: {self.event}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        for part in self.data.splitlines():
            lines.append(f"data: {part}")
        if not self.data:
            lines.append("data: ")
        return "\n".join(lines) + "\n\n"


@dataclass
class StreamOptions:
    """Configuration options for SSE streaming."""
    chunk_size: int = 16
    ping_interval_seconds: float = 15.0
    include_timestamps: bool = True
    event_name: str = "message"


class BaseStreamingSSEProvider(ABC):
    """
    Abstract interface for Streaming (SSE) provider.
    Modular, swappable component per AGENTS.md law 11 and modularity architecture (03).
    """

    @abstractmethod
    def format_event(
        self,
        data: Union[str, Dict[str, Any]],
        event: Optional[str] = None,
        id: Optional[str] = None,
        retry: Optional[int] = None,
    ) -> str:
        """Format data into standard SSE frame."""
        pass

    @abstractmethod
    def parse_event(self, raw_frame: str) -> SSEEvent:
        """Parse raw SSE wire string into SSEEvent."""
        pass

    @abstractmethod
    def format_ping(self) -> str:
        """Generate keep-alive heartbeat frame."""
        pass

    @abstractmethod
    async def stream_tokens(
        self,
        token_generator: AsyncIterator[str],
        event_name: str = "delta",
    ) -> AsyncIterator[str]:
        """Stream token chunks as SSE events."""
        pass

    @abstractmethod
    async def stream_text_chunks(
        self,
        text: str,
        chunk_size: int = 16,
        event_name: str = "delta",
    ) -> AsyncIterator[str]:
        """Chunk raw text and stream as SSE events."""
        pass
