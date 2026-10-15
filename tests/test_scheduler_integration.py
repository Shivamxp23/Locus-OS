"""Integration tests for Locus Scheduler and Research Cron Jobs (F-0058 / US-08).

Simulates the Sprint Review live demo workflow:
1. Creates a test research job in LOCUS_HOME/jobs/test_research.yaml.
2. Initializes and starts the scheduler with destination in vault/05-Daily/Research/test.md.
3. Fires the job turn via mock Pi bridge.
4. Verifies the markdown file is created in vault with required YAML frontmatter and Pi content.
5. Verifies execution run record is logged in SQLite cron_executions table.
6. Gracefully shuts down the scheduler.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sidecar.cron_runner import get_execution_logs
from sidecar.pi_bridge import PiTurnResult
from sidecar.scheduler import APSchedulerProvider


def test_scheduler_end_to_end(tmp_path: Path) -> None:
    """Full lifecycle integration test of scheduler and research cron."""
    locus_home = tmp_path / ".locus"
    jobs_dir = locus_home / "jobs"
    jobs_dir.mkdir(parents=True)

    vault_root = tmp_path / "vault"
    vault_daily = vault_root / "05-Daily" / "Research"
    vault_daily.mkdir(parents=True)

    db_path = locus_home / "cron.db"
    cfg_file = locus_home / "config.yaml"
    cfg_file.write_text(
        yaml.dump({"locus": {"scheduler": {"enabled": True}}}),
        encoding="utf-8",
    )

    # 1. Place test research job in LOCUS_HOME/jobs/
    test_job_file = jobs_dir / "test_research.yaml"
    test_job_data = {
        "id": "test_research",
        "name": "Automated Market Intelligence",
        "schedule": "* * * * *",
        "prompt": "Evaluate latest AI agent ecosystem signals.",
        "tier": "supervised",
        "destination": "vault/05-Daily/Research/test.md",
    }
    test_job_file.write_text(yaml.dump(test_job_data), encoding="utf-8")

    # 2. Configure provider
    provider = APSchedulerProvider(
        custom_config_path=cfg_file,
        locus_home=locus_home,
        vault_root=vault_root,
        db_path=db_path,
    )
    provider.initialize()

    jobs = provider.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "test_research"

    # Mock Pi turn output
    mock_pi_result = PiTurnResult(
        stdout="# Market Intelligence Report\n\n- Key trend: Headless orchestration adoption up 65%.",
        stderr="",
        returncode=0,
    )

    with patch("sidecar.cron_runner.run_pi_turn", return_value=mock_pi_result) as mock_turn:
        # Start scheduler
        provider.start()
        health = provider.health_check()
        assert health["status"] == "ok"
        assert health["running"] is True
        assert health["job_count"] == 1

        # Trigger job execution
        res = provider.run_job_now("test_research")
        assert res["status"] == "success"
        assert res["returncode"] == 0

        # Verify Pi turn invocation
        mock_turn.assert_called_once_with(
            prompt="Evaluate latest AI agent ecosystem signals.",
            session_id="cron_test_research",
            timeout=300,
        )

        # 4. Verify test.md in vault
        test_md = vault_daily / "test.md"
        assert test_md.exists()
        content = test_md.read_text(encoding="utf-8")
        assert 'title: "Automated Market Intelligence"' in content
        assert "source: locus-scheduler" in content
        assert 'job_id: "test_research"' in content
        assert "Headless orchestration adoption up 65%." in content

        # 5. Verify SQLite run log
        logs = provider.get_execution_logs()
        assert len(logs) == 1
        assert logs[0]["job_id"] == "test_research"
        assert logs[0]["status"] == "success"
        assert logs[0]["returncode"] == 0
        assert logs[0]["output_path"] == str(test_md.resolve())

        # 6. Shutdown
        provider.shutdown()
        assert provider.health_check()["running"] is False
