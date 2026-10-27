"""
SPEC §16.1-16.2 + §20.1-20.3 lines 6496-6554:
Integration tests for Desktop Screen & Computer Use Service (F-0051 / US-79).
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


def test_service_screen_capture(client: TestClient) -> None:
    """SPEC §16.1 line 6535: "RETURN native.capture_screen()" """
    res = client.post("/screen/capture", json={"display_id": 0})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "image_base64" in data
    assert data["width"] > 0
    assert data["height"] > 0
    assert data["format"] == "png"


def test_service_screen_control(client: TestClient) -> None:
    """SPEC §16.1 lines 6529-6537: "control_desktop(action): IF action.type == 'click': native.mouse_click" """
    click_res = client.post("/screen/control", json={"action_type": "click", "x": 100, "y": 200})
    assert click_res.status_code == 200
    data = click_res.json()
    assert data["status"] == "ok"
    assert data["success"] is True
    assert data["action_type"] == "click"

    type_res = client.post("/screen/control", json={"action_type": "type", "text": "automated input"})
    assert type_res.status_code == 200
    t_data = type_res.json()
    assert t_data["status"] == "ok"
    assert t_data["success"] is True

    focus_res = client.post("/screen/control", json={"action_type": "window_focus", "window_title": "Terminal"})
    assert focus_res.status_code == 200
    f_data = focus_res.json()
    assert f_data["status"] == "ok"
    assert f_data["success"] is True


def test_service_screen_analyze(client: TestClient) -> None:
    """SPEC §16.1 lines 6516-6526: "FUNCTION analyze_screen(screenshot): elements = vision_model.analyze(screenshot)" """
    res = client.post("/screen/analyze", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "elements" in data
    assert len(data["elements"]) > 0
    first_elem = data["elements"][0]
    assert "element_id" in first_elem
    assert "element_type" in first_elem
    assert "bbox" in first_elem
    assert "center" in first_elem


def test_service_screen_execute_workflow(client: TestClient) -> None:
    """SPEC §16.1 line 6528: "DESKTOP COMPANION (from OpenHuman desktop_companion/): FUNCTION control_desktop(action)" """
    workflow_payload = {
        "actions": [
            {"action_type": "click", "x": 160, "y": 70},
            {"action_type": "type", "text": "research query"},
            {"action_type": "window_focus", "window_title": "Browser"},
        ]
    }
    res = client.post("/screen/execute", json=workflow_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["count"] == 3
    assert len(data["results"]) == 3
    assert all(r["success"] for r in data["results"])


def test_service_screen_status(client: TestClient) -> None:
    """SPEC §16.1 line 6549: "Component: locus/providers/browser/ Provider Interface: BrowserProvider" """
    res = client.get("/screen/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "available" in data
    assert "capture_backend" in data
    assert "controller_backend" in data


def test_service_screen_off_switches(client: TestClient) -> None:
    """SPEC §16.1 line 6549: "Modular off-switch returns HTTP 503 when feature is disabled." """
    config.set("locus.screen.enabled", False)
    try:
        r1 = client.post("/screen/capture", json={})
        assert r1.status_code == 503
        assert "disabled" in r1.json()

        r2 = client.post("/screen/control", json={"action_type": "click"})
        assert r2.status_code == 503

        r3 = client.get("/screen/status")
        assert r3.status_code == 503
    finally:
        config.set("locus.screen.enabled", True)

    config.set("locus.desktop_control.enabled", False)
    try:
        r4 = client.post("/screen/control", json={"action_type": "click"})
        assert r4.status_code == 503
    finally:
        config.set("locus.desktop_control.enabled", True)

    config.set("locus.computer_use.enabled", False)
    try:
        r5 = client.post("/screen/execute", json={"actions": []})
        assert r5.status_code == 503
    finally:
        config.set("locus.computer_use.enabled", True)
