"""Integration tests for Memory Tree FastAPI service endpoints.

Tests Spec §4.5:
- POST /memory/tree/leaf: Append L0 chunk and trigger seal cascade.
- POST /memory/tree/seal: Seal level manually or conditionally.
- GET /memory/tree/search: Top-down relevance search.
- POST /memory/tree/topic_route: Route content into topic scopes.
- GET /memory/tree/config: Health and metrics report.
- Modular off-switch 503 behavior when locus.memory_tree_hierarchical_summarization_cascade.enabled is False.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_service_append_leaf_and_seal_endpoints(client):
    """SPEC §4.5 line 755: "FUNCTION append_leaf(tree_scope, content): node = TreeNode { level: 0, content, sealed: false }"

    Asserts /memory/tree/leaf and /memory/tree/seal endpoints operate end-to-end via FastAPI TestClient.
    """
    # Append leaf
    leaf_payload = {
        "tree_scope": "test:integration",
        "content": "First integration test chunk for Memory Tree.",
        "source_id": "integration-01",
    }
    res = client.post("/memory/tree/leaf", json=leaf_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["node"]["level"] == 0
    assert data["node"]["tree_scope"] == "test:integration"
    node_id = data["node"]["id"]

    # Retrieve nodes
    res_nodes = client.get("/memory/tree/nodes?tree_scope=test:integration")
    assert res_nodes.status_code == 200
    nodes_data = res_nodes.json()
    assert len(nodes_data["nodes"]) == 1
    assert nodes_data["nodes"][0]["id"] == node_id

    # Force seal
    res_seal = client.post(
        "/memory/tree/seal",
        json={"tree_scope": "test:integration", "level": 0, "force": True},
    )
    assert res_seal.status_code == 200
    seal_data = res_seal.json()
    assert seal_data["status"] == "ok"
    assert seal_data["sealed"] is True
    assert seal_data["node"]["level"] == 1
    assert node_id in seal_data["node"]["children"]


def test_service_search_and_topic_route_endpoints(client):
    """SPEC §4.5 line 787: "FUNCTION search(tree_scope, query, max_results): Start from highest-level nodes, descend into relevant branches"

    Asserts /memory/tree/search and /memory/tree/topic_route routes work end-to-end.
    """
    # Route topic
    res_route = client.post(
        "/memory/tree/topic_route",
        json={
            "content": "Designing high-performance memory tree cascading pipelines in Python.",
            "topics": ["Python", "Rust", "Golang"],
        },
    )
    assert res_route.status_code == 200
    route_data = res_route.json()
    assert route_data["status"] == "ok"
    assert "topic:python" in route_data["matched_scopes"]

    # Search in routed scope
    res_search = client.get("/memory/tree/search?tree_scope=topic:python&query=pipelines")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["status"] == "ok"
    assert len(search_data["nodes"]) >= 1
    assert "pipelines" in search_data["nodes"][0]["content"]


def test_service_config_and_health_endpoint(client):
    """SPEC §4.5 line 808: "SQLite table: mem_tree_chunks"

    Asserts /memory/tree/config returns active provider information and database health metrics.
    """
    res = client.get("/memory/tree/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert "HierarchicalMemoryTreeProvider" in data["provider"]
    assert data["health"]["status"] == "healthy"


def test_service_modular_off_switch_returns_503(client, monkeypatch):
    """SPEC §4.5 line 820: "Swappable / off state: locus.memory.tree.enabled. Off → raw chunks stored but never summarized (flat memory only)"

    Asserts endpoints return HTTP 503 when locus.memory_tree_hierarchical_summarization_cascade.enabled is False.
    """
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: False
        if key in (
            "locus.memory.tree.enabled",
            "locus.memory_tree_hierarchical_summarization_cascade.enabled",
        )
        else default,
    )

    # Config endpoint
    res_cfg = client.get("/memory/tree/config")
    assert res_cfg.status_code == 503
    assert res_cfg.json()["disabled"] == "locus.memory_tree_hierarchical_summarization_cascade.enabled"

    # Leaf append endpoint
    res_leaf = client.post(
        "/memory/tree/leaf",
        json={"tree_scope": "test", "content": "Hello"},
    )
    assert res_leaf.status_code == 503

    # Search endpoint
    res_search = client.get("/memory/tree/search?tree_scope=test&query=hi")
    assert res_search.status_code == 503

    # Seal endpoint
    res_seal = client.post("/memory/tree/seal", json={"tree_scope": "test"})
    assert res_seal.status_code == 503

    # Topic route endpoint
    res_route = client.post(
        "/memory/tree/topic_route",
        json={"content": "Hello", "topics": ["test"]},
    )
    assert res_route.status_code == 503
