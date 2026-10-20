"""
SPEC §6.2: Dynamic Context References Provider (F-0028).
Implements BaseContextReferenceProvider and DefaultContextReferenceProvider with modular off-switch.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sidecar.config as config
from sidecar.context.references import (
    ContextRefType,
    ContextReferenceResolver,
    ResolvedReference,
)
from sidecar.registry import get_registry

logger = logging.getLogger(__name__)


class BaseContextReferenceProvider(ABC):
    """
    SPEC §6.2 line 2113:
    Provider Interface: ContextReferenceResolver
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Context References resolution is enabled."""
        raise NotImplementedError

    @abstractmethod
    def resolve_references(
        self,
        prompt: str,
        max_budget: int = 1500,
    ) -> Tuple[str, List[ResolvedReference]]:
        """Parse @ tags, resolve target content within budget, and return cleaned prompt + resolved references."""
        raise NotImplementedError

    @abstractmethod
    def format_xml(self, refs: List[ResolvedReference]) -> str:
        """Format resolved references into <context_ref> XML enclosures."""
        raise NotImplementedError


class DefaultContextReferenceProvider(BaseContextReferenceProvider):
    """
    Default context references resolver provider.
    Off-switch: locus.context_references.enabled (default: true) and locus.context.references.enabled (default: true).
    Off-state: tags are treated as literal text; no file resolution occurs.
    """

    def __init__(self, repo_root: Optional[Path | str] = None) -> None:
        self.resolver = ContextReferenceResolver(repo_root=repo_root)

    def is_available(self) -> bool:
        """SPEC §6.2 line 2115: Swappable / off state check."""
        cr_enabled = config.get("locus.context_references.enabled", True)
        c_enabled = config.get("locus.context.references.enabled", True)
        return bool(cr_enabled and c_enabled)

    def resolve_references(
        self,
        prompt: str,
        max_budget: int = 1500,
    ) -> Tuple[str, List[ResolvedReference]]:
        if not self.is_available():
            # SPEC §6.2 line 2115: Off -> @ tags are treated as literal text; no file resolution occurs.
            return prompt, []
        return self.resolver.extract_and_resolve_references(prompt, max_ref_budget=max_budget)

    def format_xml(self, refs: List[ResolvedReference]) -> str:
        if not self.is_available():
            return ""
        return self.resolver.format_references_xml(refs)


# Register default provider in universal registry
get_registry().register("context_references", "default_context_references", DefaultContextReferenceProvider)
get_registry().register("context_references", "default", DefaultContextReferenceProvider)
