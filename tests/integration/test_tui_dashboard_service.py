"""
SPEC §7.1-7.9: Integration tests for TUI Dashboard Service Endpoints (F-0030 / US-61).
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from sidecar.service import create_app
import sidecar.config as config


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_service_tui_dashboard_config(client: TestClient) -> None:
    """SPEC §7.1: Verify GET /display/dashboard/config returns enabled status and provider name."""
    res = client.get("/display/dashboard/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "default_tui_dashboard"


def test_service_tui_dashboard_state_and_format(client: TestClient) -> None:
    """SPEC §7.1 lines 5840-5858: Query GET/POST /display/dashboard/state and POST /display/dashboard/format."""
    # 1. GET state
    res = client.get("/display/dashboard/state")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "dcs" in data["state"]
    assert "footer_preview" in data

    # 2. POST state update
    update_payload = {
        "state": {
            "dcs": 7.8,
            "mode": "DEEP WORK",
            "active_faction": "Craft",
            "neo4j_nodes": 150,
            "neo4j_edges": 300,
            "livesync_status": "OK",
            "sidecar_latency_ms": 4,
            "model_name": "claude-3-7-sonnet",
        }
    }
    res2 = client.post("/display/dashboard/state", json=update_payload)
    assert res2.status_code == 200
    assert res2.json()["state"]["mode"] == "DEEP WORK"
    assert res2.json()["state"]["active_faction"] == "Craft"

    # 3. POST format
    format_payload = {
        "state": update_payload["state"],
        "width": 80,
    }
    res3 = client.post("/display/dashboard/format", json=format_payload)
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["status"] == "ok"
    assert "DCS:7.8" in data3["footer"]
    assert "[DEEP WORK]" in data3["footer"]
    assert "LOCUS OS DASHBOARD" in data3["dashboard"]


def test_service_tui_dashboard_off_switch_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §7.1 line 5808: Off-switch returns HTTP 503 for all /display/dashboard/ routes."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "tui_dashboard" in key else default)

    res_cfg = client.get("/display/dashboard/config")
    assert res_cfg.status_code == 503
    assert res_cfg.json()["disabled"] == "locus.tui_dashboard.enabled"

    res_get = client.get("/display/dashboard/state")
    assert res_get.status_code == 503

    res_post = client.post("/display/dashboard/state", json={})
    assert res_post.status_code == 503

    res_fmt = client.post("/display/dashboard/format", json={})
    assert res_fmt.status_code == 503
