"""
SPEC §29.4 lines 7531-7612:
Notifications subsystem (F-0067 / US-105).
Source: OpenHuman notifications/dispatcher.py + Hermes gateway/platform_registry.py + Locus-original.

Logic extracted:
    NOTIFICATION SYSTEM:
        PRIORITY LEVELS:
            HIGH    — Behavioral alerts, critical state changes, approval requests
            MEDIUM  — Inner Loop observations, morning briefing, deferral warnings
            LOW     — Content drafts ready, spaced repetition prompts, non-urgent patterns

        FUNCTION send_notification(message, priority, metadata={}):
            active_channels = channel_registry.get_connected()
            current_state = state_engine.get_current_state()
            
            // Quiet hours gate (unless HIGH priority)
            IF is_quiet_hours() AND priority != "HIGH":
                queue_for_later(message, priority, metadata)
                RETURN { delivered: false, reason: "quiet_hours", queued: true }
            
            // DCS-gated delivery: suppress MEDIUM/LOW if user is stressed
            IF current_state.dcs < 3.0 AND priority != "HIGH":
                queue_for_later(message, priority, metadata)
                RETURN { delivered: false, reason: "low_dcs", queued: true }
            
            SWITCH priority:
                CASE "HIGH":
                    FOR EACH channel IN active_channels:
                        channel.send(message, urgent=true)
                    log_notification(message, "HIGH", channels=active_channels)
                
                CASE "MEDIUM":
                    primary = get_primary_channel(active_channels)
                    primary.send(message, urgent=false)
                    log_notification(message, "MEDIUM", channels=[primary])
                
                CASE "LOW":
                    queue_for_next_interaction(message, metadata)
                    log_notification(message, "LOW", channels=[], queued=true)
            
            RETURN { delivered: true, priority: priority }

        FUNCTION process_notification_queue():
            queued = get_queued_notifications()
            IF queued:
                summary = format_notification_summary(queued)
                send_notification(summary, "MEDIUM")
                mark_as_delivered(queued)

        QUIET HOURS:
            default: 00:00 - 07:00 IST
            configurable via config
            HIGH priority overrides quiet hours
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, time as dtime
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.diagnostics.notifications")


class NotificationPriority:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    ALL = [HIGH, MEDIUM, LOW]


@dataclass
class QueuedNotification:
    id: str
    message: str
    priority: str
    created_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    delivered: bool = False
    delivery_timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NotificationDeliveryResult:
    delivered: bool
    priority: str
    reason: Optional[str] = None
    queued: bool = False
    channels: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseNotificationChannel(ABC):
    """Abstract interface for delivery channels (Telegram, Desktop, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel identifier."""

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check channel specific config toggle."""

    @abstractmethod
    def send(self, message: str, urgent: bool = False, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Deliver notification through channel adapter."""


class MemoryNotificationChannel(BaseNotificationChannel):
    """In-memory notification channel adapter for testing and diagnostic sinks."""

    def __init__(self, name: str = "console", default_enabled: bool = True) -> None:
        self._name = name
        self._default_enabled = default_enabled
        self.sent_messages: List[Dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._name

    def is_enabled(self) -> bool:
        cfg_key = f"locus.notifications.channels.{self._name}.enabled"
        val = config.get(cfg_key)
        if val is not None:
            return bool(config.is_enabled(cfg_key))
        return self._default_enabled

    def send(self, message: str, urgent: bool = False, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "channel": self._name,
            "message": message,
            "urgent": urgent,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self.sent_messages.append(payload)
        return {"status": "sent", "channel": self._name}


class NotificationDispatcher:
    """
    SPEC §29.4: Multi-channel priority-aware notification dispatcher
    with quiet hours gating, DCS state suppression, and queue buffering.
    """

    SWITCH_KEY = "locus.notifications.enabled"

    def __init__(self) -> None:
        self._channels: Dict[str, BaseNotificationChannel] = {
            "telegram": MemoryNotificationChannel("telegram"),
            "desktop": MemoryNotificationChannel("desktop"),
            "console": MemoryNotificationChannel("console"),
        }
        self._queue: List[QueuedNotification] = []
        self._notification_log: List[Dict[str, Any]] = []

    def is_enabled(self) -> bool:
        """Master/subsystem toggle check."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def register_channel(self, channel: BaseNotificationChannel) -> None:
        """Register or replace a notification channel adapter."""
        self._channels[channel.name] = channel

    def get_connected_channels(self) -> List[BaseNotificationChannel]:
        """Return all registered and actively enabled channels."""
        return [c for c in self._channels.values() if c.is_enabled()]

    def get_primary_channel(self, active_channels: List[BaseNotificationChannel]) -> Optional[BaseNotificationChannel]:
        """
        Primary channel selection per SPEC §29.4:
        Telegram by default, or first active channel.
        """
        primary_name = config.get("notifications.primary_channel", "telegram")
        for ch in active_channels:
            if ch.name == primary_name:
                return ch
        return active_channels[0] if active_channels else None

    def is_quiet_hours(self, dt: Optional[datetime] = None) -> bool:
        """
        Check whether current local time is in quiet hours.
        Default: 00:00 - 07:00 IST (configurable via notifications.quiet_hours).
        """
        qh_config = config.get("notifications.quiet_hours") or config.get("locus.notifications.quiet_hours")
        start_hour = 0
        start_minute = 0
        end_hour = 7
        end_minute = 0

        if isinstance(qh_config, dict):
            start_hour = int(qh_config.get("start_hour", 0))
            start_minute = int(qh_config.get("start_minute", 0))
            end_hour = int(qh_config.get("end_hour", 7))
            end_minute = int(qh_config.get("end_minute", 0))

        now_time = (dt or datetime.now()).time()
        start_t = dtime(start_hour, start_minute)
        end_t = dtime(end_hour, end_minute)

        if start_t <= end_t:
            return start_t <= now_time < end_t
        else:
            # Over midnight window
            return now_time >= start_t or now_time < end_t

    def get_current_dcs(self) -> float:
        """Read DCS score from state engine or config, default 3.5 (stable)."""
        dcs_val = config.get("locus.state.dcs")
        if dcs_val is not None:
            try:
                return float(dcs_val)
            except (ValueError, TypeError):
                pass
        return 3.5

    def queue_for_later(self, message: str, priority: str, metadata: Optional[Dict[str, Any]] = None) -> QueuedNotification:
        """Buffer notification for subsequent interaction or morning briefing."""
        q_item = QueuedNotification(
            id=f"notif_{len(self._queue) + 1}_{int(time.time()*1000)}",
            message=message,
            priority=priority,
            created_at=time.time(),
            metadata=metadata or {},
        )
        self._queue.append(q_item)
        return q_item

    def send_notification(
        self,
        message: str,
        priority: str = NotificationPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        now_dt: Optional[datetime] = None,
        dcs_override: Optional[float] = None,
    ) -> NotificationDeliveryResult:
        """
        SPEC §29.4 lines 7545-7575:
        FUNCTION send_notification(message, priority, metadata={}):
            active_channels = channel_registry.get_connected()
            current_state = state_engine.get_current_state()
            
            // Quiet hours gate (unless HIGH priority)
            IF is_quiet_hours() AND priority != "HIGH":
                queue_for_later(message, priority, metadata)
                RETURN { delivered: false, reason: "quiet_hours", queued: true }
            
            // DCS-gated delivery: suppress MEDIUM/LOW if user is stressed
            IF current_state.dcs < 3.0 AND priority != "HIGH":
                queue_for_later(message, priority, metadata)
                RETURN { delivered: false, reason: "low_dcs", queued: true }
        """
        priority = priority.upper() if priority else NotificationPriority.MEDIUM
        meta = metadata or {}

        # Quiet hours gating
        if self.is_quiet_hours(dt=now_dt) and priority != NotificationPriority.HIGH:
            self.queue_for_later(message, priority, meta)
            return NotificationDeliveryResult(
                delivered=False,
                priority=priority,
                reason="quiet_hours",
                queued=True,
            )

        # DCS gating: suppress MEDIUM/LOW if user is stressed (dcs < 3.0)
        current_dcs = dcs_override if dcs_override is not None else self.get_current_dcs()
        if current_dcs < 3.0 and priority != NotificationPriority.HIGH:
            self.queue_for_later(message, priority, meta)
            return NotificationDeliveryResult(
                delivered=False,
                priority=priority,
                reason="low_dcs",
                queued=True,
            )

        active_channels = self.get_connected_channels()
        if not active_channels:
            self.queue_for_later(message, priority, meta)
            return NotificationDeliveryResult(
                delivered=False,
                priority=priority,
                reason="no_active_channels",
                queued=True,
            )

        delivered_channels: List[str] = []

        if priority == NotificationPriority.HIGH:
            # Deliver to ALL active channels simultaneously
            for ch in active_channels:
                try:
                    ch.send(message, urgent=True, metadata=meta)
                    delivered_channels.append(ch.name)
                except Exception as exc:
                    logger.error("Channel %s error delivering HIGH notification: %s", ch.name, exc)
            self._log_notification(message, NotificationPriority.HIGH, delivered_channels, queued=False)

        elif priority == NotificationPriority.MEDIUM:
            # Primary channel only (Telegram by default)
            primary = self.get_primary_channel(active_channels)
            if primary:
                primary.send(message, urgent=False, metadata=meta)
                delivered_channels.append(primary.name)
            self._log_notification(message, NotificationPriority.MEDIUM, delivered_channels, queued=False)

        else:
            # LOW priority: queue for next interaction
            self.queue_for_later(message, NotificationPriority.LOW, meta)
            self._log_notification(message, NotificationPriority.LOW, [], queued=True)
            return NotificationDeliveryResult(
                delivered=True,
                priority=NotificationPriority.LOW,
                queued=True,
                channels=[],
            )

        return NotificationDeliveryResult(
            delivered=len(delivered_channels) > 0,
            priority=priority,
            channels=delivered_channels,
            queued=False,
        )

    def _log_notification(
        self,
        message: str,
        priority: str,
        channels: List[str],
        queued: bool = False,
    ) -> None:
        self._notification_log.append({
            "message": message,
            "priority": priority,
            "channels": channels,
            "queued": queued,
            "timestamp": time.time(),
        })

    def get_queued_notifications(self, undelivered_only: bool = True) -> List[QueuedNotification]:
        """List buffered notifications."""
        if undelivered_only:
            return [q for q in self._queue if not q.delivered]
        return list(self._queue)

    def process_notification_queue(self) -> Dict[str, Any]:
        """
        SPEC §29.4 lines 7576-7584:
        FUNCTION process_notification_queue():
            queued = get_queued_notifications()
            IF queued:
                summary = format_notification_summary(queued)
                send_notification(summary, "MEDIUM")
                mark_as_delivered(queued)
        """
        undelivered = self.get_queued_notifications(undelivered_only=True)
        if not undelivered:
            return {"processed": 0, "delivered": False}

        summary_lines = [f"• [{q.priority}] {q.message}" for q in undelivered]
        summary = f"Queued Notification Digest ({len(undelivered)} items):\n" + "\n".join(summary_lines)

        res = self.send_notification(summary, priority=NotificationPriority.MEDIUM)
        now_ts = time.time()
        for q in undelivered:
            q.delivered = True
            q.delivery_timestamp = now_ts

        return {
            "processed": len(undelivered),
            "delivered": res.delivered,
            "digest": summary,
            "result": res.to_dict(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Observability telemetry."""
        return {
            "enabled": self.is_enabled(),
            "channel_count": len(self._channels),
            "active_channels": [c.name for c in self.get_connected_channels()],
            "queued_count": len(self.get_queued_notifications(undelivered_only=True)),
            "total_logged": len(self._notification_log),
            "current_dcs": self.get_current_dcs(),
            "is_quiet_hours": self.is_quiet_hours(),
        }
