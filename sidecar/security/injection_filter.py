"""Prompt injection filtering module for Locus OS sidecar."""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple


class PromptInjectionFilter:
    LEET_MAP = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "@": "a"}
    CYRILLIC_MAP = {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x"}
    ZWSP_CHARS = {"\u200B", "\u200C", "\u200D", "\u2060", "\uFEFF", "\u00AD", "\u034F"}
    ZWSP_DIRECTIONAL_RANGE = range(0x202A, 0x202F)

    OBFUSCATED_BONUS = 0.56
    SUSPICIOUS_COMBO_BONUS = 0.20

    RULES = [
        (
            "override.ignore_previous",
            0.44,
            re.compile(
                r"(ignore|disregard|bypass|forget|override)\s+(all\s+)?(previous|prior|above|earlier|initial)\s+(instructions|rules|prompts|guidelines|directives)",
                re.IGNORECASE,
            ),
        ),
        (
            "override.role_hijack",
            0.30,
            re.compile(
                r"(you\s+are\s+now|act\s+as\s+(if\s+)?(you|a)|developer\s+mode|DAN\s+mode|jailbreak|ignore\s+safety)",
                re.IGNORECASE,
            ),
        ),
        (
            "exfiltrate.system_prompt",
            0.42,
            re.compile(
                r"(reveal|dump|show|print|output|repeat|display|leak)\s+(your\s+)?(system\s+prompt|system\s+message|instructions|internal\s+rules|hidden\s+prompt)",
                re.IGNORECASE,
            ),
        ),
        (
            "exfiltrate.secrets",
            0.18,
            re.compile(
                r"\b(api[_\s]?key|password|secret[_\s]?key|access[_\s]?token|private[_\s]?key)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "exfiltrate.credentials_with_intent",
            0.46,
            re.compile(
                r"\b(?!(?:show|give|tell|fetch|set|update|configure|create)\b)[a-z]+\s+(?:the\s+|my\s+|your\s+)?(?:api[_\s]?key|password|secret|token|credentials)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "tool.abuse",
            0.30,
            re.compile(
                r"(call|run|execute|invoke)\s+(the\s+)?tool\s+(without|no|bypassing)\s+(approval|permission|confirmation)",
                re.IGNORECASE,
            ),
        ),
    ]

    def normalize(self, text: str) -> Tuple[str, str, bool]:
        has_zwsp = False
        collapsed_chars = []
        compact_chars = []

        for char in text:
            if char in self.ZWSP_CHARS or ord(char) in self.ZWSP_DIRECTIONAL_RANGE:
                has_zwsp = True
                continue

            norm_char = char.lower()
            if norm_char in self.LEET_MAP:
                norm_char = self.LEET_MAP[norm_char]
            elif norm_char in self.CYRILLIC_MAP:
                norm_char = self.CYRILLIC_MAP[norm_char]

            collapsed_chars.append(norm_char)
            if not norm_char.isspace():
                compact_chars.append(norm_char)

        return "".join(collapsed_chars), "".join(compact_chars), has_zwsp

    def _detect_spaced_override(self, compact_text: str) -> bool:
        overrides = ["ignoreprevious", "ignoreallprevious", "disregardprevious"]
        for ovr in overrides:
            if ovr in compact_text:
                return True
        return False

    def _has_base64(self, text: str) -> bool:
        b64_pattern = re.compile(
            r"(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?"
        )
        return bool(b64_pattern.search(text))

    def score(self, text: str) -> Tuple[float, List[str], str]:
        total_score = 0.0
        matched_rules = []

        collapsed, compact, has_zwsp = self.normalize(text)

        for name, weight, pattern in self.RULES:
            if pattern.search(collapsed):
                total_score += weight
                matched_rules.append(name)

        spaced_detected = self._detect_spaced_override(compact)
        if spaced_detected and "override.ignore_previous" not in matched_rules:
            total_score += self.OBFUSCATED_BONUS
            matched_rules.append("obfuscated.spaced_override")

        has_b64 = self._has_base64(text)
        if has_zwsp and has_b64 and total_score > 0:
            total_score += self.SUSPICIOUS_COMBO_BONUS
            matched_rules.append("suspicious.combo")

        if total_score >= 0.70:
            verdict = "BLOCK"
        elif total_score >= 0.55:
            verdict = "REVIEW"
        else:
            verdict = "ALLOW"

        return total_score, matched_rules, verdict

    def audit_log(
        self, text: str, score: float, verdict: str, reasons: List[str]
    ) -> Dict[str, Any]:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": text_hash,
            "score": score,
            "verdict": verdict,
            "reasons": reasons,
        }
