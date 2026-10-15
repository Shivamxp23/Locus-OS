"""Unit tests for Locus Scheduler and Research Jobs (F-0058 / US-08).

Tests:
- ResearchJob dataclass and YAML parsing (errata D-15 format)
- Job discovery from LOCUS_HOME/jobs/ and config
- Cron execution via run_pi_turn with session_id='cron_<job_id>'
- Vault markdown output writing with YAML frontmatter
- SQLite audit logging in cron_executions table
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from sidecar.cron_runner import (
    ensure_cron_db,
    format_vault_markdown,
    get_execution_logs,
    record_cron_execution,
    resolve_vault_destination,
    run_research_job,
)
from sidecar.pi_bridge import PiTurnResult
from sidecar.scheduler import (
    APSchedulerProvider,
    ResearchJob,
    load_job_from_dict,
    load_job_from_yaml,
    parse_cron_trigger,
)


def test_research_job_from_yaml(tmp_path: Path) -> None:
    """Verify loading research job YAML matching errata D-15 format."""
    job_file = tmp_path / "deep_dive.yaml"
    job_data = {
        "id": "deep_dive",
        "name": "Weekly Technology Deep Dive",
        "schedule": "0 2 * * 0",
        "prompt": "Synthesize developments in AI agent frameworks from this week.",
        "tier": "supervised",
        "allowed_paths": ["vault/01-Projects", "vault/03-Resources"],
        "budget": 2.50,
        "destination": "vault/05-Daily/Research/YYYY-MM-DD-ai_agents.md",
        "notify": True,
        "retry": 1,
    }
    job_file.write_text(yaml.dump(job_data), encoding="utf-8")

    job = load_job_from_yaml(job_file)
    assert job.id == "deep_dive"
    assert job.name == "Weekly Technology Deep Dive"
    assert job.schedule == "0 2 * * 0"
    assert "agent frameworks" in job.prompt
    assert job.tier == "supervised"
    assert job.budget == 2.50
    assert job.destination == "vault/05-Daily/Research/YYYY-MM-DD-ai_agents.md"
    assert job.notify is True
    assert job.retry == 1
    assert job.enabled is True


def test_research_job_from_dict_defaults() -> None:
    """Verify fallback defaults for minimal research job dict."""
    minimal = {
        "name": "Quick Pulse",
        "schedule": "@hourly",
        "prompt": "Check market signals.",
    }
    job = load_job_from_dict(minimal, default_id="quick_pulse")
    assert job.id == "quick_pulse"
    assert job.name == "Quick Pulse"
    assert job.schedule == "@hourly"
    assert job.tier == "supervised"
    assert job.budget == 0.0
    assert job.retry == 0
    assert job.enabled is True


def test_parse_cron_trigger() -> None:
    """Verify parse_cron_trigger correctly handles standard and shorthand expressions."""
    t1 = parse_cron_trigger("*/15 * * * *")
    assert t1 is not None

    t2 = parse_cron_trigger("@daily")
    assert t2 is not None

    t3 = parse_cron_trigger("@hourly")
    assert t3 is not None


def test_resolve_vault_destination(tmp_path: Path) -> None:
    """Verify date token and name token expansion in destination path."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    resolved = resolve_vault_destination(
        destination_template="vault/05-Daily/Research/YYYY-MM-DD-<name>.md",
        job_id="quantum_crypto",
        vault_root=vault_root,
    )

    assert "05-Daily" in str(resolved)
    assert "Research" in str(resolved)
    assert "quantum_crypto.md" in str(resolved)
    assert "YYYY-MM-DD" not in str(resolved)


def test_format_vault_markdown() -> None:
    """Verify markdown output has required YAML frontmatter."""
    md = format_vault_markdown(
        title="Autonomous Computing",
        content="Here are the empirical findings.",
        job_id="auto_comp",
        tags=["research", "ai"],
    )

    assert md.startswith("---\n")
    assert 'title: "Autonomous Computing"' in md
    assert "source: locus-scheduler" in md
    assert 'job_id: "auto_comp"' in md
    assert "  - research" in md
    assert "  - ai" in md
    assert "---\n\nHere are the empirical findings." in md


def test_sqlite_cron_execution_logging(tmp_path: Path) -> None:
    """Verify execution details are recorded in cron_executions table."""
    db_path = tmp_path / "cron.db"
    ensure_cron_db(db_path)

    row_id = record_cron_execution(
        db_path=db_path,
        job_id="test_run",
        status="success",
        returncode=0,
        token_usage=1420,
        output_path="/path/to/note.md",
        error=None,
    )
    assert row_id > 0

    logs = get_execution_logs(db_path)
    assert len(logs) == 1
    log = logs[0]
    assert log["job_id"] == "test_run"
    assert log["status"] == "success"
    assert log["returncode"] == 0
    assert log["token_usage"] == 1420
    assert log["output_path"] == "/path/to/note.md"
    assert log["error"] is None
    assert log["timestamp"] is not None


def test_cron_runner_writes_vault_and_log(tmp_path: Path) -> None:
    """Verify run_research_job executes turn, writes vault file, and logs audit record."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    db_path = tmp_path / "cron.db"

    job = ResearchJob(
        id="sample_job",
        name="Sample Topic",
        schedule="0 * * * *",
        prompt="Synthesize research data.",
        destination="vault/05-Daily/Research/sample_out.md",
    )

    mock_result = PiTurnResult(
        stdout="# Findings\n\nKey finding: efficiency improved by 40%.",
        stderr="",
        returncode=0,
    )

    with patch("sidecar.cron_runner.run_pi_turn", return_value=mock_result) as mock_pi:
        res = run_research_job(
            job=job,
            vault_root=vault_root,
            db_path=db_path,
        )

        assert res["status"] == "success"
        assert res["returncode"] == 0
        mock_pi.assert_called_once_with(
            prompt="Synthesize research data.",
            session_id="cron_sample_job",
            timeout=300,
        )

        out_path = Path(res["output_path"])
        assert out_path.exists()
        content = out_path.read_text(encoding="utf-8")
        assert 'title: "Sample Topic"' in content
        assert "Key finding: efficiency improved by 40%." in content

        logs = get_execution_logs(db_path)
        assert len(logs) == 1
        assert logs[0]["job_id"] == "sample_job"
        assert logs[0]["status"] == "success"


def test_cron_runner_handles_failure(tmp_path: Path) -> None:
    """Verify run_research_job handles non-zero return code and records failure in log."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    db_path = tmp_path / "cron.db"

    job = ResearchJob(
        id="failing_job",
        name="Failing Job",
        schedule="0 * * * *",
        prompt="Trigger failure.",
    )

    mock_result = PiTurnResult(
        stdout="",
        stderr="Model rate limited or timeout exceeded",
        returncode=1,
    )

    with patch("sidecar.cron_runner.run_pi_turn", return_value=mock_result):
        res = run_research_job(
            job=job,
            vault_root=vault_root,
            db_path=db_path,
        )

        assert res["status"] == "failed"
        assert res["returncode"] == 1
        assert "Model rate limited" in res["error"]
        assert res["output_path"] is None

        logs = get_execution_logs(db_path)
        assert len(logs) == 1
        assert logs[0]["job_id"] == "failing_job"
        assert logs[0]["status"] == "failed"
        assert "Model rate limited" in logs[0]["error"]
