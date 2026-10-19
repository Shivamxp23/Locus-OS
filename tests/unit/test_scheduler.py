"""
SPEC §12.1-12.5 / §26.1 / F-0058 / US-08: Unit tests for SchedulerProvider and Research Cron Jobs.
Tests:
- SchedulerProvider implements and registers under ('scheduler', 'apscheduler') and ('scheduler', 'cron')
- Loading research jobs defined in YAML under LOCUS_HOME/jobs/<job_id>.yaml per errata D-15
- Unattended execution via run_pi_turn with prompt and session_id='cron_<job_id>'
- Result saved to Obsidian vault under <destination>/<date>-<job_id>.md
- Execution logged to D-4 audit trail under 05-Daily/Logs/audit-<date>.md
- Error containment: failed job logs to audit trail and does not crash or block scheduler
- Off switch behavior when locus.scheduler.enabled is false
"""
from __future__ import annotations

import datetime
from pathlib import Path
import subprocess
import pytest
import yaml

from sidecar import config
from sidecar.registry import get_registry
from sidecar.scheduler import ResearchJob, SchedulerProvider


@pytest.fixture
def clean_locus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated LOCUS_HOME with vault and jobs directories."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    return locus_home


def test_scheduler_registers_in_registry(clean_locus_env: Path):
    """SPEC 12.1-12.5 line 4217: "SchedulerProvider default = node-cron + APScheduler"."""
    reg = get_registry()
    cls_apscheduler = reg.get("scheduler", "apscheduler")
    cls_cron = reg.get("scheduler", "cron")

    assert cls_apscheduler is SchedulerProvider
    assert cls_cron is SchedulerProvider

    scheduler = SchedulerProvider()
    scheduler.initialize()
    health = scheduler.health_check()
    assert health["status"] == "ok"
    assert health["enabled"] is True


def test_loads_research_jobs_from_yaml(clean_locus_env: Path):
    """SPEC D-15 errata: "Jobs are YAML definitions under LOCUS_HOME/jobs/<job_id>.yaml"."""
    jobs_dir = clean_locus_env / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    job_data = {
        "id": "quantum_compiler",
        "name": "Quantum Compiler Research",
        "cron": "0 3 * * *",
        "prompt": "Investigate top 3 compiler passes for topological quantum circuits.",
        "tier": "supervised",
        "allowed_paths": ["04-Captures/Research/Quantum"],
        "budget_max_tokens": 50000,
        "destination": "04-Captures/Research",
    }
    job_file = jobs_dir / "quantum_compiler.yaml"
    job_file.write_text(yaml.dump(job_data), encoding="utf-8")

    scheduler = SchedulerProvider()
    jobs = scheduler.load_jobs()

    assert "quantum_compiler" in jobs
    job = jobs["quantum_compiler"]
    assert job.id == "quantum_compiler"
    assert job.name == "Quantum Compiler Research"
    assert job.cron == "0 3 * * *"
    assert job.prompt == "Investigate top 3 compiler passes for topological quantum circuits."
    assert job.tier == "supervised"
    assert job.budget_max_tokens == 50000
    assert job.destination == "04-Captures/Research"


def test_job_execution_invokes_pi_turn_and_writes_vault_file(clean_locus_env: Path):
    """SPEC 26.1 / D-15: "unattended via run_pi_turn(prompt=job.prompt, session_id='cron_<job_id>')... saved to vault"."""
    jobs_dir = clean_locus_env / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    job_data = {
        "id": "agentic_memory",
        "name": "Agentic Memory Synthesis",
        "cron": "0 2 * * *",
        "prompt": "Synthesize latest findings on graph-based memory indexing.",
        "tier": "readonly",
        "destination": "04-Captures/Research",
    }
    (jobs_dir / "agentic_memory.yaml").write_text(yaml.dump(job_data), encoding="utf-8")

    recorded_calls = []

    def fake_pi_runner(prompt: str, session_id: str | None = None, **kwargs):
        recorded_calls.append({"prompt": prompt, "session_id": session_id})
        return subprocess.CompletedProcess(
            args=["fake-pi"],
            returncode=0,
            stdout="## Agentic Memory Synthesis\nKey finding: Graph indexing scales O(log N).",
            stderr="",
        )

    scheduler = SchedulerProvider(pi_runner=fake_pi_runner)
    scheduler.initialize()

    record = scheduler.trigger_job("agentic_memory")
    assert record is not None
    assert record["status"] == "completed"

    # Assert run_pi_turn was called with the job prompt and session_id
    assert len(recorded_calls) == 1
    assert recorded_calls[0]["prompt"] == "Synthesize latest findings on graph-based memory indexing."
    assert recorded_calls[0]["session_id"] == "cron_agentic_memory"

    # Assert output markdown file was written to vault destination
    today_str = datetime.date.today().isoformat()
    vault_dir = clean_locus_env / "vault"
    expected_file = vault_dir / "04-Captures" / "Research" / f"{today_str}-agentic_memory.md"
    assert expected_file.is_file()
    content = expected_file.read_text(encoding="utf-8")
    assert "# Research Report: Agentic Memory Synthesis" in content
    assert "Key finding: Graph indexing scales O(log N)." in content

    # Assert audit trail entry was recorded
    audit_file = vault_dir / "05-Daily" / "Logs" / f"audit-{today_str}.md"
    assert audit_file.is_file()
    audit_content = audit_file.read_text(encoding="utf-8")
    assert "[CRON] [SUCCESS] job=agentic_memory" in audit_content


def test_job_failure_does_not_block_scheduler_and_records_audit(clean_locus_env: Path):
    """SPEC 04 line 27: "Never fatal: mirroring, notification, and logging failures are logged and swallowed"."""
    jobs_dir = clean_locus_env / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)

    job_data = {
        "id": "failing_job",
        "name": "Failing Research Job",
        "prompt": "This will fail.",
    }
    (jobs_dir / "failing_job.yaml").write_text(yaml.dump(job_data), encoding="utf-8")

    def failing_pi_runner(*args, **kwargs):
        raise RuntimeError("Pi process crashed unexpectedly with SIGSEGV")

    scheduler = SchedulerProvider(pi_runner=failing_pi_runner)
    scheduler.initialize()

    # Trigger should not raise exception
    record = scheduler.trigger_job("failing_job")
    assert record is not None
    assert record["status"] == "failed"
    assert "Pi process crashed unexpectedly with SIGSEGV" in record["error"]

    # Scheduler remains operational
    assert scheduler.health_check()["status"] == "ok"

    # Audit trail recorded the failure
    today_str = datetime.date.today().isoformat()
    audit_file = clean_locus_env / "vault" / "05-Daily" / "Logs" / f"audit-{today_str}.md"
    assert audit_file.is_file()
    assert "[CRON] [FAILURE] job=failing_job" in audit_file.read_text(encoding="utf-8")


def test_disabled_scheduler_suppresses_jobs(clean_locus_env: Path):
    """SPEC 03 / 08 F-0125: "When a feature's enabled switch is false ... jobs are not scheduled"."""
    cfg_path = clean_locus_env / "config.yaml"
    cfg_path.write_text(yaml.dump({"locus": {"scheduler": {"enabled": False}}}), encoding="utf-8")

    jobs_dir = clean_locus_env / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_data = {"id": "dummy_job", "prompt": "do work"}
    (jobs_dir / "dummy_job.yaml").write_text(yaml.dump(job_data), encoding="utf-8")

    calls = []
    scheduler = SchedulerProvider(pi_runner=lambda *a, **k: calls.append(a))
    scheduler.initialize()

    health = scheduler.health_check()
    assert health["status"] == "degraded"
    assert health["enabled"] is False

    # Attempt to trigger job returns None and does not invoke Pi runner
    res = scheduler.trigger_job("dummy_job")
    assert res is None
    assert len(calls) == 0
