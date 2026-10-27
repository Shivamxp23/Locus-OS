"""
SPEC §21.1-21.3 lines 6624-6678: Google Calendar & Webhook Integration Provider.
Provides BaseCalendarProvider and DefaultCalendarProvider with modular off-switches:
- locus.integrations.calendar.enabled
- locus.google_calendar.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

import abc
import logging
from typing import Any

import sidecar.config as config
from sidecar.integrations.calendar_sync import (
    BaseCalendarClient,
    CalendarEvent,
    GoogleCalendarSync,
    MockGoogleCalendarClient,
    WebhookManager,
)

logger = logging.getLogger("locus.providers.calendar")


class BaseCalendarProvider(abc.ABC):
    """Abstract base provider for calendar synchronization and webhook events."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_feature_enabled(self) -> tuple[bool, str]:
        """Check if calendar integration features are enabled via config."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
        """Generate Google OAuth 2.0 authorization URL."""
        raise NotImplementedError

    @abc.abstractmethod
    def exchange_code(self, code: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_today_events(self) -> dict[str, Any]:
        """Fetch today's calendar events."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_events(self, time_min: str | None = None, time_max: str | None = None) -> dict[str, Any]:
        """Fetch calendar events within specified time window."""
        raise NotImplementedError

    @abc.abstractmethod
    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create new scheduled calendar event."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_temporal_context(self) -> dict[str, Any]:
        """Format today's calendar events for Context Forge temporal layer."""
        raise NotImplementedError

    @abc.abstractmethod
    def register_webhook(self, url: str, events: list[str], secret: str | None = None) -> dict[str, Any]:
        """Register outbound webhook endpoint."""
        raise NotImplementedError

    @abc.abstractmethod
    def fire_webhook(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Fire event notification to subscribed webhooks."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Return diagnostic status of integration provider."""
        raise NotImplementedError


class DefaultCalendarProvider(BaseCalendarProvider):
    """
    Default calendar and webhook integration provider wrapping GoogleCalendarSync & WebhookManager.
    Enforces modular off-switches locus.integrations.calendar.enabled and locus.google_calendar.enabled (HTTP 503).
    """

    def __init__(
        self,
        sync: GoogleCalendarSync | None = None,
        webhooks: WebhookManager | None = None,
    ) -> None:
        self.sync = sync or GoogleCalendarSync()
        self.webhooks = webhooks or WebhookManager()

    @property
    def name(self) -> str:
        return "default_calendar_provider"

    def is_feature_enabled(self) -> tuple[bool, str]:
        """Evaluate modular off-switches."""
        for switch in ("locus.integrations.calendar.enabled", "locus.google_calendar.enabled"):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def get_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        url = self.sync.get_auth_url(redirect_uri=redirect_uri)
        return {"status": "ok", "auth_url": url, "redirect_uri": redirect_uri}

    def exchange_code(self, code: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        tokens = self.sync.exchange_auth_code(code=code, redirect_uri=redirect_uri)
        return {"status": "ok", "authenticated": True, "tokens": tokens}

    def get_today_events(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        events = self.sync.fetch_today_events()
        return {"status": "ok", "events": [e.to_dict() for e in events], "count": len(events)}

    def list_events(self, time_min: str | None = None, time_max: str | None = None) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        events = self.sync.fetch_events(time_min=time_min, time_max=time_max)
        return {"status": "ok", "events": [e.to_dict() for e in events], "count": len(events)}

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: list[str] | None = None,
    ) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        ev = self.sync.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendees=attendees,
        )
        return {"status": "ok", "event": ev.to_dict()}

    def get_temporal_context(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        text = self.sync.format_temporal_context()
        return {"status": "ok", "temporal_context": text}

    def register_webhook(self, url: str, events: list[str], secret: str | None = None) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        record = self.webhooks.register_webhook(url=url, events=events, secret=secret)
        return {"status": "ok", "webhook": record}

    def fire_webhook(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        dispatches = self.webhooks.fire_webhook(event_type=event_type, payload=payload)
        return {"status": "ok", "event_type": event_type, "dispatches": dispatches, "dispatched_count": len(dispatches)}

    def get_status(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return {
            "authenticated": self.sync.credentials is not None,
            "has_credentials": bool(self.sync.credentials),
            "webhooks_count": len(self.webhooks.webhooks),
            "client_id_configured": bool(self.sync.client_id),
        }
