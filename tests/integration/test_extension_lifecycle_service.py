"""
Integration tests for Extension Lifecycle FastAPI endpoints (SPEC §1.5, F-0005).
Asserts event listing, hook inspection, event dispatching, extension toggling,
and the modular 503 off-switch.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_list_lifecycle_events_endpoint(client):
    """SPEC §1.5 line 514: "EXTENSION LIFECYCLE (25+ events):"
    Asserts GET /extensions/events returns 200 with 25+ canonical events.
    """
    res = client.get("/extensions/events")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["count"] >= 25
    assert "session_start" in data["events"]
    assert "turn_start" in data["events"]
    assert "session_shutdown" in data["events"]


def test_list_extensions_hooks_endpoint(client):
    """SPEC §1.5 line 528: "Key Locus hooks into this:"
    Asserts GET /extensions/list returns registered hooks including canonical Locus hooks.
    """
    res = client.get("/extensions/list")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["count"] >= 6
    events = [h["event"] for h in data["hooks"]]
    assert "session_start" in events
    assert "tool_execution_start" in events


def test_dispatch_lifecycle_event_endpoint(client):
    """SPEC §1.5 line 529: "- session_start: initialize all providers, load state"
    Asserts POST /extensions/dispatch executes registered hooks and returns dispatch results.
    """
    res = client.post(
        "/extensions/dispatch",
        json={"event": "session_start", "payload": {"session_id": "test-123"}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    result = data["result"]
    assert result["event"] == "session_start"
    assert result["hooks_executed"] >= 1
    assert result["modified_payload"].get("locus_session_initialized") is True


def test_toggle_extension_endpoint(client):
    """SPEC §1.5 line 540: "Swappable / off state: each Locus extension can be disabled individually via config. Off → that extension's hooks don't fire; Pi's core event loop continues unchanged."
    Asserts POST /extensions/toggle changes individual extension state.
    """
    res = client.post(
        "/extensions/toggle",
        json={"extension_id": "test_plugin", "enabled": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["extension_id"] == "test_plugin"
    assert data["enabled"] is False

    # Toggle back on
    res2 = client.post(
        "/extensions/toggle",
        json={"extension_id": "test_plugin", "enabled": True},
    )
    assert res2.status_code == 200
    assert res2.json()["enabled"] is True


def test_extension_lifecycle_service_off_switch_503(monkeypatch):
    """SPEC §1.5 line 540: "Swappable / off state: each Locus extension can be disabled individually via config. Off → that extension's hooks don't fire; Pi's core event loop continues unchanged."
    Asserts endpoints return 503 when locus.extension_lifecycle.enabled is set to False.
    """
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "extension_lifecycle" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "extension_lifecycle" in key else True)
    app = create_app()
    client = TestClient(app)

    r1 = client.get("/extensions/events")
    assert r1.status_code == 503
    assert r1.json() == {"disabled": "locus.extension_lifecycle.enabled"}

    r2 = client.get("/extensions/list")
    assert r2.status_code == 503
    assert r2.json() == {"disabled": "locus.extension_lifecycle.enabled"}

    r3 = client.post("/extensions/dispatch", json={"event": "turn_start"})
    assert r3.status_code == 503
    assert r3.json() == {"disabled": "locus.extension_lifecycle.enabled"}

    r4 = client.post("/extensions/toggle", json={"extension_id": "core", "enabled": False})
    assert r4.status_code == 503
    assert r4.json() == {"disabled": "locus.extension_lifecycle.enabled"}
