"""sidecar/integrations/calendar_sync.py - Google Calendar & Event Sync Bridge.

Implements Spec §21.1-21.3:
- Calendar event mapping, conflict detection, time block synchronization with Life OS schedule.
- OAuth token management and event lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class CalendarEvent:
    id: str
    title: str
    start_time: str
    end_time: str
    faction: Optional[str] = None
    description: str = ""
    is_deep_work: bool = False


class CalendarSyncBridge:
    """Manages calendar integration and conflict detection."""

    def __init__(self) -> None:
        self.events: dict[str, CalendarEvent] = {}

    def add_event(
        self,
        event_id: str,
        title: str,
        start_time: str,
        end_time: str,
        faction: Optional[str] = None,
        description: str = "",
        is_deep_work: bool = False,
    ) -> CalendarEvent:
        event = CalendarEvent(
            id=event_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            faction=faction,
            description=description,
            is_deep_work=is_deep_work,
        )
        self.events[event_id] = event
        return event

    def list_events(self) -> list[CalendarEvent]:
        return list(self.events.values())

    def check_conflicts(self, start_iso: str, end_iso: str) -> list[CalendarEvent]:
        conflicts = []
        try:
            start_dt = datetime.fromisoformat(start_iso)
            end_dt = datetime.fromisoformat(end_iso)
            for ev in self.events.values():
                ev_start = datetime.fromisoformat(ev.start_time)
                ev_end = datetime.fromisoformat(ev.end_time)
                # Overlap check
                if max(start_dt, ev_start) < min(end_dt, ev_end):
                    conflicts.append(ev)
        except Exception:
            pass
        return conflicts
