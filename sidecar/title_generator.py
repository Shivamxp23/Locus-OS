"""Title Generation Engine (§1.11).

Auto-generates concise 3-7 word session titles from early conversational exchanges,
featuring artifact cleanup and heuristic fallbacks.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional


TITLE_PROMPT: str = (
    "Generate a short, descriptive title (3-7 words) for a conversation "
    "that starts with the following exchange. Return ONLY the title text, "
    "nothing else. No quotes, no punctuation at the end, no prefixes."
)


def clean_title(raw_title: str) -> str:
    """Strip quotes, leading 'Title:', and trailing punctuation."""
    t = raw_title.strip()
    # Strip quotes
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()
    # Strip leading prefixes
    if t.lower().startswith("title:"):
        t = t[6:].strip()
    # Strip trailing punctuation
    t = t.rstrip(".!?;:")
    # Clamp length
    if len(t) > 80:
        t = t[:77] + "..."
    return t


def fallback_title(user_message: str) -> str:
    """Generate deterministic heuristic fallback title (first 4-6 words)."""
    words = re.findall(r"\w+", user_message)
    if not words:
        return "New Session"
    selected = words[:min(6, len(words))]
    return " ".join(selected).capitalize()


class TitleGenerator:
    """Generates session titles asynchronously or synchronously using LLM / fallbacks."""

    def __init__(self, llm_caller: Optional[Callable[[List[Dict[str, str]]], str]] = None) -> None:
        self.llm_caller = llm_caller

    def generate_title(
        self,
        user_message: str,
        assistant_response: str = "",
        timeout: float = 10.0,
    ) -> str:
        if not self.llm_caller:
            return fallback_title(user_message)

        u_snip = user_message[:500]
        a_snip = assistant_response[:500]
        messages = [
            {"role": "system", "content": TITLE_PROMPT},
            {"role": "user", "content": f"User: {u_snip}\n\nAssistant: {a_snip}"},
        ]

        try:
            raw = self.llm_caller(messages)
            cleaned = clean_title(raw)
            return cleaned if cleaned else fallback_title(user_message)
        except Exception:
            return fallback_title(user_message)
