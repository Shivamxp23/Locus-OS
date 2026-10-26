"""
SPEC §10.9 lines 6356-6430: Integration tests for Agent Experience Tracking (Procedural Memory) (F-0121 / US-67).
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


def test_service_experience_record(client: TestClient) -> None:
    """SPEC §10.9 lines 6386-6415: Test POST /experience/record."""
    payload = {
        "task_summary": "Perform codebase verification and linting",
        "task_fingerprint": "verify-lint",
        "tool_calls": [
            {"name": "run_linter", "status": "success"},
            {"name": "run_tests", "status": "success"},
        ],
    }
    res = client.post("/experience/record", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["extracted_count"] >= 1
    assert len(data["experiences"]) >= 1
    assert data["experiences"][0]["outcome"] == "Success"


def test_service_experience_query_and_render(client: TestClient) -> None:
    """SPEC §10.9 lines 6417-6425: Test POST /experience/query and POST /experience/render."""
    record_payload = {
        "task_summary": "Automated code refactoring",
        "task_fingerprint": "code-refactor",
        "tool_calls": [
            {"name": "grep", "status": "success"},
            {"name": "edit_file", "status": "success"},
        ],
    }
    client.post("/experience/record", json=record_payload)

    # Query
    q_res = client.post("/experience/query", json={"task_fingerprint": "code-refactor", "limit": 5})
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["status"] == "ok"
    assert len(q_data["experiences"]) >= 1

    # Render
    r_res = client.post(
        "/experience/render",
        json={"task_fingerprint": "code-refactor", "message": "Proceed with refactor?", "limit": 5},
    )
    assert r_res.status_code == 200
    r_data = r_res.json()
    assert r_data["status"] == "ok"
    assert "## Relevant Operating Experience" in r_data["block"]
    assert "Proceed with refactor?" in r_data["prepended_message"]


def test_service_experience_list(client: TestClient) -> None:
    """SPEC §10.9 lines 6370-6385: Test GET /experience/list."""
    res = client.get("/experience/list?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert isinstance(data["experiences"], list)


def test_service_experience_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §10.9 line 6407: Modular off-switches return 503."""
    # Test off-switch 1: locus.experience.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.experience.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.experience.enabled" else True)

    res = client.post("/experience/record", json={"task_summary": "test", "tool_calls": []})
    assert res.status_code == 503
    assert res.json()["disabled"] == "locus.experience.enabled"

    res_q = client.post("/experience/query", json={"task_fingerprint": "test"})
    assert res_q.status_code == 503

    res_r = client.post("/experience/render", json={"task_fingerprint": "test"})
    assert res_r.status_code == 503

    res_l = client.get("/experience/list")
    assert res_l.status_code == 503

    # Test off-switch 2: locus.agent_experience_tracking_procedural_memory.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.agent_experience_tracking_procedural_memory.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.agent_experience_tracking_procedural_memory.enabled" else True)

    res2 = client.post("/experience/record", json={"task_summary": "test", "tool_calls": []})
    assert res2.status_code == 503
