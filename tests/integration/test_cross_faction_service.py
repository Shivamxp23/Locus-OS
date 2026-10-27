"""
SPEC §25.15 lines 4910-4922: Integration tests for Cross-Faction Efficiency endpoints (F-0116 / US-93).
Tests FastAPI endpoints under /cross-faction/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.cross_faction import CrossFactionAllocator
from sidecar.providers.cross_faction import DefaultCrossFactionEfficiencyProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    allocator = CrossFactionAllocator()
    provider = DefaultCrossFactionEfficiencyProvider(allocator=allocator)
    app.state.cross_faction_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.cross_faction_efficiency.enabled", True)
    config.set("locus.life_os.cross_faction.enabled", True)
    yield
    config.set("locus.cross_faction_efficiency.enabled", True)
    config.set("locus.life_os.cross_faction.enabled", True)


def test_cross_faction_service_split_endpoint(client: TestClient) -> None:
    """SPEC §25.15: POST /cross-faction/split."""
    payload = {
        "task_id": "test-split-1",
        "duration": 100.0,
        "primary_faction": "Craft",
        "secondary_factions": ["Leverage"],
    }
    res = client.post("/cross-faction/split", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["task_id"] == "test-split-1"
    assert data["allocations"]["Craft"] == 70.0
    assert data["allocations"]["Leverage"] == 30.0
    assert sum(data["allocations"].values()) == 100.0


def test_cross_faction_service_aggregate_endpoint(client: TestClient) -> None:
    """SPEC §25.15: POST /cross-faction/aggregate."""
    payload = {
        "tasks": [
            {"id": "t1", "duration": 50.0, "primary_faction": "Craft"},
            {"id": "t2", "duration": 100.0, "primary_faction": "Health", "secondary_factions": ["Expression"]},
        ]
    }
    res = client.post("/cross-faction/aggregate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["total_duration"] == 150.0
    assert data["task_count"] == 2
    assert data["cross_faction_task_count"] == 1
    assert data["faction_totals"]["Craft"] == 50.0
    assert data["faction_totals"]["Health"] == 70.0
    assert data["faction_totals"]["Expression"] == 30.0


def test_cross_faction_service_status_endpoint(client: TestClient) -> None:
    """SPEC §25.15: GET /cross-faction/status."""
    res = client.get("/cross-faction/status")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "default_cross_faction_efficiency_provider"
    assert data["master_enabled"] is True
    assert data["subsystem_enabled"] is True


def test_cross_faction_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §25.15: Modular off-switches returning HTTP 503."""
    config.set("locus.cross_faction_efficiency.enabled", False)

    res_split = client.post("/cross-faction/split", json={"task_id": "t1", "duration": 60.0})
    assert res_split.status_code == 503
    assert res_split.json()["disabled"] == "locus.cross_faction_efficiency.enabled"

    res_agg = client.post("/cross-faction/aggregate", json={"tasks": []})
    assert res_agg.status_code == 503

    res_status = client.get("/cross-faction/status")
    assert res_status.status_code == 503
