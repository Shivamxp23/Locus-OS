"""Modularity tests for Locus SchedulerProvider (F-0058 / US-08).

Enforces the three mandatory modularity tests required by modularity spec (agent doc 03):
1. test_scheduler_off: enabled=false -> jobs not scheduled, health_check reports disabled.
2. test_scheduler_swap: register fake provider under another name, set locus.scheduler.provider, assert fake is active.
3. test_scheduler_health: health_check() returns status, latency_ms, and running indicator.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from sidecar.cron_runner import run_research_job
from sidecar.registry import BaseProvider, FeatureDisabledError, get_registry
from sidecar.scheduler import APSchedulerProvider, ResearchJob, SchedulerProvider


class FakeSchedulerProvider(SchedulerProvider):
    """Custom fake scheduler provider for swap verification."""

    name: str = "fake_scheduler"

    def __init__(self, **kwargs: Any) -> None:
        self.started = False
        self.jobs: list[ResearchJob] = []

    def initialize(self, options: dict[str, Any] | None = None) -> None:
        pass

    def start(self) -> None:
        self.started = True

    def shutdown(self) -> None:
        self.started = False

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "provider": "fake_scheduler", "latency_ms": 0.1}

    def load_jobs(self, jobs_dir: Path | None = None) -> list[ResearchJob]:
        return self.jobs

    def get_jobs(self) -> list[ResearchJob]:
        return self.jobs

    def run_job_now(self, job_id: str) -> dict[str, Any]:
        return {"job_id": job_id, "status": "fake_success"}


def test_scheduler_off(tmp_path: Path) -> None:
    """Verify off behavior: when disabled, no jobs start, health reports disabled."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump({"locus": {"scheduler": {"enabled": False}}}),
        encoding="utf-8",
    )

    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    (jobs_dir / "job1.yaml").write_text(
        yaml.dump({"name": "Job 1", "schedule": "* * * * *", "prompt": "test"}),
        encoding="utf-8",
    )

    provider = APSchedulerProvider(
        custom_config_path=cfg_file,
        locus_home=tmp_path,
    )
    provider.initialize()
    assert len(provider.get_jobs()) == 1

    # Calling start should not start scheduler background thread
    provider.start()
    health = provider.health_check()
    assert health["status"] == "disabled"
    assert health["running"] is False

    # Calling run_research_job directly also short-circuits with disabled
    res = run_research_job(
        job=provider.get_jobs()[0],
        custom_config_path=cfg_file,
    )
    assert res["status"] == "disabled"
    assert "disabled" in res["error"]


def test_scheduler_swap(tmp_path: Path) -> None:
    """Verify provider swapping: register fake provider, set config key, assert fake is called."""
    registry = get_registry()
    registry.register("scheduler", "fake", FakeSchedulerProvider)

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        yaml.dump({"locus": {"scheduler": {"enabled": True, "provider": "fake"}}}),
        encoding="utf-8",
    )

    resolved = registry.get(
        interface="scheduler",
        config_key="locus.scheduler",
        custom_config_path=cfg_file,
    )

    assert isinstance(resolved, FakeSchedulerProvider)
    assert resolved.health_check()["provider"] == "fake_scheduler"


def test_scheduler_health() -> None:
    """Verify health_check returns status, latency_ms, and running indicator."""
    provider = APSchedulerProvider()
    health_before = provider.health_check()
    assert health_before["status"] in ("ok", "stopped")
    assert "latency_ms" in health_before
    assert isinstance(health_before["latency_ms"], float)
    assert health_before["running"] is False
