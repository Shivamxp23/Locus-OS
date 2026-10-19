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
import pathlib
import time
from typing import Any, Callable, Dict, List, Optional
import yaml

from sidecar import config
from sidecar.pi_bridge import run_pi_turn
from sidecar.registry import get_registry


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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchJob":
        return cls(
            id=str(data.get("id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            cron=str(data.get("cron", "0 2 * * *")).strip(),
            prompt=str(data.get("prompt", "")).strip(),
            tier=str(data.get("tier", "supervised")).strip(),
            allowed_paths=list(data.get("allowed_paths", [])),
            budget_max_tokens=int(data.get("budget_max_tokens", 100000)),
            destination=str(data.get("destination", "04-Captures/Research")).strip(),
            enabled=bool(data.get("enabled", True)),
        )


class SchedulerProvider:
    """
    Autonomous research scheduler and job executor.
    Wires cron execution into the headless Pi bridge and persists results to the vault.
    """

    def __init__(self, pi_runner: Optional[Callable[..., Any]] = None) -> None:
        self._pi_runner = pi_runner or run_pi_turn
        self._jobs: Dict[str, ResearchJob] = {}
        self._enabled: bool = True
        self._running: bool = False
        self._execution_history: List[Dict[str, Any]] = []

    def set_pi_runner(self, pi_runner: Optional[Callable[..., Any]]) -> None:
        """Inject Pi runner callable for testing."""
        self._pi_runner = pi_runner or run_pi_turn

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

    def load_jobs(self) -> Dict[str, ResearchJob]:
        """Load all research job YAML files from LOCUS_HOME/jobs/."""
        jobs_dir = self.get_jobs_dir()
        loaded: Dict[str, ResearchJob] = {}

        for file_path in jobs_dir.glob("*.y*ml"):
            try:
                content = file_path.read_text(encoding="utf-8")
                raw = yaml.safe_load(content)
                if isinstance(raw, dict) and "prompt" in raw:
                    job_id = str(raw.get("id") or file_path.stem).strip()
                    raw["id"] = job_id
                    job = ResearchJob.from_dict(raw)
                    loaded[job.id] = job
            except Exception:
                # Corrupted job definition is skipped without crashing scheduler
                continue

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

        run_record = {
            "job_id": job.id,
            "status": "completed",
            "file": str(output_file),
            "chars": len(result_text),
            "timestamp": today_str,
        }
        self._execution_history.append(run_record)
        return run_record


# Register default SchedulerProvider in universal registry
get_registry().register("scheduler", "apscheduler", SchedulerProvider)
get_registry().register("scheduler", "cron", SchedulerProvider)
