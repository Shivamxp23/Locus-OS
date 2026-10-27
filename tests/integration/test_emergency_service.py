"""
SPEC §25.9 lines 4740-4758: Integration tests for Emergency Task Injection routes (F-0111 / US-87).
Tests FastAPI endpoints under /emergency/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.emergency import EmergencyTaskInjector
from sidecar.providers.emergency import DefaultEmergencyTaskProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    injector = EmergencyTaskInjector()
    provider = DefaultEmergencyTaskProvider(injector=injector)
    app.state.emergency_task_provider = provider
    return TestClient(app)


def test_emergency_service_prioritize_endpoint(client: TestClient) -> None:
    """SPEC §25.9: POST /emergency/prioritize endpoint."""
    payload = {
        "tasks": [
            {"id": "t-craft", "title": "Craft normal", "faction": "Craft", "tws": 9.0, "is_emergency": False},
            {"id": "t-health", "title": "Health crisis", "faction": "Health", "tws": 3.0, "is_emergency": True},
            {"id": "t-leverage", "title": "Leverage crisis", "faction": "Leverage", "tws": 5.0, "is_emergency": True},
        ],
        "bypass_tws": True,
    }
    res = client.post("/emergency/prioritize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["emergency_tasks_count"] == 2
    # Crisis order: Health (0) -> Leverage (1) -> Craft normal (follows)
    task_ids = [t["id"] for t in data["tasks"]]
    assert task_ids == ["t-health", "t-leverage", "t-craft"]


def test_emergency_service_inject_endpoint(client: TestClient) -> None:
    """SPEC §25.9: POST /emergency/inject endpoint."""
    payload = {
        "timeline": [
            {"block_type": "deep", "duration_minutes": 90, "task_id": "normal-1"},
        ],
        "task": {
            "id": "urgent-incident",
            "title": "Severe Security Outage",
            "faction": "Health",
            "estimated_minutes": 45,
        },
        "at_index": 0,
    }
    res = client.post("/emergency/inject", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["injected_task_id"] == "urgent-incident"
    assert data["timeline_length"] == 2
    assert data["timeline"][0]["task_id"] == "urgent-incident"


def test_emergency_service_status_endpoint(client: TestClient) -> None:
    """SPEC §25.9: GET /emergency/status diagnostic route."""
    res = client.get("/emergency/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "default_emergency_task_provider"
    assert "Health/Stability" in data["crisis_hierarchy"]


def test_emergency_service_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify HTTP 503 when locus.emergency_task_injection.enabled or locus.life_os.emergency.enabled is disabled."""
    # Master switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.emergency_task_injection.enabled" else True)
    res = client.get("/emergency/status")
    assert res.status_code == 503
    assert res.json()["disabled"] == "locus.emergency_task_injection.enabled"

    # Life OS switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.life_os.emergency.enabled" else True)
    res2 = client.post("/emergency/prioritize", json={"tasks": []})
    assert res2.status_code == 503
    assert res2.json()["disabled"] == "locus.life_os.emergency.enabled"
