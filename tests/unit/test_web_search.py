"""
SPEC §15.1 lines 2713-2719: Unit tests for Web Search (8 Providers) (F-0105 / US-77).
"""
from __future__ import annotations

import pytest

import sidecar.config as config
from sidecar.providers.web_search import (
    BaseWebSearchProvider,
    DefaultWebSearchProvider,
)
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


def test_openai_and_brave_search_providers():
    """SPEC §15.1 line 2715: "Scope: OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini + full content fetch." """
    oa = OpenAISearchProvider()
    assert oa.name == "openai"
    assert oa.search("") == []
    oa_res = oa.search("Locus cognitive system")
    assert len(oa_res) == 1
    assert oa_res[0].provider == "openai"

    br = BraveSearchProvider()
    assert br.name == "brave"
    assert br.search("") == []
    br_res = br.search("Privacy search")
    assert len(br_res) == 1
    assert br_res[0].provider == "brave"


def test_parallel_tavily_exa_providers():
    """SPEC §15.1 line 2715: "Scope: OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini + full content fetch." """
    pa = ParallelSearchProvider()
    assert pa.name == "parallel"
    assert pa.search("") == []
    assert pa.search("multi-doc")[0].provider == "parallel"

    ta = TavilySearchProvider()
    assert ta.name == "tavily"
    assert ta.search("") == []
    assert ta.search("llm-search")[0].provider == "tavily"

    ex = ExaSearchProvider()
    assert ex.name == "exa"
    assert ex.search("") == []
    assert ex.search("embeddings")[0].provider == "exa"


def test_perplexity_gemini_content_fetch_providers():
    """SPEC §15.1 line 2715: "Scope: OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini + full content fetch." """
    px = PerplexitySearchProvider()
    assert px.name == "perplexity"
    assert px.search("") == []
    assert px.search("citation query")[0].provider == "perplexity"

    ge = GeminiSearchProvider()
    assert ge.name == "gemini"
    assert ge.search("") == []
    assert ge.search("grounded query")[0].provider == "gemini"

    cf = FullContentFetchProvider()
    assert cf.name == "content_fetch"
    assert cf.search("") == []
    cf_res = cf.search("https://example.com")
    assert len(cf_res) == 1
    assert cf_res[0].provider == "content_fetch"
    assert cf_res[0].content is not None

    fetch_dict = cf.fetch_url("https://example.com/test")
    assert fetch_dict["status"] == "ok"
    assert fetch_dict["url"] == "https://example.com/test"


def test_mock_search_provider():
    """SPEC §15.1 line 2715: "Deterministic Mock Search Provider for testing." """
    mock = MockSearchProvider()
    assert mock.name == "mock"
    assert mock.is_available() is True
    assert mock.search("") == []
    results = mock.search("quantum computing", max_results=1)
    assert len(results) == 1
    assert results[0].provider == "mock"
    assert "quantum computing" in results[0].snippet


def test_web_search_manager_registration_and_dispatch():
    """SPEC §15.1 line 2715: "Manages all 8 search providers with runtime provider routing." """
    mgr = WebSearchManager()
    providers = mgr.list_providers()
    for expected in ["openai", "brave", "parallel", "tavily", "exa", "perplexity", "gemini", "content_fetch", "mock"]:
        assert expected in providers

    # Explicit provider dispatch
    mock_res = mgr.search("python", provider="mock")
    assert len(mock_res) > 0
    assert mock_res[0].provider == "mock"

    tavily_res = mgr.search("ai", provider="tavily")
    assert len(tavily_res) > 0
    assert tavily_res[0].provider == "tavily"

    with pytest.raises(ValueError, match="not registered"):
        mgr.search("error query", provider="non_existent_provider")


def test_web_search_manager_set_provider():
    """SPEC §15.1 line 2715: "Support swapping active search provider." """
    mgr = WebSearchManager()
    mgr.set_provider("brave")
    assert mgr.active_provider.name == "brave"

    mgr.set_provider(MockSearchProvider())
    assert mgr.active_provider.name == "mock"


def test_web_search_provider_modular_off_switches():
    """SPEC §15.1 line 2714: "Off state: Web search is a Pi tool; available whenever the LLM needs it. Disable via tool config." """
    mgr = WebSearchManager()
    provider = DefaultWebSearchProvider(manager=mgr)

    assert provider.is_available() is True

    # Disable via primary off-switch
    config.set("locus.web_search_8_providers.enabled", False)
    try:
        assert provider.is_available() is False
        with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
            provider.search("test")
        with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
            provider.fetch_content("https://example.com")
    finally:
        config.set("locus.web_search_8_providers.enabled", True)

    # Disable via secondary off-switch
    config.set("locus.web_search.enabled", False)
    try:
        assert provider.is_available() is False
        with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
            provider.search("test")
    finally:
        config.set("locus.web_search.enabled", True)

    assert provider.is_available() is True
