"""
SPEC §2.6a / F-0097 / US-36: Streaming (SSE) Implementation.
Provides SSE frame construction, chunk-based streaming, heartbeat pings,
wire-format parsing, and provider registration with modular off-switch.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import re
import time
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Union

from sidecar import config
from sidecar.registry import get_registry
from sidecar.providers.streaming_sse import (
    BaseStreamingSSEProvider,
    SSEEvent,
    StreamOptions,
)


def is_streaming_enabled() -> bool:
    """Check modular off-switch for streaming SSE."""
    enabled = config.get("locus.streaming_sse.enabled", None)
    if enabled is None:
        enabled = config.get("locus.brain.streaming_sse.enabled", True)
    return bool(enabled)


class StreamingSSEProvider(BaseStreamingSSEProvider):
    """
    Concrete implementation of Server-Sent Events (SSE) streaming provider.
    Registers under area 'streaming_sse'.
    """

    def __init__(self, options: Optional[StreamOptions] = None):
        self.options = options or StreamOptions()

    def format_event(
        self,
        data: Union[str, Dict[str, Any]],
        event: Optional[str] = None,
        id: Optional[str] = None,
        retry: Optional[int] = None,
    ) -> str:
        """
        Format payload into standard SSE wire specification.
        Serializes dictionaries to JSON. Multiline strings are prefixed line-by-line.
        """
        if isinstance(data, (dict, list)):
            payload = json.dumps(data, ensure_ascii=False)
        else:
            payload = str(data)

        evt = SSEEvent(
            data=payload,
            event=event or self.options.event_name,
            id=id,
            retry=retry,
        )
        return evt.encode()

    def parse_event(self, raw_frame: str) -> SSEEvent:
        """
        Parse raw SSE frame into SSEEvent structure.
        Handles comments (starting with :) and multiline data fields.
        """
        event_type: Optional[str] = None
        event_id: Optional[str] = None
        retry_val: Optional[int] = None
        data_lines: List[str] = []

        for line in raw_frame.splitlines():
            line = line.strip("\r")
            if not line:
                continue
            if line.startswith(":"):
                # Comment line, ignore
                continue
            if ":" in line:
                field, value = line.split(":", 1)
                field = field.strip()
                if value.startswith(" "):
                    value = value[1:]
            else:
                field, value = line.strip(), ""

            if field == "event":
                event_type = value
            elif field == "id":
                event_id = value
            elif field == "retry":
                try:
                    retry_val = int(value)
                except ValueError:
                    pass
            elif field == "data":
                data_lines.append(value)

        return SSEEvent(
            data="\n".join(data_lines),
            event=event_type,
            id=event_id,
            retry=retry_val,
        )

    def format_ping(self) -> str:
        """
        Generate keep-alive heartbeat frame.
        """
        return self.format_event(
            data={"type": "ping", "timestamp": int(time.time() * 1000)},
            event="ping",
        )

    async def stream_tokens(
        self,
        token_generator: AsyncIterator[str],
        event_name: str = "delta",
    ) -> AsyncIterator[str]:
        """
        Consume token async generator and yield SSE formatted chunks.
        """
        idx = 0
        async for token in token_generator:
            idx += 1
            yield self.format_event(
                data={"token": token, "index": idx},
                event=event_name,
                id=str(idx),
            )
        # Final terminal chunk
        yield self.format_event(
            data={"done": True, "total_chunks": idx},
            event="done",
            id=str(idx + 1),
        )

    async def stream_text_chunks(
        self,
        text: str,
        chunk_size: int = 16,
        event_name: str = "delta",
    ) -> AsyncIterator[str]:
        """
        Break text into fixed-size chunks and stream as SSE events.
        """
        effective_chunk_size = chunk_size or self.options.chunk_size
        idx = 0
        for i in range(0, len(text), effective_chunk_size):
            chunk = text[i : i + effective_chunk_size]
            idx += 1
            yield self.format_event(
                data={"text": chunk, "index": idx},
                event=event_name,
                id=str(idx),
            )
            # Yield control to event loop
            await asyncio.sleep(0)

        yield self.format_event(
            data={"done": True, "total_chunks": idx},
            event="done",
            id=str(idx + 1),
        )


# Canonical provider registration per modularity architecture (03)
get_registry().register("streaming_sse", "default", StreamingSSEProvider)
