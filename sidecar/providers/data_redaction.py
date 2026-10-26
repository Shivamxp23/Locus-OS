"""
SPEC §13.8 lines 3438-3512:
Data Redaction Provider Interface and Implementation (F-0041 / US-73).

Implements BaseDataRedactionProvider and DefaultDataRedactionProvider with modular off-switches:
- locus.data_redaction.enabled
- locus.security.data_redaction.enabled
- locus.security.redaction.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

from sidecar.security.redact import (
    KEY_PATTERNS,
    SENSITIVE_BODY_KEYS,
    SENSITIVE_QUERY_PARAMS,
    DataRedactor,
    mask_token as core_mask_token,
)
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseDataRedactionProvider(ABC):
    """
    SPEC §13.8: Provider Interface: DataRedactionProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Data Redaction provider is enabled."""
        raise NotImplementedError

    @abstractmethod
    def redact_text(self, text: str) -> str:
        """Redact sensitive API keys, secrets, tokens, and query params from text."""
        raise NotImplementedError

    @abstractmethod
    def redact_payload(self, payload: Any) -> Any:
        """Redact nested JSON dictionary or list payload."""
        raise NotImplementedError

    @abstractmethod
    def mask_token(self, token: str) -> str:
        """Mask single token (short=full mask, long=first6+last4)."""
        raise NotImplementedError

    @abstractmethod
    def list_patterns(self) -> List[Dict[str, Any]]:
        """List active redaction patterns and rules."""
        raise NotImplementedError


class DefaultDataRedactionProvider(BaseDataRedactionProvider):
    """
    SPEC §13.8: Default implementation of DataRedactionProvider.
    Protects logs, tool outputs, and network payloads by scrubbing API keys and credentials.
    """

    def __init__(self, custom_patterns: Optional[List[str]] = None):
        cfg_custom = custom_patterns or config.get("security.redact_patterns") or config.get("locus.security.redact_patterns") or []
        self.redactor = DataRedactor(custom_patterns=list(cfg_custom))

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.data_redaction.enabled
        - locus.security.data_redaction.enabled
        - locus.security.redaction.enabled
        """
        v1 = config.get("locus.data_redaction.enabled")
        if v1 is not None and not config.is_enabled("locus.data_redaction.enabled"):
            return False

        v2 = config.get("locus.security.data_redaction.enabled")
        if v2 is not None and not config.is_enabled("locus.security.data_redaction.enabled"):
            return False

        v3 = config.get("locus.security.redaction.enabled")
        if v3 is not None and not config.is_enabled("locus.security.redaction.enabled"):
            return False

        return True

    def redact_text(self, text: str) -> str:
        return self.redactor.redact_sensitive_text(text)

    def redact_payload(self, payload: Any) -> Any:
        return self.redactor.redact_structure(payload)

    def mask_token(self, token: str) -> str:
        return core_mask_token(token)

    def list_patterns(self) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        for r in KEY_PATTERNS:
            rules.append({
                "vendor": r["vendor"],
                "pattern": getattr(r["pattern"], "pattern", str(r["pattern"])),
            })
        for c in self.redactor.custom_patterns:
            rules.append({
                "vendor": "Custom",
                "pattern": c,
            })
        return rules
