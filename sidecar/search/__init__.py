"""
SPEC §15.1 lines 2713-2719:
Web Search module re-exports (F-0105 / US-77).
"""
from sidecar.search.manager import WebSearchManager
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

__all__ = [
    "SearchResult",
    "BaseSearchProvider",
    "OpenAISearchProvider",
    "BraveSearchProvider",
    "ParallelSearchProvider",
    "TavilySearchProvider",
    "ExaSearchProvider",
    "PerplexitySearchProvider",
    "GeminiSearchProvider",
    "FullContentFetchProvider",
    "MockSearchProvider",
    "WebSearchManager",
]
