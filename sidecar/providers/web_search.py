"""
SPEC §15.1 lines 2713-2719:
Web Search Provider Interface and Implementation (F-0105 / US-77).

Implements BaseWebSearchProvider and DefaultWebSearchProvider with modular off-switches:
- locus.web_search_8_providers.enabled
- locus.web_search.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

import sidecar.config as config
from sidecar.search.manager import WebSearchManager
from sidecar.search.providers import BaseSearchProvider, SearchResult

logger = logging.getLogger(__name__)


class BaseWebSearchProvider(ABC):
    """
    SPEC §15.1: Provider Interface: WebSearchProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if web search feature is enabled."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 5,
        provider: Optional[str] = None,
    ) -> List[SearchResult]:
        """Execute web search across registered providers."""
        raise NotImplementedError

    @abstractmethod
    def fetch_content(self, url: str) -> Dict[str, Any]:
        """Fetch full content of given URL."""
        raise NotImplementedError

    @abstractmethod
    def list_providers(self) -> List[str]:
        """List registered search providers."""
        raise NotImplementedError

    @abstractmethod
    def set_provider(self, provider: BaseSearchProvider | str) -> None:
        """Set active default search provider."""
        raise NotImplementedError


class DefaultWebSearchProvider(BaseWebSearchProvider):
    """
    SPEC §15.1: Default implementation of WebSearchProvider.
    Wraps WebSearchManager with modular off-switch checks.
    """

    def __init__(self, manager: Optional[WebSearchManager] = None) -> None:
        self.manager = manager or WebSearchManager()

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.web_search_8_providers.enabled
        - locus.web_search.enabled
        """
        v1 = config.get("locus.web_search_8_providers.enabled")
        if v1 is not None and not config.is_enabled("locus.web_search_8_providers.enabled"):
            return False

        v2 = config.get("locus.web_search.enabled")
        if v2 is not None and not config.is_enabled("locus.web_search.enabled"):
            return False

        return True

    def search(
        self,
        query: str,
        max_results: int = 5,
        provider: Optional[str] = None,
    ) -> List[SearchResult]:
        if not self.is_available():
            raise RuntimeError("Web search is disabled by modular off-switch.")
        return self.manager.search(query=query, max_results=max_results, provider=provider)

    def fetch_content(self, url: str) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Web search is disabled by modular off-switch.")
        return self.manager.fetch_content(url)

    def list_providers(self) -> List[str]:
        return self.manager.list_providers()

    def set_provider(self, provider: BaseSearchProvider | str) -> None:
        self.manager.set_provider(provider)
