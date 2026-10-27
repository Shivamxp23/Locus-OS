"""
SPEC §29.4 lines 7531-7612: Notifications Provider (F-0067 / US-105).
Modular off-switches:
- locus.notifications.enabled (master toggle, returns 503 when off)
- locus.notifications.channels.<name>.enabled (per-channel toggle)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.diagnostics.notifications import (
    NotificationDeliveryResult,
    NotificationDispatcher,
    NotificationPriority,
    QueuedNotification,
)

logger = logging.getLogger("locus.providers.notifications")


class BaseNotificationsProvider(ABC):
    """
    Abstract contract for Notifications Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def send_notification(
        self,
        message: str,
        priority: str = NotificationPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Deliver or buffer notification based on priority, quiet hours, and DCS."""

    @abstractmethod
    def get_queue(self, undelivered_only: bool = True) -> Dict[str, Any]:
        """Retrieve queued notifications."""

    @abstractmethod
    def process_queue(self) -> Dict[str, Any]:
        """Flush and summarize queued notifications."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Self-diagnostic probe."""


class DefaultNotificationsProvider(BaseNotificationsProvider):
    """
    Default provider wrapping NotificationDispatcher with modular off-switch enforcement.
    """

    FEATURE_SWITCH = "locus.notifications.enabled"

    def __init__(self, dispatcher: Optional[NotificationDispatcher] = None) -> None:
        self._dispatcher = dispatcher or NotificationDispatcher()

    @property
    def name(self) -> str:
        return "default_notifications"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Modular off-switch check: locus.notifications.enabled."""
        val = config.get(self.FEATURE_SWITCH)
        if val is not None and not config.is_enabled(self.FEATURE_SWITCH):
            return False, self.FEATURE_SWITCH
        return True, ""

    def send_notification(
        self,
        message: str,
        priority: str = NotificationPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Deliver notification or return 503 if feature disabled."""
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": f"Notifications feature is disabled by {switch}",
                "disabled": switch,
            }
        result = self._dispatcher.send_notification(
            message=message,
            priority=priority,
            metadata=metadata,
        )
        return result.to_dict()

    def get_queue(self, undelivered_only: bool = True) -> Dict[str, Any]:
        """Get queue items or return 503 if feature disabled."""
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": f"Notifications feature is disabled by {switch}",
                "disabled": switch,
            }
        items = self._dispatcher.get_queued_notifications(undelivered_only=undelivered_only)
        return {
            "status": "ok",
            "count": len(items),
            "notifications": [item.to_dict() for item in items],
        }

    def process_queue(self) -> Dict[str, Any]:
        """Process buffered queue or return 503 if feature disabled."""
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": f"Notifications feature is disabled by {switch}",
                "disabled": switch,
            }
        res = self._dispatcher.process_notification_queue()
        return {"status": "ok", **res}

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic status or return 503 if disabled."""
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": f"Notifications feature is disabled by {switch}",
                "disabled": switch,
            }
        status = self._dispatcher.get_status()
        return {
            "name": self.name,
            "feature_enabled": True,
            "switch": self.FEATURE_SWITCH,
            "dispatcher": status,
        }

    def health_check(self) -> Dict[str, Any]:
        """Self-diagnostic probe."""
        enabled, _ = self.is_feature_enabled()
        return {
            "status": "ok" if enabled else "disabled",
            "provider": self.name,
            "active_channels": [c.name for c in self._dispatcher.get_connected_channels()],
        }
