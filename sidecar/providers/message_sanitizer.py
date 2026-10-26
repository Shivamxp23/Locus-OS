"""
SPEC §13.10 lines 3599-3668:
Message Sanitization Provider (F-0043 / US-75).

Registers as a provider in sidecar/providers/ with modular off-switches:
- locus.message_sanitization.enabled
- locus.security.message_sanitization.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Tuple

import sidecar.config as config
from sidecar.security.sanitizer import (
    MessageSanitizer,
    sanitize_messages,
    sanitize_structure_surrogates,
    sanitize_surrogates,
)

logger = logging.getLogger(__name__)


class BaseMessageSanitizerProvider(ABC):
    """Abstract interface for Message Sanitization provider."""

    @abstractmethod
    def sanitize_text(self, text: str) -> str:
        """Sanitize text by replacing lone surrogates with U+FFFD."""
        raise NotImplementedError

    @abstractmethod
    def sanitize_structure(self, payload: Any) -> Tuple[Any, bool]:
        """Deeply sanitize nested dict/list structures."""
        raise NotImplementedError

    @abstractmethod
    def sanitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize message array prior to LLM API dispatch."""
        raise NotImplementedError


class DefaultMessageSanitizerProvider(BaseMessageSanitizerProvider):
    """Default implementation of Message Sanitizer provider."""

    def __init__(self) -> None:
        self._sanitizer = MessageSanitizer()

    def is_enabled(self) -> bool:
        """Modular off-switches for message sanitization."""
        v1 = config.get("locus.message_sanitization.enabled")
        if v1 is not None and not config.is_enabled("locus.message_sanitization.enabled"):
            return False
        v2 = config.get("locus.security.message_sanitization.enabled")
        if v2 is not None and not config.is_enabled("locus.security.message_sanitization.enabled"):
            return False
        return True

    def sanitize_text(self, text: str) -> str:
        if not self.is_enabled():
            return text
        return self._sanitizer.sanitize_text(text)

    def sanitize_structure(self, payload: Any) -> Tuple[Any, bool]:
        if not self.is_enabled():
            return payload, False
        return self._sanitizer.sanitize_structure(payload)

    def sanitize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.is_enabled():
            return messages
        return self._sanitizer.sanitize_messages(messages)
