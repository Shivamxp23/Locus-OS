"""Extension Lifecycle Engine (§1.5).

Coordinates 25+ lifecycle events connecting Pi Agent turn cycles
with sidecar memory flushes, state calculations, and tool audits.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


LIFECYCLE_EVENTS: List[str] = [
    "session_start",
    "turn_start",
    "message_start",
    "message_update",
    "message_end",
    "tool_execution_start",
    "tool_execution_update",
    "tool_execution_end",
    "turn_end",
    "agent_end",
    "session_shutdown",
    "before_compact",
    "after_compact",
    "before_tree",
    "session_switch",
    "replaced_session",
    "context_usage_update",
    "subagent_spawn",
    "subagent_terminate",
    "model_switch",
    "quota_exceeded",
    "approval_requested",
    "approval_granted",
    "approval_rejected",
    "error",
]


@dataclass
class LifecycleEvent:
    event_type: str
    session_id: str
    turn_id: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    data: Dict[str, Any] = field(default_factory=dict)


class LifecycleManager:
    """Dispatches lifecycle events across cognitive subsystems."""

    def __init__(self) -> None:
        self.listeners: Dict[str, List[Callable[[LifecycleEvent], Any]]] = {}
        self.history: List[LifecycleEvent] = []

    def subscribe(self, event_type: str, handler: Callable[[LifecycleEvent], Any]) -> None:
        if event_type not in LIFECYCLE_EVENTS:
            raise ValueError(f"Unknown event type: {event_type}")
        self.listeners.setdefault(event_type, []).append(handler)

    def dispatch(self, event: LifecycleEvent) -> None:
        self.history.append(event)
        for handler in self.listeners.get(event.event_type, []):
            handler(event)

    def get_event_history(self, event_type: Optional[str] = None) -> List[LifecycleEvent]:
        if event_type:
            return [e for e in self.history if e.event_type == event_type]
        return list(self.history)
