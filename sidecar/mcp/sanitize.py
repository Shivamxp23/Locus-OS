"""
SPEC §18.1-18.4 lines 4083-4090, 4297-4311: Tool description sanitization.
Strips control characters, instruction fences, and caps length to protect
against indirect prompt injection and tool poisoning.
"""
from __future__ import annotations

import re

MAX_DESCRIPTION_BYTES = 1024

INSTRUCTION_FENCE_PATTERNS = [
    re.compile(r"```+(?:system|human|assistant|instruction|prompt)[^\n]*\n?", re.IGNORECASE),
    re.compile(r"```+", re.IGNORECASE),
    re.compile(r"###\s*(?:system|instruction|human|assistant):?", re.IGNORECASE),
    re.compile(r"<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>", re.IGNORECASE),
    re.compile(r"\[/?INST\]", re.IGNORECASE),
    re.compile(r"<\/?(?:system|instruction|prompt)>", re.IGNORECASE),
]


def strip_control_chars(text: str) -> str:
    """Strip non-printable ASCII control characters except \n, \t, and \r."""
    return "".join(ch for ch in text if ch in "\n\t\r" or ord(ch) >= 32 and ord(ch) != 127)


def strip_instruction_fences(text: str) -> str:
    """Strip instruction fences that attempt to break LLM role boundaries."""
    sanitized = text
    for pattern in INSTRUCTION_FENCE_PATTERNS:
        sanitized = pattern.sub(" ", sanitized)
    return sanitized


def truncate_to_bytes(text: str, max_bytes: int = MAX_DESCRIPTION_BYTES) -> str:
    """Cap string length at max_bytes on UTF-8 character boundary."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    # Truncate and decode safely ignoring dangling multi-byte fragment
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def sanitize_for_llm(text: str, max_bytes: int = MAX_DESCRIPTION_BYTES) -> str:
    """Sanitize untrusted tool descriptions before exposing to LLM context."""
    if not text:
        return ""
    cleaned = strip_control_chars(text)
    cleaned = strip_instruction_fences(cleaned)
    cleaned = " ".join(cleaned.split())
    return truncate_to_bytes(cleaned, max_bytes=max_bytes)
