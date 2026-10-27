"""Unit tests for Graceful Gateway Restart & State Snapshotting (§17.10)."""

import pathlib
import tempfile
import time
from unittest.mock import patch
import pytest

from sidecar.gateway.lifecycle import (
    ForensicRecord,
    GatewayLifecycleManager,
    MockChannelAdapter,
    SessionSnapshot,
)
from sidecar.providers.graceful_restart import DefaultGracefulRestartProvider


def test_lifecycle_manager_in_flight_tracking():
    """SPEC §17.10 line 3869: "active_in_flight_requests: Set[string]" """
    mgr = GatewayLifecycleManager()
    assert len(mgr.active_in_flight_requests) == 0

    mgr.register_in_flight("req_001")
    mgr.register_in_flight("req_002")
    assert len(mgr.active_in_flight_requests) == 2
    assert "req_001" in mgr.active_in_flight_requests

    mgr.unregister_in_flight("req_001")
    assert len(mgr.active_in_flight_requests) == 1
    assert "req_002" in mgr.active_in_flight_requests


def test_lifecycle_manager_drain_and_timeout():
    """SPEC §17.10 line 3885: "// 2. Drain In-Flight Requests WHILE len(self.active_in_flight_requests) > 0" """
    mgr = GatewayLifecycleManager(drain_timeout_seconds=0.1)
    mgr.register_in_flight("req_drain_1")

    # Draining will timeout after 0.1s and return 1 remaining
    remaining = mgr.drain_connections(check_interval=0.01)
    assert remaining == 1

    # Now unregister and drain again
    mgr.unregister_in_flight("req_drain_1")
    remaining_clean = mgr.drain_connections(check_interval=0.01)
    assert remaining_clean == 0


def test_lifecycle_session_snapshotting_and_recovery():
    """SPEC §17.10 line 3892: "// 3. Snapshot In-Memory Session States to Disk" """
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GatewayLifecycleManager(recovery_dir=tmpdir)
        mgr.register_session("sess_101", user_id="alice", channel="telegram", state_data={"topic": "antigravity"})
        mgr.register_session("sess_102", user_id="bob", channel="discord", state_data={"topic": "research"})

        saved_files = mgr.snapshot_sessions()
        assert len(saved_files) == 2

        # Create new manager pointing to same recovery directory and recover
        new_mgr = GatewayLifecycleManager(recovery_dir=tmpdir)
        recovered = new_mgr.recover_sessions()
        assert len(recovered) == 2
        r_ids = {s.session_id for s in recovered}
        assert "sess_101" in r_ids
        assert "sess_102" in r_ids
        assert new_mgr.active_sessions["sess_101"].user_id == "alice"


def test_lifecycle_shutdown_forensics():
    """SPEC §17.10 line 3898: "// 4. Record Forensic Log in Database" """
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GatewayLifecycleManager(forensics_dir=tmpdir)
        mgr.register_session("sess_999", user_id="test", channel="cli")
        mgr.register_in_flight("req_999")

        record = mgr.log_shutdown_forensics(signal_type="SIGTERM")
        assert isinstance(record, ForensicRecord)
        assert record.reason == "SIGTERM"
        assert record.active_sessions_count == 1
        assert record.pending_events == 1
        assert record.uptime_seconds >= 0.0

        files = list(pathlib.Path(tmpdir).glob("*.json"))
        assert len(files) == 1


def test_swappable_channel_adapters():
    """SPEC §17.10 line 3881: "// 1. Stop Ingress (De-register webhook / stop polling)" """
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GatewayLifecycleManager(recovery_dir=tmpdir, forensics_dir=tmpdir)
        tg_adapter = MockChannelAdapter(name="telegram")
        dc_adapter = MockChannelAdapter(name="discord")
        mgr.register_adapter(tg_adapter)
        mgr.register_adapter(dc_adapter)

        res = mgr.handle_shutdown_signal(signal_type="SIGUSR1", dry_run=True)
        assert res["status"] == "gracefully_stopped"
        assert tg_adapter.stopped is True
        assert dc_adapter.stopped is True
        assert "telegram" in res["stopped_adapters"]
        assert "discord" in res["stopped_adapters"]
        assert mgr.db_pools_closed is True


def test_graceful_restart_modular_off_switches():
    """SPEC §17.10 line 3922: "Swappable / off state: locus.gateway.graceful_restart.enabled." """
    provider = DefaultGracefulRestartProvider()
    assert provider.is_available() is True
    status = provider.get_status()
    assert status["available"] is True

    # Test locus.graceful_restart.enabled off
    with patch("sidecar.config.get", return_value="false"):
        with patch("sidecar.config.is_enabled", return_value=False):
            assert provider.is_available() is False
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.initiate_shutdown()
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.drain_connections()
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.snapshot_sessions()
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.recover_sessions()
            with pytest.raises(RuntimeError, match="disabled by modular off-switch"):
                provider.get_status()
