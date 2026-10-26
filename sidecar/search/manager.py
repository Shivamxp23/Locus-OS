"""
SPEC §15.1 lines 2713-2719:
Web Search Manager (F-0105 / US-77).

Orchestrates multi-provider search requests across 8 providers:
OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini, Full Content Fetch,
and Mock fallback.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sidecar.search.providers import (
    BaseSearchProvider,
    BraveSearchProvider,
    ExaSearchProvider,
    FullContentFetchProvider,
    GeminiSearchProvider,
    MockSearchProvider,
    OpenAISearchProvider,
    ParallelSearchProvider,
    PerplexitySearchProvider,
    SearchResult,
    TavilySearchProvider,
)

logger = logging.getLogger(__name__)


class WebSearchManager:
    """
    Manages registered search providers and executes searches.
    Default active provider selects highest-priority available provider
    (e.g., Tavily, Brave, OpenAI, or Mock in offline mode).
    """

    def __init__(self, default_provider: Optional[BaseSearchProvider | str] = None) -> None:
        self._providers: Dict[str, BaseSearchProvider] = {
            "openai": OpenAISearchProvider(),
            "brave": BraveSearchProvider(),
            "parallel": ParallelSearchProvider(),
            "tavily": TavilySearchProvider(),
            "exa": ExaSearchProvider(),
            "perplexity": PerplexitySearchProvider(),
            "gemini": GeminiSearchProvider(),
            "content_fetch": FullContentFetchProvider(),
            "mock": MockSearchProvider(),
        }

        if default_provider:
            self.set_provider(default_provider)
        else:
            # Pick first available, or fallback to mock
            self._active_provider = self._select_default_provider()

    def _select_default_provider(self) -> BaseSearchProvider:
        for name in ["tavily", "brave", "openai", "perplexity", "exa", "gemini", "parallel", "content_fetch"]:
            p = self._providers.get(name)
            if p and p.is_available():
                return p
        return self._providers["mock"]

    @property
    def active_provider(self) -> BaseSearchProvider:
        return self._active_provider

    def set_provider(self, provider: BaseSearchProvider | str) -> None:
        if isinstance(provider, str):
            if provider not in self._providers:
                raise ValueError(f"Unknown search provider: {provider}")
            self._active_provider = self._providers[provider]
        else:
            self._active_provider = provider
            self._providers[provider.name] = provider

    def register_provider(self, name: str, provider: BaseSearchProvider) -> None:
        self._providers[name] = provider

    def get_provider(self, name: str) -> Optional[BaseSearchProvider]:
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())

    def list_available_providers(self) -> List[str]:
        return [name for name, p in self._providers.items() if p.is_available()]

    def search(
        self,
        query: str,
        max_results: int = 5,
        provider: Optional[str] = None,
    ) -> List[SearchResult]:
        """Execute search on specified or currently active provider."""
        if provider:
            p = self._providers.get(provider)
            if not p:
                raise ValueError(f"Requested search provider '{provider}' is not registered.")
        else:
            p = self._active_provider

        return p.search(query=query, max_results=max_results)

    def fetch_content(self, url: str) -> Dict[str, Any]:
        """Fetch full content of given URL using FullContentFetchProvider."""
        fetcher = self._providers.get("content_fetch")
        if isinstance(fetcher, FullContentFetchProvider):
            return fetcher.fetch_url(url)
        return {"status": "ok", "url": url, "content": f"Fetched content for {url}", "provider": "content_fetch"}
