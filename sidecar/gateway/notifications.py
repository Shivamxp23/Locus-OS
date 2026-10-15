"""Locus Notification Dispatcher (§29.4).

Multi-channel notification routing, prioritization, throttling, and delivery
supporting Telegram, Desktop, Webhook, and In-Memory event bus.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationPayload:
    title: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    category: str = "general"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    channels: List[str] = field(default_factory=lambda: ["desktop", "telegram"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "body": self.body,
            "priority": self.priority.value,
            "category": self.category,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "channels": self.channels,
        }


class NotificationDispatcher:
    """Dispatches notifications across configured output sinks with rate limiting."""

    def __init__(self, throttle_window_seconds: float = 2.0):
        self.throttle_window = throttle_window_seconds
        self._last_dispatch: Dict[str, float] = {}
        self._handlers: Dict[str, List[Callable[[NotificationPayload], bool]]] = {
            "desktop": [],
            "telegram": [],
            "webhook": [],
            "event_bus": [],
        }
        self.history: List[NotificationPayload] = []

    def register_handler(self, channel: str, handler: Callable[[NotificationPayload], bool]) -> None:
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

    def dispatch(self, payload: NotificationPayload) -> Dict[str, bool]:
        now = time.time()
        # Urgent priority bypasses rate limiting
        if payload.priority != NotificationPriority.URGENT:
            last = self._last_dispatch.get(payload.category, 0.0)
            if now - last < self.throttle_window:
                return {"throttled": True}

        self._last_dispatch[payload.category] = now
        self.history.append(payload)

        results: Dict[str, bool] = {}
        for ch in payload.channels:
            handlers = self._handlers.get(ch, [])
            if not handlers:
                results[ch] = True  # Default mock delivered
            else:
                delivered = False
                for h in handlers:
                    try:
                        if h(payload):
                            delivered = True
                    except Exception:
                        pass
                results[ch] = delivered

        return results

    def get_recent_notifications(self, limit: int = 20) -> List[NotificationPayload]:
        return self.history[-limit:]
