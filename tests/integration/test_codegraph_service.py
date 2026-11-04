"""
Integration tests for Code Graph Analysis service endpoints (SPEC §29.6 / F-0069 / US-107).
"""
import pytest
from starlette.testclient import TestClient

from sidecar.service import create_app
from sidecar import config


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_codegraph_status_endpoint(client):
    """SPEC §29.6 line 7738: Code graph status endpoint returns configuration and status."""
    res = client.get("/codegraph/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["enabled"] is True
    assert "default_code_graph_provider" in data["provider"]
    assert ".ts" in data["supported_extensions"]


def test_codegraph_analyze_endpoint(client):
    """SPEC §29.6 line 7690: Analyze codebase endpoint produces nodes and edges."""
    res = client.post("/codegraph/analyze", json={"project_path": "."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "files" in data
    assert "edges" in data
    assert "clusters" in data
    assert "importance" in data
    assert "entry_points" in data


def test_codegraph_scope_endpoint(client):
    """SPEC §29.6 line 7717: Scope task files endpoint returns seed and expanded files."""
    res = client.post(
        "/codegraph/scope",
        json={"task_description": "update connectivity check probe", "project_path": ".", "depth": 2},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "seed_files" in data
    assert "expanded_files" in data


def test_codegraph_graph_endpoint(client):
    """SPEC §29.6 line 7725: Graph endpoint retrieves cached graphify or runs AST scanner."""
    res = client.post("/codegraph/graph", json={"project_path": ".", "max_age_hours": 24.0})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "files" in data
    assert data["source"] in ("ast_scanner", "graphify")


def test_codegraph_off_switch_503(client, monkeypatch):
    """SPEC §29.6 line 7738: When locus.code_graph.enabled is false, endpoints return HTTP 503."""
    monkeypatch.setattr(config, "get", lambda k, default=None: False if "enabled" in k else default)
    monkeypatch.setattr(config, "is_enabled", lambda k, default=True: False if "enabled" in k else default)

    for path, method in [
        ("/codegraph/status", "get"),
        ("/codegraph/analyze", "post"),
        ("/codegraph/scope", "post"),
        ("/codegraph/graph", "post"),
    ]:
        if method == "get":
            res = client.get(path)
        else:
            res = client.post(path, json={})
        assert res.status_code == 503, f"{path} should return 503 when off-switch disabled"
