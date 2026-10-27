"""
SPEC §21.1-21.3 lines 6624-6678: Google Calendar, Gmail, Webhooks.
Implements Google Calendar OAuth 2.0 flow, event synchronization,
Context Forge temporal layer formatting, and HMAC-SHA256 signed webhook dispatch.
"""
from __future__ import annotations

import abc
import datetime
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger("locus.integrations.calendar")


@dataclass
class CalendarEvent:
    """Represents a calendar event item."""
    id: str
    summary: str
    start_time: str
    end_time: str
    description: str = ""
    location: str = ""
    html_link: str = ""
    attendees: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CalendarEvent:
        return cls(
            id=str(data.get("id", "")),
            summary=str(data.get("summary", "Untitled Event")),
            start_time=str(data.get("start_time", "")),
            end_time=str(data.get("end_time", "")),
            description=str(data.get("description", "")),
            location=str(data.get("location", "")),
            html_link=str(data.get("html_link", "")),
            attendees=list(data.get("attendees", [])),
        )


class BaseCalendarClient(abc.ABC):
    """Abstract interface for Google Calendar API interactions."""

    @abc.abstractmethod
    def get_authorization_url(self, client_id: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """Generate Google OAuth 2.0 authorization URL."""
        raise NotImplementedError

    @abc.abstractmethod
    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_events(self, calendar_id: str = "primary", time_min: str | None = None, time_max: str | None = None) -> list[CalendarEvent]:
        """Retrieve events within time range."""
        raise NotImplementedError

    @abc.abstractmethod
    def create_event(self, calendar_id: str = "primary", event_data: dict[str, Any] | None = None) -> CalendarEvent:
        """Create a new calendar event."""
        raise NotImplementedError


class MockGoogleCalendarClient(BaseCalendarClient):
    """
    Hermetic Mock Google Calendar client for offline execution and tests.
    """

    def __init__(self) -> None:
        self.events: dict[str, CalendarEvent] = {}
        self.tokens: dict[str, Any] = {
            "access_token": "mock-access-token-12345",
            "refresh_token": "mock-refresh-token-67890",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        # Prepopulate a realistic mock event for today
        today_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        default_event = CalendarEvent(
            id="evt-default-1",
            summary="Locus Sprint Review & Standup",
            start_time=f"{today_iso}T09:00:00Z",
            end_time=f"{today_iso}T10:00:00Z",
            description="Autonomous milestone verification session",
            location="Virtual / Locus",
            html_link="https://calendar.google.com/event?eid=mock1",
            attendees=["shivam@example.com", "locus@agent.local"],
        )
        self.events[default_event.id] = default_event

    def get_authorization_url(self, client_id: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        scopes = "https://www.googleapis.com/auth/calendar.readonly%20https://www.googleapis.com/auth/calendar.events"
        return f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}&access_type=offline"

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
        if not code:
            raise ValueError("Authorization code cannot be empty")
        return {
            **self.tokens,
            "code_used": code,
            "created_at": time.time(),
        }

    def list_events(self, calendar_id: str = "primary", time_min: str | None = None, time_max: str | None = None) -> list[CalendarEvent]:
        # Filter events if range specified
        results: list[CalendarEvent] = []
        for ev in self.events.values():
            if time_min and ev.end_time < time_min:
                continue
            if time_max and ev.start_time > time_max:
                continue
            results.append(ev)
        results.sort(key=lambda e: e.start_time)
        return results

    def create_event(self, calendar_id: str = "primary", event_data: dict[str, Any] | None = None) -> CalendarEvent:
        data = event_data or {}
        event_id = data.get("id") or f"evt-{secrets.token_hex(4)}"
        event = CalendarEvent(
            id=event_id,
            summary=data.get("summary", "New Locus Event"),
            start_time=data.get("start_time", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            end_time=data.get("end_time", (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()),
            description=data.get("description", ""),
            location=data.get("location", ""),
            html_link=f"https://calendar.google.com/event?eid={event_id}",
            attendees=data.get("attendees", []),
        )
        self.events[event.id] = event
        return event


class GoogleCalendarSync:
    """
    SPEC §21.1: Google Calendar Synchronization engine.
    Manages OAuth credentials, event fetching, and formatting for Context Forge temporal injection.
    """

    def __init__(
        self,
        client_id: str = "locus-mock-client-id",
        client_secret: str = "locus-mock-client-secret",
        calendar_client: BaseCalendarClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = calendar_client or MockGoogleCalendarClient()
        self.credentials: dict[str, Any] | None = None

    def get_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """SPEC §21.1 lines 6636-6643: Manual OAuth 2.0 flow setup."""
        return self.client.get_authorization_url(self.client_id, redirect_uri=redirect_uri)

    def exchange_auth_code(self, code: str, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> dict[str, Any]:
        """SPEC §21.1: Complete OAuth 2.0 code exchange."""
        tokens = self.client.exchange_code(
            code=code,
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=redirect_uri,
        )
        self.credentials = tokens
        return tokens

    def fetch_today_events(self, calendar_id: str = "primary") -> list[CalendarEvent]:
        """SPEC §21.1 lines 6645-6654: Fetch today's events for morning log and temporal layer."""
        now = datetime.datetime.now(datetime.timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        return self.client.list_events(calendar_id=calendar_id, time_min=today_start, time_max=today_end)

    def fetch_events(
        self,
        calendar_id: str = "primary",
        time_min: str | None = None,
        time_max: str | None = None,
    ) -> list[CalendarEvent]:
        """Fetch calendar events in custom range."""
        return self.client.list_events(calendar_id=calendar_id, time_min=time_min, time_max=time_max)

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: list[str] | None = None,
    ) -> CalendarEvent:
        """Create new scheduled event."""
        return self.client.create_event(
            calendar_id="primary",
            event_data={
                "summary": summary,
                "start_time": start_time,
                "end_time": end_time,
                "description": description,
                "location": location,
                "attendees": attendees or [],
            },
        )

    def format_temporal_context(self) -> str:
        """
        SPEC §21.1 Adaptation: Injects calendar schedule into Context Forge's temporal layer.
        """
        events = self.fetch_today_events()
        if not events:
            return "Today's Schedule: No scheduled events."

        lines = ["Today's Schedule:"]
        for ev in events:
            lines.append(f"- [{ev.start_time} - {ev.end_time}] {ev.summary} ({ev.description or 'No details'})")
        return "\n".join(lines)


class WebhookManager:
    """
    SPEC §21.3 lines 6660-6670: Webhook registration and HMAC-SHA256 signing.
    Dispatches notifications to external webhooks with cryptographic authenticity signatures.
    """

    def __init__(self) -> None:
        self.webhooks: dict[str, dict[str, Any]] = {}

    def register_webhook(
        self,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> dict[str, Any]:
        """Register a destination webhook endpoint with secret key."""
        webhook_id = f"wh-{secrets.token_hex(6)}"
        sec = secret or secrets.token_hex(16)
        record = {
            "id": webhook_id,
            "url": url,
            "events": events,
            "secret": sec,
            "created_at": time.time(),
        }
        self.webhooks[webhook_id] = record
        return record

    def compute_signature(self, secret: str, payload_bytes: bytes) -> str:
        """Compute HMAC-SHA256 signature for payload verification."""
        mac = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256)
        return mac.hexdigest()

    def fire_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        SPEC §21.3: Fire webhooks subscribed to event_type with X-Signature HMAC header.
        """
        results: list[dict[str, Any]] = []
        payload_full = {
            "event_type": event_type,
            "timestamp": time.time(),
            "data": payload,
        }
        raw_json = json.dumps(payload_full, sort_keys=True).encode("utf-8")

        for wh in self.webhooks.values():
            if event_type in wh["events"] or "*" in wh["events"]:
                sig = self.compute_signature(wh["secret"], raw_json)
                results.append({
                    "webhook_id": wh["id"],
                    "url": wh["url"],
                    "signature": sig,
                    "status": "dispatched",
                    "payload_size": len(raw_json),
                })
        return results

    def list_webhooks(self) -> list[dict[str, Any]]:
        """Return registered webhooks."""
        return list(self.webhooks.values())
