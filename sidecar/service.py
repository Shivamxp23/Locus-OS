"""
SPEC §12.1-12.5 / §02 / F-0058 / US-10: Headless Service Supervisor.
Provides single-process supervisor managing:
- FastAPI sidecar on 127.0.0.1:8420
- Headless Pi bridge turns
- Persistent SQLite research scheduler
- Graceful shutdown and state flushing
"""
from __future__ import annotations

import logging
from pathlib import Path
import threading
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from sidecar.registry import ProviderRegistry, get_registry
from sidecar.scheduler import ResearchJob, SchedulerProvider

logger = logging.getLogger("locus.service")


def create_app(
    scheduler: Optional[SchedulerProvider] = None,
    registry: Optional[ProviderRegistry] = None,
) -> FastAPI:
    """Create and configure the FastAPI application for the Locus sidecar service."""
    app = FastAPI(title="Locus Sidecar Service", version="0.1.0")
    active_scheduler = scheduler or SchedulerProvider()
    active_registry = registry or get_registry()

    # Store references on app state for route access
    app.state.scheduler = active_scheduler
    app.state.registry = active_registry

    @app.get("/health")
    def health_check() -> Dict[str, Any]:
        """Overall service health check including scheduler status and registered providers."""
        sched_health = (
            app.state.scheduler.health_check()
            if hasattr(app.state.scheduler, "health_check")
            else {"status": "none"}
        )
        return {
            "status": "ok",
            "service": "locus-headless-service",
            "scheduler": sched_health,
            "jobs_count": len(app.state.scheduler.list_jobs()),
            "providers": app.state.registry.list_providers(),
        }

    @app.get("/jobs")
    def list_jobs() -> Dict[str, Any]:
        """List all managed research jobs and their execution schedules."""
        jobs = app.state.scheduler.list_jobs()
        return {
            "status": "ok",
            "count": len(jobs),
            "jobs": [j.to_dict() for j in jobs],
        }

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> Dict[str, Any]:
        """Retrieve details of a single scheduled job."""
        job = app.state.scheduler.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        return {"status": "ok", "job": job.to_dict()}

    @app.post("/jobs/{job_id}/trigger")
    def trigger_job(job_id: str) -> Dict[str, Any]:
        """Trigger immediate unattended execution of a scheduled job."""
        record = app.state.scheduler.trigger_job(job_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found or disabled")
        return {"status": "ok", "record": record}

    @app.post("/shutdown")
    def shutdown_service() -> Dict[str, Any]:
        """Gracefully stop scheduler and flush in-flight operations."""
        if hasattr(app.state, "service_instance") and app.state.service_instance:
            app.state.service_instance.stop()
        else:
            app.state.scheduler.shutdown()
        return {"status": "shutting_down"}

    # Vault LiveSync routes (SPEC §27.2 / F-0060)
    @app.get("/vault/sync/status")
    def sync_status() -> Dict[str, Any]:
        """Check status of vault synchronization."""
        if not app.state.registry.is_feature_enabled("vault", "sync"):
            return JSONResponse(status_code=503, content={"disabled": "locus.vault.sync.enabled"})
        provider_cls = app.state.registry.get_active_provider("vault_sync", default_name="couchdb_livesync")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No vault sync provider registered")
        try:
            inst = provider_cls()
            inst.initialize()
            return {"status": "ok", "sync": inst.status()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @app.post("/vault/sync/push")
    def sync_push(body: Dict[str, Any]) -> Dict[str, Any]:
        """Push note to vault sync store."""
        if not app.state.registry.is_feature_enabled("vault", "sync"):
            return JSONResponse(status_code=503, content={"disabled": "locus.vault.sync.enabled"})
        provider_cls = app.state.registry.get_active_provider("vault_sync", default_name="couchdb_livesync")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No vault sync provider registered")
        path = body.get("path")
        if not path:
            raise HTTPException(status_code=400, detail="Missing 'path' parameter")
        try:
            inst = provider_cls()
            inst.initialize()
            result = inst.push(path, body.get("mtime"))
            return {"status": "ok", "result": result}
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Trajectory Recording & Batch Evaluation routes (SPEC §19.2 / F-0049)
    from sidecar.learning.trajectory import TrajectoryRecorder
    active_registry.register("trajectory_recorder", "default_trajectory_recorder", TrajectoryRecorder)

    @app.post("/trajectories/record")
    def record_trajectory_turn(body: Dict[str, Any]) -> Dict[str, Any]:
        """Record turn for an agent session with sensitive token redaction."""
        if not app.state.registry.is_feature_enabled("learning", "trajectory"):
            return JSONResponse(status_code=503, content={"disabled": "locus.learning.trajectory.enabled"})
        session_id = body.get("session_id")
        role = body.get("role")
        content = body.get("content")
        if not session_id or not role or content is None:
            raise HTTPException(status_code=400, detail="Missing session_id, role, or content")

        provider_cls = app.state.registry.get_active_provider("trajectory_recorder", default_name="default_trajectory_recorder")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No trajectory recorder provider registered")

        rec = provider_cls()
        rec.initialize()
        turn = rec.record_turn(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=body.get("tool_calls"),
            tokens=body.get("tokens"),
            metadata=body.get("metadata"),
        )
        if not turn:
            return {"status": "skipped", "reason": "disabled"}
        return {"status": "ok", "turn": turn.to_dict()}

    @app.post("/trajectories/sessions/{session_id}/flush")
    def flush_trajectory_session(session_id: str) -> Dict[str, Any]:
        """Flush active session trajectory to disk."""
        if not app.state.registry.is_feature_enabled("learning", "trajectory"):
            return JSONResponse(status_code=503, content={"disabled": "locus.learning.trajectory.enabled"})
        provider_cls = app.state.registry.get_active_provider("trajectory_recorder", default_name="default_trajectory_recorder")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No trajectory recorder provider registered")

        rec = provider_cls()
        rec.initialize()
        path = rec.flush_session(session_id)
        if not path:
            raise HTTPException(status_code=404, detail=f"Session trajectory '{session_id}' not found or disabled")
        return {"status": "ok", "path": str(path)}

    @app.get("/trajectories/sessions/{session_id}")
    def get_trajectory_session(session_id: str) -> Dict[str, Any]:
        """Retrieve stored trajectory for a session."""
        if not app.state.registry.is_feature_enabled("learning", "trajectory"):
            return JSONResponse(status_code=503, content={"disabled": "locus.learning.trajectory.enabled"})
        provider_cls = app.state.registry.get_active_provider("trajectory_recorder", default_name="default_trajectory_recorder")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No trajectory recorder provider registered")

        rec = provider_cls()
        rec.initialize()
        traj = rec.get_trajectory(session_id)
        if not traj:
            raise HTTPException(status_code=404, detail=f"Session trajectory '{session_id}' not found")
        return {"status": "ok", "trajectory": traj}

    @app.post("/trajectories/evaluate")
    def evaluate_trajectories(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run batch evaluation across recorded trajectories."""
        if not app.state.registry.is_feature_enabled("learning", "trajectory"):
            return JSONResponse(status_code=503, content={"disabled": "locus.learning.trajectory.enabled"})
        provider_cls = app.state.registry.get_active_provider("trajectory_recorder", default_name="default_trajectory_recorder")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No trajectory recorder provider registered")

        rec = provider_cls()
        rec.initialize()
        payload = body or {}
        evaluation = rec.batch_evaluate(
            session_ids=payload.get("session_ids"),
            eval_prompt=payload.get("eval_prompt"),
        )
        return {"status": "ok", "evaluation": evaluation}

    # AI Chat Archiver routes (SPEC §19.3 / F-0050)
    from sidecar.ingestion.chat_archiver import ChatArchiverProvider
    active_registry.register("chat_archiver", "default_chat_archiver", ChatArchiverProvider)

    @app.post("/ingestion/chats/crawl")
    def crawl_chats(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crawl export directories and return normalized conversations."""
        if not app.state.registry.is_feature_enabled("ingestion", "chat_archiver"):
            return JSONResponse(status_code=503, content={"disabled": "locus.ingestion.chat_archiver.enabled"})
        provider_cls = app.state.registry.get_active_provider("chat_archiver", default_name="default_chat_archiver")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No chat archiver provider registered")

        archiver = provider_cls()
        archiver.initialize()
        payload = body or {}
        source_dir = payload.get("source_dir")
        target_path = Path(source_dir).resolve() if source_dir else None
        chats = archiver.crawl_and_parse(target_path) if target_path else []
        return {"status": "ok", "count": len(chats), "chats": [c.to_dict() for c in chats]}

    @app.post("/ingestion/chats/archive")
    def archive_chats(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Archive discovered AI conversations into vault and trigger LiveSync."""
        if not app.state.registry.is_feature_enabled("ingestion", "chat_archiver"):
            return JSONResponse(status_code=503, content={"disabled": "locus.ingestion.chat_archiver.enabled"})
        provider_cls = app.state.registry.get_active_provider("chat_archiver", default_name="default_chat_archiver")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No chat archiver provider registered")

        archiver = provider_cls()
        archiver.initialize()
        payload = body or {}
        source_dir = payload.get("source_dir")
        source_dirs = [Path(source_dir).resolve()] if source_dir else None
        results = archiver.archive_all(source_dirs=source_dirs)
        return {"status": "ok", "count": len(results), "results": [r.to_dict() for r in results]}

    # Life OS routes (SPEC §25.1-§25.4 / F-0055)
    from sidecar.life_os import LifeOSProvider
    active_registry.register("life_os", "default_life_os", LifeOSProvider)

    @app.post("/life_os/tws")
    def calculate_tws_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compute Task Weight Score (TWS) per SPEC §25.4 and D-1 Option A."""
        if not app.state.registry.is_feature_enabled("life_os"):
            return JSONResponse(status_code=503, content={"disabled": "locus.life_os.enabled"})
        provider_cls = app.state.registry.get_active_provider("life_os", default_name="default_life_os")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No life_os provider registered")

        provider = provider_cls()
        provider.initialize()
        payload = body or {}
        from sidecar.providers.life_os import GoalStackLevel, TaskScoreInput

        scale_val = payload.get("scale", "daily")
        try:
            scale_enum = GoalStackLevel(scale_val)
        except ValueError:
            scale_enum = GoalStackLevel.DAILY

        task_input = TaskScoreInput(
            priority=payload.get("priority", 5),
            urgency=payload.get("urgency", 5),
            difficulty=payload.get("difficulty", 5),
            faction=payload.get("faction"),
            faction_lag_hours=payload.get("faction_lag_hours", 0.0),
            scale=scale_enum,
            child_scores=payload.get("child_scores"),
        )
        res = provider.calculate_tws(task_input)
        return {"status": "ok", "result": res.to_dict()}

    @app.post("/life_os/dcs")
    def calculate_dcs_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compute Daily Capacity Score (DCS) per SPEC §25.2."""
        if not app.state.registry.is_feature_enabled("life_os"):
            return JSONResponse(status_code=503, content={"disabled": "locus.life_os.enabled"})
        provider_cls = app.state.registry.get_active_provider("life_os", default_name="default_life_os")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No life_os provider registered")

        provider = provider_cls()
        provider.initialize()
        payload = body or {}
        from sidecar.providers.life_os import CheckInInput

        checkin = CheckInInput(
            energy=payload.get("energy", 5),
            mood=payload.get("mood", 5),
            sleep=payload.get("sleep", 5),
            stress=payload.get("stress", 5),
            days_since_last_checkin=payload.get("days_since_last_checkin", 0),
        )
        res = provider.calculate_dcs(checkin)
        return {"status": "ok", "result": res.to_dict()}

    @app.get("/life_os/mode")
    def resolve_mode_route(dcs: float = 5.0) -> Dict[str, Any]:
        """Resolve operating mode given DCS score per SPEC §25.3."""
        if not app.state.registry.is_feature_enabled("life_os"):
            return JSONResponse(status_code=503, content={"disabled": "locus.life_os.enabled"})
        provider_cls = app.state.registry.get_active_provider("life_os", default_name="default_life_os")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No life_os provider registered")

        provider = provider_cls()
        provider.initialize()
        mode, constraints = provider.resolve_mode(dcs)
        return {
            "status": "ok",
            "dcs": dcs,
            "mode": mode.value,
            "constraints": {
                "max_difficulty": constraints.max_difficulty,
                "max_discretionary_tasks": constraints.max_discretionary_tasks,
                "description": constraints.description,
            },
        }

    return app


class HeadlessService:
    """
    Supervisor managing the FastAPI sidecar, headless Pi bridge,
    and persistent research scheduler in a single headless process.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8420,
        scheduler: Optional[SchedulerProvider] = None,
        registry: Optional[ProviderRegistry] = None,
    ) -> None:
        # SPEC 10-security.md / D-13: Sidecar binds strictly to loopback (127.0.0.1), never 0.0.0.0
        if host in ("0.0.0.0", "::", ""):
            raise ValueError(
                "Binding plain HTTP to 0.0.0.0 is forbidden per 10-security.md and errata D-13. "
                "Sidecar service must bind only to loopback (127.0.0.1) and be accessed via SSH tunnel."
            )
        self.host = host
        self.port = port
        self.registry = registry or get_registry()
        self.scheduler = scheduler or SchedulerProvider()
        self._running: bool = False
        self.app = create_app(scheduler=self.scheduler, registry=self.registry)
        self.app.state.service_instance = self

    def start(self) -> None:
        """Start the headless service and initialize the scheduler."""
        self.scheduler.initialize()
        self._running = True
        logger.info(f"Locus Headless Service started on {self.host}:{self.port}")

    def stop(self) -> None:
        """Gracefully stop the service: flush in-flight state and shutdown scheduler."""
        if not self._running:
            return
        self.scheduler.shutdown()
        self._running = False
        logger.info("Locus Headless Service gracefully stopped")

    def is_running(self) -> bool:
        """Check whether the headless service is active."""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic runtime status."""
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "scheduler": self.scheduler.health_check(),
            "jobs_count": len(self.scheduler.list_jobs()),
        }


# Default module-level FastAPI instance
app = create_app()


def run_daemon(host: str = "127.0.0.1", port: int = 8420) -> None:
    """Run headless supervisor daemon using uvicorn."""
    import uvicorn

    service = HeadlessService(host=host, port=port)
    service.start()
    try:
        uvicorn.run(service.app, host=host, port=port)
    finally:
        service.stop()


if __name__ == "__main__":
    run_daemon()
