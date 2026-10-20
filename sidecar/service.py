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
from fastapi.responses import JSONResponse, StreamingResponse

from sidecar import config
from sidecar.registry import ProviderRegistry, get_registry
from sidecar.scheduler import ResearchJob, SchedulerProvider
import sidecar.rate_limiter  # ensures default provider is registered
from sidecar.providers.rate_limit import RateLimitState
import sidecar.cost_tracker  # ensures default cost tracker is registered
from sidecar.providers.cost_tracker import CanonicalUsage, CostResult, PricingEntry
import sidecar.title_generator  # ensures default title generator is registered
from sidecar.title_generator import clean_title, format_title_prompt, generate_fallback_title
import sidecar.onboarding  # ensures default onboarding provider is registered
from sidecar.providers.onboarding import TopologyType
import sidecar.router.classifier  # ensures default query router is registered
from sidecar.providers.query_router import ALL_RETRIEVAL_SOURCES, IntentType, RoutingManifest, TemporalScope
import sidecar.state_engine  # ensures default state engine is registered
from sidecar.providers.state_engine import CheckInRecord, CurrentState, OperatingMode as StateOperatingMode
import sidecar.context_forge  # ensures default context forge is registered
from sidecar.providers.context_forge import (
    ContextForgeResult,
    LayerBudgetConfig,
    RetrievalInput,
)
import sidecar.anti_hallucination  # ensures default anti-hallucination guard is registered
from sidecar.providers.anti_hallucination import (
    CheckResult,
    GuardMode,
)
import sidecar.streaming_sse  # ensures default streaming sse provider is registered
from sidecar.providers.streaming_sse import (
    BaseStreamingSSEProvider,
    SSEEvent,
    StreamOptions,
)

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

    # -------------------------------------------------------------
    # SPEC §1.9 / F-0009 / US-28: Rate Limit Tracking routes
    # -------------------------------------------------------------
    def _is_rate_limit_enabled() -> bool:
        val1 = config.get("locus.rate_limit_tracking.enabled")
        val2 = config.get("locus.tracking.rate_limit.enabled")
        if val1 is not None and not config.is_enabled("locus.rate_limit_tracking.enabled"):
            return False
        if val2 is not None and not config.is_enabled("locus.tracking.rate_limit.enabled"):
            return False
        if not app.state.registry.is_feature_enabled("rate_limit"):
            return False
        return True

    @app.post("/ratelimit/parse")
    def parse_rate_limit_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Parse 12 x-ratelimit-* headers and return updated rate limit state."""
        if not _is_rate_limit_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.rate_limit_tracking.enabled"})
        headers = body.get("headers") or {}
        provider_name = body.get("provider") or "default"

        provider_cls = app.state.registry.get_active_provider("rate_limit", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No rate limit provider registered")
        provider = provider_cls()
        state = provider.parse_headers(headers, provider=provider_name)
        return {"status": "ok", "state": state.to_dict()}

    @app.get("/ratelimit/state")
    def get_rate_limit_state_route(provider: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve current in-memory rate limit state for provider."""
        if not _is_rate_limit_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.rate_limit_tracking.enabled"})
        prov = provider or "default"
        provider_cls = app.state.registry.get_active_provider("rate_limit", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No rate limit provider registered")
        provider = provider_cls()
        state = provider.get_state(provider=prov)
        return {"status": "ok", "state": state.to_dict()}

    @app.post("/ratelimit/throttle/check")
    def check_throttle_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-call guard rate limit throttle check."""
        if not _is_rate_limit_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.rate_limit_tracking.enabled"})
        provider_name = body.get("provider") or "default"
        safety_margin = float(body.get("safety_margin", 0.1))
        raw_state = body.get("state")

        provider_cls = app.state.registry.get_active_provider("rate_limit", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No rate limit provider registered")
        provider = provider_cls()

        state_obj = RateLimitState.from_dict(raw_state) if raw_state else None
        should_sleep, sleep_sec = provider.should_throttle(
            state=state_obj, provider=provider_name, safety_margin=safety_margin
        )
        return {
            "status": "ok",
            "should_throttle": should_sleep,
            "throttle_seconds": sleep_sec,
        }

    @app.get("/ratelimit/display")
    def get_rate_limit_display_route(provider: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve formatted status for TUI/footer."""
        if not _is_rate_limit_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.rate_limit_tracking.enabled"})
        prov = provider or "default"
        provider_cls = app.state.registry.get_active_provider("rate_limit", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No rate limit provider registered")
        provider = provider_cls()
        state = provider.get_state(provider=prov)
        display_str = provider.format_display(state=state, provider=prov)
        return {
            "status": "ok",
            "display": display_str,
            "has_data": state.has_data,
        }

    # -------------------------------------------------------------
    # SPEC §1.10 / F-0010 / US-29: Usage / Cost Tracking routes
    # -------------------------------------------------------------
    def _is_cost_tracking_enabled() -> bool:
        val1 = config.get("locus.usage_cost_tracking.enabled")
        val2 = config.get("locus.tracking.cost.enabled")
        if val1 is not None and not config.is_enabled("locus.usage_cost_tracking.enabled"):
            return False
        if val2 is not None and not config.is_enabled("locus.tracking.cost.enabled"):
            return False
        if not app.state.registry.is_feature_enabled("cost_tracker"):
            return False
        return True

    @app.post("/cost/calculate")
    def calculate_cost_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate USD cost for a given usage and model."""
        if not _is_cost_tracking_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.usage_cost_tracking.enabled"})
        raw_usage = body.get("usage") or {}
        model = body.get("model") or ""
        provider_name = body.get("provider") or ""

        provider_cls = app.state.registry.get_active_provider("cost_tracker", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No cost tracker provider registered")
        provider = provider_cls()
        usage_obj = CanonicalUsage.from_dict(raw_usage)
        pricing = provider.resolve_pricing(model=model, provider=provider_name)
        cost_res = provider.calculate_cost(usage=usage_obj, pricing=pricing)
        return {"status": "ok", "cost": cost_res.to_dict()}

    @app.post("/cost/record")
    def record_cost_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate and record usage against session and daily totals."""
        if not _is_cost_tracking_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.usage_cost_tracking.enabled"})
        raw_usage = body.get("usage") or {}
        model = body.get("model") or ""
        provider_name = body.get("provider") or ""

        provider_cls = app.state.registry.get_active_provider("cost_tracker", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No cost tracker provider registered")
        provider = provider_cls()
        usage_obj = CanonicalUsage.from_dict(raw_usage)
        cost_res = provider.record_usage(usage=usage_obj, model=model, provider=provider_name)
        summary = provider.get_session_summary()
        return {"status": "ok", "cost": cost_res.to_dict(), "session": summary}

    @app.get("/cost/session")
    def get_session_cost_route() -> Dict[str, Any]:
        """Retrieve session and daily cost summary."""
        if not _is_cost_tracking_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.usage_cost_tracking.enabled"})
        provider_cls = app.state.registry.get_active_provider("cost_tracker", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No cost tracker provider registered")
        provider = provider_cls()
        summary = provider.get_session_summary()
        return {"status": "ok", "session": summary}

    @app.get("/cost/pricing")
    def get_model_pricing_route(model: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """Resolve pricing rates for a given model."""
        if not _is_cost_tracking_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.usage_cost_tracking.enabled"})
        provider_cls = app.state.registry.get_active_provider("cost_tracker", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No cost tracker provider registered")
        provider = provider_cls()
        pricing = provider.resolve_pricing(model=model, provider=provider or "")
        return {"status": "ok", "pricing": pricing.to_dict()}

    @app.post("/cost/pricing/override")
    def set_pricing_override_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Set user pricing override for a model."""
        if not _is_cost_tracking_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.usage_cost_tracking.enabled"})
        model = body.get("model") or ""
        if not model:
            raise HTTPException(status_code=400, detail="Missing 'model'")
        raw_pricing = body.get("pricing") or {}
        pricing_obj = PricingEntry.from_dict({**raw_pricing, "source": "user_override"})

        provider_cls = app.state.registry.get_active_provider("cost_tracker", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No cost tracker provider registered")
        provider = provider_cls()
        provider.set_pricing_override(model=model, pricing=pricing_obj)
        return {"status": "ok", "model": model, "pricing": pricing_obj.to_dict()}

    # -------------------------------------------------------------------------
    # SPEC §1.11 / F-0011 / US-30: Title Generation Routes
    # -------------------------------------------------------------------------
    def _is_title_generation_enabled() -> bool:
        if config.get("locus.title_generation.enabled") is False:
            return False
        if config.get("locus.sessions.auto_title.enabled") is False:
            return False
        return True

    @app.post("/title/generate")
    def generate_title_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a short 3-7 word session title from first conversation exchange."""
        if not _is_title_generation_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.title_generation.enabled"})
        user_message = body.get("user_message") or ""
        assistant_response = body.get("assistant_response") or ""
        timeout = float(body.get("timeout", 30.0))

        provider_cls = app.state.registry.get_active_provider("title_generator", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No title generator provider registered")
        provider = provider_cls()
        title = provider.generate_title(user_message=user_message, assistant_response=assistant_response, timeout=timeout)
        return {"status": "ok", "title": title}

    @app.post("/title/clean")
    def clean_title_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Clean artifacts (quotes, 'Title:' prefix, trailing punctuation, 80 char clamp)."""
        if not _is_title_generation_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.title_generation.enabled"})
        raw_title = body.get("raw_title") or ""
        cleaned = clean_title(raw_title)
        return {"status": "ok", "cleaned_title": cleaned}

    @app.get("/title/prompt")
    def get_title_prompt_route(user_snippet: str = "", assistant_snippet: str = "") -> Dict[str, Any]:
        """Assemble title generation system prompt and snippet payload."""
        if not _is_title_generation_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.title_generation.enabled"})
        prompt_data = format_title_prompt(user_snippet, assistant_snippet)
        return {"status": "ok", "prompt": prompt_data}

    # -------------------------------------------------------------------------
    # SPEC §1.12 / F-0012 / US-31: Onboarding Flow Routes
    # -------------------------------------------------------------------------
    def _is_onboarding_enabled() -> bool:
        if config.get("locus.onboarding_flow.enabled") is False:
            return False
        if config.get("locus.onboarding.enabled") is False:
            return False
        return True

    @app.post("/onboarding/start")
    def start_onboarding_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Start or configure onboarding topology."""
        if not _is_onboarding_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.onboarding_flow.enabled"})
        topology = body.get("topology", "local")
        provider_cls = app.state.registry.get_active_provider("onboarding", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No onboarding provider registered")
        provider = provider_cls()
        step_res = provider.set_topology(topology)
        return {"status": "ok", "result": step_res.to_dict()}

    @app.post("/onboarding/step")
    def onboarding_step_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Configure a specific onboarding step."""
        if not _is_onboarding_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.onboarding_flow.enabled"})
        step = (body.get("step") or "").strip().lower()
        payload = body.get("payload") or {}

        provider_cls = app.state.registry.get_active_provider("onboarding", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No onboarding provider registered")
        provider = provider_cls()

        if step == "llm":
            res = provider.configure_llm(
                provider=payload.get("provider", "deepseek"),
                model=payload.get("model", "deepseek-chat"),
                endpoint=payload.get("endpoint"),
                api_key=payload.get("api_key"),
                fallback_provider=payload.get("fallback_provider"),
                fallback_key=payload.get("fallback_key"),
            )
        elif step == "memory":
            res = provider.configure_memory(
                enable_neo4j=payload.get("enable_neo4j", False),
                neo4j_uri=payload.get("neo4j_uri"),
                neo4j_user=payload.get("neo4j_user"),
                neo4j_password=payload.get("neo4j_password"),
                enable_headroom=payload.get("enable_headroom", True),
            )
        elif step == "vault":
            res = provider.configure_vault(
                vault_path=payload.get("vault_path", ""),
                enable_livesync=payload.get("enable_livesync", False),
                couch_url=payload.get("couch_url"),
                couch_user=payload.get("couch_user"),
                couch_password=payload.get("couch_password"),
                couch_db=payload.get("couch_db"),
            )
        elif step == "life_os":
            res = provider.configure_life_os(
                timezone=payload.get("timezone", "Asia/Kolkata"),
                morning_checkin_time=payload.get("morning_checkin_time", "08:00"),
                factions=payload.get("factions"),
            )
        elif step == "telegram":
            res = provider.configure_telegram(
                enabled=payload.get("enabled", False),
                token=payload.get("token"),
                owner_id=payload.get("owner_id"),
            )
        elif step == "cron":
            res = provider.configure_cron(
                enabled=payload.get("enabled", True),
                schedules=payload.get("schedules"),
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown onboarding step '{step}'")

        return {"status": "ok", "result": res.to_dict()}

    @app.post("/onboarding/diagnostics")
    def run_onboarding_diagnostics_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute diagnostic probe suite across configured subsystems."""
        if not _is_onboarding_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.onboarding_flow.enabled"})
        probes = (body or {}).get("probes") if body else None
        provider_cls = app.state.registry.get_active_provider("onboarding", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No onboarding provider registered")
        provider = provider_cls()
        diag = provider.run_diagnostics(probes=probes)
        return {"status": "ok", "diagnostics": diag}

    @app.get("/onboarding/status")
    def get_onboarding_status_route() -> Dict[str, Any]:
        """Retrieve onboarding completion and topology status."""
        if not _is_onboarding_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.onboarding_flow.enabled"})
        provider_cls = app.state.registry.get_active_provider("onboarding", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No onboarding provider registered")
        provider = provider_cls()
        st = provider.get_status()
        return {"status": "ok", "onboarding": st}

    @app.post("/onboarding/reset")
    def reset_onboarding_route() -> Dict[str, Any]:
        """Reset onboarding state to uninitialized."""
        if not _is_onboarding_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.onboarding_flow.enabled"})
        provider_cls = app.state.registry.get_active_provider("onboarding", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No onboarding provider registered")
        provider = provider_cls()
        provider.reset()
        return {"status": "ok", "message": "Onboarding state reset"}

    # -------------------------------------------------------------------------
    # SPEC §2.1-2.3 / F-0092 / US-32: Query Router / Intent Classifier Routes
    # -------------------------------------------------------------------------
    def _is_query_router_enabled() -> bool:
        if config.get("locus.query_router.enabled") is False:
            return False
        if config.get("locus.intent_classifier.enabled") is False:
            return False
        return True

    @app.post("/router/classify")
    def classify_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Classify user query and emit Routing Manifest with anti-hallucination confidence gate."""
        if not _is_query_router_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.query_router.enabled"})
        query = body.get("query", "")
        tz = body.get("timezone", "Asia/Kolkata")
        provider_cls = app.state.registry.get_active_provider("query_router", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("intent_classifier", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No query router provider registered")
        provider = provider_cls()
        manifest = provider.classify(query=query, timezone=tz)
        return {"status": "ok", "manifest": manifest.to_dict()}

    # -------------------------------------------------------------------------
    # SPEC §2.4 / F-0093 / US-33: State Engine (Stage 3) Routes
    # -------------------------------------------------------------------------
    def _is_state_engine_enabled() -> bool:
        if config.get("locus.state_engine.enabled") is False:
            return False
        return True

    @app.get("/state/current")
    def get_current_state_route() -> Dict[str, Any]:
        """Retrieve CURRENT_STATE snapshot with staleness penalties if applicable."""
        if not _is_state_engine_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.state_engine.enabled"})
        provider_cls = app.state.registry.get_active_provider("state_engine", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No state engine provider registered")
        provider = provider_cls()
        state = provider.get_current_state()
        return {"status": "ok", "state": state.to_dict()}

    @app.post("/state/calculate")
    def calculate_state_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Process check-in and update CURRENT_STATE."""
        if not _is_state_engine_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.state_engine.enabled"})
        provider_cls = app.state.registry.get_active_provider("state_engine", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No state engine provider registered")
        provider = provider_cls()
        checkin = CheckInRecord.from_dict(body)
        state = provider.process_checkin(checkin)
        return {"status": "ok", "state": state.to_dict()}

    @app.post("/state/reset")
    def reset_state_route() -> Dict[str, Any]:
        """Reset state engine for testing isolation."""
        if not _is_state_engine_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.state_engine.enabled"})
        provider_cls = app.state.registry.get_active_provider("state_engine", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No state engine provider registered")
        provider = provider_cls()
        provider.reset()
        return {"status": "ok", "message": "State engine reset"}

    # -------------------------------------------------------------------------
    # SPEC §2.5 / F-0094 / US-34: Context Forge (Stage 6) Routes
    # -------------------------------------------------------------------------
    def _is_context_forge_enabled() -> bool:
        val = config.get("locus.brain.context_forge.enabled")
        if val is None:
            val = config.get("locus.context_forge.enabled", True)
        return bool(val)

    @app.post("/forge/assemble")
    def assemble_context_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble 6-layer context block with global relevance scoring and headroom CCR compression."""
        if not _is_context_forge_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.brain.context_forge.enabled"})
        provider_cls = app.state.registry.get_active_provider("context_forge", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No context forge provider registered")
        provider = provider_cls()
        retrieval_data = body.get("retrieval_input", body)
        retrieval_input = RetrievalInput.from_dict(retrieval_data)
        budget_override = None
        if "budget_override" in body:
            budget_override = LayerBudgetConfig.from_dict(body["budget_override"])
        result = provider.assemble_context(retrieval_input, budget_override=budget_override)
        return {"status": "ok", "result": result.to_dict()}

    @app.get("/forge/config")
    def get_forge_config_route() -> Dict[str, Any]:
        """Get current Context Forge layer budgets and status."""
        if not _is_context_forge_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.brain.context_forge.enabled"})
        provider_cls = app.state.registry.get_active_provider("context_forge", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No context forge provider registered")
        provider = provider_cls()
        budgets = provider.get_layer_budget_config()
        return {
            "status": "ok",
            "enabled": True,
            "budgets": budgets.to_dict(),
        }

    # -------------------------------------------------------------------------
    # SPEC §2.6 / F-0095 / US-35: Anti-Hallucination Guard (Stage 10) Routes
    # -------------------------------------------------------------------------
    def _is_anti_hallucination_enabled() -> bool:
        val = config.get("locus.brain.anti_hallucination.enabled")
        if val is None:
            val = config.get("locus.anti_hallucination.enabled", True)
        return bool(val)

    @app.post("/guard/check")
    def check_hallucination_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Verify LLM response against Context Forge content with strict/warn modes."""
        if not _is_anti_hallucination_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.brain.anti_hallucination.enabled"})
        provider_cls = app.state.registry.get_active_provider("anti_hallucination", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No anti-hallucination provider registered")
        provider = provider_cls()
        llm_response = body.get("llm_response", "")
        context_content = body.get("context_forge_content", "")
        mode = body.get("mode")
        result = provider.check(llm_response=llm_response, context_forge_content=context_content, mode=mode)
        return {"status": "ok", "result": result.to_dict()}

    @app.get("/guard/config")
    def get_guard_config_route() -> Dict[str, Any]:
        """Get current Anti-Hallucination Guard status and mode."""
        if not _is_anti_hallucination_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.brain.anti_hallucination.enabled"})
        provider_cls = app.state.registry.get_active_provider("anti_hallucination", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No anti-hallucination provider registered")
        provider = provider_cls()
        return {
            "status": "ok",
            "enabled": True,
            "mode": provider.get_mode().value,
        }

    # -------------------------------------------------------------------------
    # SPEC §2.6a / F-0097 / US-36: Streaming (SSE) Routes
    # -------------------------------------------------------------------------
    def _is_streaming_sse_enabled() -> bool:
        val = config.get("locus.streaming_sse.enabled")
        if val is None:
            val = config.get("locus.brain.streaming_sse.enabled", True)
        return bool(val)

    @app.get("/stream/events")
    async def stream_events_route(text: str = "Hello, world!", chunk_size: int = 16):
        """Stream simulated response chunks as Server-Sent Events."""
        if not _is_streaming_sse_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.streaming_sse.enabled"})
        provider_cls = app.state.registry.get_active_provider("streaming_sse", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No streaming SSE provider registered")
        provider = provider_cls()
        generator = provider.stream_text_chunks(text=text, chunk_size=chunk_size)
        return StreamingResponse(generator, media_type="text/event-stream")

    @app.get("/stream/config")
    def get_streaming_config_route() -> Dict[str, Any]:
        """Get current streaming SSE configuration."""
        if not _is_streaming_sse_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.streaming_sse.enabled"})
        provider_cls = app.state.registry.get_active_provider("streaming_sse", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No streaming SSE provider registered")
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider_cls.__name__,
            "media_type": "text/event-stream",
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
