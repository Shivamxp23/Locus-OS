"""
SPEC §16.1-16.2 + §20.1-20.3 lines 6496-6554:
Integration tests for Browser Service (F-0045 / US-78).
"""
from __future__ import annotations

import base64
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_service_browser_navigate(client: TestClient) -> None:
    """SPEC §16.1 line 6499: "page.goto(task.url) RETURN page.content()" """
    res = client.post("/browser/navigate", json={"url": "https://example.com"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["url"] == "https://example.com"
    assert "content" in data


def test_service_browser_interaction(client: TestClient) -> None:
    """SPEC §16.1 line 6499: "Click/type based on identified elements" """
    click_res = client.post("/browser/click", json={"selector": "#btn-test", "x": 100, "y": 200})
    assert click_res.status_code == 200
    assert click_res.json()["status"] == "ok"

    type_res = client.post("/browser/type", json={"selector": "#input-test", "text": "automated text"})
    assert type_res.status_code == 200
    assert type_res.json()["status"] == "ok"


def test_service_browser_screenshot_and_analyze(client: TestClient) -> None:
    """SPEC §16.1 line 6516: "screenshot = page.screenshot() elements = vision_model.identify_elements(screenshot)" """
    shot_res = client.post("/browser/screenshot")
    assert shot_res.status_code == 200
    shot_data = shot_res.json()
    assert shot_data["status"] == "ok"
    assert "screenshot" in shot_data
    assert shot_data["format"] == "png"

    analyze_res = client.post("/browser/analyze", json={"screenshot": shot_data["screenshot"]})
    assert analyze_res.status_code == 200
    analyze_data = analyze_res.json()
    assert analyze_data["status"] == "ok"
    assert "elements" in analyze_data
    assert len(analyze_data["elements"]) > 0


def test_service_browser_automate_task(client: TestClient) -> None:
    """SPEC §16.1 line 6499: "BROWSER AUTOMATION: FUNCTION automate_browser(task)" """
    task_payload = {
        "url": "https://locus.dev/research",
        "actions": [
            {"type": "click", "selector": "#start"},
            {"type": "type", "selector": "#q", "text": "antigravity"},
        ],
        "capture_screenshot": True,
    }
    res = client.post("/browser/automate", json=task_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["url"] == "https://locus.dev/research"
    assert "content" in data
    assert data["screenshot_base64"] is not None


def test_service_browser_providers(client: TestClient) -> None:
    """SPEC §16.1 line 6549: "Provider Interface: BrowserProvider Default: Playwright." """
    res = client.get("/browser/providers")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "playwright" in data["engines"]
    assert "mock" in data["engines"]


def test_service_browser_off_switches(client: TestClient) -> None:
    """SPEC §16.1 line 6549: "Modular off-switch returns HTTP 503 when feature is disabled." """
    config.set("locus.browser.enabled", False)
    try:
        r1 = client.post("/browser/navigate", json={"url": "https://example.com"})
        assert r1.status_code == 503
        assert "disabled" in r1.json()

        r2 = client.post("/browser/screenshot")
        assert r2.status_code == 503

        r3 = client.get("/browser/providers")
        assert r3.status_code == 503
    finally:
        config.set("locus.browser.enabled", True)

    config.set("locus.browser_automation.enabled", False)
    try:
        r4 = client.post("/browser/navigate", json={"url": "https://example.com"})
        assert r4.status_code == 503
    finally:
        config.set("locus.browser_automation.enabled", True)
