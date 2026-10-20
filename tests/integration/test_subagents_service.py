"""
SPEC §11.1-11.5 + §3.7 / F-0036 / US-39: Integration Tests for Subagents & AutoResearch Service.
Asserts FastAPI routes `/subagents/spawn`, `/subagents/archetypes`, `/subagents/config`,
`/subagents/autoresearch`, and the modular 503 off-switch on locus.subagents_autoresearch.enabled.
"""
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


def test_spawn_subagent_endpoint(client):
    """SPEC §11.1: Spawning subagent via HTTP returns 200 and incremented depth."""
    payload = {
        "task": "Optimize database indices for query plan",
        "archetype": "data_engineer",
        "parent_session_id": "session-parent-abc",
        "current_depth": 0,
    }
    resp = client.post("/subagents/spawn", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "result" in data
    res = data["result"]
    assert res["archetype"] == "data_engineer"
    assert res["depth"] == 1
    assert res["skip_memory"] is True
    assert res["skip_review"] is True
    assert res["parent_session_id"] == "session-parent-abc"


def test_spawn_subagent_depth_limit_400(client):
    """SPEC §11.1: Exceeding MAX_SPAWN_DEPTH (3) returns 400 Bad Request."""
    payload = {
        "task": "Deeper task execution",
        "archetype": "researcher",
        "current_depth": 3,
    }
    resp = client.post("/subagents/spawn", json=payload)
    assert resp.status_code == 400
    assert "Maximum subagent depth reached" in resp.json()["detail"]


def test_spawn_subagent_unknown_archetype_404(client):
    """Unknown archetype returns 404 Not Found."""
    payload = {
        "task": "Run unknown task",
        "archetype": "invalid_archetype_xyz",
        "current_depth": 0,
    }
    resp = client.post("/subagents/spawn", json=payload)
    assert resp.status_code == 404
    assert "Unknown subagent archetype" in resp.json()["detail"]


def test_list_archetypes_endpoint(client):
    """SPEC §11.1: List archetypes returns all registered archetypes and supports category filtering."""
    resp = client.get("/subagents/archetypes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "archetypes" in data
    assert len(data["archetypes"]) >= 19

    # Filter by faction category
    resp_faction = client.get("/subagents/archetypes?category=faction")
    assert resp_faction.status_code == 200
    data_f = resp_faction.json()
    assert len(data_f["archetypes"]) == 4
    names = {a["name"] for a in data_f["archetypes"]}
    assert names == {"planner", "curator", "analyst", "builder"}


def test_subagents_config_endpoint(client):
    """Get subagents and AutoResearch configuration endpoint."""
    resp = client.get("/subagents/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["max_spawn_depth"] == 3
    assert data["archetype_count"] >= 19


def test_autoresearch_endpoint(client):
    """AutoResearch endpoint runs topic synthesis across subagents."""
    payload = {
        "topic": "Graph RAG indexing performance trade-offs",
        "depth_mode": "quick",
    }
    resp = client.post("/subagents/autoresearch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "result" in data
    res = data["result"]
    assert res["topic"] == "Graph RAG indexing performance trade-offs"
    assert res["status"] == "completed"
    assert res["subagents_spawned"] >= 1
    assert len(res["findings"]) >= 1


def test_subagents_503_off_switch(monkeypatch):
    """Modularity architecture (03): Off switch on locus.subagents_autoresearch.enabled returns 503."""
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: False
        if "subagents" in key or "autoresearch" in key
        else True,
    )
    app = create_app()
    with TestClient(app) as disabled_client:
        resp_spawn = disabled_client.post("/subagents/spawn", json={"task": "test", "archetype": "planner"})
        assert resp_spawn.status_code == 503
        assert resp_spawn.json()["disabled"] == "locus.subagents_autoresearch.enabled"

        resp_archetypes = disabled_client.get("/subagents/archetypes")
        assert resp_archetypes.status_code == 503
        assert resp_archetypes.json()["disabled"] == "locus.subagents_autoresearch.enabled"

        resp_config = disabled_client.get("/subagents/config")
        assert resp_config.status_code == 503
        assert resp_config.json()["disabled"] == "locus.subagents_autoresearch.enabled"

        resp_research = disabled_client.post("/subagents/autoresearch", json={"topic": "test"})
        assert resp_research.status_code == 503
        assert resp_research.json()["disabled"] == "locus.subagents_autoresearch.enabled"
