"""
Integration tests for State Engine FastAPI endpoints (SPEC §2.4 / F-0093 / US-33).
Asserts endpoints `/state/current`, `/state/calculate`, `/state/reset`, and 503 off-switch.
"""
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.providers.state_engine import (
    BaseStateEngineProvider,
    CheckInRecord,
    CurrentState,
    OperatingMode,
)
from sidecar.service import create_app
from sidecar.state_engine import StateEngineProvider


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_state_current_endpoint(client):
    """SPEC §2.4 line 1737: "STEP 5: Update Redis CURRENT_STATE Cache"."""
    res = client.get("/state/current")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "state" in data
    state = data["state"]
    assert "dcs" in state
    assert "operating_mode" in state
    assert state["operating_mode"] in [m.value for m in OperatingMode]


def test_state_calculate_endpoint(client):
    """SPEC §2.4 line 1720: "STEP 3: Canonical DCS Calculation"."""
    res = client.post(
        "/state/calculate",
        json={
            "energy": 9.0,
            "mood": 9.0,
            "sleep": 9.0,
            "stress": 1.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    state = data["state"]
    assert state["dcs"] == 8.1
    assert state["operating_mode"] == OperatingMode.PEAK.value

    # Verify subsequent GET returns the updated snapshot
    cur_res = client.get("/state/current")
    assert cur_res.status_code == 200
    assert cur_res.json()["state"]["dcs"] == 8.1


def test_state_reset_endpoint(client):
    """SPEC §2.4 line 1714: "STEP 2: Last Check-in Read"."""
    res = client.post("/state/reset")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_state_engine_503_off_switch(client, monkeypatch):
    """SPEC §2.4 line 1748: "Integration: Triggered by PostgreSQL LISTEN channel on every event write. Read by Context Forge & Inner Loop."."""
    monkeypatch.setattr(config, "get", lambda k, d=None: False if "state_engine" in k else True)

    res_get = client.get("/state/current")
    assert res_get.status_code == 503
    assert res_get.json()["disabled"] == "locus.state_engine.enabled"

    res_calc = client.post("/state/calculate", json={"energy": 5, "mood": 5, "sleep": 5, "stress": 2})
    assert res_calc.status_code == 503

    res_reset = client.post("/state/reset")
    assert res_reset.status_code == 503
