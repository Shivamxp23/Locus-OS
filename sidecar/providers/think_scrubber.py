"""
SPEC §13.9 lines 3513-3598:
Think Token Scrubbing Provider (F-0042 / US-74).

Registers as a provider in sidecar/providers/ with modular off-switches:
- locus.think_token_scrubbing.enabled
- locus.security.think_scrubbing.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

import sidecar.config as config
from sidecar.security.think_scrubber import (
    SUPPORTED_TAGS,
    StreamingThinkScrubber,
)

logger = logging.getLogger(__name__)


class BaseThinkScrubberProvider(ABC):
    """Abstract interface for Think Token Scrubbing provider."""

    @abstractmethod
    def feed_chunk(self, delta_text: str) -> str:
        """Feed a delta text chunk through the scrubber."""
        raise NotImplementedError

    @abstractmethod
    def flush(self) -> str:
        """Flush any held-back buffer at end of stream."""
        raise NotImplementedError

    @abstractmethod
    def scrub_text(self, text: str) -> str:
        """Complete batch scrub of a text payload."""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset the scrubber state for a new turn."""
        raise NotImplementedError

    @abstractmethod
    def list_tags(self) -> List[str]:
        """List supported thinking tag markers."""
        raise NotImplementedError


class DefaultThinkScrubberProvider(BaseThinkScrubberProvider):
    """Default implementation of Think Token Scrubber provider."""

    def __init__(self, tags: Optional[List[str]] = None) -> None:
        self._scrubber = StreamingThinkScrubber(tags=tags)

    def is_enabled(self) -> bool:
        """Modular off-switches for think token scrubbing."""
        v1 = config.get("locus.think_token_scrubbing.enabled")
        if v1 is not None and not config.is_enabled("locus.think_token_scrubbing.enabled"):
            return False
        v2 = config.get("locus.security.think_scrubbing.enabled")
        if v2 is not None and not config.is_enabled("locus.security.think_scrubbing.enabled"):
            return False
        return True

    def feed_chunk(self, delta_text: str) -> str:
        if not self.is_enabled():
            return delta_text
        return self._scrubber.feed(delta_text)

    def flush(self) -> str:
        if not self.is_enabled():
            return ""
        return self._scrubber.flush()

    def scrub_text(self, text: str) -> str:
        if not self.is_enabled():
            return text
        return self._scrubber.process_complete(text)

    def reset(self) -> None:
        self._scrubber.reset()

    def list_tags(self) -> List[str]:
        return list(SUPPORTED_TAGS)
