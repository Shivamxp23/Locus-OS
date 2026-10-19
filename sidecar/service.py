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
