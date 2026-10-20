"""
Headroom CCR Pipeline (SPEC §4.17: Token Compression (Headroom CCR)).
Implements:
  CacheAligner → ContentRouter → [SmartCrusher (JSON) | CodeCompressor (code) | Kompress (prose)] → CCR
With:
  - protect_recent=4, min_tokens_to_compress=250, compress_user_messages=False
  - Reversible CCR cache with cryptographic keys and TTL
  - Inflation guard (reverts to original if compressed token count exceeds original)
  - KV-cache frozen prefix alignment
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sidecar.config as config

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    PROSE = "PROSE"
    JSON = "JSON"
    CODE = "CODE"


@dataclass
class CompressConfig:
    """SPEC §4.17 line 680, 690: CompressConfig knobs."""
    protect_recent: int = 4
    min_tokens_to_compress: int = 250
    compress_user_messages: bool = False
    target_ratio: Optional[float] = None
    frozen_message_count: int = 0
    enabled: bool = True
    ttl_seconds: float = 86400.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CompressConfig:
        return cls(
            protect_recent=int(data.get("protect_recent", 4)),
            min_tokens_to_compress=int(data.get("min_tokens_to_compress", 250)),
            compress_user_messages=bool(data.get("compress_user_messages", False)),
            target_ratio=float(data["target_ratio"]) if data.get("target_ratio") is not None else None,
            frozen_message_count=int(data.get("frozen_message_count", 0)),
            enabled=bool(data.get("enabled", True)),
            ttl_seconds=float(data.get("ttl_seconds", 86400.0)),
        )


@dataclass
class CompressResult:
    """SPEC §4.17 line 689, 699: CompressResult return structure."""
    messages: List[Dict[str, Any]]
    tokens_before: int
    tokens_after: int
    tokens_saved: int
    ratio: float
    transforms_applied: List[str] = field(default_factory=list)
    cached_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": self.messages,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "tokens_saved": self.tokens_saved,
            "ratio": round(self.ratio, 4),
            "transforms_applied": self.transforms_applied,
            "cached_keys": self.cached_keys,
        }


class CacheAligner:
    """
    SPEC §4.17 line 664, 684, 693:
    CacheAligner anchors frozen prefix so provider KV cache still hits
    without turning a 0.1x cache read into a full-price rewrite.
    """

    def align(
        self,
        messages: List[Dict[str, Any]],
        frozen_message_count: int = 0,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if frozen_message_count <= 0 or not messages:
            return [], list(messages)
        frozen = messages[:frozen_message_count]
        active = messages[frozen_message_count:]
        return frozen, active


class ContentRouter:
    """
    SPEC §4.17 line 665, 681, 694:
    Detects PROSE | JSON | CODE per message content.
    """

    CODE_PATTERNS = [
        re.compile(r"^\s*(?:def|class|import|from|async\s+def)\s+\w+", re.M),
        re.compile(r"^\s*(?:function|const|let|var|export|interface|type)\s+\w+", re.M),
        re.compile(r"```(?:python|javascript|typescript|json|sh|bash|html|css|sql|rust|go)\b", re.I),
        re.compile(r"[{};]\s*$", re.M),
    ]

    def classify(self, content: str) -> ContentType:
        if not content or not content.strip():
            return ContentType.PROSE

        stripped = content.strip()
        # JSON check: starts and ends with {} or []
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            try:
                json.loads(stripped)
                return ContentType.JSON
            except Exception:
                pass

        # Code block markdown or structural keywords
        if "```" in content:
            return ContentType.CODE

        code_hits = sum(len(pat.findall(content)) for pat in self.CODE_PATTERNS)
        if code_hits >= 2 or any(pat.search(content) for pat in self.CODE_PATTERNS[:2]):
            return ContentType.CODE

        return ContentType.PROSE


class SmartCrusher:
    """
    SPEC §4.17 line 666, 681, 695:
    JSON compressor: array dedup, lossless-first + lossy fallback if still over budget.
    """

    def compress(self, text: str, target_ratio: Optional[float] = None) -> str:
        try:
            parsed = json.loads(text)
        except Exception:
            return text

        # Lossless step 1: dedup arrays of primitives or dictionaries
        cleaned = self._lossless_crush(parsed)
        lossless_str = json.dumps(cleaned, separators=(",", ":"))

        if target_ratio is None or target_ratio >= 1.0:
            return lossless_str

        # If aggressive target ratio is specified, apply lossy compression
        current_len = len(lossless_str)
        target_len = int(len(text) * target_ratio)
        if current_len <= target_len:
            return lossless_str

        lossy = self._lossy_crush(cleaned, max_items=5)
        return json.dumps(lossy, separators=(",", ":"))

    def _lossless_crush(self, val: Any) -> Any:
        if isinstance(val, dict):
            return {k: self._lossless_crush(v) for k, v in val.items()}
        if isinstance(val, list):
            seen: List[Any] = []
            for item in val:
                c = self._lossless_crush(item)
                if c not in seen:
                    seen.append(c)
            return seen
        return val

    def _lossy_crush(self, val: Any, max_items: int = 5) -> Any:
        if isinstance(val, dict):
            # Prune empty or None values
            return {
                k: self._lossy_crush(v, max_items)
                for k, v in val.items()
                if v is not None and v != "" and v != [] and v != {}
            }
        if isinstance(val, list):
            if len(val) > max_items:
                truncated = [self._lossy_crush(x, max_items) for x in val[:max_items]]
                truncated.append(f"...[{len(val) - max_items} items omitted by SmartCrusher]")
                return truncated
            return [self._lossy_crush(x, max_items) for x in val]
        return val


class CodeCompressor:
    """
    SPEC §4.17 line 667, 681, 695:
    Code structural compressor: comment stripping, excessive blank line collapse,
    and trailing whitespace elimination while maintaining syntax structure.
    """

    def compress(self, text: str) -> str:
        lines = text.splitlines()
        compressed_lines: List[str] = []
        prev_blank = False

        for line in lines:
            stripped = line.strip()
            # Strip pure line comments (preserve shebang or doc directives)
            if (stripped.startswith("#") and not stripped.startswith("#!")) or stripped.startswith("//"):
                continue
            if not stripped:
                if not prev_blank:
                    compressed_lines.append("")
                    prev_blank = True
                continue
            prev_blank = False
            # Strip trailing inline whitespace
            compressed_lines.append(line.rstrip())

        out = "\n".join(compressed_lines)
        return out if out.strip() else text


class KompressCompressor:
    """
    SPEC §4.17 line 668, 681, 695:
    Prose and conversational compressor (Kompress-v2 style):
    removes redundant whitespace, eliminates recurring conversational filler phrases.
    """

    FILLER_PATTERNS = [
        re.compile(r"\b(?:as mentioned earlier|as noted above|in order to|as you know)\b", re.I),
        re.compile(r"\b(?:furthermore|moreover|needless to say|it is important to note that)\b", re.I),
    ]

    def compress(self, text: str) -> str:
        # Collapse multiple blank lines
        res = re.sub(r"\n{3,}", "\n\n", text)
        # Collapse multi-spaces
        res = re.sub(r"[ \t]{2,}", " ", res)
        # Remove common filler phrases
        for pat in self.FILLER_PATTERNS:
            res = pat.sub("", res)
        # Clean up double punctuation resulting from removals
        res = re.sub(r"\s+([,.;])", r"\1", res)
        return res.strip()


class CCRStore:
    """
    SPEC §4.17 line 669, 682, 701:
    Cache-Compress-Retrieve store:
    Originals cached locally with cryptographic key; retrievable within TTL.
    """

    def __init__(self, cache_dir: Optional[Path] = None, ttl_seconds: float = 86400.0) -> None:
        self.ttl_seconds = ttl_seconds
        if cache_dir:
            self.cache_dir = Path(cache_dir).resolve()
        else:
            self.cache_dir = config.get_locus_home() / "headroom_cache"
        self._memory_cache: Dict[str, Tuple[str, float]] = {}
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def store(self, content: str, key: Optional[str] = None, ttl: Optional[float] = None) -> str:
        k = key or hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        expires_at = time.time() + (ttl if ttl is not None else self.ttl_seconds)
        self._memory_cache[k] = (content, expires_at)
        try:
            fp = self.cache_dir / f"{k}.txt"
            fp.write_text(content, encoding="utf-8")
        except Exception as exc:
            logger.debug(f"CCRStore failed to write disk cache: {exc}")
        return k

    def retrieve(self, cache_key: str) -> Optional[str]:
        # Memory cache check
        if cache_key in self._memory_cache:
            content, expires = self._memory_cache[cache_key]
            if time.time() < expires:
                return content
            del self._memory_cache[cache_key]

        # Disk cache check
        try:
            fp = self.cache_dir / f"{cache_key}.txt"
            if fp.is_file():
                return fp.read_text(encoding="utf-8")
        except Exception:
            pass
        return None

    def clear(self) -> None:
        self._memory_cache.clear()


class HeadroomPipeline:
    """
    SPEC §4.17 line 674-702:
    Headroom CCR compression pipeline:
    CacheAligner → ContentRouter → [SmartCrusher | CodeCompressor | Kompress] → CCR
    With Inflation Guard and retrieval marker embedding.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        config_override: Optional[CompressConfig] = None,
    ) -> None:
        self.config = config_override or CompressConfig()
        self.aligner = CacheAligner()
        self.router = ContentRouter()
        self.crusher = SmartCrusher()
        self.code_compressor = CodeCompressor()
        self.kompress = KompressCompressor()
        self.ccr = CCRStore(cache_dir=cache_dir, ttl_seconds=self.config.ttl_seconds)

    def estimate_tokens(self, text_or_messages: Any) -> int:
        if text_or_messages is None:
            return 0
        if isinstance(text_or_messages, str):
            text = text_or_messages
            if not text.strip():
                return 0
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

    def compress(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        config: Optional[CompressConfig] = None,
    ) -> CompressResult:
        """
        SPEC §4.17 lines 689-700:
        compress(messages, model, config) -> CompressResult
        """
        cfg = config or self.config
        tokens_before = self.estimate_tokens(messages)

        if not cfg.enabled or not messages:
            return CompressResult(
                messages=list(messages),
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                tokens_saved=0,
                ratio=1.0,
                transforms_applied=[],
                cached_keys=[],
            )

        # 1. CacheAligner: anchor frozen prefix for KV-cache hits (SPEC line 693)
        frozen_prefix, active_messages = self.aligner.align(
            messages, frozen_message_count=cfg.frozen_message_count
        )

        # Protect recent N messages (SPEC line 680: protect_recent=4)
        if len(active_messages) <= cfg.protect_recent:
            return CompressResult(
                messages=list(messages),
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                tokens_saved=0,
                ratio=1.0,
                transforms_applied=["CacheAligner"],
                cached_keys=[],
            )

        compressible_slice = active_messages[:-cfg.protect_recent]
        recent_slice = active_messages[-cfg.protect_recent:]

        transforms_applied: List[str] = ["CacheAligner"]
        cached_keys: List[str] = []
        compressed_slice: List[Dict[str, Any]] = []

        for msg in compressible_slice:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # SPEC line 680: compress_user_messages=False
            if role == "user" and not cfg.compress_user_messages:
                compressed_slice.append(dict(msg))
                continue

            msg_tokens = self.estimate_tokens(content)
            # SPEC line 680: min_tokens_to_compress=250 (short messages untouched)
            if msg_tokens < cfg.min_tokens_to_compress:
                compressed_slice.append(dict(msg))
                continue

            # 2. ContentRouter: detect PROSE | JSON | CODE (SPEC line 694)
            ctype = self.router.classify(content)

            # 3. Route -> SmartCrusher | CodeCompressor | Kompress (SPEC line 695)
            if ctype == ContentType.JSON:
                crushed = self.crusher.compress(content, target_ratio=cfg.target_ratio)
                transform_name = "SmartCrusher"
            elif ctype == ContentType.CODE:
                crushed = self.code_compressor.compress(content)
                transform_name = "CodeCompressor"
            else:
                crushed = self.kompress.compress(content)
                transform_name = "KompressCompressor"

            # 4. CCR: cache originals, swap in compressed + retrieval marker (SPEC line 696)
            key = self.ccr.store(content)
            cached_keys.append(key)
            if transform_name not in transforms_applied:
                transforms_applied.append(transform_name)
            if "CCR" not in transforms_applied:
                transforms_applied.append("CCR")

            marker = f" [CCR:{key}: {msg_tokens}t compressed. Use headroom_retrieve('{key}') to view original.]"
            new_content = crushed + marker

            # Inflation guard per message (SPEC line 697)
            if self.estimate_tokens(new_content) >= msg_tokens:
                compressed_slice.append(dict(msg))
            else:
                new_msg = dict(msg)
                new_msg["content"] = new_content
                new_msg["metadata"] = dict(msg.get("metadata", {}))
                new_msg["metadata"]["headroom_ccr"] = {
                    "cache_key": key,
                    "original_tokens": msg_tokens,
                    "transform": transform_name,
                }
                compressed_slice.append(new_msg)

        assembled = frozen_prefix + compressed_slice + recent_slice
        tokens_after = self.estimate_tokens(assembled)

        # Global inflation guard (SPEC line 697: if result.tokens_after > result.tokens_before: revert)
        if tokens_after > tokens_before:
            return CompressResult(
                messages=list(messages),
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                tokens_saved=0,
                ratio=1.0,
                transforms_applied=["InflationGuardRevert"],
                cached_keys=cached_keys,
            )

        tokens_saved = max(0, tokens_before - tokens_after)
        ratio = (tokens_after / tokens_before) if tokens_before > 0 else 1.0

        return CompressResult(
            messages=assembled,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            tokens_saved=tokens_saved,
            ratio=ratio,
            transforms_applied=transforms_applied,
            cached_keys=cached_keys,
        )

    def headroom_retrieve(self, cache_key: str) -> Optional[str]:
        """SPEC §4.17 line 701: headroom_retrieve(cache_key) -> full original text."""
        return self.ccr.retrieve(cache_key)
