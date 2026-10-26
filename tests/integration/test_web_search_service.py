"""
SPEC §15.1 lines 2713-2719: Integration tests for Web Search Service (F-0105 / US-77).
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_service_search_query(client: TestClient) -> None:
    """SPEC §15.1 line 2715: "Scope: OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini + full content fetch." """
    res = client.post("/search/query", json={"query": "Locus OS specifications", "max_results": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["query"] == "Locus OS specifications"
    assert "results" in data
    assert len(data["results"]) > 0


def test_service_search_query_specific_provider(client: TestClient) -> None:
    """SPEC §15.1 line 2715: "Execute search with specific provider selection." """
    res = client.post("/search/query", json={"query": "privacy search", "provider": "brave"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "brave"
    assert len(data["results"]) == 1
    assert data["results"][0]["provider"] == "brave"


def test_service_search_fetch(client: TestClient) -> None:
    """SPEC §15.1 line 2715: "Full content fetch provider for webpage retrieval and parsing." """
    res = client.post("/search/fetch", json={"url": "https://example.com/spec"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["url"] == "https://example.com/spec"
    assert "content" in data


def test_service_search_providers(client: TestClient) -> None:
    """SPEC §15.1 line 2715: "List available and active search providers." """
    res = client.get("/search/providers")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "openai" in data["providers"]
    assert "brave" in data["providers"]
    assert "tavily" in data["providers"]
    assert "perplexity" in data["providers"]
    assert "exa" in data["providers"]
    assert "gemini" in data["providers"]
    assert "parallel" in data["providers"]
    assert "content_fetch" in data["providers"]
    assert "active_provider" in data


def test_service_search_off_switches(client: TestClient) -> None:
    """SPEC §15.1 line 2714: "Off state: Web search is a Pi tool; available whenever the LLM needs it. Disable via tool config." """
    config.set("locus.web_search_8_providers.enabled", False)
    try:
        r1 = client.post("/search/query", json={"query": "test"})
        assert r1.status_code == 503
        assert "disabled" in r1.json()

        r2 = client.post("/search/fetch", json={"url": "https://example.com"})
        assert r2.status_code == 503

        r3 = client.get("/search/providers")
        assert r3.status_code == 503
    finally:
        config.set("locus.web_search_8_providers.enabled", True)

    config.set("locus.web_search.enabled", False)
    try:
        r4 = client.post("/search/query", json={"query": "test"})
        assert r4.status_code == 503
    finally:
        config.set("locus.web_search.enabled", True)
