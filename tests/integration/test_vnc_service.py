"""
SPEC §20.3 lines 6555-6621: Integration tests for VNC Remote Desktop Control routes (F-0052 / US-82).
Tests FastAPI endpoints under /vnc/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.desktop.vnc_client import (
    BoundingBox,
    MockRFBProtocolClient,
    VNCDesktopController,
)
from sidecar.providers.vnc import DefaultVNCProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    boundary = BoundingBox(min_x=0, min_y=0, max_x=1920, max_y=1080)
    controller = VNCDesktopController(
        host="127.0.0.1",
        port=5900,
        rfb_client=MockRFBProtocolClient(),
        safety_boundary=boundary,
    )
    provider = DefaultVNCProvider(controller=controller)
    app.state.vnc_provider = provider
    return TestClient(app)


def test_vnc_service_connect_and_status(client: TestClient) -> None:
    """SPEC §20.3 line 6578: POST /vnc/connect and GET /vnc/status."""
    res_conn = client.post("/vnc/connect", json={"host": "127.0.0.1", "port": 5900, "password": "pass"})
    assert res_conn.status_code == 200
    assert res_conn.json()["connected"] is True

    res_status = client.get("/vnc/status")
    assert res_status.status_code == 200
    data = res_status.json()
    assert data["connected"] is True
    assert data["port"] == 5900
    assert "safety_boundary" in data


def test_vnc_service_capture_framebuffer(client: TestClient) -> None:
    """SPEC §20.3 line 6583: GET /vnc/capture."""
    client.post("/vnc/connect", json={})
    res_cap = client.get("/vnc/capture")
    assert res_cap.status_code == 200
    data = res_cap.json()
    assert data["format"] == "png"
    assert "data" in data
    assert data["width"] == 1920
    assert data["height"] == 1080


def test_vnc_service_click_and_safety_gate(client: TestClient) -> None:
    """SPEC §20.3 line 6587-6590: POST /vnc/click with safety gate enforcement."""
    client.post("/vnc/connect", json={})

    # Allowed click
    res_ok = client.post("/vnc/click", json={"x": 500, "y": 400, "button": "left"})
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "ok"
    assert res_ok.json()["coordinates"] == {"x": 500, "y": 400}

    # Out of bounds click -> 403 Security violation
    res_bad = client.post("/vnc/click", json={"x": 3000, "y": 5000})
    assert res_bad.status_code == 403
    assert res_bad.json()["error"] == "security_violation"

    # Missing coordinates -> 400 Bad Request
    res_invalid = client.post("/vnc/click", json={"button": "left"})
    assert res_invalid.status_code == 400


def test_vnc_service_type_and_disconnect(client: TestClient) -> None:
    """SPEC §20.3 line 6605: POST /vnc/type and POST /vnc/disconnect."""
    client.post("/vnc/connect", json={})

    res_type = client.post("/vnc/type", json={"text": "ls -la\n"})
    assert res_type.status_code == 200
    assert res_type.json()["characters_count"] == 7

    res_dis = client.post("/vnc/disconnect")
    assert res_dis.status_code == 200
    assert res_dis.json()["connected"] is False


def test_vnc_service_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §20.3 line 6617: Off-switches return HTTP 503."""
    # Switch 1: locus.vnc.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.vnc.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.vnc.enabled" else True)

    res_status = client.get("/vnc/status")
    assert res_status.status_code == 503
    assert res_status.json()["disabled"] == "locus.vnc.enabled"

    res_cap = client.get("/vnc/capture")
    assert res_cap.status_code == 503

    res_conn = client.post("/vnc/connect", json={})
    assert res_conn.status_code == 503

    # Switch 2: locus.tools.vnc.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.tools.vnc.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.tools.vnc.enabled" else True)

    res_status2 = client.get("/vnc/status")
    assert res_status2.status_code == 503
    assert res_status2.json()["disabled"] == "locus.tools.vnc.enabled"
