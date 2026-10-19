"""
SPEC §25.1-§25.4 / §03 line 35: Life OS Service Integration Tests.
Tests HTTP endpoints on the sidecar service for TWS, DCS, Operating Modes,
and modular 503 off-switch behavior.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from sidecar import config
from sidecar.life_os import LifeOSProvider
from sidecar.registry import ProviderRegistry
from sidecar.service import create_app


def test_life_os_service_endpoints():
    """SPEC §25.1-§25.4 line 4557: "Life OS Service endpoints compute TWS, DCS, and Operating Modes"."""
    registry = ProviderRegistry()
    registry.register("life_os", "default_life_os", LifeOSProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    # 1. TWS calculation endpoint
    tws_res = client.post(
        "/life_os/tws",
        json={
            "priority": 8,
            "urgency": 7,
            "difficulty": 6,
            "faction_lag_hours": 4.0,
            "scale": "daily",
        },
    )
    assert tws_res.status_code == 200
    tws_data = tws_res.json()
    assert tws_data["status"] == "ok"
    # Base TWS: (8 * 0.4) + (7 * 0.4) + (6 * 0.2) = 3.2 + 2.8 + 1.2 = 7.2
    # Lag > 3h -> lag_bonus = 2.0 -> final_tws = 9.2
    assert tws_data["result"]["base_tws"] == 7.2
    assert tws_data["result"]["lag_bonus"] == 2.0
    assert tws_data["result"]["final_tws"] == 9.2
    assert tws_data["result"]["scale"] == "daily"

    # 2. DCS calculation endpoint
    dcs_res = client.post(
        "/life_os/dcs",
        json={
            "energy": 9,
            "mood": 8,
            "sleep": 8,
            "stress": 3,
            "days_since_last_checkin": 0,
        },
    )
    assert dcs_res.status_code == 200
    dcs_data = dcs_res.json()
    assert dcs_data["status"] == "ok"
    # ((9+8+8)/3) * (1 - 3/20) = 8.333 * 0.85 = 7.08
    assert dcs_data["result"]["dcs"] == 7.08
    assert dcs_data["result"]["mode"] == "DEEP WORK"
    assert dcs_data["result"]["staleness_applied"] is False

    # 3. Mode resolution endpoint
    mode_res = client.get("/life_os/mode?dcs=8.5")
    assert mode_res.status_code == 200
    mode_data = mode_res.json()
    assert mode_data["status"] == "ok"
    assert mode_data["mode"] == "PEAK"
    assert mode_data["constraints"]["max_difficulty"] == 10


def test_life_os_service_modular_off_switch(monkeypatch):
    """SPEC §03 line 35: "a disabled feature's HTTP routes answer 503 with {'disabled': '<config key>'}"."""
    monkeypatch.setattr(config, "get", lambda k, d=None: False if k == "locus.life_os.enabled" else d)

    registry = ProviderRegistry()
    registry.register("life_os", "default_life_os", LifeOSProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    # All /life_os/* endpoints must return 503
    tws_res = client.post("/life_os/tws", json={"priority": 5, "urgency": 5, "difficulty": 5})
    assert tws_res.status_code == 503
    assert tws_res.json() == {"disabled": "locus.life_os.enabled"}

    dcs_res = client.post("/life_os/dcs", json={"energy": 5, "mood": 5, "sleep": 5, "stress": 5})
    assert dcs_res.status_code == 503
    assert dcs_res.json() == {"disabled": "locus.life_os.enabled"}

    mode_res = client.get("/life_os/mode?dcs=5.0")
    assert mode_res.status_code == 503
    assert mode_res.json() == {"disabled": "locus.life_os.enabled"}
