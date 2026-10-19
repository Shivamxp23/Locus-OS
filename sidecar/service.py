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
import time
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from sidecar import config
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

    # Coding Harness Delegation routes (SPEC §3.7 + §11.5 / F-0020)
    from sidecar.harness.delegation import HarnessProvider
    active_registry.register("harness", "default_harness", HarnessProvider)

    @app.post("/harness/delegate")
    def delegate_harness_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Delegate coding task execution to external harness in isolated scratch worktree."""
        if not app.state.registry.is_feature_enabled("harness"):
            return JSONResponse(status_code=503, content={"disabled": "locus.harness.enabled"})
        provider_cls = app.state.registry.get_active_provider("harness", default_name="default_harness")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No harness provider registered")

        provider = provider_cls()
        provider.initialize()
        payload = body or {}
        from sidecar.providers.harness import HarnessType, TaskBrief

        h_override = None
        if payload.get("harness_override"):
            try:
                h_override = HarnessType(payload["harness_override"])
            except ValueError:
                h_override = None

        brief = TaskBrief(
            description=payload.get("description", "Inspect codebase"),
            target_files=payload.get("target_files", []),
            constraints=payload.get("constraints", []),
            test_commands=payload.get("test_commands", []),
            timeout=payload.get("timeout", 600),
            complexity=payload.get("complexity", "normal"),
            requires_autonomous=payload.get("requires_autonomous", False),
            is_quick_fix=payload.get("is_quick_fix", False),
            harness_override=h_override,
        )
        res = provider.execute_delegation(brief)
        return {"status": "ok", "result": res.to_dict()}

    @app.get("/harness/harnesses")
    def list_harnesses_route() -> Dict[str, Any]:
        """List available coding harnesses and status."""
        if not app.state.registry.is_feature_enabled("harness"):
            return JSONResponse(status_code=503, content={"disabled": "locus.harness.enabled"})
        provider_cls = app.state.registry.get_active_provider("harness", default_name="default_harness")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No harness provider registered")

        provider = provider_cls()
        provider.initialize()
        health = provider.health_check()
        return {"status": "ok", "harnesses": health.get("available_harnesses", [])}

    # Prompt builder routes (SPEC §1.2 / F-0002 / US-21)
    @app.post("/prompt/build")
    def build_system_prompt_route(body: Optional[Dict[str, Any]] = Body(None)) -> Dict[str, Any]:
        """Construct Locus system prompt with personality, state engine, and context forge."""
        if not app.state.registry.is_feature_enabled("prompt_builder"):
            return JSONResponse(status_code=503, content={"disabled": "locus.prompt_builder.enabled"})
        provider_cls = app.state.registry.get_active_provider("prompt_builder", default_name="default_prompt_builder")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No prompt builder provider registered")
        provider = provider_cls()
        payload = body or {}
        from sidecar.providers.prompt_builder import ContextFile, OperatingState, PromptOptions, SkillSummary

        ctx_files = [ContextFile(path=cf.get("path", ""), content=cf.get("content", "")) for cf in payload.get("context_files", [])]
        skills = [SkillSummary(name=s.get("name", ""), description=s.get("description", "")) for s in payload.get("skills", [])]
        op_state = None
        if payload.get("operating_state"):
            os_data = payload["operating_state"]
            op_state = OperatingState(
                dcs=float(os_data.get("dcs", 5.0)),
                operating_mode=os_data.get("operating_mode", "NORMAL"),
                faction_status=os_data.get("faction_status", {}),
            )
        opts = PromptOptions(
            cwd=payload.get("cwd", "/"),
            custom_prompt=payload.get("custom_prompt"),
            append_system_prompt=payload.get("append_system_prompt"),
            context_files=ctx_files,
            skills=skills,
            available_tools=payload.get("available_tools", ["read", "bash", "edit", "write"]),
            prompt_guidelines=payload.get("prompt_guidelines", []),
            soul_context=payload.get("soul_context"),
            context_forge_tokens=payload.get("context_forge_tokens"),
            operating_state=op_state,
        )
        prompt = provider.build_system_prompt(opts)
        return {"status": "ok", "prompt": prompt}

    @app.get("/prompt/personality")
    def get_personality_route() -> Dict[str, Any]:
        """Return the active Locus SOUL personality context."""
        if not app.state.registry.is_feature_enabled("prompt_builder"):
            return JSONResponse(status_code=503, content={"disabled": "locus.prompt_builder.enabled"})
        provider_cls = app.state.registry.get_active_provider("prompt_builder", default_name="default_prompt_builder")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No prompt builder provider registered")
        provider = provider_cls()
        personality = provider.load_soul_personality()
        return {"status": "ok", "personality": personality}

    # Tool System routes (SPEC §1.3 / F-0003 / US-22)
    from sidecar.tool_system import ToolSystemProvider
    active_registry.register("tool_system", "default_tool_system", ToolSystemProvider)

    def _is_tool_system_enabled() -> bool:
        val = config.get("locus.tool_system_13_canonical_tools.enabled")
        if val is not None and not config.is_enabled("locus.tool_system_13_canonical_tools.enabled"):
            return False
        if not app.state.registry.is_feature_enabled("tool_system"):
            return False
        return True

    @app.get("/tools/list")
    def list_tools_route() -> Dict[str, Any]:
        """List registered canonical and custom tools."""
        if not _is_tool_system_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.tool_system_13_canonical_tools.enabled"})
        provider_cls = app.state.registry.get_active_provider("tool_system", default_name="default_tool_system")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No tool system provider registered")
        provider = provider_cls()
        tools = provider.list_tools()
        return {
            "status": "ok",
            "count": len(tools),
            "tools": [
                {
                    "name": t.name,
                    "label": t.label,
                    "description": t.description,
                    "schema": t.schema,
                    "execution_mode": t.execution_mode.value if hasattr(t.execution_mode, "value") else str(t.execution_mode),
                }
                for t in tools
            ],
        }

    @app.post("/tools/execute")
    def execute_tool_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool through the 5-step lifecycle."""
        if not _is_tool_system_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.tool_system_13_canonical_tools.enabled"})
        tool_name = body.get("tool") or body.get("name")
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing 'tool' or 'name' parameter")
        tool_call_id = body.get("tool_call_id") or "call-manual"
        params = body.get("params") or {}
        context = body.get("context")

        provider_cls = app.state.registry.get_active_provider("tool_system", default_name="default_tool_system")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No tool system provider registered")
        provider = provider_cls()
        result = provider.execute_tool(
            name=tool_name,
            tool_call_id=tool_call_id,
            raw_params=params,
            context=context,
        )
        return {"status": "ok", "result": result.to_dict()}

    # Model Management & Escalation routes (SPEC §1.4 / F-0004 / US-23)
    from sidecar.model_escalation import ModelEscalationProvider
    active_registry.register("model_management", "default_model_management", ModelEscalationProvider)

    def _is_model_escalation_enabled() -> bool:
        val = config.get("locus.model_management_escalation.enabled")
        if val is not None and not config.is_enabled("locus.model_management_escalation.enabled"):
            return False
        if not app.state.registry.is_feature_enabled("model_management"):
            return False
        return True

    @app.get("/models/list")
    def list_models_route() -> Dict[str, Any]:
        """List model catalog with tiers, context windows, and capabilities."""
        if not _is_model_escalation_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.model_management_escalation.enabled"})
        provider_cls = app.state.registry.get_active_provider("model_management", default_name="default_model_management")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No model management provider registered")
        provider = provider_cls()
        models = provider.list_models()
        return {
            "status": "ok",
            "models": [m.to_dict() for m in models],
            "escalation_enabled": provider.is_escalation_enabled(),
        }

    @app.post("/models/resolve")
    def resolve_model_route(body: Optional[Dict[str, Any]] = Body(None)) -> Dict[str, Any]:
        """Resolve model tier for next turn based on complexity, tokens, or task type."""
        if not _is_model_escalation_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.model_management_escalation.enabled"})
        provider_cls = app.state.registry.get_active_provider("model_management", default_name="default_model_management")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No model management provider registered")
        provider = provider_cls()
        payload = body or {}
        from sidecar.providers.model_manager import TurnEscalationRequest
        req = TurnEscalationRequest(
            task_type=payload.get("task_type", "general"),
            estimated_tokens=int(payload.get("estimated_tokens", 1000)),
            complexity_score=float(payload.get("complexity_score", 1.0)),
            is_sunday_synthesis=bool(payload.get("is_sunday_synthesis", False)),
            is_background=bool(payload.get("is_background", False)),
            user_preferred_model=payload.get("user_preferred_model"),
        )
        decision = provider.resolve_turn_model(req)
        return {"status": "ok", "decision": decision.to_dict()}

    # Extension Lifecycle routes (SPEC §1.5 / F-0005 / US-24)
    from sidecar.extension_lifecycle import ExtensionLifecycleProvider
    active_registry.register("extension_lifecycle", "default_extension_lifecycle", ExtensionLifecycleProvider)

    def _is_extension_lifecycle_enabled() -> bool:
        val = config.get("locus.extension_lifecycle.enabled")
        if val is not None and not config.is_enabled("locus.extension_lifecycle.enabled"):
            return False
        if not app.state.registry.is_feature_enabled("extension_lifecycle"):
            return False
        return True

    @app.get("/extensions/events")
    def list_lifecycle_events_route() -> Dict[str, Any]:
        """List 25+ canonical extension lifecycle events."""
        if not _is_extension_lifecycle_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.extension_lifecycle.enabled"})
        provider_cls = app.state.registry.get_active_provider("extension_lifecycle", default_name="default_extension_lifecycle")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No extension lifecycle provider registered")
        provider = provider_cls()
        events = provider.list_events()
        return {"status": "ok", "count": len(events), "events": events}

    @app.get("/extensions/list")
    def list_extensions_route() -> Dict[str, Any]:
        """List registered extension hooks and status."""
        if not _is_extension_lifecycle_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.extension_lifecycle.enabled"})
        provider_cls = app.state.registry.get_active_provider("extension_lifecycle", default_name="default_extension_lifecycle")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No extension lifecycle provider registered")
        provider = provider_cls()
        hooks = provider.list_hooks()
        return {
            "status": "ok",
            "count": len(hooks),
            "hooks": [h.to_dict() for h in hooks],
        }

    @app.post("/extensions/dispatch")
    def dispatch_lifecycle_event_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a lifecycle event across extensions with error containment."""
        if not _is_extension_lifecycle_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.extension_lifecycle.enabled"})
        event_name = body.get("event")
        if not event_name:
            raise HTTPException(status_code=400, detail="Missing 'event' parameter")
        payload = body.get("payload") or {}

        provider_cls = app.state.registry.get_active_provider("extension_lifecycle", default_name="default_extension_lifecycle")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No extension lifecycle provider registered")
        provider = provider_cls()
        result = provider.dispatch_event(event=event_name, payload=payload)
        return {"status": "ok", "result": result.to_dict()}

    @app.post("/extensions/toggle")
    def toggle_extension_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Enable or disable an individual extension."""
        if not _is_extension_lifecycle_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.extension_lifecycle.enabled"})
        extension_id = body.get("extension_id")
        if not extension_id:
            raise HTTPException(status_code=400, detail="Missing 'extension_id' parameter")
        enabled = bool(body.get("enabled", True))

        provider_cls = app.state.registry.get_active_provider("extension_lifecycle", default_name="default_extension_lifecycle")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No extension lifecycle provider registered")
        provider = provider_cls()
        provider.set_extension_enabled(extension_id, enabled)
        return {
            "status": "ok",
            "extension_id": extension_id,
            "enabled": provider.is_extension_enabled(extension_id),
        }

    # Context Window Management & Headroom CCR routes (SPEC §1.6 & §4.17 / F-0006 / US-25)
    from sidecar.context.headroom_adapter import HeadroomCCRAdapter
    active_registry.register("context_compression", "default_context_compression", HeadroomCCRAdapter)

    def _is_context_compression_enabled() -> bool:
        val = config.get("locus.context_window_management.enabled")
        if val is not None and not config.is_enabled("locus.context_window_management.enabled"):
            return False
        if not app.state.registry.is_feature_enabled("context_compression"):
            return False
        return True

    @app.post("/context/estimate")
    def estimate_context_tokens_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate token count for a text snippet or list of messages."""
        if not _is_context_compression_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.context_window_management.enabled"})
        provider_cls = app.state.registry.get_active_provider("context_compression", default_name="default_context_compression")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No context compression provider registered")
        provider = provider_cls()
        text_or_messages = body.get("messages") if "messages" in body else body.get("text", "")
        tokens = provider.estimate_tokens(text_or_messages)
        return {"status": "ok", "estimated_tokens": tokens}

    @app.post("/context/compact")
    def compact_context_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Compact message history preserving first 3 and last 6 messages with CCR."""
        if not _is_context_compression_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.context_window_management.enabled"})
        messages = body.get("messages") or []
        protect_first_n = int(body.get("protect_first_n", 3))
        protect_last_n = int(body.get("protect_last_n", 6))
        options = body.get("options") or {}

        provider_cls = app.state.registry.get_active_provider("context_compression", default_name="default_context_compression")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No context compression provider registered")
        provider = provider_cls()
        result = provider.compact(
            messages=messages,
            protect_first_n=protect_first_n,
            protect_last_n=protect_last_n,
            options=options,
        )
        return {"status": "ok", "compaction": result.to_dict()}

    @app.post("/context/compress")
    def compress_text_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Compress text with CCR caching and inflation guard."""
        if not _is_context_compression_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.context_window_management.enabled"})
        text = body.get("text", "")
        cache_key = body.get("cache_key")

        provider_cls = app.state.registry.get_active_provider("context_compression", default_name="default_context_compression")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No context compression provider registered")
        provider = provider_cls()
        result = provider.compress_text(text=text, cache_key=cache_key)
        return {"status": "ok", "result": result}

    @app.get("/context/retrieve/{cache_key}")
    def retrieve_original_route(cache_key: str) -> Dict[str, Any]:
        """Retrieve original uncompressed content by CCR cache key."""
        if not _is_context_compression_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.context_window_management.enabled"})
        provider_cls = app.state.registry.get_active_provider("context_compression", default_name="default_context_compression")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No context compression provider registered")
        provider = provider_cls()
        original = provider.retrieve_original(cache_key)
        if original is None:
            raise HTTPException(status_code=404, detail=f"CCR cache key '{cache_key}' not found or expired")
        return {"status": "ok", "cache_key": cache_key, "original": original}

    # Post-Turn Background Review routes (SPEC §1.7 & §10.1 / F-0007 / US-26)
    from sidecar.learning.reflector import PostTurnReviewer
    from sidecar.providers.post_turn import ALLOWED_REVIEW_TOOLS
    active_registry.register("post_turn_review", "default_post_turn_review", PostTurnReviewer)

    def _is_post_turn_review_enabled() -> bool:
        val = config.get("locus.post_turn_review.enabled")
        if val is not None and not config.is_enabled("locus.post_turn_review.enabled"):
            return False
        if not app.state.registry.is_feature_enabled("post_turn_review"):
            return False
        return True

    @app.post("/review/post-turn")
    def post_turn_review_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn daemon background review for memory and skill updates."""
        if not _is_post_turn_review_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.post_turn_review.enabled"})
        messages = body.get("messages") or []
        session_id = body.get("session_id")
        sync = bool(body.get("sync", False))

        provider_cls = app.state.registry.get_active_provider("post_turn_review", default_name="default_post_turn_review")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No post-turn review provider registered")
        provider = provider_cls()
        result = provider.spawn_background_review(conversation_snapshot=messages, session_id=session_id, sync=sync)
        return {"status": "ok", "result": result.to_dict()}

    @app.get("/review/tools/allowed")
    def allowed_review_tools_route() -> Dict[str, Any]:
        """Return the strict tool whitelist permitted during post-turn review."""
        if not _is_post_turn_review_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.post_turn_review.enabled"})
        return {
            "status": "ok",
            "allowed_tools": ALLOWED_REVIEW_TOOLS,
            "policy": "All unlisted tools strictly denied",
        }

    @app.get("/review/skills/preferences")
    def skill_preferences_route() -> Dict[str, Any]:
        """Return the 4-tier skill update preference hierarchy."""
        if not _is_post_turn_review_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.post_turn_review.enabled"})
        provider_cls = app.state.registry.get_active_provider("post_turn_review", default_name="default_post_turn_review")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No post-turn review provider registered")
        provider = provider_cls()
        return {
            "status": "ok",
            "preferences": provider.get_skill_preferences(),
        }

    @app.get("/review/result/{review_id}")
    def get_review_result_route(review_id: str) -> Dict[str, Any]:
        """Retrieve completed or dispatched review result by review_id."""
        if not _is_post_turn_review_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.post_turn_review.enabled"})
        provider_cls = app.state.registry.get_active_provider("post_turn_review", default_name="default_post_turn_review")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No post-turn review provider registered")
        provider = provider_cls()
        res = provider.get_review_result(review_id)
        if not res:
            raise HTTPException(status_code=404, detail=f"Review ID '{review_id}' not found")
        return {"status": "ok", "result": res.to_dict()}

    # Learning / Profiling / Reward Model routes (SPEC §1.7, §10.1, §10.3, §10.5, §10.6-10.7 / F-0035 / US-27)
    from sidecar.learning.learning_system import UnifiedLearningProvider
    from sidecar.providers.learning import LearningCandidate
    active_registry.register("learning", "default_learning", UnifiedLearningProvider)

    def _is_learning_enabled() -> bool:
        val = config.get("locus.learning_profiling_reward_model.enabled")
        if val is not None and not config.is_enabled("locus.learning_profiling_reward_model.enabled"):
            return False
        if not app.state.registry.is_feature_enabled("learning"):
            return False
        return True

    @app.post("/learning/candidate")
    def record_learning_candidate_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Record candidate reflection item."""
        if not _is_learning_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.learning_profiling_reward_model.enabled"})
        facet_class = body.get("facet_class", "workflow")
        cue_family = body.get("cue_family", "implicit_pattern")
        evidence = body.get("evidence") or {}
        timestamp = float(body.get("timestamp", time.time()))
        val = body.get("value")

        provider_cls = app.state.registry.get_active_provider("learning", default_name="default_learning")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No learning provider registered")
        provider = provider_cls()
        cand = LearningCandidate(
            facet_class=facet_class,
            cue_family=cue_family,
            evidence=evidence,
            timestamp=timestamp,
            value=val,
        )
        provider.record_candidate(cand)
        return {"status": "ok", "candidate": cand.to_dict()}

    @app.post("/learning/stability/check")
    def check_stability_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Run stability detection and stabilize converged facets."""
        if not _is_learning_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.learning_profiling_reward_model.enabled"})
        window_seconds = float(body.get("window_seconds", 1800.0))
        threshold = float(body.get("threshold", 0.7))

        provider_cls = app.state.registry.get_active_provider("learning", default_name="default_learning")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No learning provider registered")
        provider = provider_cls()
        stabilized = provider.check_stability(window_seconds=window_seconds, threshold=threshold)
        return {"status": "ok", "stabilized": [s.to_dict() for s in stabilized]}

    @app.get("/learning/profile")
    def get_user_profile_route() -> Dict[str, Any]:
        """Retrieve rendered markdown user profile."""
        if not _is_learning_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.learning_profiling_reward_model.enabled"})
        provider_cls = app.state.registry.get_active_provider("learning", default_name="default_learning")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No learning provider registered")
        provider = provider_cls()
        profile_md = provider.generate_profile_markdown()
        return {"status": "ok", "profile": profile_md}

    @app.post("/learning/tool-usage")
    def record_tool_usage_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Record tool usage execution event."""
        if not _is_learning_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.learning_profiling_reward_model.enabled"})
        tool_name = body.get("tool_name", "")
        args = body.get("args") or {}
        success = bool(body.get("success", True))
        duration_ms = float(body.get("duration_ms", 0.0))

        provider_cls = app.state.registry.get_active_provider("learning", default_name="default_learning")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No learning provider registered")
        provider = provider_cls()
        rec = provider.record_tool_usage(tool_name=tool_name, args=args, success=success, duration_ms=duration_ms)
        return {"status": "ok", "record": rec.to_dict()}

    @app.post("/learning/reward/signal")
    def record_reward_signal_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Record a thumbs-up or thumbs-down feedback signal."""
        if not _is_learning_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.learning_profiling_reward_model.enabled"})
        features = body.get("features") or {}
        label = int(body.get("label", 1))

        provider_cls = app.state.registry.get_active_provider("learning", default_name="default_learning")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No learning provider registered")
        provider = provider_cls()
        sig = provider.record_reward_signal(features=features, label=label)
        return {"status": "ok", "signal": sig.to_dict()}

    @app.post("/learning/reward/score")
    def score_thought_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Score candidate thought/action returning probability of thumbs_up."""
        if not _is_learning_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.learning_profiling_reward_model.enabled"})
        features = body.get("features") or {}

        provider_cls = app.state.registry.get_active_provider("learning", default_name="default_learning")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No learning provider registered")
        provider = provider_cls()
        score = provider.score_thought(features)
        return {
            "status": "ok",
            "probability": score,
            "deliver_proactive": score >= 0.6,
        }

    @app.post("/learning/hebbian/update")
    def update_hebbian_weight_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Update Hebbian pathway weight with access, feedback, and STDP."""
        if not _is_learning_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.learning_profiling_reward_model.enabled"})
        edge_id = body.get("edge_id")
        if not edge_id:
            raise HTTPException(status_code=400, detail="Missing 'edge_id'")
        feedback = body.get("feedback")
        response_time_ms = body.get("response_time_ms")
        if response_time_ms is not None:
            response_time_ms = float(response_time_ms)

        provider_cls = app.state.registry.get_active_provider("learning", default_name="default_learning")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No learning provider registered")
        provider = provider_cls()
        weight = provider.update_edge_weight(edge_id=edge_id, feedback=feedback, response_time_ms=response_time_ms)
        return {"status": "ok", "edge_id": edge_id, "weight": weight}

    @app.get("/learning/patterns")
    def get_patterns_route() -> Dict[str, Any]:
        """Detect and return behavioral patterns across horizons."""
        if not _is_learning_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.learning_profiling_reward_model.enabled"})
        provider_cls = app.state.registry.get_active_provider("learning", default_name="default_learning")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No learning provider registered")
        provider = provider_cls()
        patterns = provider.detect_patterns()
        return {"status": "ok", "patterns": [p.to_dict() for p in patterns]}

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
