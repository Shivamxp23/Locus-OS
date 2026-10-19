"""
SPEC §12.1-12.5 / §26.1 / F-0058 / US-08: SchedulerProvider and Research Cron Jobs.
Implements:
- SchedulerProvider registered under ('scheduler', 'apscheduler') and ('scheduler', 'cron')
- Loading research jobs defined in YAML under LOCUS_HOME/jobs/<job_id>.yaml (per D-15)
- Unattended execution via run_pi_turn(prompt=job.prompt, session_id='cron_<job_id>')
- Writing results to Obsidian vault under <destination>/<date>-<job_id>.md
- Writing execution records to the D-4 audit trail
- Error containment: failed job logs to audit trail and never blocks subsequent jobs
- Off-switch behavior when locus.scheduler.enabled is false
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
import json
import pathlib
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional
import yaml

from sidecar import config
from sidecar.pi_bridge import run_pi_turn
from sidecar.providers.channel import BaseChannelProvider
from sidecar.registry import get_registry
from sidecar.telegram.pairing import PairingManager


@dataclass
class ResearchJob:
    """Owner-defined research cron job specification per errata D-15."""
    id: str
    name: str
    cron: str
    prompt: str
    tier: str = "supervised"  # readonly | supervised | full
    allowed_paths: List[str] = field(default_factory=list)
    budget_max_tokens: int = 100000
    destination: str = "04-Captures/Research"
    enabled: bool = True
    next_run_time: Optional[str] = None
    last_run_time: Optional[str] = None

    def compute_next_run_time(self, base_time: Optional[datetime.datetime] = None) -> Optional[str]:
        """Compute the next ISO execution timestamp using cron trigger."""
        if not self.cron:
            return None
        try:
            from apscheduler.triggers.cron import CronTrigger
            trigger = CronTrigger.from_crontab(self.cron)
            now = base_time or datetime.datetime.now(datetime.timezone.utc)
            nxt = trigger.get_next_fire_time(None, now)
            if nxt:
                self.next_run_time = nxt.isoformat()
                return self.next_run_time
        except Exception:
            pass
        return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchJob":
        job = cls(
            id=str(data.get("id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            cron=str(data.get("cron", "0 2 * * *")).strip(),
            prompt=str(data.get("prompt", "")).strip(),
            tier=str(data.get("tier", "supervised")).strip(),
            allowed_paths=list(data.get("allowed_paths", [])),
            budget_max_tokens=int(data.get("budget_max_tokens", 100000)),
            destination=str(data.get("destination", "04-Captures/Research")).strip(),
            enabled=bool(data.get("enabled", True)),
            next_run_time=data.get("next_run_time"),
            last_run_time=data.get("last_run_time"),
        )
        if not job.next_run_time:
            job.compute_next_run_time()
        return job

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "cron": self.cron,
            "prompt": self.prompt,
            "tier": self.tier,
            "allowed_paths": self.allowed_paths,
            "budget_max_tokens": self.budget_max_tokens,
            "destination": self.destination,
            "enabled": self.enabled,
            "next_run_time": self.next_run_time,
            "last_run_time": self.last_run_time,
        }


class SchedulerProvider:
    """
    Autonomous research scheduler and job executor.
    Wires cron execution into the headless Pi bridge, persists results to the vault,
    and delivers execution notifications to the paired owner via Telegram.
    """

    def __init__(
        self,
        pi_runner: Optional[Callable[..., Any]] = None,
        channel_provider: Optional[BaseChannelProvider] = None,
        pairing_manager: Optional[PairingManager] = None,
    ) -> None:
        self._pi_runner = pi_runner or run_pi_turn
        self._channel_provider = channel_provider
        self.pairing_manager = pairing_manager or PairingManager()
        self._jobs: Dict[str, ResearchJob] = {}
        self._enabled: bool = True
        self._running: bool = False
        self._execution_history: List[Dict[str, Any]] = []

    def set_pi_runner(self, pi_runner: Optional[Callable[..., Any]]) -> None:
        """Inject Pi runner callable for testing."""
        self._pi_runner = pi_runner or run_pi_turn

    def set_channel_provider(self, channel_provider: Optional[BaseChannelProvider]) -> None:
        """Inject ChannelProvider for delivery testing."""
        self._channel_provider = channel_provider

    def get_jobs_dir(self) -> pathlib.Path:
        """Resolve directory containing owner job definitions."""
        locus_home = config.get_locus_home()
        jobs_dir = locus_home / "jobs"
        jobs_dir.mkdir(parents=True, exist_ok=True)
        return jobs_dir

    def get_vault_dir(self) -> pathlib.Path:
        """Resolve root directory of the Obsidian vault."""
        vault_cfg = config.get("locus.vault.path")
        if vault_cfg:
            p = pathlib.Path(str(vault_cfg))
        else:
            p = config.get_locus_home() / "vault"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_db_path(self) -> pathlib.Path:
        """Resolve path to SQLite job store."""
        locus_home = config.get_locus_home()
        locus_home.mkdir(parents=True, exist_ok=True)
        return locus_home / "scheduler.db"

    def _init_db(self) -> None:
        """Initialize SQLite table for persistent job definitions and schedules."""
        db_path = self.get_db_path()
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    cron TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    tier TEXT DEFAULT 'supervised',
                    allowed_paths TEXT DEFAULT '[]',
                    budget_max_tokens INTEGER DEFAULT 100000,
                    destination TEXT DEFAULT '04-Captures/Research',
                    enabled INTEGER DEFAULT 1,
                    next_run_time TEXT,
                    last_run_time TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            conn.commit()

    def save_job_to_db(self, job: ResearchJob) -> None:
        """Persist or update a research job definition and schedule in SQLite."""
        self._init_db()
        db_path = self.get_db_path()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, name, cron, prompt, tier, allowed_paths,
                    budget_max_tokens, destination, enabled,
                    next_run_time, last_run_time, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    cron=excluded.cron,
                    prompt=excluded.prompt,
                    tier=excluded.tier,
                    allowed_paths=excluded.allowed_paths,
                    budget_max_tokens=excluded.budget_max_tokens,
                    destination=excluded.destination,
                    enabled=excluded.enabled,
                    next_run_time=excluded.next_run_time,
                    last_run_time=coalesce(excluded.last_run_time, jobs.last_run_time),
                    updated_at=excluded.updated_at
                """,
                (
                    job.id,
                    job.name,
                    job.cron,
                    job.prompt,
                    job.tier,
                    json.dumps(job.allowed_paths),
                    job.budget_max_tokens,
                    job.destination,
                    1 if job.enabled else 0,
                    job.next_run_time,
                    job.last_run_time,
                    now_iso,
                ),
            )
            conn.commit()

    def load_jobs_from_db(self) -> Dict[str, ResearchJob]:
        """Load all job definitions and schedules from SQLite."""
        self._init_db()
        db_path = self.get_db_path()
        loaded: Dict[str, ResearchJob] = {}
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM jobs")
            for row in cursor.fetchall():
                try:
                    paths = json.loads(row["allowed_paths"]) if row["allowed_paths"] else []
                except Exception:
                    paths = []
                job = ResearchJob(
                    id=row["id"],
                    name=row["name"],
                    cron=row["cron"],
                    prompt=row["prompt"],
                    tier=row["tier"] or "supervised",
                    allowed_paths=paths,
                    budget_max_tokens=int(row["budget_max_tokens"] or 100000),
                    destination=row["destination"] or "04-Captures/Research",
                    enabled=bool(row["enabled"]),
                    next_run_time=row["next_run_time"],
                    last_run_time=row["last_run_time"],
                )
                loaded[job.id] = job
        return loaded

    def add_job(self, job: ResearchJob) -> None:
        """Add or update a job in memory and persist to SQLite."""
        if not job.next_run_time:
            job.compute_next_run_time()
        self._jobs[job.id] = job
        self.save_job_to_db(job)

    def get_job(self, job_id: str) -> Optional[ResearchJob]:
        """Retrieve a job by ID from memory or DB."""
        if job_id in self._jobs:
            return self._jobs[job_id]
        db_jobs = self.load_jobs_from_db()
        return db_jobs.get(job_id)

    def list_jobs(self) -> List[ResearchJob]:
        """Return all managed jobs."""
        return list(self._jobs.values())

    def load_jobs(self) -> Dict[str, ResearchJob]:
        """
        Load research jobs from SQLite store and sync from YAML definitions in LOCUS_HOME/jobs/.
        Persists all definitions in SQLite across service restarts.
        """
        self._init_db()
        loaded = self.load_jobs_from_db()

        # Sync from YAML files if present
        jobs_dir = self.get_jobs_dir()
        for file_path in jobs_dir.glob("*.y*ml"):
            try:
                content = file_path.read_text(encoding="utf-8")
                raw = yaml.safe_load(content)
                if isinstance(raw, dict) and "prompt" in raw:
                    job_id = str(raw.get("id") or file_path.stem).strip()
                    raw["id"] = job_id
                    yaml_job = ResearchJob.from_dict(raw)
                    if job_id in loaded:
                        db_job = loaded[job_id]
                        yaml_job.last_run_time = db_job.last_run_time
                        if db_job.next_run_time:
                            yaml_job.next_run_time = db_job.next_run_time
                    if not yaml_job.next_run_time:
                        yaml_job.compute_next_run_time()
                    loaded[job_id] = yaml_job
                    self.save_job_to_db(yaml_job)
            except Exception:
                continue

        # Ensure all loaded jobs have a next_run_time
        for job in loaded.values():
            if not job.next_run_time:
                job.compute_next_run_time()
                self.save_job_to_db(job)

        self._jobs = loaded
        return loaded

    def initialize(self, options: Optional[Dict[str, Any]] = None) -> None:
        """Initialize scheduler provider and load configured jobs."""
        opts = options or {}
        self._enabled = config.is_enabled("locus.scheduler.enabled")
        if config.get("locus.scheduler.enabled") is None:
            self._enabled = opts.get("enabled", True)

        if not self._enabled:
            self._running = False
            return

        self.load_jobs()
        self._running = True

    def shutdown(self) -> None:
        """Cleanly shutdown the scheduler."""
        self._running = False

    def health_check(self) -> Dict[str, Any]:
        """
        Return health metrics and registered job count.
        Returns status ('ok', 'degraded', 'error').
        """
        start = time.perf_counter()
        if not self._enabled:
            return {
                "status": "degraded",
                "provider": "scheduler",
                "enabled": False,
                "latency_ms": 0.0,
                "message": "Scheduler is disabled in configuration",
            }

        latency_ms = (time.perf_counter() - start) * 1000.0
        return {
            "status": "ok",
            "provider": "scheduler",
            "enabled": True,
            "jobs_count": len(self._jobs),
            "jobs": list(self._jobs.keys()),
            "latency_ms": round(latency_ms, 3),
        }

    def append_audit_trail(self, job: ResearchJob, success: bool, details: str) -> None:
        """
        Record job execution into the D-4 append-only audit trail in the vault.
        Target: <vault>/05-Daily/Logs/audit-YYYY-MM-DD.md
        """
        try:
            vault_root = self.get_vault_dir()
            today_str = datetime.date.today().isoformat()
            audit_dir = vault_root / "05-Daily" / "Logs"
            audit_dir.mkdir(parents=True, exist_ok=True)
            audit_file = audit_dir / f"audit-{today_str}.md"

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_tag = "SUCCESS" if success else "FAILURE"
            entry = f"- [{timestamp}] [CRON] [{status_tag}] job={job.id} tier={job.tier} :: {details}\n"

            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            # Audit recording failures must never crash the scheduler
            pass

    def trigger_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Execute one owner-defined research job via run_pi_turn.
        Writes the output to the vault and records execution in the audit trail.
        Never raises exceptions; errors are captured and logged.
        """
        if not self._enabled or not self._running:
            return None

        job = self._jobs.get(job_id)
        if not job or not job.enabled:
            return None

        today_str = datetime.date.today().isoformat()
        session_id = f"cron_{job.id}"

        # Execute unattended turn through the Pi bridge
        error_msg: Optional[str] = None
        result_text: str = ""

        try:
            proc = self._pi_runner(prompt=job.prompt, session_id=session_id)
            if hasattr(proc, "stdout"):
                if getattr(proc, "returncode", 0) != 0:
                    error_msg = proc.stderr.strip() if proc.stderr else f"Exit code {proc.returncode}"
                result_text = proc.stdout.strip() if proc.stdout else ""
            elif isinstance(proc, str):
                result_text = proc
            elif proc is not None:
                result_text = str(proc)
            else:
                error_msg = "Pi runner returned None"
        except Exception as exc:
            error_msg = str(exc)

        # Handle execution failure gracefully (containment)
        if error_msg:
            self.append_audit_trail(job, success=False, details=f"Error: {error_msg}")
            run_record = {
                "job_id": job.id,
                "status": "failed",
                "error": error_msg,
                "timestamp": today_str,
            }
            self._execution_history.append(run_record)
            return run_record

        # Ensure destination folder exists in the vault
        vault_root = self.get_vault_dir()
        dest_dir = vault_root / pathlib.Path(job.destination)
        dest_dir.mkdir(parents=True, exist_ok=True)

        output_file = dest_dir / f"{today_str}-{job.id}.md"
        header = f"# Research Report: {job.name}\n- Date: {today_str}\n- Job ID: `{job.id}`\n- Tier: `{job.tier}`\n\n"
        output_file.write_text(header + result_text + "\n", encoding="utf-8")

        self.append_audit_trail(job, success=True, details=f"Output saved to {output_file.name} ({len(result_text)} chars)")

        # Deliver notification to paired owner on Telegram (never fatal)
        self._notify_owner(job, output_file, result_text)

        # Update last run time, compute next schedule, and persist to SQLite
        job.last_run_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        job.compute_next_run_time()
        self.save_job_to_db(job)

        run_record = {
            "job_id": job.id,
            "status": "completed",
            "file": str(output_file),
            "chars": len(result_text),
            "timestamp": today_str,
            "next_run_time": job.next_run_time,
        }
        self._execution_history.append(run_record)
        return run_record

    def _notify_owner(self, job: ResearchJob, output_file: pathlib.Path, result_text: str) -> bool:
        """
        Send an executive summary to the paired owner via Telegram channel provider.
        Truncates or splits if exceeding 4096 characters and references the vault note.
        Failures are logged and swallowed (never fatal).
        """
        owner_id = self.pairing_manager.get_owner_id()
        if owner_id is None:
            return False

        header = f"🔔 Research Job Completed: {job.name}\n• ID: `{job.id}`\n• Vault Note: `{output_file.name}`\n\n"
        suffix = f"\n\n... (truncated; full report in `{output_file.name}`)"
        max_body_len = 4096 - len(header) - len(suffix) - 5
        if len(result_text) > max_body_len:
            body = result_text[:max_body_len].rstrip() + suffix
        else:
            body = result_text

        message = header + body

        try:
            provider = self._channel_provider
            if provider is None:
                provider_cls = get_registry().get("channels", "telegram") or get_registry().get("channel", "telegram")
                if provider_cls:
                    provider = provider_cls(pairing_manager=self.pairing_manager)

            if provider is not None:
                if hasattr(provider, "initialize"):
                    provider.initialize()
                return bool(provider.send_message(owner_id, message))
        except Exception as exc:
            # SPEC 04 line 27: Never fatal: notification failures are logged and swallowed
            self.append_audit_trail(job, success=True, details=f"Telegram notification swallowed error: {exc}")

        return False


# Register default SchedulerProvider in universal registry
get_registry().register("scheduler", "apscheduler", SchedulerProvider)
get_registry().register("scheduler", "cron", SchedulerProvider)
