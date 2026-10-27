"""
SPEC §17.10 lines 3855-3926:
Integration tests for Graceful Gateway Restart & State Snapshotting Service (F-0047 / US-80).
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_service_restart_status(client: TestClient) -> None:
    """SPEC §17.10 line 3869: "CLASS GatewayLifecycleManager" """
    res = client.get("/gateway/restart/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["available"] is True
    assert "is_shutting_down" in data
    assert "drain_timeout_seconds" in data
    assert "uptime_seconds" in data


def test_service_restart_drain(client: TestClient) -> None:
    """SPEC §17.10 line 3885: "// 2. Drain In-Flight Requests" """
    res = client.post("/gateway/restart/drain")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "remaining_in_flight" in data


def test_service_restart_snapshot(client: TestClient) -> None:
    """SPEC §17.10 line 3892: "// 3. Snapshot In-Memory Session States to Disk" """
    res = client.post("/gateway/restart/snapshot")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "snapshots_saved" in data
    assert "files" in data


def test_service_restart_recovery(client: TestClient) -> None:
    """SPEC §17.10 line 3892: "write_json(f'~/.locus/sessions/recovery/{session.id}.json', snapshot)" """
    res = client.get("/gateway/restart/recovery")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "recovered_sessions" in data
    assert "count" in data


def test_service_restart_initiate(client: TestClient) -> None:
    """SPEC §17.10 lines 3874-3914: "FUNCTION handle_shutdown_signal(signal_type: 'SIGTERM' | 'SIGUSR1' | 'RELOAD'):" """
    payload = {
        "signal_type": "SIGTERM",
        "dry_run": True,
    }
    res = client.post("/gateway/restart/initiate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "gracefully_stopped"
    assert "forensic_id" in data
    assert data["signal"] == "SIGTERM"
    assert data["dry_run"] is True


def test_service_restart_off_switches(client: TestClient) -> None:
    """SPEC §17.10 line 3922: "Modular off-switch returns HTTP 503 when feature is disabled." """
    config.set("locus.graceful_restart.enabled", False)
    try:
        r1 = client.get("/gateway/restart/status")
        assert r1.status_code == 503
        assert "disabled" in r1.json()

        r2 = client.post("/gateway/restart/drain")
        assert r2.status_code == 503

        r3 = client.post("/gateway/restart/snapshot")
        assert r3.status_code == 503

        r4 = client.post("/gateway/restart/initiate", json={})
        assert r4.status_code == 503
    finally:
        config.set("locus.graceful_restart.enabled", True)

    config.set("locus.gateway.graceful_restart.enabled", False)
    try:
        r5 = client.get("/gateway/restart/status")
        assert r5.status_code == 503
    finally:
        config.set("locus.gateway.graceful_restart.enabled", True)
