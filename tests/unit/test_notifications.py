"""
Unit tests for Notifications (F-0067 / US-105).
SPEC §29.4 lines 7531-7612.
"""
from __future__ import annotations

from datetime import datetime
import pytest

from sidecar import config
from sidecar.diagnostics.notifications import (
    BaseNotificationChannel,
    MemoryNotificationChannel,
    NotificationDeliveryResult,
    NotificationDispatcher,
    NotificationPriority,
    QueuedNotification,
)
from sidecar.providers.notifications import (
    BaseNotificationsProvider,
    DefaultNotificationsProvider,
)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.notifications.enabled", True)
    config.set("locus.state.dcs", 3.5)
    config.set("notifications.quiet_hours", {"start_hour": 0, "start_minute": 0, "end_hour": 7, "end_minute": 0})
    yield
    config.set("locus.notifications.enabled", True)
    config.set("locus.state.dcs", None)
    config.set("notifications.quiet_hours", None)


def test_high_priority_broadcasts_all_channels():
    """SPEC §29.4 line 7558: 'CASE \"HIGH\": FOR EACH channel IN active_channels: channel.send(message, urgent=true)'"""
    dispatcher = NotificationDispatcher()
    t_ch = MemoryNotificationChannel("telegram")
    d_ch = MemoryNotificationChannel("desktop")
    c_ch = MemoryNotificationChannel("console")
    dispatcher.register_channel(t_ch)
    dispatcher.register_channel(d_ch)
    dispatcher.register_channel(c_ch)

    dt = datetime(2027, 11, 15, 14, 0)  # 2:00 PM (not quiet hours)
    res = dispatcher.send_notification("Critical alert!", priority=NotificationPriority.HIGH, now_dt=dt)

    assert res.delivered is True
    assert set(res.channels) == {"telegram", "desktop", "console"}
    assert len(t_ch.sent_messages) == 1
    assert t_ch.sent_messages[0]["urgent"] is True
    assert len(d_ch.sent_messages) == 1
    assert len(c_ch.sent_messages) == 1


def test_medium_priority_delivers_to_primary_channel_only():
    """SPEC §29.4 line 7564: 'CASE \"MEDIUM\": primary = get_primary_channel(active_channels); primary.send(message, urgent=false)'"""
    dispatcher = NotificationDispatcher()
    t_ch = MemoryNotificationChannel("telegram")
    d_ch = MemoryNotificationChannel("desktop")
    dispatcher.register_channel(t_ch)
    dispatcher.register_channel(d_ch)

    dt = datetime(2027, 11, 15, 14, 0)
    res = dispatcher.send_notification("Daily briefing ready", priority=NotificationPriority.MEDIUM, now_dt=dt)

    assert res.delivered is True
    assert res.channels == ["telegram"]
    assert len(t_ch.sent_messages) == 1
    assert t_ch.sent_messages[0]["urgent"] is False
    assert len(d_ch.sent_messages) == 0


def test_low_priority_queues_for_next_interaction():
    """SPEC §29.4 line 7570: 'CASE \"LOW\": queue_for_next_interaction(message, metadata)'"""
    dispatcher = NotificationDispatcher()
    dt = datetime(2027, 11, 15, 14, 0)
    res = dispatcher.send_notification("Drafts available for review", priority=NotificationPriority.LOW, now_dt=dt)

    assert res.delivered is True
    assert res.queued is True
    assert res.channels == []

    queued = dispatcher.get_queued_notifications()
    assert len(queued) == 1
    assert queued[0].priority == "LOW"
    assert "Drafts available" in queued[0].message


def test_quiet_hours_gating_suppresses_medium():
    """SPEC §29.4 line 7549: 'IF is_quiet_hours() AND priority != \"HIGH\": queue_for_later(message, priority, metadata)'"""
    dispatcher = NotificationDispatcher()
    dt_night = datetime(2027, 11, 15, 3, 30)  # 3:30 AM (quiet hours)
    res = dispatcher.send_notification("Mid-night status", priority=NotificationPriority.MEDIUM, now_dt=dt_night)

    assert res.delivered is False
    assert res.queued is True
    assert res.reason == "quiet_hours"

    queued = dispatcher.get_queued_notifications()
    assert len(queued) == 1
    assert queued[0].message == "Mid-night status"


def test_quiet_hours_override_for_high_priority():
    """SPEC §29.4 line 7549: 'HIGH priority overrides quiet hours'"""
    dispatcher = NotificationDispatcher()
    dt_night = datetime(2027, 11, 15, 3, 30)  # 3:30 AM (quiet hours)
    res = dispatcher.send_notification("Emergency breach!", priority=NotificationPriority.HIGH, now_dt=dt_night)

    assert res.delivered is True
    assert res.queued is False
    assert len(res.channels) > 0


def test_dcs_gated_delivery_suppresses_medium_when_stressed():
    """SPEC §29.4 line 7554: 'IF current_state.dcs < 3.0 AND priority != \"HIGH\": queue_for_later(message, priority, metadata)'"""
    dispatcher = NotificationDispatcher()
    dt = datetime(2027, 11, 15, 14, 0)
    res = dispatcher.send_notification("Routine notice", priority=NotificationPriority.MEDIUM, now_dt=dt, dcs_override=2.4)

    assert res.delivered is False
    assert res.queued is True
    assert res.reason == "low_dcs"

    queued = dispatcher.get_queued_notifications()
    assert len(queued) == 1


def test_dcs_override_for_high_priority():
    """SPEC §29.4 line 7554: HIGH priority overrides low DCS suppression."""
    dispatcher = NotificationDispatcher()
    dt = datetime(2027, 11, 15, 14, 0)
    res = dispatcher.send_notification("Critical failure", priority=NotificationPriority.HIGH, now_dt=dt, dcs_override=1.5)

    assert res.delivered is True
    assert res.queued is False


def test_process_notification_queue():
    """SPEC §29.4 line 7576: 'FUNCTION process_notification_queue():'"""
    dispatcher = NotificationDispatcher()
    dispatcher.queue_for_later("Note 1", NotificationPriority.LOW)
    dispatcher.queue_for_later("Note 2", NotificationPriority.MEDIUM)

    assert len(dispatcher.get_queued_notifications()) == 2

    # Process queue delivers digest
    res = dispatcher.process_notification_queue()
    assert res["processed"] == 2
    assert res["delivered"] is True
    assert "Digest" in res["digest"]

    # All marked delivered
    assert len(dispatcher.get_queued_notifications(undelivered_only=True)) == 0


def test_provider_modular_off_switch():
    """SPEC §29.4 line 7598: 'Swappable / off state: locus.notifications.enabled.'"""
    config.set("locus.notifications.enabled", False)
    provider = DefaultNotificationsProvider()
    res = provider.send_notification("Test off")
    assert res.get("status_code") == 503
    assert "disabled by locus.notifications.enabled" in res.get("detail", "")

    q_res = provider.get_queue()
    assert q_res.get("status_code") == 503

    p_res = provider.process_queue()
    assert p_res.get("status_code") == 503


def test_provider_polymorphism():
    """SPEC §29.4 line 7598: Provider polymorphism and swappability."""
    class CustomNotificationsProvider(BaseNotificationsProvider):
        @property
        def name(self) -> str:
            return "custom_notif"

        def is_feature_enabled(self):
            return True, ""

        def send_notification(self, message, priority="MEDIUM", metadata=None):
            return {"delivered": True, "custom": True}

        def get_queue(self, undelivered_only=True):
            return {"status": "ok", "custom": True}

        def process_queue(self):
            return {"status": "ok", "custom": True}

        def get_status(self):
            return {"name": self.name}

        def health_check(self):
            return {"status": "ok"}

    custom = CustomNotificationsProvider()
    assert isinstance(custom, BaseNotificationsProvider)
    assert custom.name == "custom_notif"
    assert custom.send_notification("hi")["custom"] is True
