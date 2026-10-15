"""Locus Sidecar Daemon & Service Lifecycle Engine.

Starts:
- FastAPI HTTP service on loopback (:8420)
- APScheduler background scheduler runner
- Health monitoring endpoint (/health)
- Graceful shutdown on SIGTERM / SIGINT
- Job persistence across restarts (SQLite + jobs directory)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from sidecar.config import get as config_get, get_env, is_enabled
from sidecar.registry import ProviderRegistry, get_registry
from sidecar.scheduler import APSchedulerProvider, SchedulerProvider

logger = logging.getLogger("sidecar.service")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8420


def get_scheduler(
    custom_config_path: Path | None = None,
    locus_home: Path | None = None,
    vault_root: Path | None = None,
    db_path: Path | None = None,
) -> APSchedulerProvider:
    """Resolve and configure active scheduler instance."""
    return APSchedulerProvider(
        custom_config_path=custom_config_path,
        locus_home=locus_home,
        vault_root=vault_root,
        db_path=db_path,
    )


def create_app(
    custom_config_path: Path | None = None,
    locus_home: Path | None = None,
    vault_root: Path | None = None,
    db_path: Path | None = None,
) -> FastAPI:
    """Create and configure FastAPI application with lifespan management."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup phase
        logger.info("Starting Locus Sidecar daemon services...")
        scheduler = get_scheduler(
            custom_config_path=custom_config_path,
            locus_home=locus_home,
            vault_root=vault_root,
            db_path=db_path,
        )
        scheduler.initialize()
        if scheduler.is_enabled:
            scheduler.start()
            logger.info("Scheduler started successfully with %d jobs", len(scheduler.get_jobs()))
        else:
            logger.info("Scheduler is disabled in configuration; skipping job schedule")

        app.state.scheduler = scheduler
        app.state.custom_config_path = custom_config_path
        app.state.is_ready = True

        yield

        # Shutdown phase
        logger.info("Shutting down Locus Sidecar daemon services...")
        app.state.is_ready = False
        if hasattr(app.state, "scheduler") and app.state.scheduler:
            try:
                app.state.scheduler.shutdown()
            except Exception as e:
                logger.error("Error shutting down scheduler: %s", e)
        logger.info("Locus Sidecar daemon shutdown complete")

    app = FastAPI(title="Locus Sidecar", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health_check() -> dict[str, Any]:
        """Health check endpoint reporting sidecar, scheduler, and provider states."""
        scheduler_health = (
            app.state.scheduler.health_check()
            if hasattr(app.state, "scheduler") and app.state.scheduler
            else {"status": "down", "running": False, "job_count": 0}
        )

        overall = "ok"
        if scheduler_health.get("status") not in ("ok", "stopped", "disabled"):
            overall = "degraded"

        return {
            "status": overall,
            "sidecar": "ok",
            "scheduler": scheduler_health,
            "version": "0.1.0",
        }

    @app.get("/jobs")
    def list_jobs() -> dict[str, Any]:
        """List loaded research jobs and their status."""
        if not hasattr(app.state, "scheduler") or not app.state.scheduler:
            return {"jobs": []}
        jobs = [j.to_dict() for j in app.state.scheduler.get_jobs()]
        return {"jobs": jobs, "count": len(jobs)}

    @app.post("/jobs/{job_id}/run")
    def trigger_job(job_id: str) -> dict[str, Any]:
        """Manually trigger a research job by ID."""
        if not hasattr(app.state, "scheduler") or not app.state.scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")
        try:
            res = app.state.scheduler.run_job_now(job_id)
            return res
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/logs")
    def list_logs(limit: int = 50) -> dict[str, Any]:
        """Retrieve recent cron execution logs."""
        if not hasattr(app.state, "scheduler") or not app.state.scheduler:
            return {"logs": []}
        logs = app.state.scheduler.get_execution_logs(limit=limit)
        return {"logs": logs, "count": len(logs)}

    return app


class ServiceRunner:
    """Manages the background execution, lifecycle, and signals for the Sidecar daemon."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        custom_config_path: Path | None = None,
        locus_home: Path | None = None,
        vault_root: Path | None = None,
        db_path: Path | None = None,
    ) -> None:
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError(f"Binding to non-loopback address {host} is forbidden (Law 6 / S-2)")

        self.host = host
        self.port = port
        self.custom_config_path = custom_config_path
        self.locus_home = locus_home
        self.vault_root = vault_root
        self.db_path = db_path

        self.app = create_app(
            custom_config_path=custom_config_path,
            locus_home=locus_home,
            vault_root=vault_root,
            db_path=db_path,
        )
        self.config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            loop="asyncio",
        )
        self.server = uvicorn.Server(self.config)
        self._thread: threading.Thread | None = None
        self._should_exit = False

    def start_background(self) -> None:
        """Start the service in a background daemon thread."""
        self._thread = threading.Thread(target=self.server.run, daemon=True)
        self._thread.start()
        # Wait up to 5 seconds for server to report started
        t0 = time.time()
        while not self.server.started and time.time() - t0 < 5.0:
            time.sleep(0.05)

    def stop(self) -> None:
        """Signal uvicorn server to shut down."""
        self.server.should_exit = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    @property
    def is_running(self) -> bool:
        return bool(self.server.started and not self.server.should_exit)

    def run_blocking(self) -> None:
        """Run service blocking in current thread, handling system signals cleanly."""
        def signal_handler(sig: int, frame: Any) -> None:
            logger.info("Received signal %s, initiating graceful shutdown...", sig)
            self.server.should_exit = True

        for sig_name in ("SIGINT", "SIGTERM"):
            if hasattr(signal, sig_name):
                try:
                    signal.signal(getattr(signal, sig_name), signal_handler)
                except Exception:
                    pass

        self.server.run()


def main() -> None:
    """CLI entry point for running the daemon service."""
    parser = argparse.ArgumentParser(description="Locus Sidecar Daemon Service")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address (strictly loopback)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port (default 8420)")
    parser.add_argument("--config", type=str, default=None, help="Custom configuration file path")

    args = parser.parse_args()
    cfg_path = Path(args.config) if args.config else None

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    runner = ServiceRunner(host=args.host, port=args.port, custom_config_path=cfg_path)
    runner.run_blocking()


if __name__ == "__main__":
    main()
