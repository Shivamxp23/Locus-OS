"""
SPEC §25.10 lines 4759-4777: Integration tests for Exhaustion Predictor routes (F-0112 / US-88).
Tests FastAPI endpoints under /exhaustion/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.exhaustion import ExhaustionPredictor
from sidecar.providers.exhaustion import DefaultExhaustionPredictorProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    predictor = ExhaustionPredictor()
    provider = DefaultExhaustionPredictorProvider(predictor=predictor)
    app.state.exhaustion_predictor_provider = provider
    return TestClient(app)


def test_exhaustion_service_predict_endpoint_high_exhaustion(client: TestClient) -> None:
    """SPEC §25.10: POST /exhaustion/predict endpoint predicting SURVIVAL recommendation."""
    payload = {
        "metrics": {
            "consecutive_high_d_tasks": 4,
            "sleep_deficit_hours": 2.5,
            "stress_trend": 2.0,
            "current_dcs": 6.5,
        }
    }
    res = client.post("/exhaustion/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    prediction = data["prediction"]
    assert prediction["predicted_dcs_drop"] > 2.0
    assert prediction["preemptive_survival_recommended"] is True
    assert prediction["recommended_mode"] == "SURVIVAL"


def test_exhaustion_service_predict_endpoint_stable(client: TestClient) -> None:
    """SPEC §25.10: POST /exhaustion/predict endpoint predicting stable state."""
    payload = {
        "metrics": {
            "consecutive_high_d_tasks": 1,
            "sleep_deficit_hours": 0.0,
            "stress_trend": 0.0,
            "current_dcs": 7.5,
        }
    }
    res = client.post("/exhaustion/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    prediction = data["prediction"]
    assert prediction["predicted_dcs_drop"] <= 2.0
    assert prediction["preemptive_survival_recommended"] is False


def test_exhaustion_service_status_endpoint(client: TestClient) -> None:
    """SPEC §25.10: GET /exhaustion/status diagnostic route."""
    res = client.get("/exhaustion/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "default_exhaustion_predictor_provider"
    assert data["threshold"] == 2.0


def test_exhaustion_service_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify HTTP 503 when locus.exhaustion_predictor.enabled or locus.life_os.exhaustion.enabled is disabled."""
    # Master switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.exhaustion_predictor.enabled" else True)
    res = client.get("/exhaustion/status")
    assert res.status_code == 503
    assert res.json()["disabled"] == "locus.exhaustion_predictor.enabled"

    # Life OS switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.life_os.exhaustion.enabled" else True)
    res2 = client.post("/exhaustion/predict", json={"metrics": {}})
    assert res2.status_code == 503
    assert res2.json()["disabled"] == "locus.life_os.exhaustion.enabled"
