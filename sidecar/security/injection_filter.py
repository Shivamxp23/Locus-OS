"""
SPEC §13.1 lines 3006-3140:
Prompt Injection Protection (Injection Filter) (F-0037 / US-68).

Pure synchronous analysis library:
- Single-pass Unicode normalization (leet-speak, Cyrillic confusables, ZWSP stripping)
- Scored DFA rule detection across normalized variants
- Inline heuristics for obfuscated instruction overrides and exfiltration
- Strict PII-safe audit logging (SHA-256 hashed prompts, never raw content)
- Tool definition scanning
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Zero-width, formatting, and obfuscation codepoints (SPEC §13.1 Step 1d)
OBFUSCATION_CODEPOINTS = {
    0x200B,  # ZWSP
    0x200C,  # ZWNJ
    0x200D,  # ZWJ
    0x2060,  # Word joiner
    0xFEFF,  # BOM / ZWNBSP
    0x00AD,  # Soft hyphen
    0x034F,  # Combining grapheme joiner
    0x180E,  # Mongolian vowel separator
    0x200E,  # LTR mark
    0x200F,  # RTL mark
    0x202A,  # LRE
    0x202B,  # RLE
    0x202C,  # PDF
    0x202D,  # LRO
    0x202E,  # RLO
    0x2066,  # LRI
    0x2067,  # RLI
    0x2068,  # FSI
    0x2069,  # PDI
}

# Leet-speak folding table (SPEC §13.1 Step 1b)
LEET_MAP = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "6": "g",
    "7": "t",
    "8": "b",
    "@": "a",
}

# Cyrillic homoglyph folding table (UAX#39 confusables, SPEC §13.1 Step 1c)
CYRILLIC_HOMOGLYPH_MAP = {
    "\u0430": "a",  # Cyrillic small letter a
    "\u0410": "a",  # Cyrillic capital letter A
    "\u0435": "e",  # Cyrillic small letter ie
    "\u0415": "e",  # Cyrillic capital letter IE
    "\u043e": "o",  # Cyrillic small letter o
    "\u041e": "o",  # Cyrillic capital letter O
    "\u0440": "p",  # Cyrillic small letter er
    "\u0420": "p",  # Cyrillic capital letter ER
    "\u0441": "c",  # Cyrillic small letter es
    "\u0421": "c",  # Cyrillic capital letter ES
    "\u0443": "y",  # Cyrillic small letter u
    "\u0423": "y",  # Cyrillic capital letter U
    "\u0445": "x",  # Cyrillic small letter ha
    "\u0425": "x",  # Cyrillic capital letter HA
    "\u0456": "i",  # Cyrillic small letter byelorussian-ukrainian i
    "\u0406": "i",  # Cyrillic capital letter BYELORUSSIAN-UKRAINIAN I
    "\u0455": "s",  # Cyrillic small letter dze
    "\u0405": "s",  # Cyrillic capital letter DZE
    "\u04bb": "h",  # Cyrillic small letter shha
    "\u04ba": "h",  # Cyrillic capital letter SHHA
    "\u0501": "d",  # Cyrillic small letter komi de
    "\u0500": "d",  # Cyrillic capital letter KOMI DE
}

BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
INSTRUCTION_OVERRIDE_PATTERN = re.compile(
    r"\b(ignore|disregard|forget|bypass)\b.*?\b(previous|prior|system|above|all)\b.*?\b(instructions|rules|prompts|directives)\b",
    re.IGNORECASE | re.DOTALL,
)
EXFILTRATION_INTENT_PATTERN = re.compile(
    r"\b(system\s+prompt|developer\s+instructions|initial\s+prompt|reveal\s+instructions)\b",
    re.IGNORECASE,
)


@dataclass
class NormalizedPrompt:
    """SPEC §13.1: Output of normalize_prompt."""
    lowered: str
    collapsed: str
    compact: str
    had_zwsp: bool
    has_base64_marker: bool
    has_instruction_override: bool
    has_exfiltration_intent: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_prompt(text: str) -> NormalizedPrompt:
    """
    SPEC §13.1 Step 1: Normalization in a single character pass.
    a) Lowercasing
    b) Leet-speak folding
    c) Cyrillic homoglyph folding
    d) Zero-width / obfuscation character stripping + flag
    e) Fullwidth ASCII folding (U+FF01..U+FF5E -> U+0021..U+007E)
    f) Whitespace collapse and whitespace strip
    """
    if not text:
        return NormalizedPrompt(
            lowered="",
            collapsed="",
            compact="",
            had_zwsp=False,
            has_base64_marker=False,
            has_instruction_override=False,
            has_exfiltration_intent=False,
        )

    had_zwsp = False
    cleaned_chars: List[str] = []

    for ch in text:
        cp = ord(ch)
        if cp in OBFUSCATION_CODEPOINTS:
            had_zwsp = True
            continue

        # Fullwidth ASCII folding: U+FF01..U+FF5E -> U+0021..U+007E
        if 0xFF01 <= cp <= 0xFF5E:
            ch = chr(cp - 0xFEE0)

        # Cyrillic homoglyphs
        if ch in CYRILLIC_HOMOGLYPH_MAP:
            ch = CYRILLIC_HOMOGLYPH_MAP[ch]

        # Lowercase
        ch = ch.lower()

        # Leet-speak
        if ch in LEET_MAP:
            ch = LEET_MAP[ch]

        cleaned_chars.append(ch)

    collapsed_str = re.sub(r"\s+", " ", "".join(cleaned_chars)).strip()
    compact_str = re.sub(r"\s+", "", collapsed_str)
    lowered_str = text.lower()

    # Base64 marker check
    has_base64 = bool(BASE64_PATTERN.search(text))

    # Instruction override check (tested on collapsed and compact)
    has_override = bool(
        INSTRUCTION_OVERRIDE_PATTERN.search(collapsed_str)
        or "ignorepreviousinstructions" in compact_str
        or "disregardpreviousinstructions" in compact_str
        or "forgetpreviousinstructions" in compact_str
        or "bypasspreviousinstructions" in compact_str
    )

    # Exfiltration intent check
    has_exfil = bool(
        EXFILTRATION_INTENT_PATTERN.search(collapsed_str)
        or "systemprompt" in compact_str
        or "developerinstructions" in compact_str
    )

    return NormalizedPrompt(
        lowered=lowered_str,
        collapsed=collapsed_str,
        compact=compact_str,
        had_zwsp=had_zwsp,
        has_base64_marker=has_base64,
        has_instruction_override=has_override,
        has_exfiltration_intent=has_exfil,
    )


# SPEC §13.1 Step 2: Detection Rules (code -> score -> pattern)
DETECTION_RULES: List[Tuple[str, float, re.Pattern[str]]] = [
    (
        "override.ignore_previous",
        0.44,
        re.compile(
            r"\b(ignore|disregard|forget|bypass)\s+(all\s+)?(previous|prior|system|above)\s+(instructions|rules|prompts|directives)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "override.role_hijack",
        0.30,
        re.compile(
            r"\b(you\s+are\s+now|developer\s+mode|jailbreak|DAN\s+mode|act\s+as\s+(an?\s+)?unrestricted)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "exfiltrate.system_prompt",
        0.42,
        re.compile(
            r"\b(reveal|show|dump|print|display|leak)\s+(the\s+)?(system\s+prompt|system\s+instructions|initial\s+prompt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "exfiltrate.secrets",
        0.18,
        re.compile(
            r"\b(api[_\s-]?key|secret|token|password|credential)s?\b",
            re.IGNORECASE,
        ),
    ),
    (
        # Bounded window (<=2 filler words) with extraction verbs, excluding show, give, tell, fetch (issue #1940)
        "exfiltrate.credentials_with_intent",
        0.46,
        re.compile(
            r"\b(extract|leak|steal|exfiltrate|dump|export|send|transmit)\b(?:\s+\w+){0,2}\s+\b(api[_\s-]?key|secret|token|password|credentials?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tool.abuse",
        0.30,
        re.compile(
            r"\b(call|use|run|execute)\s+(a\s+)?tool\s+(without|bypass(ing)?)\s+(approval|confirmation|permission|even\s+if\s+forbidden)\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass
class PromptEnforcementDecision:
    """SPEC §13.1 Step 6: Audit (PII-safe)."""
    verdict: str  # "Allow" | "Review" | "Block"
    action: str   # "Allow" | "ReviewBlocked" | "Blocked"
    score: float
    reasons: List[str]
    prompt_hash: str
    prompt_chars: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def enforce_prompt_input(
    input_text: str,
    context: Optional[Dict[str, Any]] = None,
    use_heuristic_classifier: bool = True,
) -> PromptEnforcementDecision:
    """
    SPEC §13.1: Synchronous analysis pipeline.
    Returns PromptEnforcementDecision with fixed thresholds (0.55 Review, 0.70 Block).
    NEVER logs or exposes raw prompt text in audit record.
    """
    prompt_hash = hashlib.sha256((input_text or "").encode("utf-8")).hexdigest()
    prompt_chars = len(input_text or "")

    if not input_text or not input_text.strip():
        return PromptEnforcementDecision(
            verdict="Allow",
            action="Allow",
            score=0.0,
            reasons=[],
            prompt_hash=prompt_hash,
            prompt_chars=prompt_chars,
        )

    # Step 1: Normalization
    norm = normalize_prompt(input_text)

    score = 0.0
    reasons: List[str] = []

    # Step 2: Detection Rules across lowered, collapsed, and compact
    matched_codes: set[str] = set()
    for code, rule_score, pattern in DETECTION_RULES:
        if (
            pattern.search(norm.lowered)
            or pattern.search(norm.collapsed)
            or pattern.search(norm.compact)
        ):
            if code not in matched_codes:
                matched_codes.add(code)
                score += rule_score
                reasons.append(code)

    # Step 3: Inline Heuristics (pre-DFA)
    if norm.has_instruction_override and "override.ignore_previous" not in matched_codes:
        score += 0.56
        reasons.append("override.obfuscated_instruction")

    if norm.has_exfiltration_intent and "exfiltrate.system_prompt" not in matched_codes:
        score += 0.24
        reasons.append("exfiltration.intent")

    # Step 4: Optional Heuristic Classifier
    if use_heuristic_classifier:
        h_score = 0.0
        if norm.had_zwsp:
            h_score += 0.08
        if norm.has_base64_marker:
            h_score += 0.08
        if norm.has_instruction_override and norm.has_exfiltration_intent:
            h_score += 0.20
        if h_score > 0.0:
            score += min(h_score, 0.25)
            reasons.append("classifier.suspicious_combo")

    total_score = min(score, 1.0)

    # Step 5: Verdict (fixed thresholds: >= 0.70 Block, >= 0.55 Review)
    if total_score >= 0.70:
        verdict = "Block"
        action = "Blocked"
    elif total_score >= 0.55:
        verdict = "Review"
        action = "ReviewBlocked"
    else:
        verdict = "Allow"
        action = "Allow"

    logger.info(
        "Prompt enforcement: verdict=%s, score=%.2f, reasons=%s, hash=%s",
        verdict,
        total_score,
        reasons,
        prompt_hash,
    )

    return PromptEnforcementDecision(
        verdict=verdict,
        action=action,
        score=round(total_score, 4),
        reasons=reasons,
        prompt_hash=prompt_hash,
        prompt_chars=prompt_chars,
    )


def scan_tool_definition(name: str, description: str) -> PromptEnforcementDecision:
    """
    SPEC §13.1 BONUS: TOOL DEFINITION SCANNING.
    Rejects on any non-Allow verdict (no Review-vs-Block UX for tool metadata).
    """
    combined = f"{name} {description}".strip()
    decision = enforce_prompt_input(combined)
    if decision.verdict != "Allow":
        # Reject outright for tool metadata
        return PromptEnforcementDecision(
            verdict="Block",
            action="Blocked",
            score=decision.score,
            reasons=decision.reasons + ["tool_definition_rejected"],
            prompt_hash=decision.prompt_hash,
            prompt_chars=decision.prompt_chars,
        )
    return decision
