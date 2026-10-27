"""
Integration tests for Notifications FastAPI endpoints (F-0067 / US-105).
SPEC §29.4 lines 7531-7612.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from sidecar import config
from sidecar.service import create_app


@pytest.fixture
def client():
    config.set("locus.notifications.enabled", True)
    config.set("locus.state.dcs", 3.8)
    config.set("notifications.quiet_hours", {"start_hour": 0, "start_minute": 0, "end_hour": 0, "end_minute": 0})
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config.set("locus.notifications.enabled", True)
    config.set("locus.state.dcs", None)
    config.set("notifications.quiet_hours", None)


def test_notifications_send_endpoint(client: TestClient):
    """SPEC §29.4 line 7545: Send notification via FastAPI route."""
    res = client.post(
        "/notifications/send",
        json={"message": "System operational", "priority": "HIGH"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["delivered"] is True
    assert data["priority"] == "HIGH"
    assert len(data["channels"]) > 0


def test_notifications_queue_endpoint(client: TestClient):
    """SPEC §29.4 line 7570: Send LOW notification and check queue endpoint."""
    res_send = client.post(
        "/notifications/send",
        json={"message": "Low priority observation", "priority": "LOW"},
    )
    assert res_send.status_code == 200

    res_q = client.get("/notifications/queue")
    assert res_q.status_code == 200
    q_data = res_q.json()
    assert q_data["status"] == "ok"
    assert q_data["count"] >= 1
    assert any("Low priority" in n["message"] for n in q_data["notifications"])


def test_notifications_process_queue_endpoint(client: TestClient):
    """SPEC §29.4 line 7576: Process buffered queue."""
    client.post(
        "/notifications/send",
        json={"message": "Queue item to digest", "priority": "LOW"},
    )
    res_proc = client.post("/notifications/process_queue")
    assert res_proc.status_code == 200
    p_data = res_proc.json()
    assert p_data["status"] == "ok"
    assert p_data["processed"] >= 1


def test_notifications_status_endpoint(client: TestClient):
    """SPEC §29.4 line 7598: Notifications diagnostic status endpoint."""
    res = client.get("/notifications/status")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "default_notifications"
    assert data["feature_enabled"] is True
    assert "dispatcher" in data


def test_notifications_off_switch_503(client: TestClient):
    """SPEC §29.4 line 7598: Modular off-switch returns HTTP 503."""
    config.set("locus.notifications.enabled", False)

    res_send = client.post("/notifications/send", json={"message": "hi"})
    assert res_send.status_code == 503
    assert "disabled" in res_send.json()["detail"].lower()

    res_q = client.get("/notifications/queue")
    assert res_q.status_code == 503

    res_proc = client.post("/notifications/process_queue")
    assert res_proc.status_code == 503

    res_stat = client.get("/notifications/status")
    assert res_stat.status_code == 503
