"""
Locus third-party integrations package (Google Calendar, Webhooks, Gmail).
"""
from sidecar.integrations.calendar_sync import (
    BaseCalendarClient,
    CalendarEvent,
    GoogleCalendarSync,
    MockGoogleCalendarClient,
    WebhookManager,
)

__all__ = [
    "BaseCalendarClient",
    "CalendarEvent",
    "GoogleCalendarSync",
    "MockGoogleCalendarClient",
    "WebhookManager",
]
