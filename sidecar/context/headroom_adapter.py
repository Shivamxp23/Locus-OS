"""Context Window Management & Headroom Adapter (§1.6).

Adapts Headroom CCR and token estimators into the session context compaction flow:
- estimate_context_tokens(messages)
- should_compact(prompt_tokens, threshold)
- compact(messages, options)
- HeadroomCompactionAdapter
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from sidecar.memory.headroom_ccr import (
    CompressConfig,
    CompressResult,
    HeadroomCompressor,
    estimate_tokens,
)


@dataclass
class CompactionOptions:
    protect_first_n: int = 3
    protect_last_n: int = 6
    threshold_tokens: int = 64000
    focus_topic: Optional[str] = None


@dataclass
class CompactionResult:
    compacted_messages: List[Dict[str, Any]]
    original_tokens: int
    compacted_tokens: int
    saved_tokens: int
    retrieval_keys: List[str] = field(default_factory=list)


def estimate_context_tokens(messages: List[Dict[str, Any]]) -> int:
    """Estimate total token usage across message array."""
    return sum(estimate_tokens(str(m.get("content", ""))) for m in messages)


def should_compact(prompt_tokens: int, threshold_tokens: int) -> bool:
    """Check if token usage has exceeded threshold."""
    return prompt_tokens >= threshold_tokens


class HeadroomCompactionAdapter:
    """Adapter invoking Headroom CCR as the context compaction provider."""

    def __init__(self, compressor: Optional[HeadroomCompressor] = None) -> None:
        self.compressor = compressor or HeadroomCompressor()

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        return estimate_context_tokens(messages)

    def should_compact(self, current_tokens: int, threshold: int = 64000) -> bool:
        return should_compact(current_tokens, threshold)

    def compact(
        self,
        messages: List[Dict[str, Any]],
        options: Optional[CompactionOptions] = None,
    ) -> CompactionResult:
        opts = options or CompactionOptions()
        orig = estimate_context_tokens(messages)

        cfg = CompressConfig(
            protect_recent=opts.protect_last_n,
            min_tokens_to_compress=100,
            frozen_message_count=opts.protect_first_n + 1,
        )
        self.compressor.config = cfg

        res: CompressResult = self.compressor.compress(messages)
        compacted = res.compressed_messages
        comp_tokens = estimate_context_tokens(compacted)
        saved = max(0, orig - comp_tokens)

        return CompactionResult(
            compacted_messages=compacted,
            original_tokens=orig,
            compacted_tokens=comp_tokens,
            saved_tokens=saved,
            retrieval_keys=res.cache_keys_created,
        )
