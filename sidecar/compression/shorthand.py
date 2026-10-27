"""
SPEC §27.3 lines 7115-7151: LOCUS_SHORTHAND 4× Text Compressor (F-0122 / US-96).
Source: LOCUS_SYSTEM_v1.md §14
Logic:
    Deterministic 4× regex compression pipeline reducing prompt token consumption.
    Replaces common transition words with dense mathematical/shorthand symbols:
    - because -> ∵
    - therefore -> ∴
    - approximately -> ≈
    - greater than -> >
    - less than -> <
    - and -> &
    - with -> w/
    - without -> w/o
    - which -> wh/
    - between -> b/w
    - regarding -> re:
    - for example -> e.g.
    Strips unambiguous grammatical articles:
    - regex replace r"\\b(the|a|an)\\s+" -> ""
    Encodes behavioral event streams to compact shorthand:
    - task completion -> {✓:task_name,dur:45,q:8}
    - deferral -> {→:task_name,n:3,r:tired}
    - checkin -> {e:7,m:6,s:3,sl:7}
    Decoder dictionary provided for LLM system prompt prepending.
Off state:
    locus.compression.shorthand.enabled: when off, text remains uncompressed.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.compression.shorthand")

SHORTHAND_DICTIONARY: List[Tuple[str, str]] = [
    ("for example", "e.g."),
    ("greater than", ">"),
    ("less than", "<"),
    ("without", "w/o"),
    ("because", "∵"),
    ("therefore", "∴"),
    ("approximately", "≈"),
    ("between", "b/w"),
    ("regarding", "re:"),
    ("which", "wh/"),
    ("with", "w/"),
    ("and", "&"),
]

# Reverse decoder mapping for expansion
SHORTHAND_DECODER_DICT: Dict[str, str] = {
    "∵": "because",
    "∴": "therefore",
    "≈": "approximately",
    ">": "greater than",
    "<": "less than",
    "&": "and",
    "w/": "with",
    "w/o": "without",
    "wh/": "which",
    "b/w": "between",
    "re:": "regarding",
    "e.g.": "for example",
}


@dataclass
class ShorthandCompressionResult:
    original_text: str
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    tokens_saved: int
    compressed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "compressed_text": self.compressed_text,
            "original_tokens": self.original_tokens,
            "compressed_tokens": self.compressed_tokens,
            "compression_ratio": round(self.compression_ratio, 2),
            "tokens_saved": self.tokens_saved,
            "compressed": self.compressed,
        }


class LocusShorthandCompressor:
    """
    SPEC §27.3: Deterministic 4× regex compression pipeline reducing prompt token consumption.
    """

    SWITCH_KEY = "locus.compression.shorthand.enabled"

    def is_shorthand_enabled(self) -> bool:
        """Check subsystem off-switch."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate BPE token count using the standard ~4 chars per subword token rule of thumb.
        """
        words = text.strip().split()
        if not words:
            return 0
        return sum(max(1, (len(w) + 3) // 4) for w in words)

    def compress(self, text: str, strip_articles: bool = True) -> ShorthandCompressionResult:
        """
        Compress text using LOCUS_SHORTHAND dictionary and article stripping.
        """
        orig_tokens = self.estimate_tokens(text)

        if not self.is_shorthand_enabled():
            return ShorthandCompressionResult(
                original_text=text,
                compressed_text=text,
                original_tokens=orig_tokens,
                compressed_tokens=orig_tokens,
                compression_ratio=1.0,
                tokens_saved=0,
                compressed=False,
            )

        compressed = text

        # 1. Substitute dictionary terms with case insensitivity and boundary checking
        for word, sym in SHORTHAND_DICTIONARY:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            compressed = pattern.sub(sym, compressed)

        # 2. Strip unambiguous grammatical articles (the, a, an)
        if strip_articles:
            compressed = re.sub(r"\b(the|a|an)\s+", "", compressed, flags=re.IGNORECASE)

        # 3. Clean up multiple whitespaces
        compressed = re.sub(r"[ \t]+", " ", compressed).strip()

        comp_tokens = self.estimate_tokens(compressed)
        ratio = (orig_tokens / max(1, comp_tokens)) if comp_tokens else 1.0
        saved = max(0, orig_tokens - comp_tokens)

        return ShorthandCompressionResult(
            original_text=text,
            compressed_text=compressed,
            original_tokens=orig_tokens,
            compressed_tokens=comp_tokens,
            compression_ratio=ratio,
            tokens_saved=saved,
            compressed=True,
        )

    def decompress(self, text: str) -> str:
        """
        Expand LOCUS_SHORTHAND compressed symbols back into full words.
        """
        expanded = text
        for sym, word in SHORTHAND_DECODER_DICT.items():
            # For symbol characters like ∵, ∴, ≈, >, <, &, w/, w/o
            if sym in ("w/", "w/o", "wh/", "b/w", "re:", "e.g."):
                pattern = re.compile(rf"(^|\s){re.escape(sym)}(\s|$)", re.IGNORECASE)
                expanded = pattern.sub(rf"\1{word}\2", expanded)
            else:
                pattern = re.compile(rf"\s*{re.escape(sym)}\s*")
                expanded = pattern.sub(f" {word} ", expanded)

        return re.sub(r"[ \t]+", " ", expanded).strip()

    def compress_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """
        SPEC §27.3 / microsystems:
        Encode recent behavioral events into compact shorthand format:
        - task completion: {✓:task_name,dur:45,q:8}
        - deferral: {→:task_name,n:3,r:tired}
        - checkin: {e:7,m:6,s:3,sl:7}
        """
        etype = event_type.lower()
        if etype in ("task_completion", "task_complete", "completion"):
            name = str(data.get("task", data.get("name", "task"))).replace(" ", "_")
            dur = data.get("dur", data.get("duration", 0))
            q = data.get("q", data.get("quality", 5))
            return f"{{✓:{name},dur:{dur},q:{q}}}"

        elif etype in ("deferral", "task_deferral", "deferred"):
            name = str(data.get("task", data.get("name", "task"))).replace(" ", "_")
            n = data.get("n", data.get("defer_count", 1))
            r = str(data.get("r", data.get("reason", "deferred"))).replace(" ", "_")
            return f"{{→:{name},n:{n},r:{r}}}"

        elif etype in ("checkin", "check_in"):
            e = data.get("e", data.get("energy", 5))
            m = data.get("m", data.get("mood", 5))
            s = data.get("s", data.get("stress", 5))
            sl = data.get("sl", data.get("sleep", 7))
            return f"{{e:{e},m:{m},s:{s},sl:{sl}}}"

        else:
            # Generic compact dict
            parts = [f"{k}:{v}" for k, v in data.items()]
            return f"{{{','.join(parts)}}}"

    def get_decoder_dictionary(self) -> Dict[str, str]:
        """Return shorthand decoder dictionary for system prompt prepending."""
        return dict(SHORTHAND_DECODER_DICT)
