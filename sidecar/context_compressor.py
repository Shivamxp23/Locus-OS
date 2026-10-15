"""Context Compression Engine (§4.16).

Implements Hermes-style context compression with threshold tracking, range protection
(protect_first_n, protect_last_n), lock protection, and middle-range compaction.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


DEFAULT_CONTEXT_LENGTH: int = 128000
DEFAULT_THRESHOLD_PERCENT: float = 0.75
DEFAULT_PROTECT_FIRST_N: int = 3
DEFAULT_PROTECT_LAST_N: int = 6


@dataclass
class UsageMetrics:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ContextEngine:
    """Manages token thresholds and compaction triggers across LLM conversation turns."""

    def __init__(
        self,
        name: str = "hermes_compressor",
        context_length: int = DEFAULT_CONTEXT_LENGTH,
        threshold_percent: float = DEFAULT_THRESHOLD_PERCENT,
        protect_first_n: int = DEFAULT_PROTECT_FIRST_N,
        protect_last_n: int = DEFAULT_PROTECT_LAST_N,
    ) -> None:
        self.name = name
        self.context_length = context_length
        self.threshold_percent = threshold_percent
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n
        self.threshold_tokens = int(self.context_length * self.threshold_percent)

        self.last_prompt_tokens: int = 0
        self.compression_count: int = 0
        self.active_session_id: Optional[str] = None
        self._lock = threading.Lock()

    def update_model(self, context_length: int) -> None:
        self.context_length = context_length
        self.threshold_tokens = int(self.context_length * self.threshold_percent)

    def update_from_response(self, usage: Dict[str, Any]) -> None:
        self.last_prompt_tokens = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)))

    def should_compress(self, prompt_tokens: Optional[int] = None) -> bool:
        tokens = prompt_tokens if prompt_tokens is not None else self.last_prompt_tokens
        return tokens >= self.threshold_tokens

    def on_session_start(self, session_id: str) -> None:
        self.active_session_id = session_id
        self.on_session_reset()

    def on_session_end(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        self.active_session_id = None

    def on_session_reset(self) -> None:
        self.last_prompt_tokens = 0
        self.compression_count = 0

    def compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: int = 0,
        focus_topic: Optional[str] = None,
        summarizer_fn: Optional[Callable[[List[Dict[str, Any]], Optional[str]], str]] = None,
    ) -> List[Dict[str, Any]]:
        """Compact conversation by preserving head (first N) and tail (last N) while summarizing middle."""
        with self._lock:
            # If total messages <= protect_first_n + protect_last_n + 1 (for system prompt), nothing to compress
            head_count = self.protect_first_n + 1
            tail_count = self.protect_last_n

            if len(messages) <= (head_count + tail_count):
                return list(messages)

            head = messages[:head_count]
            tail = messages[-tail_count:]
            middle = messages[head_count:-tail_count]

            if not middle:
                return list(messages)

            # Summarization step
            if summarizer_fn:
                summary_text = summarizer_fn(middle, focus_topic)
            else:
                summary_lines = []
                for m in middle:
                    role = m.get("role", "unknown")
                    content = str(m.get("content", ""))
                    summary_lines.append(f"[{role}]: {content[:80]}")
                summary_text = f"Compressed conversation history ({len(middle)} messages):\n" + "\n".join(summary_lines[:8])

            if focus_topic:
                summary_text += f"\n[Focus Area: {focus_topic}]"

            summary_message = {
                "role": "system",
                "content": f"[Previous context summary]: {summary_text}",
                "compressed": True,
            }

            self.compression_count += 1
            return head + [summary_message] + tail


def compress_context(
    messages: List[Dict[str, Any]],
    engine: Optional[ContextEngine] = None,
    focus_topic: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Helper entry point for single-call compression."""
    eng = engine or ContextEngine()
    return eng.compress(messages=messages, focus_topic=focus_topic)
