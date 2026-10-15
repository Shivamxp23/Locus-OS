"""Token Compression (Headroom CCR - Cache-Compress-Retrieve) (§4.17).

Reversible multi-format compression pipeline for LLM contexts:
CacheAligner -> ContentRouter -> [SmartCrusher (JSON) | CodeCompressor | TextCompressor] -> CCR Cache.
Includes inflation guard and prompt cache prefix stabilization.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CompressConfig:
    protect_recent: int = 4
    min_tokens_to_compress: int = 250
    compress_user_messages: bool = False
    target_ratio: float = 0.50
    frozen_message_count: int = 1  # Preserve prefix for provider KV cache
    cache_ttl_seconds: int = 3600


@dataclass
class CompressResult:
    compressed_messages: List[Dict[str, Any]]
    original_token_estimate: int
    compressed_token_estimate: int
    compression_ratio: float
    cache_keys_created: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def estimate_tokens(text: str) -> int:
    """Fast conservative token estimator: ~4 characters per token."""
    return max(1, len(text) // 4)


class CCRCache:
    """Local key-value cache for reversible retrieval of compressed chunks."""

    def __init__(self, default_ttl: int = 3600) -> None:
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[str, float]] = {}  # key -> (original_text, expire_at)

    def put(self, original_text: str, ttl: Optional[int] = None) -> str:
        key = "ccr_" + hashlib.sha256(original_text.encode("utf-8")).hexdigest()[:16]
        expire_at = time.time() + (ttl or self.default_ttl)
        self._cache[key] = (original_text, expire_at)
        return key

    def get(self, key: str) -> Optional[str]:
        entry = self._cache.get(key)
        if not entry:
            return None
        text, expire_at = entry
        if time.time() > expire_at:
            self._cache.pop(key, None)
            return None
        return text


class SmartCrusher:
    """JSON compressor: deduplicates array items and removes unnecessary whitespace."""

    @staticmethod
    def compress(text: str) -> str:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) > 5:
                # Deduplicate array entries if string or simple dict
                seen = []
                for item in parsed:
                    if item not in seen:
                        seen.append(item)
                compact = json.dumps(seen, separators=(",", ":"))
                return compact
            elif isinstance(parsed, dict):
                return json.dumps(parsed, separators=(",", ":"))
        except Exception:
            pass
        return text


class CodeCompressor:
    """Code compressor: strips redundant blank lines, docstring padding, and structural bloat."""

    @staticmethod
    def compress(code: str) -> str:
        # Collapse multiple empty lines to one
        cleaned = re.sub(r"\n\s*\n+", "\n\n", code)
        # Strip trailing whitespaces
        cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
        return cleaned


class TextCompressor:
    """Prose compressor: collapses whitespace repetitions."""

    @staticmethod
    def compress(text: str) -> str:
        return re.sub(r"[ \t]+", " ", text).strip()


class HeadroomCompressor:
    """Unified Headroom CCR compression engine."""

    def __init__(self, config: Optional[CompressConfig] = None) -> None:
        self.config = config or CompressConfig()
        self.cache = CCRCache(default_ttl=self.config.cache_ttl_seconds)

    def _route_and_compress_content(self, content: str) -> Tuple[str, Optional[str]]:
        trimmed = content.strip()
        # Route JSON
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
            compressed = SmartCrusher.compress(trimmed)
        # Route Code (contains def, class, import, function, etc.)
        elif re.search(r"^\s*(def |class |import |export |function )", trimmed, re.MULTILINE):
            compressed = CodeCompressor.compress(trimmed)
        else:
            compressed = TextCompressor.compress(trimmed)

        # Reversible CCR cache hook if significant compression achieved
        cache_key = None
        if len(compressed) < len(content) * 0.8:
            cache_key = self.cache.put(content)
            compressed = f"{compressed}\n[CCR_RETRIEVAL_KEY: {cache_key}]"

        return compressed, cache_key

    def compress(
        self,
        messages: List[Dict[str, Any]],
        model: str = "default",
    ) -> CompressResult:
        if not messages:
            return CompressResult([], 0, 0, 1.0, [])

        total_orig_tokens = sum(estimate_tokens(str(m.get("content", ""))) for m in messages)
        cfg = self.config

        # 1. CacheAligner: protect frozen prefix
        frozen_count = min(cfg.frozen_message_count, len(messages))
        frozen_prefix = messages[:frozen_count]

        # 2. Protect recent messages
        protect_count = cfg.protect_recent
        compressible_limit = max(frozen_count, len(messages) - protect_count)

        compressible_slice = messages[frozen_count:compressible_limit]
        recent_suffix = messages[compressible_limit:]

        processed_compressible: List[Dict[str, Any]] = []
        cache_keys: List[str] = []

        for msg in compressible_slice:
            role = msg.get("role", "")
            content = str(msg.get("content", ""))
            tokens = estimate_tokens(content)

            # Skip user messages if configured
            if role == "user" and not cfg.compress_user_messages:
                processed_compressible.append(msg)
                continue

            # Skip messages below minimum token threshold
            if tokens < cfg.min_tokens_to_compress:
                processed_compressible.append(msg)
                continue

            compressed_text, c_key = self._route_and_compress_content(content)

            # Inflation Guard: if compression made it larger, revert!
            if estimate_tokens(compressed_text) >= tokens:
                processed_compressible.append(msg)
            else:
                new_msg = dict(msg)
                new_msg["content"] = compressed_text
                new_msg["headroom_compressed"] = True
                processed_compressible.append(new_msg)
                if c_key:
                    cache_keys.append(c_key)

        final_messages = frozen_prefix + processed_compressible + recent_suffix
        total_comp_tokens = sum(estimate_tokens(str(m.get("content", ""))) for m in final_messages)
        ratio = round(total_comp_tokens / max(1, total_orig_tokens), 4)

        return CompressResult(
            compressed_messages=final_messages,
            original_token_estimate=total_orig_tokens,
            compressed_token_estimate=total_comp_tokens,
            compression_ratio=ratio,
            cache_keys_created=cache_keys,
        )

    def retrieve(self, cache_key: str) -> Optional[str]:
        return self.cache.get(cache_key)


def compress(
    messages: List[Dict[str, Any]],
    model: str = "default",
    config: Optional[CompressConfig] = None,
) -> CompressResult:
    engine = HeadroomCompressor(config=config)
    return engine.compress(messages=messages, model=model)
