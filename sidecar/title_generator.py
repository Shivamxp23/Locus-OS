"""
SPEC §1.11 / F-0011 / US-30: Title Generation Implementation.
Auto-generates 3-7 word session titles from first user/assistant exchange,
runs asynchronously post-response to avoid latency, and cleans artifacts.
"""
from __future__ import annotations

from datetime import datetime
import logging
import re
import threading
import time
from typing import Any, Callable, Dict, Optional

from sidecar import config
from sidecar.providers.title_generator import (
    BaseTitleGeneratorProvider,
    TitleGenerationRequest,
    TitleGenerationResult,
)
from sidecar.registry import get_registry

logger = logging.getLogger(__name__)

# SPEC §1.11 line 2386: PROMPT
TITLE_SYSTEM_PROMPT = (
    "Generate a short, descriptive title (3-7 words) for a conversation "
    "that starts with the following exchange. Return ONLY the title text, "
    "nothing else. No quotes, no punctuation at the end, no prefixes."
)


def clean_title(raw_title: Optional[str]) -> str:
    """
    SPEC §1.11 line 2415:
    // Clean up artifacts
    title = strip_quotes(title)
    IF title starts with "Title:": title = title[6:].strip()
    IF len(title) > 80: title = title[:77] + "..."
    """
    if not raw_title:
        return ""

    title = str(raw_title).strip()

    # Remove outer quotes and common quoting marks
    quote_chars = "\"\'`«»“”„”"
    title = title.strip(quote_chars).strip()

    # Strip prefixes like "Title:" or "title:"
    if title.lower().startswith("title:"):
        title = title[6:].strip()

    # Strip surrounding quotes again if they were inside the prefix
    title = title.strip(quote_chars).strip()

    # Strip trailing punctuation (., !, ?, :, ;)
    title = re.sub(r"[\.\!\?\:\;\,]+$", "", title).strip()

    # Clean multi-spaces and newlines
    title = re.sub(r"\s+", " ", title)

    # Clamp to max 80 characters
    if len(title) > 80:
        title = title[:77] + "..."

    return title


def format_title_prompt(
    user_snippet: str, assistant_snippet: str, timeout: float = 30.0
) -> Dict[str, Any]:
    """
    SPEC §1.11 line 2392:
    // Truncate to keep request small
    user_snippet = user_message[:500]
    assistant_snippet = assistant_response[:500]
    """
    u = (user_snippet or "")[:500]
    a = (assistant_snippet or "")[:500]

    return {
        "task": "title_generation",
        "messages": [
            {"role": "system", "content": TITLE_SYSTEM_PROMPT},
            {"role": "user", "content": f"User: {u}\n\nAssistant: {a}"},
        ],
        "max_tokens": 500,
        "temperature": 0.3,
        "timeout": timeout,
    }


def generate_fallback_title(
    user_message: str = "", timestamp: Optional[datetime] = None
) -> str:
    """
    SPEC §1.11 line 2426:
    // If fails: log warning, session keeps timestamp-based title ("Session 2026-08-19 14:30")
    """
    ts = timestamp or datetime.now()
    ts_str = ts.strftime("%Y-%m-%d %H:%M")

    # If user message is available and short, derive 3-5 words
    cleaned_user = clean_title(user_message)
    if cleaned_user:
        words = cleaned_user.split()
        if len(words) <= 7 and len(cleaned_user) <= 50:
            return cleaned_user
        if len(words) > 7:
            return " ".join(words[:6]) + "..."

    return f"Session {ts_str}"


class TitleGeneratorProvider(BaseTitleGeneratorProvider):
    """
    Concrete implementation of BaseTitleGeneratorProvider.
    Generates titles synchronously or in background threads.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def is_enabled(self) -> bool:
        """
        Check modular off-switch.
        SPEC §1.11 line 2431: locus.sessions.auto_title.enabled
        """
        if config.get("locus.title_generation.enabled") is False:
            return False
        if config.get("locus.sessions.auto_title.enabled") is False:
            return False
        return True

    def clean_title(self, raw_title: str) -> str:
        return clean_title(raw_title)

    def format_prompt(
        self, user_snippet: str, assistant_snippet: str, timeout: float = 30.0
    ) -> Dict[str, Any]:
        return format_title_prompt(user_snippet, assistant_snippet, timeout=timeout)

    def generate_title(
        self,
        user_message: str,
        assistant_response: str,
        timeout: float = 30.0,
        llm_caller: Optional[Callable[[Dict[str, Any]], str]] = None,
    ) -> Optional[str]:
        """
        SPEC §1.11 line 2390:
        FUNCTION generate_title(user_message, assistant_response, timeout=30s):
        """
        if not self.is_enabled():
            return None

        # If both messages are empty, return fallback title
        if not (user_message or "").strip() and not (assistant_response or "").strip():
            return generate_fallback_title()

        payload = self.format_prompt(user_message, assistant_response, timeout=timeout)

        start_time = time.time()
        raw_output: str = ""

        try:
            if llm_caller:
                raw_output = llm_caller(payload)
            else:
                # Built-in lightweight heuristic fallback when no remote LLM caller is injected
                raw_output = self._heuristic_title(user_message, assistant_response)

            cleaned = self.clean_title(raw_output)
            if cleaned:
                return cleaned
            return generate_fallback_title(user_message)
        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            return generate_fallback_title(user_message)

    def _heuristic_title(self, user_message: str, assistant_response: str) -> str:
        """Derive meaningful 3-7 word title from conversation start if caller absent."""
        first_line = (user_message or "").strip().splitlines()[0] if user_message else ""
        cleaned = re.sub(r"^[#/\\>\*\-\d\.\s]+", "", first_line).strip()
        words = cleaned.split()
        if 3 <= len(words) <= 7:
            return " ".join(words)
        elif len(words) > 7:
            return " ".join(words[:5])
        elif words:
            return f"Discussion on {words[0]}"
        return "New Conversation Session"

    def generate_title_async(
        self,
        user_message: str,
        assistant_response: str,
        callback: Callable[[str], None],
        timeout: float = 30.0,
        failure_callback: Optional[Callable[[Exception], None]] = None,
        llm_caller: Optional[Callable[[Dict[str, Any]], str]] = None,
    ) -> threading.Thread:
        """
        SPEC §1.11 line 2422:
        FUNCTION generate_title_async(user_msg, assistant_msg, callback):
            spawn_thread:
                title = generate_title(user_msg, assistant_msg)
                IF title: callback(title)
                // If fails: log warning, session keeps timestamp-based title
                // Wire failure_callback to emit_auxiliary_failure for visibility
        """
        def _worker() -> None:
            try:
                title = self.generate_title(
                    user_message=user_message,
                    assistant_response=assistant_response,
                    timeout=timeout,
                    llm_caller=llm_caller,
                )
                if title:
                    callback(title)
            except Exception as e:
                logger.warning(f"Background title generation error: {e}")
                if failure_callback:
                    try:
                        failure_callback(e)
                    except Exception:
                        pass

        thread = threading.Thread(target=_worker, name="locus-title-gen-worker", daemon=True)
        thread.start()
        return thread


# Register default provider in global registry
get_registry().register("title_generator", "default", TitleGeneratorProvider)
get_registry().register("title_gen", "default", TitleGeneratorProvider)
