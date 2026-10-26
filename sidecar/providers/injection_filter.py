"""
SPEC §13.1 lines 3006-3140:
Prompt Injection Protection (Injection Filter) Provider Interface and Implementation (F-0037 / US-68).
Implements BaseInjectionFilterProvider and DefaultInjectionFilterProvider with modular off-switches:
- locus.injection_filter.enabled
- locus.security.prompt_injection.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Optional

from sidecar.security.injection_filter import (
    NormalizedPrompt,
    PromptEnforcementDecision,
    enforce_prompt_input,
    normalize_prompt,
    scan_tool_definition,
)
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseInjectionFilterProvider(ABC):
    """
    SPEC §13.1: Provider Interface: InjectionFilterProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Injection Filter is enabled."""
        raise NotImplementedError

    @abstractmethod
    def enforce(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Screen prompt input and return enforcement decision."""
        raise NotImplementedError

    @abstractmethod
    def scan_tool(self, name: str, description: str) -> Dict[str, Any]:
        """Scan tool definition for prompt injection attempts."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, input_text: str) -> Dict[str, Any]:
        """Normalize input prompt for inspection."""
        raise NotImplementedError


class DefaultInjectionFilterProvider(BaseInjectionFilterProvider):
    """
    SPEC §13.1: Default implementation of InjectionFilterProvider.
    Synchronous analysis pipeline with Unicode normalization, DFA rules, and PII-safe hashing.
    """

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.injection_filter.enabled
        - locus.security.prompt_injection.enabled
        """
        v1 = config.get("locus.injection_filter.enabled")
        if v1 is not None and not config.is_enabled("locus.injection_filter.enabled"):
            return False

        v2 = config.get("locus.security.prompt_injection.enabled")
        if v2 is not None and not config.is_enabled("locus.security.prompt_injection.enabled"):
            return False

        return True

    def enforce(self, input_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Screen prompt input."""
        decision = enforce_prompt_input(input_text=input_text, context=context)
        return {
            "status": "ok",
            "decision": decision.to_dict(),
        }

    def scan_tool(self, name: str, description: str) -> Dict[str, Any]:
        """Scan tool metadata."""
        decision = scan_tool_definition(name=name, description=description)
        return {
            "status": "ok",
            "decision": decision.to_dict(),
        }

    def normalize(self, input_text: str) -> Dict[str, Any]:
        """Normalize input text."""
        norm = normalize_prompt(text=input_text)
        return {
            "status": "ok",
            "normalized": norm.to_dict(),
        }
