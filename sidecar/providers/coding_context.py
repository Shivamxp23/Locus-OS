"""
SPEC §6.3: Coding Context Engine Provider (F-0029).
Implements BaseCodingContextProvider and DefaultCodingContextProvider with modular off-switch.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

import sidecar.config as config
from sidecar.context.coding_context import (
    CodingContextEngine,
    WorkspaceCodingState,
)
from sidecar.registry import get_registry

logger = logging.getLogger(__name__)


class BaseCodingContextProvider(ABC):
    """
    SPEC §6.3 line 2185:
    Provider Interface: CodingContextProvider
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Coding Context extraction is enabled."""
        raise NotImplementedError

    @abstractmethod
    def get_coding_context(self, token_budget: int = 500) -> WorkspaceCodingState:
        """Extract workspace coding context including git branch, diff stat, and AST repo map."""
        raise NotImplementedError

    @abstractmethod
    def format_layer(self, state: WorkspaceCodingState) -> str:
        """Format coding context into structured text layer."""
        raise NotImplementedError


class DefaultCodingContextProvider(BaseCodingContextProvider):
    """
    Default coding context engine provider.
    Off-switch: locus.coding_context.enabled (default: true) and locus.context.coding_map.enabled (default: true).
    Off-state: coding context omitted; agent relies on explicit tool lookups.
    """

    def __init__(self, repo_root: Optional[Path | str] = None) -> None:
        self.engine = CodingContextEngine(repo_root=repo_root)

    def is_available(self) -> bool:
        """SPEC §6.3 line 2187: Swappable / off state check."""
        cc_enabled = config.get("locus.coding_context.enabled", True)
        cm_enabled = config.get("locus.context.coding_map.enabled", True)
        return bool(cc_enabled and cm_enabled)

    def get_coding_context(self, token_budget: int = 500) -> WorkspaceCodingState:
        if not self.is_available():
            # SPEC §6.3 line 2187: Off -> coding context omitted from prompt
            return WorkspaceCodingState(repo_root=str(self.engine.repo_root))
        return self.engine.generate_coding_context(token_budget=token_budget)

    def format_layer(self, state: WorkspaceCodingState) -> str:
        if not self.is_available():
            return ""
        return self.engine.format_coding_context_layer(state)


# Register default provider in universal registry
get_registry().register("coding_context", "default_coding_context", DefaultCodingContextProvider)
get_registry().register("coding_context", "default", DefaultCodingContextProvider)
