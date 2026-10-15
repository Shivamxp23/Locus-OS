"""Locus Scheduler Provider & Job Engine.

Implements SchedulerProvider behind the universal provider registry:
- Loads research jobs matching errata D-15 format from LOCUS_HOME/jobs/ or locus.research.jobs.
- Triggers cron_runner with session_id='cron_<job_id>' executing via run_pi_turn.
- Writes research outputs to vault (e.g. vault/05-Daily/Research/YYYY-MM-DD-<name>.md).
- Records execution run logs in SQLite database.
- Obeys feature toggle locus.scheduler.enabled (fail-closed/no-op when disabled).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from sidecar.config import get as config_get, get_env, is_enabled as config_is_enabled
from sidecar.cron_runner import (
    DEFAULT_DB_FILE,
    get_execution_logs,
    run_research_job,
)
from sidecar.registry import BaseProvider, get_registry

logger = logging.getLogger("sidecar.scheduler")
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ResearchJob:
    """Owner-defined research job conforming to errata D-15."""

    id: str
    name: str
    schedule: str  # e.g. "0 2 * * *" or "@daily" or "*/1 * * * *"
    prompt: str
    tier: str = "supervised"
    allowed_paths: list[str] = field(default_factory=list)
    budget: float = 0.0
    destination: str = "vault/05-Daily/Research/YYYY-MM-DD-<name>.md"
    notify: bool | str = True
    retry: int = 0
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "schedule": self.schedule,
            "prompt": self.prompt,
            "tier": self.tier,
            "allowed_paths": self.allowed_paths,
            "budget": self.budget,
            "destination": self.destination,
            "notify": self.notify,
            "retry": self.retry,
            "enabled": self.enabled,
        }


def load_job_from_dict(d: dict[str, Any], default_id: str = "") -> ResearchJob:
    """Parse dictionary into ResearchJob."""
    job_id = str(d.get("id") or default_id or d.get("name") or "job").strip()
    name = str(d.get("name") or job_id).strip()
    schedule = str(d.get("schedule") or "0 0 * * *").strip()
    prompt = str(d.get("prompt") or "").strip()
    tier = str(d.get("tier") or "supervised").strip()
    allowed_paths = list(d.get("allowed_paths") or [])
    budget = float(d.get("budget") or 0.0)
    destination = str(d.get("destination") or "vault/05-Daily/Research/YYYY-MM-DD-<name>.md").strip()
    notify = d.get("notify", True)
    retry = int(d.get("retry") or 0)
    enabled = bool(d.get("enabled", True))

    return ResearchJob(
        id=job_id,
        name=name,
        schedule=schedule,
        prompt=prompt,
        tier=tier,
        allowed_paths=allowed_paths,
        budget=budget,
        destination=destination,
        notify=notify,
        retry=retry,
        enabled=enabled,
    )


def load_job_from_yaml(path: Path) -> ResearchJob:
    """Load ResearchJob from YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return load_job_from_dict(data, default_id=path.stem)


def parse_cron_trigger(schedule_str: str) -> CronTrigger:
    """Parse schedule expression (including shorthands) into CronTrigger."""
    s = schedule_str.strip()
    shorthands = {
        "@hourly": "0 * * * *",
        "@daily": "0 0 * * *",
        "@weekly": "0 0 * * 0",
        "@monthly": "0 0 1 * *",
    }
    cron_expr = shorthands.get(s, s)
    return CronTrigger.from_crontab(cron_expr)


class SchedulerProvider(BaseProvider):
    """Abstract provider interface for Locus job scheduling."""

    name: str = "scheduler"

    def initialize(self, options: dict[str, Any] | None = None) -> None:
        pass

    def start(self) -> None:
        raise NotImplementedError

    def shutdown(self) -> None:
        raise NotImplementedError

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "latency_ms": 0.0}

    def load_jobs(self, jobs_dir: Path | None = None) -> list[ResearchJob]:
        raise NotImplementedError

    def get_jobs(self) -> list[ResearchJob]:
        raise NotImplementedError

    def run_job_now(self, job_id: str) -> dict[str, Any]:
        raise NotImplementedError


class APSchedulerProvider(SchedulerProvider):
    """Concrete SchedulerProvider backed by APScheduler BackgroundScheduler."""

    def __init__(
        self,
        custom_config_path: Path | None = None,
        locus_home: Path | None = None,
        vault_root: Path | None = None,
        db_path: Path | None = None,
    ) -> None:
        self._config_path = custom_config_path
        self._locus_home = locus_home
        self._vault_root = vault_root
        self._db_path = db_path

        self._scheduler: BackgroundScheduler | None = None
        self._jobs: dict[str, ResearchJob] = {}
        self._is_initialized = False
        self._is_running = False

    @property
    def is_enabled(self) -> bool:
        val = config_get("locus.scheduler.enabled", default=True, custom_path=self._config_path)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "on")
        if isinstance(val, (int, float)):
            return val != 0
        return True

    def _resolve_paths(self) -> tuple[Path, Path, Path, Path]:
        """Resolve locus_home, jobs_dir, vault_root, and db_path."""
        if self._locus_home:
            home = self._locus_home
        else:
            home = Path(get_env("LOCUS_HOME", default=str(Path.home() / ".locus")))

        jobs_dir = home / "jobs"
        vault_root = self._vault_root or (REPO_ROOT / "vault")
        db_path = self._db_path or (home / DEFAULT_DB_FILE)
        return home, jobs_dir, vault_root, db_path

    def load_jobs(self, jobs_dir: Path | None = None) -> list[ResearchJob]:
        """Scan jobs_dir and config for research jobs."""
        _, default_jobs_dir, _, _ = self._resolve_paths()
        target_dir = jobs_dir or default_jobs_dir
        loaded: dict[str, ResearchJob] = {}

        # 1. Scan directory for YAML files
        if target_dir.exists() and target_dir.is_dir():
            for p in sorted(target_dir.iterdir()):
                if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}:
                    try:
                        job = load_job_from_yaml(p)
                        loaded[job.id] = job
                        logger.debug("Loaded job %s from %s", job.id, p)
                    except Exception as e:
                        logger.error("Failed to parse research job from %s: %s", p, e)

        # 2. Check config locus.research.jobs
        config_jobs = config_get("locus.research.jobs", default=[], custom_path=self._config_path)
        if isinstance(config_jobs, list):
            for i, item in enumerate(config_jobs):
                if isinstance(item, dict):
                    try:
                        job = load_job_from_dict(item, default_id=f"cfg_job_{i}")
                        loaded[job.id] = job
                    except Exception as e:
                        logger.error("Failed to parse job from config locus.research.jobs[%s]: %s", i, e)

        self._jobs = loaded
        return list(loaded.values())

    def get_jobs(self) -> list[ResearchJob]:
        return list(self._jobs.values())

    def initialize(self, options: dict[str, Any] | None = None) -> None:
        """Initialize scheduler provider and discover jobs."""
        opts = options or {}
        if "custom_config_path" in opts:
            self._config_path = Path(opts["custom_config_path"])
        if "locus_home" in opts:
            self._locus_home = Path(opts["locus_home"])
        if "vault_root" in opts:
            self._vault_root = Path(opts["vault_root"])
        if "db_path" in opts:
            self._db_path = Path(opts["db_path"])

        self.load_jobs()
        self._is_initialized = True
        logger.info(
            "APSchedulerProvider initialized: enabled=%s, loaded %d jobs",
            self.is_enabled,
            len(self._jobs),
        )

    def start(self) -> None:
        """Start scheduler. If disabled by config, no jobs fire."""
        if not self._is_initialized:
            self.initialize()

        if not self.is_enabled:
            logger.info("Scheduler disabled by locus.scheduler.enabled. Not starting.")
            return

        if self._scheduler and self._scheduler.running:
            return

        self._scheduler = BackgroundScheduler()
        for job in self._jobs.values():
            if not job.enabled:
                logger.info("Job %s is disabled, skipping schedule", job.id)
                continue
            try:
                trigger = parse_cron_trigger(job.schedule)
                self._scheduler.add_job(
                    func=self._execute_job,
                    trigger=trigger,
                    args=[job],
                    id=job.id,
                    name=job.name,
                    replace_existing=True,
                )
                logger.info("Scheduled job '%s' with cron '%s'", job.id, job.schedule)
            except Exception as e:
                logger.error("Failed to schedule job %s with schedule '%s': %s", job.id, job.schedule, e)

        self._scheduler.start()
        self._is_running = True
        logger.info("APScheduler started with %d active jobs", len(self._scheduler.get_jobs()))

    def _execute_job(self, job: ResearchJob) -> dict[str, Any]:
        """Trigger cron_runner to execute research job."""
        _, _, vault_root, db_path = self._resolve_paths()
        return run_research_job(
            job=job,
            vault_root=vault_root,
            db_path=db_path,
            custom_config_path=self._config_path,
        )

    def run_job_now(self, job_id: str) -> dict[str, Any]:
        """Manually trigger a job by ID."""
        if job_id not in self._jobs:
            self.load_jobs()
        if job_id not in self._jobs:
            raise KeyError(f"Job '{job_id}' not found")
        job = self._jobs[job_id]
        return self._execute_job(job)

    def shutdown(self) -> None:
        """Gracefully stop background scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self._is_running = False
        logger.info("APScheduler stopped")

    def health_check(self) -> dict[str, Any]:
        """Health check reporting scheduler status, latency, and job count."""
        t0 = time.perf_counter()
        if not self.is_enabled:
            return {
                "status": "disabled",
                "running": False,
                "job_count": len(self._jobs),
                "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
            }

        running = bool(self._scheduler and self._scheduler.running)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
        return {
            "status": "ok" if running else "stopped",
            "running": running,
            "job_count": len(self._jobs),
            "latency_ms": elapsed_ms,
        }

    def get_execution_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent run logs from database."""
        _, _, _, db_path = self._resolve_paths()
        return get_execution_logs(db_path, limit=limit)


# Register provider in universal registry
_registry = get_registry()
_registry.register("scheduler", "apscheduler", APSchedulerProvider, is_default=True)
