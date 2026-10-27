"""
SPEC §21.1-21.3 line 6624: "## Feature §21.1-21.3: Google Calendar, Gmail, Webhooks"
Unit tests for Google Calendar and Webhooks integration (F-0053 / US-83).
Asserts OAuth flow parameters, event synchronization, temporal context formatting,
HMAC-SHA256 webhook signing, swappable provider interface, and modular off-switches.
"""
from __future__ import annotations

from typing import Any
import pytest

import sidecar.config as config
from sidecar.integrations.calendar_sync import (
    BaseCalendarClient,
    CalendarEvent,
    GoogleCalendarSync,
    MockGoogleCalendarClient,
    WebhookManager,
)
from sidecar.providers.calendar import (
    BaseCalendarProvider,
    DefaultCalendarProvider,
)


def test_calendar_oauth_and_event_sync() -> None:
    """SPEC §21.1 line 6636-6654: OAuth URL generation, code exchange, and event fetching."""
    sync = GoogleCalendarSync(client_id="test-client-id", client_secret="test-client-secret")
    
    # 1. OAuth URL
    url = sync.get_auth_url()
    assert "accounts.google.com/o/oauth2" in url
    assert "client_id=test-client-id" in url
    assert "calendar.readonly" in url

    # 2. Exchange Code
    tokens = sync.exchange_auth_code(code="auth-code-12345")
    assert tokens["access_token"] == "mock-access-token-12345"
    assert sync.credentials is not None

    # 3. Fetch Today's Events
    today_events = sync.fetch_today_events()
    assert len(today_events) >= 1
    assert today_events[0].summary == "Locus Sprint Review & Standup"

    # 4. Create Event
    new_ev = sync.create_event(
        summary="Deep Work Focus Slot",
        start_time="2027-08-19T14:00:00Z",
        end_time="2027-08-19T16:00:00Z",
        description="Focused feature decomposition block",
    )
    assert new_ev.summary == "Deep Work Focus Slot"
    assert new_ev.id.startswith("evt-")

    # Verify event appears in list
    all_events = sync.fetch_events()
    ids = [e.id for e in all_events]
    assert new_ev.id in ids


def test_temporal_context_formatting() -> None:
    """SPEC §21.1 Adaptation: Calendar events injected into Context Forge temporal layer."""
    sync = GoogleCalendarSync()
    context = sync.format_temporal_context()
    assert "Today's Schedule:" in context
    assert "Locus Sprint Review & Standup" in context


def test_webhook_hmac_signing_and_dispatch() -> None:
    """SPEC §21.3 lines 6660-6670: Webhook registration and HMAC-SHA256 signature verification."""
    manager = WebhookManager()
    wh = manager.register_webhook(
        url="https://hooks.example.com/locus-event",
        events=["research.completed", "calendar.updated"],
        secret="super-secure-webhook-secret-key",
    )
    assert wh["url"] == "https://hooks.example.com/locus-event"
    assert "super-secure-webhook-secret-key" == wh["secret"]

    # Fire event matching subscription
    dispatches = manager.fire_webhook(
        event_type="research.completed",
        payload={"topic": "Quantum Architecture", "status": "verified"},
    )
    assert len(dispatches) == 1
    d = dispatches[0]
    assert d["webhook_id"] == wh["id"]
    assert len(d["signature"]) == 64  # SHA-256 hex length

    # Unsubscribed event is ignored
    dispatches_ignored = manager.fire_webhook(
        event_type="unrelated.event",
        payload={"dummy": True},
    )
    assert len(dispatches_ignored) == 0


def test_swappable_calendar_provider() -> None:
    """Verify BaseCalendarProvider interface and DefaultCalendarProvider swappability."""
    class CustomCalendarProvider(BaseCalendarProvider):
        @property
        def name(self) -> str:
            return "custom_cal"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def get_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def exchange_code(self, code: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_today_events(self) -> dict[str, Any]:
            return {"status": "ok", "events": []}

        def list_events(self, time_min: str | None = None, time_max: str | None = None) -> dict[str, Any]:
            return {"status": "ok", "events": []}

        def create_event(self, summary: str, start_time: str, end_time: str, description: str = "", location: str = "", attendees: list[str] | None = None) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_temporal_context(self) -> dict[str, Any]:
            return {"status": "ok", "temporal_context": "custom schedule"}

        def register_webhook(self, url: str, events: list[str], secret: str | None = None) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def fire_webhook(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "custom_active": True}

    custom = CustomCalendarProvider()
    assert custom.name == "custom_cal"
    assert custom.get_auth_url()["custom"] is True

    default_prov = DefaultCalendarProvider()
    assert default_prov.name == "default_calendar_provider"
    assert default_prov.get_today_events()["status"] == "ok"


def test_calendar_provider_off_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §21.1: Modular off-switches locus.integrations.calendar.enabled and locus.google_calendar.enabled return 503."""
    provider = DefaultCalendarProvider()

    # Enabled when config has no override
    enabled, switch = provider.is_feature_enabled()
    assert enabled is True

    # Disable via locus.integrations.calendar.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.integrations.calendar.enabled" else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.integrations.calendar.enabled" else True)

    enabled, switch = provider.is_feature_enabled()
    assert enabled is False
    assert switch == "locus.integrations.calendar.enabled"

    res_events = provider.get_today_events()
    assert res_events["status_code"] == 503
    assert res_events["disabled"] == "locus.integrations.calendar.enabled"

    res_temporal = provider.get_temporal_context()
    assert res_temporal["status_code"] == 503

    res_wh = provider.register_webhook("https://hook", ["test"])
    assert res_wh["status_code"] == 503

    # Disable via locus.google_calendar.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.google_calendar.enabled" else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.google_calendar.enabled" else True)

    enabled2, switch2 = provider.is_feature_enabled()
    assert enabled2 is False
    assert switch2 == "locus.google_calendar.enabled"
