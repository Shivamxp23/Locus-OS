"""
SPEC §27.1 lines 1477-1540: Integration tests for PageIndex Retrieval endpoints (F-0059 / US-95).
Tests FastAPI endpoints under /pageindex/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.search.pageindex import PageIndexEngine
from sidecar.providers.pageindex import DefaultPageIndexRetrievalProvider
from sidecar.service import create_app

SAMPLE_MD = """
# Test Handbook

This is the main root.

## Architecture Guidelines

Guidelines for building services.

### Microservices

Keep services isolated and swappable.
"""


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    engine = PageIndexEngine()
    provider = DefaultPageIndexRetrievalProvider(engine=engine)
    app.state.pageindex_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.pageindex_retrieval.enabled", True)
    config.set("locus.retrieval.pageindex.enabled", True)
    yield
    config.set("locus.pageindex_retrieval.enabled", True)
    config.set("locus.retrieval.pageindex.enabled", True)


def test_pageindex_service_build_tree_endpoint(client: TestClient) -> None:
    """SPEC §27.1: POST /pageindex/build-tree."""
    payload = {
        "content": SAMPLE_MD,
        "doc_name": "handbook.md",
        "min_node_token": 1,
        "summary_token_threshold": 100,
    }
    res = client.post("/pageindex/build-tree", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["doc_name"] == "handbook.md"
    assert len(data["structure"]) >= 1
    root = data["structure"][0]
    assert root["title"] == "Test Handbook"
    assert root["node_id"] == "0001"


def test_pageindex_service_retrieve_endpoint(client: TestClient) -> None:
    """SPEC §27.1: POST /pageindex/retrieve."""
    # First build tree to populate engine cache
    client.post(
        "/pageindex/build-tree",
        json={"content": SAMPLE_MD, "doc_name": "handbook.md", "min_node_token": 1},
    )

    # Now retrieve
    res = client.post(
        "/pageindex/retrieve",
        json={"query": "Microservices isolated swappable", "doc_name": "handbook.md"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["doc_name"] == "handbook.md"
    assert data["leaf_title"] == "Microservices"
    assert "Keep services isolated" in data["text"]
    assert "Microservices" in data["citation_path"]
    assert data["hops"] >= 2


def test_pageindex_service_status_endpoint(client: TestClient) -> None:
    """SPEC §27.1: GET /pageindex/status."""
    res = client.get("/pageindex/status")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "default_pageindex_retrieval_provider"
    assert data["feature_enabled"] is True
    assert data["subsystem_enabled"] is True


def test_pageindex_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §27.1: Modular off-switches returning HTTP 503."""
    config.set("locus.pageindex_retrieval.enabled", False)

    res_build = client.post(
        "/pageindex/build-tree",
        json={"content": "# Test", "doc_name": "doc.md"},
    )
    assert res_build.status_code == 503
    assert res_build.json()["disabled"] == "locus.pageindex_retrieval.enabled"

    res_ret = client.post(
        "/pageindex/retrieve",
        json={"query": "test"},
    )
    assert res_ret.status_code == 503

    res_st = client.get("/pageindex/status")
    assert res_st.status_code == 503
