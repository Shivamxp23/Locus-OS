"""
SPEC §25.11 lines 4778-4800: Integration tests for Weekly Faction Rebalance routes (F-0113 / US-89).
Tests FastAPI endpoints under /rebalance/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.rebalance import WeeklyFactionRebalancer
from sidecar.providers.rebalance import DefaultWeeklyFactionRebalanceProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    rebalancer = WeeklyFactionRebalancer()
    provider = DefaultWeeklyFactionRebalanceProvider(rebalancer=rebalancer)
    app.state.rebalance_provider = provider
    return TestClient(app)


def test_rebalance_service_calculate_endpoint(client: TestClient) -> None:
    """SPEC §25.11 line 4787: POST /rebalance/calculate endpoint performing weekly deficit rebalance."""
    payload = {
        "actual_hours": {
            "Health/Stability": 10.0,
            "Leverage/Money": 10.0,
            "Craft/Skills": 60.0,
            "Expression/Explore": 20.0,
        },
        "correction_factor": 1.0,
    }
    res = client.post("/rebalance/calculate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    reb = data["rebalance"]
    assert reb["total_hours"] == 100.0
    assert "Health/Stability" in reb["adjusted_weights"]
    assert "Craft/Skills" in reb["adjusted_weights"]
    # Craft was 60% vs 30% target -> deficit is negative, weight decreases
    assert reb["deficits"]["Craft/Skills"] < 0
    # Health was 10% vs 25% target -> deficit is positive, weight increases
    assert reb["deficits"]["Health/Stability"] > 0


def test_rebalance_service_weights_and_duration_endpoints(client: TestClient) -> None:
    """SPEC §25.11 line 4792: Active weights query and duration logging endpoints."""
    # Query weights
    res_w = client.get("/rebalance/weights")
    assert res_w.status_code == 200
    data_w = res_w.json()
    assert data_w["status"] == "ok"
    assert "Health/Stability" in data_w["weights"]

    # Log duration
    res_d = client.post("/rebalance/duration", json={"faction": "Health", "duration_hours": 3.5})
    assert res_d.status_code == 200
    data_d = res_d.json()
    assert data_d["status"] == "ok"
    assert data_d["durations"]["Health/Stability"] >= 3.5


def test_rebalance_service_status_endpoint(client: TestClient) -> None:
    """SPEC §25.11 line 4796: GET /rebalance/status diagnostic endpoint."""
    res = client.get("/rebalance/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "default_weekly_faction_rebalance_provider"
    assert data["enabled"] is True


def test_rebalance_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §25.11 line 4797: Modular off-switches returning HTTP 503."""
    config.set("locus.weekly_faction_rebalance.enabled", False)
    try:
        res = client.post("/rebalance/calculate", json={})
        assert res.status_code == 503
        data = res.json()
        assert "disabled" in data

        res_w = client.get("/rebalance/weights")
        assert res_w.status_code == 503

        res_s = client.get("/rebalance/status")
        assert res_s.status_code == 503
    finally:
        config.set("locus.weekly_faction_rebalance.enabled", True)

    config.set("locus.life_os.rebalance.enabled", False)
    try:
        res2 = client.post("/rebalance/calculate", json={})
        assert res2.status_code == 503
    finally:
        config.set("locus.life_os.rebalance.enabled", True)
