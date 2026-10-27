"""
SPEC §21.1-21.3 lines 6624-6678: Integration tests for Google Calendar & Webhook routes (F-0053 / US-83).
Tests FastAPI endpoints under /integrations/calendar/ and /integrations/webhooks/, and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.integrations.calendar_sync import (
    GoogleCalendarSync,
    MockGoogleCalendarClient,
    WebhookManager,
)
from sidecar.providers.calendar import DefaultCalendarProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    sync = GoogleCalendarSync(calendar_client=MockGoogleCalendarClient())
    webhooks = WebhookManager()
    provider = DefaultCalendarProvider(sync=sync, webhooks=webhooks)
    app.state.calendar_provider = provider
    return TestClient(app)


def test_calendar_service_auth_flow(client: TestClient) -> None:
    """SPEC §21.1 line 6636: POST /integrations/calendar/auth-url and /exchange."""
    res_url = client.post("/integrations/calendar/auth-url", json={"redirect_uri": "urn:ietf:wg:oauth:2.0:oob"})
    assert res_url.status_code == 200
    assert "auth_url" in res_url.json()
    assert "accounts.google.com" in res_url.json()["auth_url"]

    res_ex = client.post("/integrations/calendar/exchange", json={"code": "sample-code"})
    assert res_ex.status_code == 200
    assert res_ex.json()["authenticated"] is True
    assert "tokens" in res_ex.json()


def test_calendar_service_events_and_temporal(client: TestClient) -> None:
    """SPEC §21.1 line 6645: GET/POST /integrations/calendar/events and GET /temporal."""
    # List events
    res_list = client.get("/integrations/calendar/events")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["status"] == "ok"
    assert data["count"] >= 1

    # Create event
    res_create = client.post(
        "/integrations/calendar/events",
        json={
            "summary": "Team Sync",
            "start_time": "2027-08-19T10:00:00Z",
            "end_time": "2027-08-19T11:00:00Z",
            "description": "Weekly status update",
        },
    )
    assert res_create.status_code == 200
    assert res_create.json()["event"]["summary"] == "Team Sync"

    # Temporal context endpoint
    res_temporal = client.get("/integrations/calendar/temporal")
    assert res_temporal.status_code == 200
    assert "Today's Schedule:" in res_temporal.json()["temporal_context"]


def test_webhook_service_register_and_fire(client: TestClient) -> None:
    """SPEC §21.3 lines 6660-6670: Webhook registration and firing."""
    res_reg = client.post(
        "/integrations/webhooks/register",
        json={"url": "https://callback.service/webhook", "events": ["event.sync"]},
    )
    assert res_reg.status_code == 200
    assert res_reg.json()["webhook"]["url"] == "https://callback.service/webhook"

    res_fire = client.post(
        "/integrations/webhooks/fire",
        json={"event_type": "event.sync", "payload": {"status": "ok"}},
    )
    assert res_fire.status_code == 200
    assert res_fire.json()["dispatched_count"] == 1
    assert "signature" in res_fire.json()["dispatches"][0]


def test_calendar_service_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §21.1: Modular off-switches return HTTP 503."""
    # Switch 1: locus.integrations.calendar.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.integrations.calendar.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.integrations.calendar.enabled" else True)

    res_status = client.get("/integrations/calendar/status")
    assert res_status.status_code == 503
    assert res_status.json()["disabled"] == "locus.integrations.calendar.enabled"

    res_events = client.get("/integrations/calendar/events")
    assert res_events.status_code == 503

    res_url = client.post("/integrations/calendar/auth-url", json={})
    assert res_url.status_code == 503

    # Switch 2: locus.google_calendar.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.google_calendar.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.google_calendar.enabled" else True)

    res_status2 = client.get("/integrations/calendar/status")
    assert res_status2.status_code == 503
    assert res_status2.json()["disabled"] == "locus.google_calendar.enabled"
