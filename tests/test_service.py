"""Unit and integration tests for US-10: Sidecar Daemon Service Lifecycle.

Verifies:
- sidecar/service.py defines a unified service lifecycle that boots sidecar API and APScheduler.
- Clean signal handling and shutdown stops the scheduler and releases resources.
- Job store and execution history persist across service restarts.
- Loopback binding constraint (127.0.0.1) is strictly enforced.
- Live HTTP /health endpoint returns 200 with sidecar and scheduler ok.
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sidecar.pi_bridge import PiTurnResult
from sidecar.service import DEFAULT_HOST, ServiceRunner, create_app


def find_free_port() -> int:
    """Locate an available loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_reject_non_loopback_binding() -> None:
    """Verify binding to public interfaces (0.0.0.0, etc.) is rejected per Law 6 / S-2."""
    with pytest.raises(ValueError, match="non-loopback"):
        ServiceRunner(host="0.0.0.0", port=8420)

    with pytest.raises(ValueError, match="non-loopback"):
        ServiceRunner(host="192.168.1.100", port=8420)


def test_service_lifecycle_and_health_endpoint(tmp_path: Path) -> None:
    """Verify service startup, /health HTTP response, and clean shutdown."""
    locus_home = tmp_path / ".locus"
    jobs_dir = locus_home / "jobs"
    jobs_dir.mkdir(parents=True)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    db_path = locus_home / "cron.db"

    cfg_file = locus_home / "config.yaml"
    cfg_file.write_text(
        yaml.dump({"locus": {"scheduler": {"enabled": True}}}),
        encoding="utf-8",
    )

    # Place a test job
    (jobs_dir / "pulse.yaml").write_text(
        yaml.dump({
            "id": "pulse",
            "name": "System Pulse",
            "schedule": "*/10 * * * *",
            "prompt": "Echo status",
        }),
        encoding="utf-8",
    )

    port = find_free_port()
    runner = ServiceRunner(
        host="127.0.0.1",
        port=port,
        custom_config_path=cfg_file,
        locus_home=locus_home,
        vault_root=vault_root,
        db_path=db_path,
    )

    try:
        runner.start_background()
        assert runner.is_running is True

        # Query /health over live HTTP socket
        url = f"http://127.0.0.1:{port}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"
            assert data["sidecar"] == "ok"
            assert data["scheduler"]["running"] is True
            assert data["scheduler"]["job_count"] == 1

        # Query /jobs endpoint
        jobs_url = f"http://127.0.0.1:{port}/jobs"
        with urllib.request.urlopen(urllib.request.Request(jobs_url), timeout=5) as resp:
            assert resp.status == 200
            jobs_data = json.loads(resp.read().decode("utf-8"))
            assert jobs_data["count"] == 1
            assert jobs_data["jobs"][0]["id"] == "pulse"

    finally:
        runner.stop()
        assert runner.is_running is False


def test_service_restart_persists_jobs_and_history(tmp_path: Path) -> None:
    """Verify job store and execution history persist across service reboots."""
    locus_home = tmp_path / ".locus"
    jobs_dir = locus_home / "jobs"
    jobs_dir.mkdir(parents=True)
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    db_path = locus_home / "cron.db"

    cfg_file = locus_home / "config.yaml"
    cfg_file.write_text(
        yaml.dump({"locus": {"scheduler": {"enabled": True}}}),
        encoding="utf-8",
    )

    (jobs_dir / "persisted_job.yaml").write_text(
        yaml.dump({
            "id": "persisted_job",
            "name": "Persisted Job",
            "schedule": "@hourly",
            "prompt": "Persistent prompt",
            "destination": "vault/05-Daily/Research/persisted.md",
        }),
        encoding="utf-8",
    )

    port = find_free_port()

    # Pass 1: Start service, execute job, and shutdown
    runner1 = ServiceRunner(
        host="127.0.0.1",
        port=port,
        custom_config_path=cfg_file,
        locus_home=locus_home,
        vault_root=vault_root,
        db_path=db_path,
    )

    mock_pi = PiTurnResult(stdout="Output 1", stderr="", returncode=0)
    with patch("sidecar.cron_runner.run_pi_turn", return_value=mock_pi):
        runner1.start_background()
        assert runner1.is_running is True

        # Manually trigger job via API
        run_url = f"http://127.0.0.1:{port}/jobs/persisted_job/run"
        post_req = urllib.request.Request(run_url, data=b"", method="POST")
        with urllib.request.urlopen(post_req, timeout=5) as resp:
            assert resp.status == 200
            run_res = json.loads(resp.read().decode("utf-8"))
            assert run_res["status"] == "success"

        runner1.stop()
        assert runner1.is_running is False

    # Verify log file exists on disk
    assert db_path.exists()

    # Pass 2: Restart service on same state directory
    port2 = find_free_port()
    runner2 = ServiceRunner(
        host="127.0.0.1",
        port=port2,
        custom_config_path=cfg_file,
        locus_home=locus_home,
        vault_root=vault_root,
        db_path=db_path,
    )

    try:
        runner2.start_background()
        assert runner2.is_running is True

        # Check logs endpoint returns previous execution history
        logs_url = f"http://127.0.0.1:{port2}/logs"
        with urllib.request.urlopen(urllib.request.Request(logs_url), timeout=5) as resp:
            assert resp.status == 200
            logs_data = json.loads(resp.read().decode("utf-8"))
            assert logs_data["count"] == 1
            assert logs_data["logs"][0]["job_id"] == "persisted_job"

        # Check jobs still loaded and active
        health_url = f"http://127.0.0.1:{port2}/health"
        with urllib.request.urlopen(urllib.request.Request(health_url), timeout=5) as resp:
            assert resp.status == 200
            h_data = json.loads(resp.read().decode("utf-8"))
            assert h_data["scheduler"]["running"] is True
            assert h_data["scheduler"]["job_count"] == 1

    finally:
        runner2.stop()
        assert runner2.is_running is False
