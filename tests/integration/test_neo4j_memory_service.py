"""
SPEC §4.1-4.2 / F-0021 / US-46: Integration Tests for Graph-Native Memory Service.
Asserts FastAPI routes `/memory/store`, `/memory/query`, `/memory/context`,
`/memory/entity`, `/memory/entity/{entity_id}`, `/memory/reasoning`, `/memory/config`,
and the modular 503 off-switch on locus.memory.enabled.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_store_memory_endpoint(client):
    """SPEC §4.1-4.2 line 617: "store_conversation_turn(user, assistant, session_id)" """
    resp = client.post(
        "/memory/store",
        json={
            "content": "Shivam attended the Meeting at the Office with Alice.",
            "entry_type": "long_term",
            "metadata": {"source": "cli"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "entry" in data
    assert data["entry"]["entry_type"] == "long_term"
    entities = data["entry"]["entities"]
    names = [e["name"].lower() for e in entities]
    assert "shivam" in names
    assert "meeting" in names


def test_query_memory_endpoint(client):
    """SPEC §4.1-4.2 line 610: "Retrieval path: get_context(query) → hybrid (vector similarity over embeddings + text search + graph traversal)" """
    resp = client.post(
        "/memory/query",
        json={"query": "Shivam", "limit": 5, "depth": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    result = data["result"]
    assert len(result["entities"]) >= 1
    assert any(e["name"] == "Shivam" for e in result["entities"])


def test_context_for_forge_endpoint(client):
    """SPEC §4.1-4.2 line 635: "Provider Interface: implements MemoryProvider; get_context(query) feeds Context Forge Layer 4 (Graph, 150t)." """
    resp = client.post(
        "/memory/context",
        json={"query": "Locus", "max_tokens": 150},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "context" in data
    assert "Graph Pathways" in data["context"]
    assert "Locus" in data["context"]


def test_entity_endpoints(client):
    """SPEC §4.1-4.2 line 604: "- **Long-term** (knowledge graph): Entity + Preference + Fact nodes, in the **POLE+O** entity-type taxonomy" """
    # 1. Create custom entity
    create_resp = client.post(
        "/memory/entity",
        json={
            "id": "ent_test_device",
            "name": "ServerNode",
            "type": "Object",
            "properties": {"cores": 16},
        },
    )
    assert create_resp.status_code == 200
    assert create_resp.json()["success"] is True

    # 2. Get entity
    get_resp = client.get("/memory/entity/ent_test_device")
    assert get_resp.status_code == 200
    ent = get_resp.json()["entity"]
    assert ent["name"] == "ServerNode"
    assert ent["type"] == "Object"

    # 3. 404 on nonexistent entity
    resp_404 = client.get("/memory/entity/nonexistent_ent_xyz")
    assert resp_404.status_code == 404


def test_reasoning_step_endpoint(client):
    """SPEC §4.1-4.2 line 605: "- **Reasoning** (learn from past decisions): ReasoningTrace + ReasoningStep + Tool + ToolCall nodes, with explicit :TOUCHED audit edges" """
    resp = client.post(
        "/memory/reasoning",
        json={
            "step_name": "ContextEnrichment",
            "touched_entities": ["ent_shivam", "ent_locus"],
            "tool_calls": [{"tool": "web_search", "status": "success"}],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["step_id"].startswith("trace_")


def test_memory_config_endpoint(client):
    """SPEC §4.1-4.2 line 638: "Swappable / off state" """
    resp = client.get("/memory/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "Neo4jMemoryProvider"
    assert data["health"]["entities_count"] >= 4
    assert "pole_schema" in data["health"]


def test_memory_off_switch_503(client, monkeypatch):
    """SPEC §4.1-4.2 line 638: "locus.memory.enabled=false disables the whole subsystem." """
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: False if key == "locus.memory.enabled" else default,
    )

    resp_store = client.post("/memory/store", json={"content": "test"})
    assert resp_store.status_code == 503
    assert resp_store.json() == {"disabled": "locus.memory.enabled"}

    resp_query = client.post("/memory/query", json={"query": "test"})
    assert resp_query.status_code == 503

    resp_ctx = client.post("/memory/context", json={"query": "test"})
    assert resp_ctx.status_code == 503

    resp_ent = client.post("/memory/entity", json={"id": "e1", "name": "test"})
    assert resp_ent.status_code == 503

    resp_get_ent = client.get("/memory/entity/ent_shivam")
    assert resp_get_ent.status_code == 503

    resp_reason = client.post("/memory/reasoning", json={"step_name": "test"})
    assert resp_reason.status_code == 503

    resp_cfg = client.get("/memory/config")
    assert resp_cfg.status_code == 503
