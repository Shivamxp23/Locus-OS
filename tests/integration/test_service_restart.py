"""
SPEC §12.1-12.5 / §02 / F-0058 / US-10: Integration Tests for Headless Service and Restart Persistence.
Tests:
- HeadlessService starts FastAPI sidecar, Pi bridge, and SchedulerProvider in a single headless process.
- Job definitions and schedules persist in SQLite under LOCUS_HOME across service restarts.
- On restart, existing jobs are reloaded and execution schedules (next_run_time) remain intact.
- Graceful shutdown stops workers cleanly and flushes state.
"""
from __future__ import annotations

import datetime
from pathlib import Path
import sqlite3
import subprocess
from fastapi.testclient import TestClient
import pytest
import yaml

from sidecar.scheduler import ResearchJob, SchedulerProvider
from sidecar.service import HeadlessService, create_app


@pytest.fixture
def clean_locus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated LOCUS_HOME environment."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    return locus_home


def test_headless_service_starts_fastapi_and_scheduler(clean_locus_env: Path):
    """SPEC §12.1-12.5 line 4217 / §02: HeadlessService starts FastAPI sidecar, Pi bridge, and scheduler in a single process."""
    # Write a research job YAML in LOCUS_HOME/jobs
    jobs_dir = clean_locus_env / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_data = {
        "id": "morning_brief",
        "name": "Morning Briefing",
        "cron": "0 6 * * *",
        "prompt": "Synthesize overnight updates.",
        "tier": "readonly",
        "destination": "05-Daily/Briefs",
    }
    (jobs_dir / "morning_brief.yaml").write_text(yaml.dump(job_data), encoding="utf-8")

    scheduler = SchedulerProvider()
    service = HeadlessService(scheduler=scheduler)
    service.start()
    assert service.is_running() is True

    client = TestClient(service.app)

    # Health endpoint check
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "locus-headless-service"
    assert data["jobs_count"] >= 1
    assert data["scheduler"]["enabled"] is True

    # Jobs endpoint check
    resp_jobs = client.get("/jobs")
    assert resp_jobs.status_code == 200
    jobs_list = resp_jobs.json()["jobs"]
    assert len(jobs_list) == 1
    assert jobs_list[0]["id"] == "morning_brief"
    assert jobs_list[0]["next_run_time"] is not None

    service.stop()
    assert service.is_running() is False


def test_job_store_persists_in_sqlite_across_service_restart(clean_locus_env: Path):
    """SPEC §12.1-12.5 / US-10: Schedule a test job, stop the scheduler service, restart it, and assert the job is loaded from SQLite with its next execution schedule intact."""
    db_path = clean_locus_env / "scheduler.db"

    # Step 1: Initial service start with a new research job
    initial_scheduler = SchedulerProvider()
    initial_service = HeadlessService(scheduler=initial_scheduler)
    initial_service.start()

    test_job = ResearchJob(
        id="weekly_neuro_synthesis",
        name="Weekly Neuro Synthesis",
        cron="0 2 * * 0",  # Sunday at 02:00
        prompt="Analyze weekly cognitive rhythms.",
        destination="05-Daily/Weekly",
    )
    initial_scheduler.add_job(test_job)

    # Assert job is scheduled and next_run_time is computed
    job_before_restart = initial_scheduler.get_job("weekly_neuro_synthesis")
    assert job_before_restart is not None
    next_run_before = job_before_restart.next_run_time
    assert next_run_before is not None

    # Step 2: Graceful stop of the service
    initial_service.stop()
    assert initial_service.is_running() is False

    # Verify SQLite database contains the persisted job record
    assert db_path.is_file()
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("SELECT id, name, next_run_time FROM jobs WHERE id = ?", ("weekly_neuro_synthesis",))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "weekly_neuro_synthesis"
        assert row[1] == "Weekly Neuro Synthesis"
        assert row[2] == next_run_before

    # Step 3: Restart service (simulate process restart with a fresh instance)
    mock_runner_executed = []

    def mock_pi_runner(prompt: str, session_id: str | None = None, **kwargs):
        mock_runner_executed.append((prompt, session_id))
        return subprocess.CompletedProcess(
            args=["fake-pi"],
            returncode=0,
            stdout="# Weekly Neuro Synthesis Result\nCognitive load was stable.",
            stderr="",
        )

    restarted_scheduler = SchedulerProvider(pi_runner=mock_pi_runner)
    restarted_service = HeadlessService(scheduler=restarted_scheduler)
    restarted_service.start()
    assert restarted_service.is_running() is True

    # Assert job is retained across the restart with schedule intact
    restarted_job = restarted_scheduler.get_job("weekly_neuro_synthesis")
    assert restarted_job is not None
    assert restarted_job.id == "weekly_neuro_synthesis"
    assert restarted_job.name == "Weekly Neuro Synthesis"
    assert restarted_job.next_run_time == next_run_before

    # Assert job still fires properly in restarted service
    run_record = restarted_scheduler.trigger_job("weekly_neuro_synthesis")
    assert run_record is not None
    assert run_record["status"] == "completed"
    assert len(mock_runner_executed) == 1
    assert "cron_weekly_neuro_synthesis" in mock_runner_executed[0][1]

    # Verify output written to vault
    today_str = datetime.date.today().isoformat()
    vault_file = clean_locus_env / "vault" / "05-Daily" / "Weekly" / f"{today_str}-weekly_neuro_synthesis.md"
    assert vault_file.is_file()

    restarted_service.stop()
    assert restarted_service.is_running() is False


def test_service_api_trigger_job(clean_locus_env: Path):
    """SPEC §12.1-12.5: Test trigger of job via HTTP endpoint in HeadlessService."""
    scheduler = SchedulerProvider(pi_runner=lambda *a, **k: "API trigger test succeeded.")
    service = HeadlessService(scheduler=scheduler)
    service.start()

    job = ResearchJob(
        id="api_test_job",
        name="API Test Job",
        cron="0 12 * * *",
        prompt="Test API trigger.",
    )
    scheduler.add_job(job)

    client = TestClient(service.app)

    # Trigger job through API
    resp = client.post("/jobs/api_test_job/trigger")
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "ok"
    assert res_data["record"]["status"] == "completed"

    # Trigger nonexistent job returns 404
    resp_404 = client.post("/jobs/nonexistent_job/trigger")
    assert resp_404.status_code == 404

    service.stop()
