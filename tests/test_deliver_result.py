"""Unit and integration tests for US-09 (F-0046): Research job delivery via Telegram.

Verifies:
- Finished research jobs dispatch output to paired owner via ChannelProvider when notify=True.
- Notification payload contains job title, status, timestamp, and research body.
- Outputs > 4096 characters are chunked and delivered sequentially without truncation.
- Delivery errors or unconfigured channels log failures in SQLite run log while scheduler continues unaffected.
- Disabling notify skips notification completely.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sidecar.channel_telegram import MAX_TELEGRAM_MESSAGE_LENGTH, TelegramChannelProvider
from sidecar.cron_runner import (
    dispatch_job_notification,
    format_notification_message,
    get_execution_logs,
    run_research_job,
)
from sidecar.pi_bridge import PiTurnResult
from sidecar.registry import get_registry
from sidecar.scheduler import ResearchJob


class MockChannel:
    """Mock ChannelProvider for delivery testing."""

    def __init__(self, allowed_user_ids: list[int] | None = None) -> None:
        self.sent_messages: list[tuple[int | str, str]] = []
        self._allowed_user_ids = allowed_user_ids or [987654321]
        self.pairing_manager = MagicMock()
        self.pairing_manager.get_allowed_user_ids.return_value = self._allowed_user_ids

    def send_message(self, recipient: int | str, text: str, keyboard: any = None) -> bool:
        self.sent_messages.append((recipient, text))
        return True


def test_format_notification_message() -> None:
    """Verify notification format includes title, status, timestamp, and body."""
    msg = format_notification_message(
        job_title="Quantum Computing",
        status="success",
        timestamp="2026-11-27T10:00:00Z",
        body="Major breakthrough in error correction.",
    )
    assert "📊 Research Job: Quantum Computing" in msg
    assert "Status: SUCCESS" in msg
    assert "Timestamp: 2026-11-27T10:00:00Z" in msg
    assert "Major breakthrough in error correction." in msg


def test_dispatch_job_notification_success() -> None:
    """Verify dispatch_job_notification delivers to paired owner."""
    job = ResearchJob(
        id="crypto_analysis",
        name="Crypto Analysis",
        schedule="@daily",
        prompt="Analyze trends",
        notify=True,
    )
    mock_chan = MockChannel(allowed_user_ids=[123456789])

    ok, err = dispatch_job_notification(
        job=job,
        status="success",
        stdout="BTC and ETH network metrics stable.",
        stderr="",
        channel_provider=mock_chan,
    )

    assert ok is True
    assert err is None
    assert len(mock_chan.sent_messages) == 1
    recipient, text = mock_chan.sent_messages[0]
    assert recipient == 123456789
    assert "Crypto Analysis" in text
    assert "BTC and ETH network metrics stable." in text


def test_dispatch_job_notification_notify_disabled() -> None:
    """Verify notify=False skips channel delivery."""
    job = ResearchJob(
        id="silent_job",
        name="Silent Job",
        schedule="@daily",
        prompt="Quiet task",
        notify=False,
    )
    mock_chan = MockChannel()

    ok, err = dispatch_job_notification(
        job=job,
        status="success",
        stdout="Some findings",
        stderr="",
        channel_provider=mock_chan,
    )

    assert ok is True
    assert err is None
    assert len(mock_chan.sent_messages) == 0


def test_dispatch_job_notification_long_text_chunking(tmp_path: Path) -> None:
    """Verify outputs > 4096 characters are properly chunked without loss."""
    # Create long text (e.g. 10,000 chars)
    long_body = "A" * 5000 + "\n\n" + "B" * 5000
    job = ResearchJob(
        id="huge_job",
        name="Huge Analysis",
        schedule="@daily",
        prompt="Deep research",
        notify=True,
    )

    # Use a real TelegramChannelProvider with a mock transport
    transport_calls: list[tuple[any, str]] = []

    def mock_sender(recipient: any, chunk: str, keyboard: any = None) -> bool:
        transport_calls.append((recipient, chunk))
        return True

    channel = TelegramChannelProvider()
    channel._transport_sender = mock_sender
    channel._explicit_token = "TEST_TOKEN"
    channel._connected = True
    channel.is_enabled = MagicMock(return_value=True)

    # Configure pairing
    channel.pairing_manager.get_allowed_user_ids = MagicMock(return_value=[555666777])

    ok, err = dispatch_job_notification(
        job=job,
        status="success",
        stdout=long_body,
        stderr="",
        channel_provider=channel,
    )

    assert ok is True
    assert err is None
    assert len(transport_calls) >= 3  # Header + 2 large chunks
    total_received = "".join(chunk for _, chunk in transport_calls)
    assert "A" * 5000 in total_received
    assert "B" * 5000 in total_received
    for _, chunk in transport_calls:
        assert len(chunk) <= MAX_TELEGRAM_MESSAGE_LENGTH


def test_delivery_failure_recorded_in_run_log_and_scheduler_unaffected(tmp_path: Path) -> None:
    """Verify delivery failure is recorded in SQLite log without crashing run_research_job."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    db_path = tmp_path / "cron.db"

    job = ResearchJob(
        id="failing_delivery_job",
        name="Failing Delivery Job",
        schedule="@daily",
        prompt="Run research",
        notify=True,
    )

    # Broken channel that raises an exception on send
    failing_channel = MockChannel()
    failing_channel.send_message = MagicMock(side_effect=RuntimeError("Network socket timed out"))

    mock_result = PiTurnResult(
        stdout="Solid research output.",
        stderr="",
        returncode=0,
    )

    with patch("sidecar.cron_runner.run_pi_turn", return_value=mock_result):
        res = run_research_job(
            job=job,
            vault_root=vault_root,
            db_path=db_path,
            channel_provider=failing_channel,
        )

        # Run still succeeded in vault write
        assert res["status"] == "success"
        assert res["output_path"] is not None
        assert res["notify_delivered"] is False
        assert "Delivery error" in res["error"]

        # Run log in SQLite reflects the delivery error
        logs = get_execution_logs(db_path)
        assert len(logs) == 1
        assert logs[0]["job_id"] == "failing_delivery_job"
        assert "Delivery error: Channel send_message raised exception: Network socket timed out" in logs[0]["error"]
