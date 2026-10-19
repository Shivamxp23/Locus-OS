"""
Headroom CCR Adapter (SPEC §1.6: Context Window Management & §4.17: Token Compression).
Implements Cache-Compress-Retrieve (CCR) reversible compression, token estimation,
inflation guards, and preservation of first-N / last-N messages.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sidecar.config as config
from sidecar.providers.context_compression import (
    BaseCompressionProvider,
    CompactionResult,
    CompressionMode,
)

logger = logging.getLogger(__name__)


class HeadroomCCRAdapter(BaseCompressionProvider):
    """
    Headroom CCR compression adapter.
    Reversible token compression: originals are cached locally with a cryptographic key,
    allowing the LLM to call headroom_retrieve(cache_key) to recover original content on demand.
    Includes inflation guard (never increases token count) and preservation rules.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.custom_config = custom_config or {}
        if cache_dir:
            self.cache_dir = Path(cache_dir).resolve()
        else:
            self.cache_dir = config.get_locus_home() / "headroom_cache"
        self._memory_cache: Dict[str, Tuple[str, float]] = {}
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def is_enabled(self) -> bool:
        if "locus.context_window_management.enabled" in self.custom_config:
            return bool(self.custom_config["locus.context_window_management.enabled"])
        val = config.get("locus.context_window_management.enabled")
        if val is not None and not config.is_enabled("locus.context_window_management.enabled"):
            return False
        return True

    def get_provider_mode(self) -> str:
        if "locus.compaction.provider" in self.custom_config:
            return str(self.custom_config["locus.compaction.provider"])
        return str(config.get("locus.compaction.provider", CompressionMode.HEADROOM_CCR.value))

    def estimate_tokens(self, text_or_messages: Any) -> int:
        """
        Estimate context tokens.
        Rule of thumb: approx 4 characters per token in English, with word and punctuation weighting.
        """
        if text_or_messages is None:
            return 0
        if isinstance(text_or_messages, str):
            text = text_or_messages
            if not text.strip():
                return 0
            # Approx 4 characters per token with minimum 1 token per whitespace word
            char_count = len(text)
            words = len(text.split())
            return max(int(char_count / 3.8), words)

        if isinstance(text_or_messages, list):
            total = 0
            for item in text_or_messages:
                if isinstance(item, dict):
                    role = item.get("role", "")
                    content = item.get("content", "")
                    total += self.estimate_tokens(role) + self.estimate_tokens(content) + 4
                elif isinstance(item, str):
                    total += self.estimate_tokens(item)
            return total

        return len(str(text_or_messages)) // 4

    def should_compact(self, current_tokens: int, threshold: int) -> bool:
        """Return True when token count reaches or exceeds compaction threshold."""
        return current_tokens >= threshold

    def _store_cache(self, key: str, text: str, ttl_seconds: float = 86400.0) -> None:
        now = time.time()
        self._memory_cache[key] = (text, now + ttl_seconds)
        try:
            cache_file = self.cache_dir / f"{key}.txt"
            cache_file.write_text(text, encoding="utf-8")
        except Exception as exc:
            logger.debug(f"Could not persist CCR cache to disk: {exc}")

    def retrieve_original(self, cache_key: str) -> Optional[str]:
        """Retrieve original uncompressed content by cache key."""
        # Check memory cache
        if cache_key in self._memory_cache:
            text, expires = self._memory_cache[cache_key]
            if time.time() < expires:
                return text
            del self._memory_cache[cache_key]

        # Check disk cache
        try:
            cache_file = self.cache_dir / f"{cache_key}.txt"
            if cache_file.is_file():
                return cache_file.read_text(encoding="utf-8")
        except Exception:
            pass
        return None

    def compress_text(self, text: str, cache_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Compress text with CCR reversibility and inflation guard.
        If transform increases tokens, reverts to original.
        """
        if not text:
            return {
                "compressed": "",
                "cache_key": "",
                "original_tokens": 0,
                "compressed_tokens": 0,
                "inflated": False,
            }

        orig_tokens = self.estimate_tokens(text)
        key = cache_key or hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        self._store_cache(key, text)

        # Attempt structured compression (JSON whitespace elimination, repeating pattern dedup)
        compressed = text
        try:
            parsed = json.loads(text)
            if isinstance(parsed, (dict, list)):
                # Lossless structural compaction
                compressed = json.dumps(parsed, separators=(",", ":"))
        except Exception:
            # Text compression: collapse excess newlines and redundant spaces
            compressed = re.sub(r"\n{3,}", "\n\n", text)
            compressed = re.sub(r"[ \t]{2,}", " ", compressed)
            # If large markdown / conversation, add CCR reference header
            if orig_tokens > 150:
                snippet = compressed[:120].strip()
                compressed = f"{snippet}... [CCR:{key}: {orig_tokens} tokens compressed. Use headroom_retrieve('{key}') to view full original.]"

        comp_tokens = self.estimate_tokens(compressed)

        # Inflation guard: if compressed version is larger than original, keep original
        if comp_tokens >= orig_tokens:
            return {
                "compressed": text,
                "cache_key": key,
                "original_tokens": orig_tokens,
                "compressed_tokens": orig_tokens,
                "inflated": True,
            }

        return {
            "compressed": compressed,
            "cache_key": key,
            "original_tokens": orig_tokens,
            "compressed_tokens": comp_tokens,
            "inflated": False,
        }

    def compact(
        self,
        messages: List[Dict[str, Any]],
        protect_first_n: int = 3,
        protect_last_n: int = 6,
        options: Optional[Dict[str, Any]] = None,
    ) -> CompactionResult:
        """
        SPEC §1.6:
        Preserves first protect_first_n messages (default 3).
        Preserves last protect_last_n messages (default 6).
        Everything between is compressed via Headroom CCR with cached original keys.
        """
        opts = options or {}
        orig_tokens = self.estimate_tokens(messages)

        if not self.is_enabled():
            return CompactionResult(
                compressed_messages=list(messages),
                original_tokens=orig_tokens,
                compressed_tokens=orig_tokens,
                ratio=1.0,
                cached_keys=[],
                summary="Compaction disabled by configuration",
                protected_count=len(messages),
            )

        total_msgs = len(messages)
        # If total messages <= protected sum, nothing to compact in between
        if total_msgs <= (protect_first_n + protect_last_n):
            return CompactionResult(
                compressed_messages=list(messages),
                original_tokens=orig_tokens,
                compressed_tokens=orig_tokens,
                ratio=1.0,
                cached_keys=[],
                summary="Message count within protected bounds; no compaction needed",
                protected_count=total_msgs,
            )

        # Extract segments
        first_segment = messages[:protect_first_n]
        middle_segment = messages[protect_first_n:total_msgs - protect_last_n]
        last_segment = messages[total_msgs - protect_last_n:]

        cached_keys: List[str] = []
        compacted_middle: List[Dict[str, Any]] = []

        # Summarize / CCR compress middle segment
        combined_middle_text = "\n".join(
            f"[{m.get('role', 'user')}]: {m.get('content', '')}" for m in middle_segment
        )
        middle_tokens = self.estimate_tokens(combined_middle_text)
        key = hashlib.sha256(combined_middle_text.encode("utf-8")).hexdigest()[:16]
        self._store_cache(key, combined_middle_text)
        cached_keys.append(key)

        preview = middle_segment[0].get("content", "")[:60].replace("\n", " ").strip()
        summary_text = (
            f"[CCR:{key}]: {len(middle_segment)} intermediate turns compressed via Headroom CCR ({middle_tokens} tokens). "
            f"Excerpt: '{preview}...'. Use headroom_retrieve('{key}') to restore original."
        )

        compacted_entry = {
            "role": "system",
            "content": summary_text,
            "metadata": {
                "compaction": True,
                "cache_key": key,
                "compressed_turns": len(middle_segment),
                "original_tokens": middle_tokens,
            },
        }
        compacted_middle.append(compacted_entry)

        final_messages = first_segment + compacted_middle + last_segment
        final_tokens = self.estimate_tokens(final_messages)
        ratio = (final_tokens / orig_tokens) if orig_tokens > 0 else 1.0

        return CompactionResult(
            compressed_messages=final_messages,
            original_tokens=orig_tokens,
            compressed_tokens=final_tokens,
            ratio=ratio,
            cached_keys=cached_keys,
            summary=f"Compacted {len(middle_segment)} intermediate messages using Headroom CCR",
            protected_count=len(first_segment) + len(last_segment),
        )
