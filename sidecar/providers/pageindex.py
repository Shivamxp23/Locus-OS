"""
SPEC §27.1 lines 1477-1540: PageIndex Retrieval Provider (F-0059 / US-95).
Modular off-switches:
- locus.pageindex_retrieval.enabled (returns HTTP 503 when off)
- locus.retrieval.pageindex.enabled (subsystem toggle; when off, retrieval returns empty)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.search.pageindex import (
    PageIndexDoc,
    PageIndexEngine,
    PageIndexNode,
    PageIndexSearchResult,
)

logger = logging.getLogger("locus.providers.pageindex")


class BasePageIndexRetrievalProvider(ABC):
    """
    Abstract contract for Vectorless PageIndex Retrieval Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def build_tree(
        self,
        content: str,
        doc_name: str = "document.md",
        min_node_token: int = 50,
        summary_token_threshold: int = 200,
    ) -> Dict[str, Any]:
        """Parse markdown and build hierarchical PageIndex tree."""

    @abstractmethod
    def retrieve(
        self,
        query: str,
        doc_name: Optional[str] = None,
        tree_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Reasoning-based tree search returning leaf full text with citation path."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultPageIndexRetrievalProvider(BasePageIndexRetrievalProvider):
    """
    Default provider wrapping PageIndexEngine with modular off-switch enforcement.
    """

    def __init__(self, engine: Optional[PageIndexEngine] = None) -> None:
        self.engine = engine or PageIndexEngine()

    @property
    def name(self) -> str:
        return "default_pageindex_retrieval_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        switch = "locus.pageindex_retrieval.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def build_tree(
        self,
        content: str,
        doc_name: str = "document.md",
        min_node_token: int = 50,
        summary_token_threshold: int = 200,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "PageIndex retrieval is disabled",
                "disabled": switch,
            }

        doc = self.engine.md_to_tree(
            content=content,
            doc_name=doc_name,
            min_node_token=min_node_token,
            summary_token_threshold=summary_token_threshold,
        )
        return doc.to_dict()

    def retrieve(
        self,
        query: str,
        doc_name: Optional[str] = None,
        tree_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "PageIndex retrieval is disabled",
                "disabled": switch,
            }

        doc: Optional[PageIndexDoc] = None
        if tree_data:
            doc = PageIndexDoc.from_dict(tree_data)

        res: PageIndexSearchResult = self.engine.retrieve(
            query=query,
            doc=doc,
            doc_name=doc_name,
        )
        return res.to_dict()

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        subsystem_enabled = self.engine.is_engine_enabled()

        if not enabled:
            return {
                "status_code": 503,
                "detail": "PageIndex retrieval is disabled",
                "disabled": switch,
                "feature_enabled": False,
                "subsystem_enabled": subsystem_enabled,
            }

        status = self.engine.get_status()
        status["feature_enabled"] = True
        status["subsystem_enabled"] = subsystem_enabled
        status["provider"] = self.name
        return status
