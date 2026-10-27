"""
SPEC §25.16 lines 4923-4936: Integration tests for Four-Level Emergency Protocol endpoints (F-0117 / US-94).
Tests FastAPI endpoints under /emergency-protocol/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.emergency_protocol import FourLevelEmergencyProtocol
from sidecar.providers.emergency_protocol import DefaultFourLevelEmergencyProtocolProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    protocol = FourLevelEmergencyProtocol()
    provider = DefaultFourLevelEmergencyProtocolProvider(protocol=protocol)
    app.state.emergency_protocol_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.four_level_emergency_protocol.enabled", True)
    config.set("locus.life_os.emergency_protocol.enabled", True)
    yield
    config.set("locus.four_level_emergency_protocol.enabled", True)
    config.set("locus.life_os.emergency_protocol.enabled", True)


def test_emergency_protocol_service_evaluate_endpoint(client: TestClient) -> None:
    """SPEC §25.16: POST /emergency-protocol/evaluate."""
    payload = {
        "disruption_hours": 1.5,
        "disruption_days": 0,
        "is_life_event": False,
        "trigger_reason": "Delayed flight",
    }
    res = client.post("/emergency-protocol/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["level"] == 1
    assert data["level_name"] == "LEVEL_1_MINOR"
    assert data["mode_override"] == "NORMAL"
    assert data["overrides_applied"] is True


def test_emergency_protocol_service_activate_and_deactivate_endpoints(client: TestClient) -> None:
    """SPEC §25.16: POST /emergency-protocol/activate and POST /emergency-protocol/deactivate."""
    res_act = client.post(
        "/emergency-protocol/activate",
        json={"level": 3, "reason": "Family emergency"},
    )
    assert res_act.status_code == 200
    data_act = res_act.json()
    assert data_act["success"] is True
    assert data_act["level"] == 3
    assert data_act["mode_override"] == "SURVIVAL"
    assert data_act["redistribution_window_days"] == 14

    res_deact = client.post("/emergency-protocol/deactivate")
    assert res_deact.status_code == 200
    data_deact = res_deact.json()
    assert data_deact["success"] is True
    assert data_deact["previous_level"] == 3
    assert data_deact["require_weekly_review"] is True
    assert data_deact["redistribution_window_days"] == 14


def test_emergency_protocol_service_apply_overrides_endpoint(client: TestClient) -> None:
    """SPEC §25.16: POST /emergency-protocol/apply-overrides."""
    payload = {
        "level": 4,
        "tasks": [
            {"id": "t1", "title": "Art work", "faction": "Expression/Explore", "tws": 9.0},
            {"id": "t2", "title": "Sleep", "faction": "Health/Stability", "tws": 5.0},
            {"id": "t3", "title": "Study", "faction": "Craft/Skills", "tws": 7.0},
        ],
    }
    res = client.post("/emergency-protocol/apply-overrides", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "CRISIS"
    assert len(data["tasks_suspended"]) == 1
    assert data["tasks_suspended"][0]["id"] == "t1"
    retained_factions = [t["faction"] for t in data["tasks_retained"]]
    assert retained_factions == ["Health/Stability", "Craft/Skills"]


def test_emergency_protocol_service_status_endpoint(client: TestClient) -> None:
    """SPEC §25.16: GET /emergency-protocol/status."""
    res = client.get("/emergency-protocol/status")
    assert res.status_code == 200
    data = res.json()
    assert data["feature_enabled"] is True
    assert data["subsystem_enabled"] is True
    assert "Health/Stability" in data["crisis_hierarchy"]


def test_emergency_protocol_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §25.16: Modular off-switches returning HTTP 503."""
    config.set("locus.four_level_emergency_protocol.enabled", False)

    res_eval = client.post("/emergency-protocol/evaluate", json={"disruption_hours": 1.0})
    assert res_eval.status_code == 503
    assert res_eval.json()["disabled"] == "locus.four_level_emergency_protocol.enabled"

    res_act = client.post("/emergency-protocol/activate", json={"level": 2})
    assert res_act.status_code == 503

    res_deact = client.post("/emergency-protocol/deactivate")
    assert res_deact.status_code == 503

    res_ov = client.post("/emergency-protocol/apply-overrides", json={"tasks": []})
    assert res_ov.status_code == 503

    res_status = client.get("/emergency-protocol/status")
    assert res_status.status_code == 503
