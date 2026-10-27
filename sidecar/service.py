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
import sidecar.model_routing  # ensures default model routing provider is registered
from sidecar.providers.model_routing import (
    BaseModelRoutingProvider,
    RoutingHints,
)
import sidecar.image_generation  # ensures default image generation provider is registered
from sidecar.providers.image_generation import (
    BaseImageGenerationProvider,
    ImageGenerationRequest,
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

    # -------------------------------------------------------------------------
    # SPEC §2.7-2.8 / F-0096 / US-37: Intelligent Model Routing & Quality Fallback Routes
    # -------------------------------------------------------------------------
    def _is_model_routing_enabled() -> bool:
        val = config.get("locus.intelligent_model_routing_quality_based_fallback.enabled")
        if val is None:
            val = config.get("locus.routing.enabled")
        if val is None:
            val = config.get("locus.brain.model_routing.enabled", True)
        return bool(val)

    @app.post("/routing/decide")
    def route_decide_endpoint(body: Dict[str, Any]) -> Dict[str, Any]:
        """Compute model routing decision (primary, fallback, model) based on policy."""
        if not _is_model_routing_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.intelligent_model_routing_quality_based_fallback.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("model_routing", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider(
                "intelligent_model_routing_quality_based_fallback", default_name="default"
            )
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No model routing provider registered")
        provider = provider_cls()
        model_string = body.get("model", "")
        category = provider.classify(model_string)
        hints_data = body.get("hints", {})
        hints = RoutingHints.from_dict(hints_data)
        has_tools = bool(body.get("tools"))
        health = provider.check_local_health()
        decision = provider.decide(
            category=category,
            local_healthy=health.healthy,
            hints=hints,
            has_tools=has_tools,
        )
        return {"status": "ok", "decision": decision.to_dict()}

    @app.get("/routing/health")
    def route_health_endpoint(force: bool = False) -> Dict[str, Any]:
        """Check local model server health with cached 30s TTL."""
        if not _is_model_routing_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.intelligent_model_routing_quality_based_fallback.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("model_routing", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No model routing provider registered")
        provider = provider_cls()
        health = provider.check_local_health(force_refresh=force)
        return {"status": "ok", "health": health.to_dict()}

    @app.post("/routing/quality-check")
    def route_quality_check_endpoint(body: Dict[str, Any]) -> Dict[str, Any]:
        """Check if response text is low quality or refusal."""
        if not _is_model_routing_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.intelligent_model_routing_quality_based_fallback.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("model_routing", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No model routing provider registered")
        provider = provider_cls()
        text = body.get("text", "")
        low_quality = provider.is_low_quality(text)
        return {"status": "ok", "low_quality": low_quality}

    @app.get("/routing/config")
    def route_config_endpoint() -> Dict[str, Any]:
        """Get model routing configuration."""
        if not _is_model_routing_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.intelligent_model_routing_quality_based_fallback.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("model_routing", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No model routing provider registered")
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider_cls.__name__,
        }

    # -------------------------------------------------------------------------
    # SPEC §2.9 / F-0098 / US-38: Image Generation Routes
    # -------------------------------------------------------------------------
    def _is_image_generation_enabled() -> bool:
        val = config.get("locus.image_generation.enabled")
        if val is None:
            val = config.get("locus.images.enabled", True)
        return bool(val)

    @app.post("/images/generate")
    def generate_image_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Generate image from prompt and model parameters."""
        if not _is_image_generation_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.image_generation.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("image_generation", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("images", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No image generation provider registered")
        provider = provider_cls()
        req = ImageGenerationRequest.from_dict(body)
        try:
            result = provider.generate_image(req)
            return {"status": "ok", "result": result.to_dict()}
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except RuntimeError as re:
            raise HTTPException(status_code=500, detail=str(re))

    @app.get("/images/models")
    def list_image_models_route() -> Dict[str, Any]:
        """List registered image generation models."""
        if not _is_image_generation_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.image_generation.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("image_generation", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No image generation provider registered")
        provider = provider_cls()
        models = [m.to_dict() for m in provider.list_models()]
        return {"status": "ok", "models": models}

    @app.get("/images/config")
    def get_image_config_route() -> Dict[str, Any]:
        """Get image generation configuration and status."""
        if not _is_image_generation_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.image_generation.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("image_generation", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No image generation provider registered")
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider_cls.__name__,
            "default_model": "openai/dall-e-3",
        }

    # Subagents & AutoResearch routes (SPEC §11.1-11.5 + §3.7 / F-0036)
    from sidecar.subagents import SubagentProvider
    from sidecar.providers.subagents import (
        SubagentSpawnRequest,
        AutoResearchRequest,
    )
    active_registry.register("subagents", "default", SubagentProvider)
    active_registry.register("subagent_archetype", "default", SubagentProvider)

    def _is_subagents_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("subagents"):
            return False
        if config.get("locus.subagents_autoresearch.enabled", True) is False:
            return False
        if config.get("locus.subagents.enabled", True) is False:
            return False
        return True

    @app.post("/subagents/spawn")
    def spawn_subagent_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn isolated subagent adhering to MAX_SPAWN_DEPTH = 3."""
        if not _is_subagents_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.subagents_autoresearch.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("subagents", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No subagents provider registered")
        provider = provider_cls()
        req = SubagentSpawnRequest(
            task=body.get("task", ""),
            archetype=body.get("archetype", "planner"),
            parent_session_id=body.get("parent_session_id"),
            current_depth=body.get("current_depth", 0),
            model_override=body.get("model_override"),
            context_extra=body.get("context_extra"),
            max_turns_override=body.get("max_turns_override"),
        )
        try:
            result = provider.spawn_subagent(req)
            return {"status": "ok", "result": result.to_dict()}
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except KeyError as ke:
            raise HTTPException(status_code=404, detail=str(ke))
        except RuntimeError as re:
            raise HTTPException(status_code=500, detail=str(re))

    @app.get("/subagents/archetypes")
    def list_subagent_archetypes_route(category: Optional[str] = None) -> Dict[str, Any]:
        """List registered subagent archetypes (factions and OpenHuman)."""
        if not _is_subagents_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.subagents_autoresearch.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("subagents", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No subagents provider registered")
        provider = provider_cls()
        archetypes = [a.to_dict() for a in provider.list_archetypes(category=category)]
        return {"status": "ok", "archetypes": archetypes}

    @app.get("/subagents/config")
    def get_subagents_config_route() -> Dict[str, Any]:
        """Get subagents and AutoResearch configuration and status."""
        if not _is_subagents_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.subagents_autoresearch.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("subagents", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No subagents provider registered")
        provider = provider_cls()
        health = provider.health_check()
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider_cls.__name__,
            "max_spawn_depth": health.get("max_spawn_depth", 3),
            "archetype_count": health.get("archetype_count", 0),
        }

    @app.post("/subagents/autoresearch")
    def autoresearch_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AutoResearch topic decomposition and hypothesis synthesis."""
        if not _is_subagents_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.subagents_autoresearch.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("subagents", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No subagents provider registered")
        provider = provider_cls()
        req = AutoResearchRequest(
            topic=body.get("topic", ""),
            depth_mode=body.get("depth_mode", "quick"),
            hypotheses=body.get("hypotheses", []),
            parent_session_id=body.get("parent_session_id"),
        )
        try:
            result = provider.execute_autoresearch(req)
            return {"status": "ok", "result": result.to_dict()}
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except RuntimeError as re:
            raise HTTPException(status_code=500, detail=str(re))

    # Git Tools routes (SPEC §3.7a / F-0099)
    from sidecar.git_tools import GitToolsProvider
    active_registry.register("git_tools", "default", GitToolsProvider)
    active_registry.register("git", "default", GitToolsProvider)

    def _is_git_tools_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("git_tools") and not app.state.registry.is_feature_enabled("git"):
            return False
        if config.get("locus.git_tools.enabled", True) is False:
            return False
        if config.get("locus.tools.git.enabled", True) is False:
            return False
        return True

    @app.get("/git/status")
    def get_git_status_route(repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Query working tree status, branch, staged/unstaged changes."""
        if not _is_git_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.git_tools.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("git_tools", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("git", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No git tools provider registered")
        provider = provider_cls()
        try:
            result = provider.get_status(repo_path=repo_path)
            return {"status": "ok", "result": result.to_dict()}
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except RuntimeError as re:
            raise HTTPException(status_code=500, detail=str(re))

    @app.post("/git/diff")
    def get_git_diff_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Retrieve git diff for working tree or staged changes."""
        if not _is_git_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.git_tools.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("git_tools", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("git", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No git tools provider registered")
        provider = provider_cls()
        payload = body or {}
        staged = bool(payload.get("staged", False))
        path = payload.get("path")
        repo_path = payload.get("repo_path")
        try:
            result = provider.get_diff(repo_path=repo_path, staged=staged, path=path)
            return {"status": "ok", "result": result.to_dict()}
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except RuntimeError as re:
            raise HTTPException(status_code=500, detail=str(re))

    @app.post("/git/commit")
    def create_git_commit_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new commit in the target repository."""
        if not _is_git_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.git_tools.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("git_tools", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("git", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No git tools provider registered")
        provider = provider_cls()
        message = body.get("message", "")
        repo_path = body.get("repo_path")
        files = body.get("files")
        try:
            result = provider.create_commit(message=message, repo_path=repo_path, files=files)
            if not result.success:
                raise HTTPException(status_code=400, detail=result.error or "Git commit failed")
            return {"status": "ok", "result": result.to_dict()}
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except HTTPException:
            raise
        except RuntimeError as re:
            raise HTTPException(status_code=500, detail=str(re))

    @app.get("/git/log")
    def get_git_log_route(max_count: int = 10, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Query recent git commit history."""
        if not _is_git_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.git_tools.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("git_tools", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("git", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No git tools provider registered")
        provider = provider_cls()
        try:
            log_entries = [entry.to_dict() for entry in provider.get_log(repo_path=repo_path, max_count=max_count)]
            return {"status": "ok", "log": log_entries}
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except RuntimeError as re:
            raise HTTPException(status_code=500, detail=str(re))

    @app.get("/git/config")
    def get_git_config_route() -> Dict[str, Any]:
        """Get Git Tools configuration and status."""
        if not _is_git_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.git_tools.enabled"},
            )
        provider_cls = app.state.registry.get_active_provider("git_tools", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("git", default_name="default")
        if not provider_cls:
            raise HTTPException(status_code=404, detail="No git tools provider registered")
        provider = provider_cls()
        health = provider.health_check()
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider_cls.__name__,
            "git_binary": health.get("git_binary"),
        }

    # Tool Call Validation routes (SPEC §3.8 / F-0100)
    from sidecar.tool_call_validation import ToolCallValidationProvider
    active_registry.register("tool_call_validation", "default", ToolCallValidationProvider)
    active_registry.register("tool_validation", "default", ToolCallValidationProvider)
    active_registry.register("guardrails", "default", ToolCallValidationProvider)

    _tool_validation_instance: Optional[Any] = None

    def _get_tool_validation_provider() -> Optional[Any]:
        nonlocal _tool_validation_instance
        provider_cls = app.state.registry.get_active_provider("tool_call_validation", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("tool_validation", default_name="default")
        if not provider_cls:
            return None
        if _tool_validation_instance is None or not isinstance(_tool_validation_instance, provider_cls):
            _tool_validation_instance = provider_cls()
        return _tool_validation_instance

    def _is_tool_call_validation_enabled() -> bool:
        if config.get("locus.tool_call_validation.enabled") is False:
            return False
        if config.get("locus.tools.validation.enabled") is False:
            return False
        if config.get("locus.brain.tool_call_validation.enabled") is False:
            return False
        return True

    @app.post("/tools/validate")
    def validate_tool_call_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool call parameters and evaluate pre-execution guardrails."""
        if not _is_tool_call_validation_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_call_validation.enabled"},
            )
        provider = _get_tool_validation_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool call validation provider registered")
        tool_name = body.get("tool_name", "")
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing required field: tool_name")
        params = body.get("params") or {}
        schema = body.get("schema")
        try:
            decision = provider.before_call(tool_name=tool_name, params=params, schema=schema)
            return {"status": "ok", "decision": decision.to_dict()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/observe")
    def observe_tool_call_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Record tool execution outcome, updating failure streaks and duplicate detectors."""
        if not _is_tool_call_validation_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_call_validation.enabled"},
            )
        provider = _get_tool_validation_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool call validation provider registered")
        tool_name = body.get("tool_name", "")
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing required field: tool_name")
        params = body.get("params") or {}
        result = body.get("result")
        failed = body.get("failed")
        try:
            observation = provider.observe_call(tool_name=tool_name, params=params, result=result, failed=failed)
            return {"status": "ok", "observation": observation.to_dict()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/reset")
    def reset_tool_validation_route() -> Dict[str, Any]:
        """Reset turn-local streak counters and loop detectors."""
        if not _is_tool_call_validation_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_call_validation.enabled"},
            )
        provider = _get_tool_validation_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool call validation provider registered")
        provider.reset_for_turn()
        return {"status": "ok", "reset": True}

    @app.get("/tools/validation/config")
    def get_tool_validation_config_route() -> Dict[str, Any]:
        """Get Tool Call Validation configuration and health."""
        if not _is_tool_call_validation_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_call_validation.enabled"},
            )
        provider = _get_tool_validation_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool call validation provider registered")
        health = provider.health_check()
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "config": provider.get_config().to_dict(),
            "health": health,
        }

    # Tool Result Classification routes (SPEC §3.9 / F-0101)
    from sidecar.tool_result_classification import ToolResultClassificationProvider
    active_registry.register("tool_result_classification", "default", ToolResultClassificationProvider)
    active_registry.register("result_classification", "default", ToolResultClassificationProvider)

    _tool_result_classification_instance: Optional[Any] = None

    def _get_tool_result_classification_provider() -> Optional[Any]:
        nonlocal _tool_result_classification_instance
        provider_cls = app.state.registry.get_active_provider("tool_result_classification", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("result_classification", default_name="default")
        if not provider_cls:
            return None
        if _tool_result_classification_instance is None or not isinstance(_tool_result_classification_instance, provider_cls):
            _tool_result_classification_instance = provider_cls()
        return _tool_result_classification_instance

    def _is_tool_result_classification_enabled() -> bool:
        if config.get("locus.tool_result_classification.enabled") is False:
            return False
        if config.get("locus.tools.result_classification.enabled") is False:
            return False
        if config.get("locus.brain.tool_result_classification.enabled") is False:
            return False
        return True

    @app.post("/tools/classify-result")
    def classify_tool_result_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Classify tool result into success, failure, or partial."""
        if not _is_tool_result_classification_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_result_classification.enabled"},
            )
        provider = _get_tool_result_classification_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool result classification provider registered")
        tool_name = body.get("tool_name", "")
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing required field: tool_name")
        result = body.get("result")
        error = body.get("error")
        exit_code = body.get("exit_code")
        params = body.get("params")
        try:
            classification = provider.classify_result(
                tool_name=tool_name,
                result=result,
                error=error,
                exit_code=exit_code,
                params=params,
            )
            return {"status": "ok", "classification": classification.to_dict()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/tools/classification/config")
    def get_tool_classification_config_route() -> Dict[str, Any]:
        """Get Tool Result Classification configuration and health."""
        if not _is_tool_result_classification_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_result_classification.enabled"},
            )
        provider = _get_tool_result_classification_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool result classification provider registered")
        health = provider.health_check()
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "config": provider.get_config().to_dict(),
            "health": health,
        }

    # Tool Output Accumulator routes (SPEC §3.10 / F-0102)
    from sidecar.tool_output_accumulator import ToolOutputAccumulatorProvider
    active_registry.register("tool_output_accumulator", "default", ToolOutputAccumulatorProvider)
    active_registry.register("output_accumulator", "default", ToolOutputAccumulatorProvider)

    _tool_output_accumulator_instance: Optional[Any] = None

    def _get_tool_output_accumulator_provider() -> Optional[Any]:
        nonlocal _tool_output_accumulator_instance
        provider_cls = app.state.registry.get_active_provider("tool_output_accumulator", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("output_accumulator", default_name="default")
        if not provider_cls:
            return None
        if _tool_output_accumulator_instance is None or not isinstance(_tool_output_accumulator_instance, provider_cls):
            _tool_output_accumulator_instance = provider_cls()
        return _tool_output_accumulator_instance

    def _is_tool_output_accumulator_enabled() -> bool:
        if config.get("locus.tool_output_accumulator.enabled") is False:
            return False
        if config.get("locus.tools.output_accumulator.enabled") is False:
            return False
        if config.get("locus.brain.tool_output_accumulator.enabled") is False:
            return False
        return True

    @app.post("/tools/accumulator/create")
    def create_accumulator_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new streaming accumulator session."""
        if not _is_tool_output_accumulator_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_output_accumulator.enabled"},
            )
        provider = _get_tool_output_accumulator_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool output accumulator provider registered")
        payload = body or {}
        acc_id = provider.create_accumulator(
            accumulator_id=payload.get("accumulator_id"),
            max_lines=payload.get("max_lines"),
            max_bytes=payload.get("max_bytes"),
            temp_file_prefix=payload.get("temp_file_prefix"),
        )
        return {"status": "ok", "accumulator_id": acc_id}

    @app.post("/tools/accumulator/{acc_id}/append")
    def append_accumulator_route(acc_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Append data to an active output accumulator."""
        if not _is_tool_output_accumulator_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_output_accumulator.enabled"},
            )
        provider = _get_tool_output_accumulator_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool output accumulator provider registered")
        data = body.get("data", "")
        try:
            snapshot = provider.append(accumulator_id=acc_id, data=data)
            return {"status": "ok", "snapshot": snapshot.to_dict()}
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Accumulator '{acc_id}' not found")
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/tools/accumulator/{acc_id}/snapshot")
    def snapshot_accumulator_route(acc_id: str, persist: bool = True) -> Dict[str, Any]:
        """Fetch snapshot of accumulated output."""
        if not _is_tool_output_accumulator_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_output_accumulator.enabled"},
            )
        provider = _get_tool_output_accumulator_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool output accumulator provider registered")
        try:
            snapshot = provider.snapshot(accumulator_id=acc_id, persist_if_truncated=persist)
            return {"status": "ok", "snapshot": snapshot.to_dict()}
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Accumulator '{acc_id}' not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/accumulator/{acc_id}/finish")
    def finish_accumulator_route(acc_id: str) -> Dict[str, Any]:
        """Finish accumulation and flush buffers."""
        if not _is_tool_output_accumulator_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_output_accumulator.enabled"},
            )
        provider = _get_tool_output_accumulator_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool output accumulator provider registered")
        try:
            snapshot = provider.finish(accumulator_id=acc_id)
            return {"status": "ok", "snapshot": snapshot.to_dict()}
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Accumulator '{acc_id}' not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/tools/accumulator/{acc_id}/full")
    def read_full_accumulator_route(acc_id: str, max_bytes: int = 50000) -> Dict[str, Any]:
        """Read full output up to max_bytes with omission markers if truncated."""
        if not _is_tool_output_accumulator_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_output_accumulator.enabled"},
            )
        provider = _get_tool_output_accumulator_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool output accumulator provider registered")
        try:
            full_out = provider.read_full_output(accumulator_id=acc_id, max_bytes=max_bytes)
            return {"status": "ok", "full_output": full_out.to_dict()}
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Accumulator '{acc_id}' not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/tools/accumulator/{acc_id}")
    def delete_accumulator_route(acc_id: str) -> Dict[str, Any]:
        """Close and discard accumulator session."""
        if not _is_tool_output_accumulator_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_output_accumulator.enabled"},
            )
        provider = _get_tool_output_accumulator_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool output accumulator provider registered")
        provider.close(accumulator_id=acc_id)
        return {"status": "ok", "closed": True}

    @app.get("/tools/accumulator/config")
    def get_tool_accumulator_config_route() -> Dict[str, Any]:
        """Get Tool Output Accumulator configuration and health."""
        if not _is_tool_output_accumulator_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_output_accumulator.enabled"},
            )
        provider = _get_tool_output_accumulator_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool output accumulator provider registered")
        health = provider.health_check()
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "config": provider.get_config().to_dict(),
            "health": health,
        }

    # Tool Timeout / Budget routes (SPEC §3.11 / F-0103)
    from sidecar.tool_timeout_budget import ToolTimeoutBudgetProvider
    active_registry.register("tool_timeout_budget", "default", ToolTimeoutBudgetProvider)
    active_registry.register("tool_timeout", "default", ToolTimeoutBudgetProvider)
    active_registry.register("timeout_budget", "default", ToolTimeoutBudgetProvider)

    _tool_timeout_budget_instance: Optional[Any] = None

    def _get_tool_timeout_budget_provider() -> Optional[Any]:
        nonlocal _tool_timeout_budget_instance
        provider_cls = app.state.registry.get_active_provider("tool_timeout_budget", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("tool_timeout", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("timeout_budget", default_name="default")
        if not provider_cls:
            return None
        if _tool_timeout_budget_instance is None or not isinstance(_tool_timeout_budget_instance, provider_cls):
            _tool_timeout_budget_instance = provider_cls()
        return _tool_timeout_budget_instance

    def _is_tool_timeout_budget_enabled() -> bool:
        if config.get("locus.tool_timeout_budget.enabled") is False:
            return False
        if config.get("locus.tools.timeout.enabled") is False:
            return False
        if config.get("locus.brain.tool_timeout_budget.enabled") is False:
            return False
        return True

    @app.post("/tools/timeout/resolve")
    def resolve_tool_timeout_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve effective execution timeout for a tool."""
        if not _is_tool_timeout_budget_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_timeout_budget.enabled"},
            )
        provider = _get_tool_timeout_budget_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool timeout budget provider registered")
        tool_name = body.get("tool_name", "")
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing required field: tool_name")
        requested_timeout = body.get("requested_timeout")
        try:
            resolution = provider.resolve_timeout(
                tool_name=tool_name,
                requested_timeout=requested_timeout,
            )
            return {"status": "ok", "resolution": resolution.to_dict()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/tools/timeout/record")
    def record_tool_execution_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Record completed tool execution duration and update turn budget."""
        if not _is_tool_timeout_budget_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_timeout_budget.enabled"},
            )
        provider = _get_tool_timeout_budget_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool timeout budget provider registered")
        tool_name = body.get("tool_name", "")
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing required field: tool_name")
        elapsed_secs = body.get("elapsed_secs", 0.0)
        timed_out = body.get("timed_out", False)
        provider.record_execution(
            tool_name=tool_name,
            elapsed_secs=elapsed_secs,
            timed_out=timed_out,
        )
        return {"status": "ok", "recorded": True}

    @app.get("/tools/timeout/remaining")
    def get_remaining_timeout_budget_route() -> Dict[str, Any]:
        """Get remaining turn budget in seconds."""
        if not _is_tool_timeout_budget_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_timeout_budget.enabled"},
            )
        provider = _get_tool_timeout_budget_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool timeout budget provider registered")
        rem = provider.get_remaining_turn_budget()
        return {"status": "ok", "remaining_turn_budget_secs": rem}

    @app.post("/tools/timeout/reset")
    def reset_tool_timeout_budget_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Reset elapsed time and optionally configure new turn budget."""
        if not _is_tool_timeout_budget_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_timeout_budget.enabled"},
            )
        provider = _get_tool_timeout_budget_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool timeout budget provider registered")
        payload = body or {}
        provider.reset_turn_budget(total_budget_secs=payload.get("total_budget_secs"))
        return {"status": "ok", "reset": True}

    @app.get("/tools/timeout/config")
    def get_tool_timeout_config_route() -> Dict[str, Any]:
        """Get Tool Timeout / Budget configuration and health."""
        if not _is_tool_timeout_budget_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.tool_timeout_budget.enabled"},
            )
        provider = _get_tool_timeout_budget_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No tool timeout budget provider registered")
        health = provider.health_check()
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "config": provider.get_config().to_dict(),
            "health": health,
        }

    # Custom Locus Tools routes (SPEC §3.12 / F-0104)
    from sidecar.custom_locus_tools import CustomLocusToolsProvider
    active_registry.register("custom_locus_tools", "default", CustomLocusToolsProvider)
    active_registry.register("custom_tools", "default", CustomLocusToolsProvider)
    active_registry.register("tools_custom", "default", CustomLocusToolsProvider)

    _custom_locus_tools_instance: Optional[Any] = None

    def _get_custom_locus_tools_provider() -> Optional[Any]:
        nonlocal _custom_locus_tools_instance
        provider_cls = app.state.registry.get_active_provider("custom_locus_tools", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("custom_tools", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("tools_custom", default_name="default")
        if not provider_cls:
            return None
        if _custom_locus_tools_instance is None or not isinstance(_custom_locus_tools_instance, provider_cls):
            _custom_locus_tools_instance = provider_cls()
        return _custom_locus_tools_instance

    def _is_custom_locus_tools_enabled() -> bool:
        if config.get("locus.custom_locus_tools.enabled") is False:
            return False
        if config.get("locus.tools.custom.enabled") is False:
            return False
        return True

    @app.get("/tools/custom/list")
    def list_custom_tools_route(include_disabled: bool = False) -> Dict[str, Any]:
        """List registered custom Locus tools."""
        if not _is_custom_locus_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.custom_locus_tools.enabled"},
            )
        provider = _get_custom_locus_tools_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No custom locus tools provider registered")
        tools = provider.list_tools(include_disabled=include_disabled)
        return {"status": "ok", "tools": [t.to_dict() for t in tools]}

    @app.get("/tools/custom/config")
    def get_custom_tools_config_route() -> Dict[str, Any]:
        """Get custom tools configuration and health check."""
        if not _is_custom_locus_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.custom_locus_tools.enabled"},
            )
        provider = _get_custom_locus_tools_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No custom locus tools provider registered")
        health = provider.health_check()
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "config": provider.get_config().to_dict(),
            "health": health,
        }

    @app.get("/tools/custom/{tool_name}")
    def get_custom_tool_route(tool_name: str) -> Dict[str, Any]:
        """Get custom tool specification by name."""
        if not _is_custom_locus_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.custom_locus_tools.enabled"},
            )
        provider = _get_custom_locus_tools_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No custom locus tools provider registered")
        tool = provider.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Custom tool '{tool_name}' not found")
        return {"status": "ok", "tool": tool.to_dict()}

    @app.post("/tools/custom/execute")
    def execute_custom_tool_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom tool with parameters."""
        if not _is_custom_locus_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.custom_locus_tools.enabled"},
            )
        provider = _get_custom_locus_tools_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No custom locus tools provider registered")
        tool_name = body.get("tool_name", "")
        if not tool_name:
            raise HTTPException(status_code=400, detail="Missing required field: tool_name")
        params = body.get("parameters", {})
        result = provider.execute_tool(tool_name, params)
        return {"status": "ok", "result": result.to_dict()}

    @app.post("/tools/custom/{tool_name}/toggle")
    def toggle_custom_tool_route(tool_name: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Toggle enabled state of a specific custom tool."""
        if not _is_custom_locus_tools_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.custom_locus_tools.enabled"},
            )
        provider = _get_custom_locus_tools_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No custom locus tools provider registered")
        enabled = body.get("enabled", True)
        try:
            provider.set_tool_enabled(tool_name, enabled)
            return {"status": "ok", "tool_name": tool_name, "enabled": enabled}
        except KeyError as ke:
            raise HTTPException(status_code=404, detail=str(ke))

    # -------------------------------------------------------------------------
    # SPEC §4.1-4.2 / F-0021 / US-46: Graph-Native Memory (Neo4j POLE+O) Routes
    # -------------------------------------------------------------------------
    from sidecar.neo4j_memory import Neo4jMemoryProvider
    from sidecar.providers.memory import POLEEntity, Relationship
    active_registry.register("memory", "default", Neo4jMemoryProvider)
    active_registry.register("neo4j_memory", "default", Neo4jMemoryProvider)
    active_registry.register("graph_memory", "default", Neo4jMemoryProvider)

    _memory_provider_instance: Optional[Any] = None

    def _get_memory_provider() -> Optional[Any]:
        nonlocal _memory_provider_instance
        provider_cls = app.state.registry.get_active_provider("memory", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("neo4j_memory", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("graph_memory", default_name="default")
        if not provider_cls:
            return None
        if _memory_provider_instance is None or not isinstance(_memory_provider_instance, provider_cls):
            _memory_provider_instance = provider_cls()
        return _memory_provider_instance

    def _is_memory_enabled() -> bool:
        if config.get("locus.memory.enabled") is False:
            return False
        return True

    @app.post("/memory/store")
    def store_memory_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Store conversation turn or content, extracting POLE+O entities."""
        if not _is_memory_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory.enabled"},
            )
        provider = _get_memory_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory provider registered")
        content = body.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Missing required field: content")
        entry_type = body.get("entry_type", "long_term")
        metadata = body.get("metadata")
        entry = provider.store(content=content, entry_type=entry_type, metadata=metadata)
        return {"status": "ok", "entry": entry.to_dict()}

    @app.post("/memory/query")
    def query_memory_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hybrid search and graph traversal over POLE+O entities."""
        if not _is_memory_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory.enabled"},
            )
        provider = _get_memory_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory provider registered")
        query_text = body.get("query", "")
        limit = body.get("limit", 10)
        depth = body.get("depth", 2)
        result = provider.query(query=query_text, limit=limit, depth=depth)
        return {"status": "ok", "result": result.to_dict()}

    @app.post("/memory/context")
    def get_memory_context_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve formatted graph pathways block for Context Forge Layer 4."""
        if not _is_memory_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory.enabled"},
            )
        provider = _get_memory_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory provider registered")
        query_text = body.get("query", "")
        max_tokens = body.get("max_tokens", 150)
        ctx_str = provider.get_context(query=query_text, max_tokens=max_tokens)
        return {"status": "ok", "context": ctx_str}

    @app.get("/memory/config")
    def get_memory_config_route() -> Dict[str, Any]:
        """Get graph memory diagnostics and POLE+O schema status."""
        if not _is_memory_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory.enabled"},
            )
        provider = _get_memory_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory provider registered")
        health = provider.health_check()
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "config": provider.get_config().to_dict(),
            "health": health,
        }

    @app.post("/memory/entity")
    def add_memory_entity_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Add or merge a POLE+O entity."""
        if not _is_memory_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory.enabled"},
            )
        provider = _get_memory_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory provider registered")
        entity = POLEEntity.from_dict(body)
        success = provider.add_entity(entity)
        return {"status": "ok", "success": success, "entity_id": entity.id}

    @app.get("/memory/entity/{entity_id}")
    def get_memory_entity_route(entity_id: str) -> Dict[str, Any]:
        """Get POLE+O entity by id or name."""
        if not _is_memory_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory.enabled"},
            )
        provider = _get_memory_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory provider registered")
        ent = provider.get_entity(entity_id)
        if not ent:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found")
        return {"status": "ok", "entity": ent.to_dict()}

    @app.post("/memory/reasoning")
    def record_memory_reasoning_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Record reasoning step and create :TOUCHED audit edges."""
        if not _is_memory_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory.enabled"},
            )
        provider = _get_memory_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory provider registered")
        step_name = body.get("step_name", "")
        if not step_name:
            raise HTTPException(status_code=400, detail="Missing required field: step_name")
        touched = body.get("touched_entities", [])
        tool_calls = body.get("tool_calls")
        step_id = provider.record_reasoning_step(step_name=step_name, touched_entities=touched, tool_calls=tool_calls)
        return {"status": "ok", "step_id": step_id}

    # -------------------------------------------------------------------------
    # SPEC §4.5 / F-0088 / US-47: Memory Tree (Hierarchical Summarization Cascade)
    # -------------------------------------------------------------------------
    from sidecar.memory_tree import HierarchicalMemoryTreeProvider
    from sidecar.providers.memory_tree import MemoryTreeConfig, TreeNode, TreeScopeConfig

    active_registry.register("memory_tree", "default", HierarchicalMemoryTreeProvider)
    active_registry.register(
        "memory_tree_hierarchical_summarization_cascade", "default", HierarchicalMemoryTreeProvider
    )

    _memory_tree_instance: Optional[HierarchicalMemoryTreeProvider] = None

    def _get_memory_tree_provider() -> Optional[HierarchicalMemoryTreeProvider]:
        nonlocal _memory_tree_instance
        provider_cls = app.state.registry.get_active_provider("memory_tree", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider(
                "memory_tree_hierarchical_summarization_cascade", default_name="default"
            )
        if not provider_cls:
            return None
        if _memory_tree_instance is None or not isinstance(_memory_tree_instance, provider_cls):
            tree_cfg = MemoryTreeConfig(
                enabled=config.get("locus.memory.tree.enabled", config.get("locus.memory_tree_hierarchical_summarization_cascade.enabled", True)),
                default_seal_gate=int(config.get("locus.memory.tree.seal_gate", 8)),
                stale_flush_seconds=float(config.get("locus.memory.tree.stale_flush_seconds", 10800.0)),
                db_path=config.get("locus.memory.tree.db_path", None),
            )
            _memory_tree_instance = provider_cls(config=tree_cfg)
        return _memory_tree_instance

    def _is_memory_tree_enabled() -> bool:
        if config.get("locus.memory_tree_hierarchical_summarization_cascade.enabled") is False:
            return False
        if config.get("locus.memory.tree.enabled") is False:
            return False
        return True

    @app.get("/memory/tree/config")
    def get_memory_tree_config_route() -> Dict[str, Any]:
        """Get Memory Tree subsystem configuration and health metrics."""
        if not _is_memory_tree_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_tree_hierarchical_summarization_cascade.enabled"},
            )
        provider = _get_memory_tree_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory tree provider registered")
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "health": provider.health(),
        }

    @app.get("/memory/tree/nodes")
    def get_memory_tree_nodes_route(
        tree_scope: Optional[str] = None,
        level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieve stored tree nodes with optional scope and level filtering."""
        if not _is_memory_tree_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_tree_hierarchical_summarization_cascade.enabled"},
            )
        provider = _get_memory_tree_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory tree provider registered")
        nodes = provider.get_nodes(tree_scope=tree_scope, level=level)
        return {"status": "ok", "nodes": [n.to_dict() for n in nodes]}

    @app.get("/memory/tree/search")
    def search_memory_tree_route(
        tree_scope: str = "default",
        query: str = "",
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """Perform top-down relevance search descending through tree nodes."""
        if not _is_memory_tree_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_tree_hierarchical_summarization_cascade.enabled"},
            )
        provider = _get_memory_tree_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory tree provider registered")
        nodes = provider.search(tree_scope=tree_scope, query=query, max_results=max_results)
        return {"status": "ok", "tree_scope": tree_scope, "query": query, "nodes": [n.to_dict() for n in nodes]}

    @app.post("/memory/tree/leaf")
    def append_memory_tree_leaf_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Append raw chunk to L0 buffer, auto-sealing if gate threshold is reached."""
        if not _is_memory_tree_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_tree_hierarchical_summarization_cascade.enabled"},
            )
        provider = _get_memory_tree_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory tree provider registered")
        tree_scope = body.get("tree_scope", "default")
        content = body.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Missing required field: content")
        source_id = body.get("source_id")
        source_kind = body.get("source_kind")
        node = provider.append_leaf(
            tree_scope=tree_scope,
            content=content,
            source_id=source_id,
            source_kind=source_kind,
        )
        return {"status": "ok", "node": node.to_dict()}

    @app.post("/memory/tree/seal")
    def seal_memory_tree_level_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Manually or conditionally seal a level in a tree scope."""
        if not _is_memory_tree_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_tree_hierarchical_summarization_cascade.enabled"},
            )
        provider = _get_memory_tree_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory tree provider registered")
        tree_scope = body.get("tree_scope", "default")
        level = int(body.get("level", 0))
        force = bool(body.get("force", False))
        parent = provider.seal_level(tree_scope=tree_scope, level=level, force=force)
        return {
            "status": "ok",
            "sealed": parent is not None,
            "node": parent.to_dict() if parent else None,
        }

    @app.post("/memory/tree/topic_route")
    def topic_route_memory_tree_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Route content chunk across matching topic trees."""
        if not _is_memory_tree_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_tree_hierarchical_summarization_cascade.enabled"},
            )
        provider = _get_memory_tree_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory tree provider registered")
        content = body.get("content", "")
        if not content:
            raise HTTPException(status_code=400, detail="Missing required field: content")
        topics = body.get("topics", [])
        if not isinstance(topics, list):
            raise HTTPException(status_code=400, detail="Field 'topics' must be a list of strings")
        matched = provider.topic_route(content=content, topics=topics)
        return {"status": "ok", "matched_scopes": matched}

    # -------------------------------------------------------------------------
    # SPEC §4.7 / F-0089 / US-48: Memory Sync (Multi-Source Ingestion Pipelines)
    # -------------------------------------------------------------------------
    from sidecar.memory_sync import MemorySyncManager
    from sidecar.providers.memory_sync import MemorySyncConfig, SourceScope, SyncOutcome, SyncPipelineKind

    active_registry.register("memory_sync", "default", MemorySyncManager)
    active_registry.register(
        "memory_sync_multi_source_ingestion_pipelines", "default", MemorySyncManager
    )

    _memory_sync_instance: Optional[MemorySyncManager] = None

    def _get_memory_sync_provider() -> Optional[MemorySyncManager]:
        nonlocal _memory_sync_instance
        provider_cls = app.state.registry.get_active_provider("memory_sync", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider(
                "memory_sync_multi_source_ingestion_pipelines", default_name="default"
            )
        if not provider_cls:
            return None
        if _memory_sync_instance is None or not isinstance(_memory_sync_instance, provider_cls):
            sync_cfg = MemorySyncConfig(
                enabled=config.get(
                    "locus.memory.sync.enabled",
                    config.get("locus.memory_sync_multi_source_ingestion_pipelines.enabled", True),
                ),
                periodic_interval_seconds=float(config.get("locus.memory.sync.periodic_interval_seconds", 1200.0)),
                queue_scheduler_interval_seconds=float(
                    config.get("locus.memory.sync.queue_scheduler_interval_seconds", 10800.0)
                ),
                daily_budget_cap=int(config.get("locus.memory.sync.daily_budget_cap", 1000)),
                state_db_path=config.get("locus.memory.sync.state_db_path", None),
            )
            _memory_sync_instance = provider_cls(config=sync_cfg)
        return _memory_sync_instance

    def _is_memory_sync_enabled() -> bool:
        if config.get("locus.memory_sync_multi_source_ingestion_pipelines.enabled") is False:
            return False
        if config.get("locus.memory.sync.enabled") is False:
            return False
        return True

    @app.get("/memory/sync/config")
    def get_memory_sync_config_route() -> Dict[str, Any]:
        """Get Multi-Source Ingestion Sync subsystem configuration and health."""
        if not _is_memory_sync_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_sync_multi_source_ingestion_pipelines.enabled"},
            )
        provider = _get_memory_sync_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory sync provider registered")
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "health": provider.health(),
        }

    @app.get("/memory/sync/pipelines")
    def list_memory_sync_pipelines_route() -> Dict[str, Any]:
        """List all registered ingestion pipelines across Composio, Workspace, and MCP."""
        if not _is_memory_sync_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_sync_multi_source_ingestion_pipelines.enabled"},
            )
        provider = _get_memory_sync_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory sync provider registered")
        return {"status": "ok", "pipelines": provider.list_pipelines()}

    @app.post("/memory/sync/tick_all")
    def tick_all_memory_sync_route() -> Dict[str, Any]:
        """Execute sync step across all active pipelines."""
        if not _is_memory_sync_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_sync_multi_source_ingestion_pipelines.enabled"},
            )
        provider = _get_memory_sync_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory sync provider registered")
        outcomes = provider.tick_all()
        return {"status": "ok", "outcomes": {k: v.to_dict() for k, v in outcomes.items()}}

    @app.post("/memory/sync/heal")
    def heal_memory_sync_source_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Self-healing raw-archive set difference reconciliation per Spec §4.7 line 887."""
        if not _is_memory_sync_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_sync_multi_source_ingestion_pipelines.enabled"},
            )
        provider = _get_memory_sync_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory sync provider registered")
        src_data = body.get("source", {})
        on_disk_files = body.get("on_disk_files", [])
        if not isinstance(on_disk_files, list):
            raise HTTPException(status_code=400, detail="Field 'on_disk_files' must be a list of file paths/IDs")
        source = SourceScope(
            tree_scope=src_data.get("tree_scope", "default"),
            raw_archive_id=src_data.get("raw_archive_id", "default"),
            provider=src_data.get("provider", "generic"),
        )
        healed = provider.check_and_rebuild_tree(source=source, on_disk_files=on_disk_files)
        return {"status": "ok", "healed_count": len(healed), "healed_files": healed}

    @app.post("/memory/sync/tick/{pipeline_id}")
    def tick_single_memory_sync_route(pipeline_id: str) -> Dict[str, Any]:
        """Execute single pipeline tick by ID."""
        if not _is_memory_sync_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_sync_multi_source_ingestion_pipelines.enabled"},
            )
        provider = _get_memory_sync_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory sync provider registered")
        outcome = provider.tick_pipeline(pipeline_id)
        return {"status": "ok", "pipeline_id": pipeline_id, "outcome": outcome.to_dict()}

    # -------------------------------------------------------------------------
    # SPEC §4.8 / F-0090 / US-49: Memory Queue (Async Job Pipeline)
    # -------------------------------------------------------------------------
    from sidecar.memory_queue import SqliteMemoryQueue
    from sidecar.providers.memory_queue import JobRecord, MemoryQueueConfig

    active_registry.register("memory_queue", "default", SqliteMemoryQueue)
    active_registry.register(
        "memory_queue_async_job_pipeline", "default", SqliteMemoryQueue
    )

    _memory_queue_instance: Optional[SqliteMemoryQueue] = None

    def _get_memory_queue_provider() -> Optional[SqliteMemoryQueue]:
        nonlocal _memory_queue_instance
        provider_cls = app.state.registry.get_active_provider("memory_queue", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider(
                "memory_queue_async_job_pipeline", default_name="default"
            )
        if not provider_cls:
            return None
        if _memory_queue_instance is None or not isinstance(_memory_queue_instance, provider_cls):
            queue_cfg = MemoryQueueConfig(
                workers=int(config.get("locus.memory.queue.workers", 2)),
                enabled=config.get(
                    "locus.memory.queue.enabled",
                    config.get("locus.memory_queue_async_job_pipeline.enabled", True),
                ),
                db_path=config.get("locus.memory.queue.db_path", None),
                lock_duration_ms=int(config.get("locus.memory.queue.lock_duration_ms", 300_000)),
                llm_concurrency=int(config.get("locus.memory.queue.llm_concurrency", 3)),
                throttle_gate_enabled=bool(config.get("locus.memory.queue.throttle_gate_enabled", True)),
            )
            _memory_queue_instance = provider_cls(config=queue_cfg)
        return _memory_queue_instance

    def _is_memory_queue_enabled() -> bool:
        if config.get("locus.memory_queue_async_job_pipeline.enabled") is False:
            return False
        if config.get("locus.memory.queue.enabled") is False:
            return False
        workers = config.get("locus.memory.queue.workers")
        if workers is not None and int(workers) <= 0:
            return False
        return True

    @app.get("/memory/queue/config")
    def get_memory_queue_config_route() -> Dict[str, Any]:
        """Get Memory Queue subsystem configuration and health."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "config": provider.config.to_dict(),
        }

    @app.get("/memory/queue/stats")
    def get_memory_queue_stats_route() -> Dict[str, Any]:
        """Get memory queue status counts and concurrency statistics."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        return {"status": "ok", "stats": provider.stats()}

    @app.get("/memory/queue/jobs")
    def list_memory_queue_jobs_route(
        status: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List memory queue jobs optionally filtered by status."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        jobs = provider.list_jobs(status=status, limit=limit)
        return {"status": "ok", "jobs": [j.to_dict() for j in jobs]}

    @app.post("/memory/queue/enqueue")
    def enqueue_memory_queue_job_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Enqueue memory processing job with deduplication key support."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        kind = body.get("kind")
        if not kind:
            raise HTTPException(status_code=400, detail="Missing required field: kind")
        payload = body.get("payload", {})
        dedupe_key = body.get("dedupe_key")
        job_id = provider.enqueue(kind=kind, payload=payload, dedupe_key=dedupe_key)
        return {
            "status": "ok",
            "job_id": job_id,
            "suppressed": job_id is None,
        }

    @app.post("/memory/queue/claim")
    def claim_memory_queue_job_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Claim next ready job atomically with lease token."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        worker_id = body.get("worker_id", "worker-1")
        job = provider.claim_next(worker_id=worker_id)
        return {"status": "ok", "job": job.to_dict() if job else None}

    @app.post("/memory/queue/settle")
    def settle_memory_queue_job_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Settle job (done or failed) with lease claim token verification."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        job_id = body.get("job_id")
        claim_token = body.get("claim_token")
        if job_id is None or not claim_token:
            raise HTTPException(status_code=400, detail="Missing job_id or claim_token")
        success = bool(body.get("success", True))
        error_msg = body.get("error_message", "")
        if success:
            settled = provider.mark_done(job_id=int(job_id), claim_token=claim_token)
        else:
            settled = provider.mark_failed(job_id=int(job_id), claim_token=claim_token, error_message=error_msg)
        return {"status": "ok", "settled": settled}

    @app.post("/memory/queue/recover_stale")
    def recover_stale_memory_queue_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Recover expired running leases back to ready."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        lock_duration_ms = body.get("lock_duration_ms")
        count = provider.recover_stale_locks(
            lock_duration_ms=int(lock_duration_ms) if lock_duration_ms else None
        )
        return {"status": "ok", "recovered_count": count}

    @app.post("/memory/queue/trigger_digest")
    def trigger_digest_memory_queue_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Manual helper to trigger single digest_daily job."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        date_str = body.get("date")
        if not date_str:
            raise HTTPException(status_code=400, detail="Missing required field: date")
        job_id = provider.trigger_digest(date_str=date_str)
        return {"status": "ok", "job_id": job_id}

    @app.post("/memory/queue/backfill_digests")
    def backfill_digests_memory_queue_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Manual helper to batch enqueue digest jobs across date range."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        from_date = body.get("from_date")
        to_date = body.get("to_date")
        if not from_date or not to_date:
            raise HTTPException(status_code=400, detail="Missing required fields: from_date, to_date")
        enqueued_ids = provider.backfill_missing_digests(from_date_str=from_date, to_date_str=to_date)
        return {"status": "ok", "enqueued_ids": enqueued_ids}

    @app.post("/memory/queue/flush_stale")
    def flush_stale_memory_queue_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Enqueue flush stale job for time-stale buffers (>3h)."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        date_str = body.get("date")
        if not date_str:
            raise HTTPException(status_code=400, detail="Missing required field: date")
        job_id = provider.flush_stale_daily(date_str=date_str)
        return {"status": "ok", "job_id": job_id}

    @app.post("/memory/queue/daily_tick")
    def daily_tick_memory_queue_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Run daily scheduler tick (enqueues DigestDaily(yesterday) + FlushStale(today))."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        date_str = body.get("date")
        digest_id, flush_id = provider.daily_tick(today_date_str=date_str)
        return {"status": "ok", "digest_job_id": digest_id, "flush_job_id": flush_id}

    @app.get("/memory/queue/jobs/{job_id}")
    def get_memory_queue_job_route(job_id: int) -> Dict[str, Any]:
        """Get single job record by ID."""
        if not _is_memory_queue_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_queue_async_job_pipeline.enabled"},
            )
        provider = _get_memory_queue_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory queue provider registered")
        job = provider.get_job(job_id=job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return {"status": "ok", "job": job.to_dict()}

    # -------------------------------------------------------------------------
    # SPEC §4.9 / F-0091 / US-50: Memory Diff (Snapshot-Based Change Tracking)
    # -------------------------------------------------------------------------
    from sidecar.memory_diff import SqliteMemoryDiffProvider
    from sidecar.providers.memory_diff import MemoryDiffConfig

    active_registry.register("memory_diff", "default", SqliteMemoryDiffProvider)
    active_registry.register(
        "memory_diff_snapshot_based_change_tracking", "default", SqliteMemoryDiffProvider
    )

    _memory_diff_instance: Optional[SqliteMemoryDiffProvider] = None

    def _get_memory_diff_provider() -> Optional[SqliteMemoryDiffProvider]:
        nonlocal _memory_diff_instance
        provider_cls = app.state.registry.get_active_provider("memory_diff", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider(
                "memory_diff_snapshot_based_change_tracking", default_name="default"
            )
        if not provider_cls:
            return None
        if _memory_diff_instance is None or not isinstance(_memory_diff_instance, provider_cls):
            diff_cfg = MemoryDiffConfig(
                enabled=config.get(
                    "locus.memory.diff.enabled",
                    config.get("locus.memory_diff_snapshot_based_change_tracking.enabled", True),
                ),
                db_path=config.get("locus.memory.diff.db_path", None),
                auto_snapshot_post_sync=bool(
                    config.get("locus.memory.diff.auto_snapshot_post_sync", True)
                ),
            )
            _memory_diff_instance = provider_cls(config=diff_cfg)
        return _memory_diff_instance

    def _is_memory_diff_enabled() -> bool:
        if config.get("locus.memory_diff_snapshot_based_change_tracking.enabled") is False:
            return False
        if config.get("locus.memory.diff.enabled") is False:
            return False
        return True

    @app.get("/memory/diff/config")
    def get_memory_diff_config_route() -> Dict[str, Any]:
        """Get Memory Diff subsystem configuration and health."""
        if not _is_memory_diff_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_diff_snapshot_based_change_tracking.enabled"},
            )
        provider = _get_memory_diff_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory diff provider registered")
        return {
            "status": "ok",
            "enabled": True,
            "provider": provider.__class__.__name__,
            "config": provider.config.to_dict(),
        }

    @app.get("/memory/diff/snapshots")
    def list_memory_diff_snapshots_route(
        source_scope: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List snapshots for a source scope, newest first."""
        if not _is_memory_diff_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_diff_snapshot_based_change_tracking.enabled"},
            )
        provider = _get_memory_diff_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory diff provider registered")
        snapshots = provider.list_snapshots(source_scope=source_scope, limit=limit)
        return {"status": "ok", "snapshots": [s.to_dict() for s in snapshots]}

    @app.post("/memory/diff/snapshot")
    def take_memory_diff_snapshot_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Take a new snapshot of memory source items."""
        if not _is_memory_diff_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_diff_snapshot_based_change_tracking.enabled"},
            )
        provider = _get_memory_diff_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory diff provider registered")
        source_scope = body.get("source_scope", "default")
        trigger = body.get("trigger", "manual")
        items = body.get("items", [])
        snapshot = provider.take_snapshot(source_scope=source_scope, trigger=trigger, items=items)
        return {"status": "ok", "snapshot": snapshot.to_dict()}

    @app.post("/memory/diff/compare")
    def compare_memory_diff_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two snapshots and return additions, removals, and modifications."""
        if not _is_memory_diff_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_diff_snapshot_based_change_tracking.enabled"},
            )
        provider = _get_memory_diff_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory diff provider registered")
        source_scope = body.get("source_scope", "default")
        from_id = body.get("from_snapshot_id")
        to_id = body.get("to_snapshot_id")
        if not from_id or not to_id:
            raise HTTPException(status_code=400, detail="Missing from_snapshot_id or to_snapshot_id")
        diff_res = provider.diff(source_scope=source_scope, from_snapshot_id=from_id, to_snapshot_id=to_id)
        return {"status": "ok", "diff": diff_res.to_dict()}

    @app.post("/memory/diff/checkpoint")
    def create_memory_diff_checkpoint_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Create a named baseline checkpoint across active source scopes."""
        if not _is_memory_diff_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_diff_snapshot_based_change_tracking.enabled"},
            )
        provider = _get_memory_diff_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory diff provider registered")
        name = body.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="Missing required field: name")
        scopes = body.get("scopes")
        scope_items = body.get("scope_items")
        checkpoint = provider.create_checkpoint(name=name, scopes=scopes, scope_items=scope_items)
        return {"status": "ok", "checkpoint": checkpoint.to_dict()}

    @app.post("/memory/diff/checkpoint/diff")
    def diff_since_checkpoint_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Compute cross-source diff since a named checkpoint."""
        if not _is_memory_diff_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_diff_snapshot_based_change_tracking.enabled"},
            )
        provider = _get_memory_diff_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory diff provider registered")
        name = body.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="Missing required field: name")
        current_scope_items = body.get("current_scope_items")
        try:
            cross_diff = provider.diff_since_checkpoint(
                name=name,
                current_scope_items=current_scope_items,
            )
            return {"status": "ok", "cross_diff": cross_diff.to_dict()}
        except ValueError as err:
            raise HTTPException(status_code=404, detail=str(err))

    @app.get("/memory/diff/what_changed")
    def what_changed_memory_diff_route(
        checkpoint_name: Optional[str] = None,
        source_scope: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Agent tool endpoint returning human-readable diff summary."""
        if not _is_memory_diff_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_diff_snapshot_based_change_tracking.enabled"},
            )
        provider = _get_memory_diff_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory diff provider registered")
        summary_text = provider.what_changed(checkpoint_name=checkpoint_name, source_scope=source_scope)
        return {"status": "ok", "summary": summary_text}

    @app.get("/memory/diff/snapshots/{snapshot_id}")
    def get_memory_diff_snapshot_route(snapshot_id: str) -> Dict[str, Any]:
        """Retrieve single snapshot record by ID."""
        if not _is_memory_diff_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.memory_diff_snapshot_based_change_tracking.enabled"},
            )
        provider = _get_memory_diff_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No memory diff provider registered")
        snapshot = provider.get_snapshot(snapshot_id=snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail=f"Snapshot {snapshot_id} not found")
        return {"status": "ok", "snapshot": snapshot.to_dict()}

    # SPEC §4.10 / F-0022 / US-51: Holographic HRR (Memory Binding)
    from sidecar.memory.hrr import HolographicMemory
    from sidecar.providers.holographic import HolographicConfig, HRRVector

    active_registry.register("holographic_hrr", "default", HolographicMemory)
    active_registry.register("associative_memory", "default", HolographicMemory)

    _holographic_instance: Optional[HolographicMemory] = None

    def _get_holographic_provider() -> Optional[HolographicMemory]:
        nonlocal _holographic_instance
        provider_cls = app.state.registry.get_active_provider("holographic_hrr", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("associative_memory", default_name="default")
        if not provider_cls:
            return None
        if _holographic_instance is None or not isinstance(_holographic_instance, provider_cls):
            dim = config.get("locus.memory.hrr.dimension", 2048)
            threshold = config.get("locus.memory.hrr.similarity_threshold", 0.70)
            cache_path = config.get("locus.memory.hrr.codebook_path", None)
            hrr_cfg = HolographicConfig(
                enabled=config.get("locus.holographic_hrr.enabled", config.get("locus.memory.hrr.enabled", True)),
                dimension=int(dim),
                similarity_threshold=float(threshold),
                codebook_cache_path=cache_path,
            )
            _holographic_instance = provider_cls(config=hrr_cfg)
        return _holographic_instance

    def _is_holographic_enabled() -> bool:
        if config.get("locus.holographic_hrr.enabled") is False:
            return False
        if config.get("locus.memory.hrr.enabled") is False:
            return False
        return True

    @app.get("/memory/hrr/config")
    def get_holographic_config_route() -> Dict[str, Any]:
        """Get Holographic HRR configuration and status."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        return {"status": "ok", "config": provider.config.to_dict()}

    @app.post("/memory/hrr/bind")
    def bind_holographic_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Circular convolution: a ⊛ b."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        a_vec = HRRVector.from_dict(body.get("a", {}))
        b_vec = HRRVector.from_dict(body.get("b", {}))
        res = provider.bind(a_vec, b_vec)
        return {"status": "ok", "vector": res.to_dict()}

    @app.post("/memory/hrr/unbind")
    def unbind_holographic_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Circular correlation: a ≈ c ⊙ b."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        c_vec = HRRVector.from_dict(body.get("c", {}))
        b_vec = HRRVector.from_dict(body.get("b", {}))
        res = provider.unbind(c_vec, b_vec)
        return {"status": "ok", "vector": res.to_dict()}

    @app.post("/memory/hrr/bundle")
    def bundle_holographic_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Vector superposition: s = normalize(sum(vectors))."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        raw_vecs = body.get("vectors", [])
        if not raw_vecs:
            raise HTTPException(status_code=400, detail="vectors list cannot be empty")
        vecs = [HRRVector.from_dict(v) for v in raw_vecs]
        res = provider.bundle(vecs)
        return {"status": "ok", "vector": res.to_dict()}

    @app.post("/memory/hrr/cleanup")
    def cleanup_holographic_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Associative recall against codebook symbols."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        vec = HRRVector.from_dict(body.get("vector", {}))
        threshold = body.get("threshold")
        th_val = float(threshold) if threshold is not None else None
        sym, sim = provider.cleanup_with_score(vec, threshold=th_val)
        return {"status": "ok", "symbol": sym, "similarity": sim}

    @app.post("/memory/hrr/encode_state")
    def encode_state_holographic_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Fast Ephemeral State Composition Pipeline."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        curr_task = body.get("current_task")
        act_mode = body.get("active_mode")
        stress_lvl = body.get("stress_level")
        res = provider.encode_ephemeral_state(curr_task, act_mode, stress_lvl)
        return {"status": "ok", "vector": res.to_dict()}

    @app.get("/memory/hrr/codebook/symbols")
    def list_holographic_symbols_route() -> Dict[str, Any]:
        """List registered symbols in HRR codebook."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        symbols = provider.list_symbols()
        return {"status": "ok", "symbols": symbols}

    @app.post("/memory/hrr/codebook/symbol")
    def get_or_create_symbol_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve or create proto-vector for a symbol."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        symbol = body.get("symbol")
        if not symbol:
            raise HTTPException(status_code=400, detail="symbol is required")
        vec = provider.get_or_create_symbol(str(symbol))
        return {"status": "ok", "symbol": symbol, "vector": vec.to_dict()}

    @app.get("/memory/hrr/codebook/symbols/{symbol}")
    def get_holographic_symbol_route(symbol: str) -> Dict[str, Any]:
        """Retrieve stored proto-vector for a symbol if present."""
        if not _is_holographic_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.holographic_hrr.enabled"},
            )
        provider = _get_holographic_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No holographic provider registered")
        vec = provider.get_symbol_vector(symbol)
        if not vec:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found in codebook")
        return {"status": "ok", "symbol": symbol, "vector": vec.to_dict()}

    # SPEC §4.12 / F-0023 / US-52: STDP Reinforcement (Spike-Timing-Dependent Plasticity)
    from sidecar.memory.graph_reinforcement import GraphPlasticityProvider
    from sidecar.providers.stdp_reinforcement import (
        OutcomeEvent,
        RetrievalEvent,
        STDPConfig,
        TraversedEdgeRecord,
        TurnAuditLog,
    )

    active_registry.register("stdp_reinforcement", "default", GraphPlasticityProvider)
    active_registry.register("graph_plasticity", "default", GraphPlasticityProvider)

    _stdp_instance: Optional[GraphPlasticityProvider] = None

    def _get_stdp_provider() -> Optional[GraphPlasticityProvider]:
        nonlocal _stdp_instance
        provider_cls = app.state.registry.get_active_provider("stdp_reinforcement", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("graph_plasticity", default_name="default")
        if not provider_cls:
            return None
        if _stdp_instance is None or not isinstance(_stdp_instance, provider_cls):
            db_path = config.get("locus.memory.stdp.db_path", None)
            stdp_cfg = STDPConfig(
                enabled=config.get("locus.stdp_reinforcement.enabled", config.get("locus.memory.stdp.enabled", True)),
                a_plus=float(config.get("locus.memory.stdp.a_plus", 0.15)),
                a_minus=float(config.get("locus.memory.stdp.a_minus", 0.12)),
                tau_plus=float(config.get("locus.memory.stdp.tau_plus", 300.0)),
                tau_minus=float(config.get("locus.memory.stdp.tau_minus", 600.0)),
                w_min=float(config.get("locus.memory.stdp.w_min", 0.05)),
                w_max=float(config.get("locus.memory.stdp.w_max", 1.00)),
                prune_threshold=float(config.get("locus.memory.stdp.prune_threshold", 0.08)),
                storage_path=db_path,
            )
            _stdp_instance = provider_cls(config=stdp_cfg, db_path=db_path)
        return _stdp_instance

    def _is_stdp_enabled() -> bool:
        if config.get("locus.stdp_reinforcement.enabled") is False:
            return False
        if config.get("locus.memory.stdp.enabled") is False:
            return False
        return True

    @app.get("/memory/stdp/config")
    def get_stdp_config_route() -> Dict[str, Any]:
        """Get STDP Reinforcement configuration and status."""
        if not _is_stdp_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.stdp_reinforcement.enabled"},
            )
        provider = _get_stdp_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No STDP provider registered")
        return {"status": "ok", "config": provider.config.to_dict()}

    @app.post("/memory/stdp/update")
    def calculate_stdp_update_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Compute single edge STDP update."""
        if not _is_stdp_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.stdp_reinforcement.enabled"},
            )
        provider = _get_stdp_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No STDP provider registered")
        retrieval = RetrievalEvent.from_dict(body.get("retrieval", {}))
        outcome = OutcomeEvent.from_dict(body.get("outcome", {}))
        current_w = float(body.get("current_weight", 0.50))
        new_w = provider.apply_stdp_update(retrieval, outcome, current_w)
        return {"status": "ok", "updated_weight": new_w}

    @app.post("/memory/stdp/process_turn")
    def process_turn_stdp_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Batch graph reinforcement cycle for turn audit log."""
        if not _is_stdp_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.stdp_reinforcement.enabled"},
            )
        provider = _get_stdp_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No STDP provider registered")
        turn_log = TurnAuditLog.from_dict(body)
        res = provider.process_turn_stdp(turn_log)
        return {"status": "ok", "result": res}

    @app.get("/memory/stdp/prune_candidates")
    def list_stdp_prune_candidates_route() -> Dict[str, Any]:
        """List edges tagged or eligible for pruning."""
        if not _is_stdp_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.stdp_reinforcement.enabled"},
            )
        provider = _get_stdp_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No STDP provider registered")
        candidates = provider.list_prune_candidates()
        return {"status": "ok", "candidates": candidates}

    @app.get("/memory/stdp/weights/{edge_id}")
    def get_stdp_edge_weight_route(edge_id: str) -> Dict[str, Any]:
        """Get weight for an edge."""
        if not _is_stdp_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.stdp_reinforcement.enabled"},
            )
        provider = _get_stdp_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No STDP provider registered")
        w = provider.get_edge_weight(edge_id)
        return {"status": "ok", "edge_id": edge_id, "weight": w}

    @app.post("/memory/stdp/weights/{edge_id}")
    def set_stdp_edge_weight_route(edge_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Set weight for an edge."""
        if not _is_stdp_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.stdp_reinforcement.enabled"},
            )
        provider = _get_stdp_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No STDP provider registered")
        w = float(body.get("weight", 0.50))
        provider.set_edge_weight(edge_id, w)
        return {"status": "ok", "edge_id": edge_id, "weight": provider.get_edge_weight(edge_id)}

    # SPEC §4.13 / F-0024 / US-53: Spaced Repetition Memory Consolidation (FSRS / SM-2)
    from sidecar.memory.memory_scheduler import SpacedRepetitionMemoryScheduler
    from sidecar.providers.spaced_repetition import (
        MemoryConsolidationProvider,
        MemoryNodeState,
        SpacedRepetitionConfig,
    )

    active_registry.register("spaced_repetition", "default", SpacedRepetitionMemoryScheduler)
    active_registry.register("memory_consolidation", "default", SpacedRepetitionMemoryScheduler)

    _sr_instance: Optional[MemoryConsolidationProvider] = None

    def _get_sr_provider() -> Optional[MemoryConsolidationProvider]:
        nonlocal _sr_instance
        provider_cls = app.state.registry.get_active_provider("spaced_repetition", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("memory_consolidation", default_name="default")
        if not provider_cls:
            return None
        if _sr_instance is None or (isinstance(provider_cls, type) and not isinstance(_sr_instance, provider_cls)):
            db_path = config.get("locus.memory.spaced_repetition.db_path", None)
            sr_cfg = SpacedRepetitionConfig(
                enabled=config.get("locus.spaced_repetition.enabled", config.get("locus.memory.spaced_repetition.enabled", True)),
                default_ease_factor=float(config.get("locus.memory.spaced_repetition.default_ease_factor", 2.50)),
                min_ease_factor=float(config.get("locus.memory.spaced_repetition.min_ease_factor", 1.30)),
                initial_interval_first=int(config.get("locus.memory.spaced_repetition.initial_interval_first", 1)),
                initial_interval_second=int(config.get("locus.memory.spaced_repetition.initial_interval_second", 6)),
                core_fact_min_repetitions=int(config.get("locus.memory.spaced_repetition.core_fact_min_repetitions", 5)),
                core_fact_min_ease=float(config.get("locus.memory.spaced_repetition.core_fact_min_ease", 2.50)),
                max_batch_size=int(config.get("locus.memory.spaced_repetition.max_batch_size", 50)),
                storage_path=db_path,
            )
            if isinstance(provider_cls, type):
                _sr_instance = provider_cls(config=sr_cfg, db_path=db_path)
            else:
                _sr_instance = provider_cls()
        return _sr_instance

    def _is_sr_enabled() -> bool:
        if config.get("locus.spaced_repetition.enabled") is False:
            return False
        if config.get("locus.memory.spaced_repetition.enabled") is False:
            return False
        return True

    @app.get("/memory/spaced_repetition/config")
    def get_sr_config_route() -> Dict[str, Any]:
        """Get Spaced Repetition configuration and status."""
        if not _is_sr_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.spaced_repetition.enabled"},
            )
        provider = _get_sr_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Spaced Repetition provider registered")
        return {"status": "ok", "config": provider.config.to_dict()}

    @app.post("/memory/spaced_repetition/calculate")
    def calculate_sr_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Statelessly compute next SM-2 review interval without mutating store."""
        if not _is_sr_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.spaced_repetition.enabled"},
            )
        provider = _get_sr_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Spaced Repetition provider registered")
        raw_state = body.get("state", {})
        state = MemoryNodeState.from_dict(raw_state)
        grade = int(body.get("quality_grade", 3))
        ts = body.get("timestamp")
        timestamp = float(ts) if ts is not None else None
        next_state = provider.calculate_next_review(state, grade, timestamp=timestamp)
        return next_state.to_dict()

    @app.post("/memory/spaced_repetition/review")
    def record_sr_review_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Record review outcome for a node and advance its schedule."""
        if not _is_sr_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.spaced_repetition.enabled"},
            )
        provider = _get_sr_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Spaced Repetition provider registered")
        node_id = str(body.get("node_id", ""))
        grade = int(body.get("quality_grade", 3))
        ts = body.get("timestamp")
        timestamp = float(ts) if ts is not None else None
        updated = provider.record_review(node_id, grade, timestamp=timestamp)
        return updated.to_dict()

    @app.get("/memory/spaced_repetition/due")
    def get_sr_due_nodes_route(limit: int = 50, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """Fetch nodes currently due for memory review."""
        if not _is_sr_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.spaced_repetition.enabled"},
            )
        provider = _get_sr_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Spaced Repetition provider registered")
        due = provider.get_due_nodes(limit=limit, timestamp=timestamp)
        return {"status": "ok", "count": len(due), "nodes": [n.to_dict() for n in due]}

    @app.post("/memory/spaced_repetition/consolidate")
    def run_sr_consolidation_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run nightly memory consolidation worker over due nodes."""
        if not _is_sr_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.spaced_repetition.enabled"},
            )
        provider = _get_sr_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Spaced Repetition provider registered")
        b = body or {}
        limit = int(b.get("limit", 50))
        simulated_grades = b.get("simulated_grades")
        ts = b.get("timestamp")
        timestamp = float(ts) if ts is not None else None
        res = provider.run_consolidation(limit=limit, simulated_grades=simulated_grades, timestamp=timestamp)
        return {"status": "ok", "result": res}

    @app.get("/memory/spaced_repetition/core_facts")
    def list_sr_core_facts_route() -> Dict[str, Any]:
        """List all nodes promoted to permanent core facts."""
        if not _is_sr_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.spaced_repetition.enabled"},
            )
        provider = _get_sr_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Spaced Repetition provider registered")
        facts = provider.list_core_facts()
        return {"status": "ok", "count": len(facts), "core_facts": [f.to_dict() for f in facts]}

    @app.get("/memory/spaced_repetition/nodes/{node_id}")
    def get_sr_node_route(node_id: str) -> Dict[str, Any]:
        """Get state for a memory node."""
        if not _is_sr_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.spaced_repetition.enabled"},
            )
        provider = _get_sr_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Spaced Repetition provider registered")
        node = provider.get_node_state(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        return node.to_dict()

    @app.post("/memory/spaced_repetition/nodes/{node_id}")
    def save_sr_node_route(node_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize or update state for a memory node."""
        if not _is_sr_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.spaced_repetition.enabled"},
            )
        provider = _get_sr_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Spaced Repetition provider registered")
        node = MemoryNodeState.from_dict({**body, "node_id": node_id})
        provider.save_node_state(node)
        return {"status": "ok", "node": node.to_dict()}

    # SPEC §4.14 / F-0025 / US-54: Project-Specific Memory Decay Engine
    from sidecar.providers.project_memory_decay import (
        DefaultProjectMemoryDecayProvider,
        MemoryDecayProvider,
        ProjectDecayConfig,
        ProjectMemoryDecayProvider,
    )
    from sidecar.memory.project_decay import (
        ProjectNode,
        ProjectRecord,
        calculate_retention_strength,
    )

    active_registry.register("project_memory_decay", "default", DefaultProjectMemoryDecayProvider)
    active_registry.register("memory_decay", "default", DefaultProjectMemoryDecayProvider)

    _decay_instance: Optional[MemoryDecayProvider] = None

    def _get_decay_provider() -> Optional[MemoryDecayProvider]:
        nonlocal _decay_instance
        provider_cls = app.state.registry.get_active_provider("project_memory_decay", default_name="default")
        if not provider_cls:
            provider_cls = app.state.registry.get_active_provider("memory_decay", default_name="default")
        if not provider_cls:
            return None
        if _decay_instance is None or (isinstance(provider_cls, type) and not isinstance(_decay_instance, provider_cls)):
            cfg = ProjectDecayConfig(
                enabled=config.get("locus.project_memory_decay.enabled", config.get("locus.memory.decay.enabled", True)),
                cold_storage_threshold=float(config.get("locus.memory.decay.cold_storage_threshold", 0.10)),
                storage_dir=config.get("locus.memory.decay.storage_dir", None),
            )
            if isinstance(provider_cls, type):
                _decay_instance = provider_cls(config=cfg)
            elif callable(provider_cls):
                _decay_instance = provider_cls()
            else:
                _decay_instance = provider_cls
        return _decay_instance

    def _is_decay_enabled() -> bool:
        if config.get("locus.project_memory_decay.enabled") is False:
            return False
        if config.get("locus.memory.decay.enabled") is False:
            return False
        return True

    @app.get("/memory/decay/config")
    def get_decay_config_route() -> Dict[str, Any]:
        """Get Project Memory Decay configuration and status."""
        if not _is_decay_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.project_memory_decay.enabled"},
            )
        provider = _get_decay_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Memory Decay provider registered")
        return {"status": "ok", "config": provider.config.to_dict()}

    @app.post("/memory/decay/calculate")
    def calculate_decay_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate retention strength S(t) for a project state and days inactive."""
        if not _is_decay_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.project_memory_decay.enabled"},
            )
        provider = _get_decay_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Memory Decay provider registered")
        project_state = str(body.get("project_state", "ACTIVE"))
        days = float(body.get("days_since_last_touch", body.get("days_inactive", 0.0)))
        s_0 = float(body.get("s_0", 1.0))
        strength = provider.calculate_retention(project_state=project_state, days_since_last_touch=days, s_0=s_0)
        return {
            "status": "ok",
            "project_state": project_state.upper(),
            "days_since_last_touch": days,
            "retention_strength": strength,
            "cold_archive_candidate": bool(strength < provider.config.cold_storage_threshold),
        }

    @app.post("/memory/decay/projects")
    def register_decay_project_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Register or update a project and its associated nodes."""
        if not _is_decay_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.project_memory_decay.enabled"},
            )
        provider = _get_decay_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Memory Decay provider registered")
        proj = ProjectRecord.from_dict(body)
        provider.register_project(proj)
        nodes_data = body.get("nodes", [])
        for nd in nodes_data:
            node = ProjectNode.from_dict({**nd, "project_id": proj.project_id})
            provider.add_project_node(node)
        return {"status": "ok", "project": proj.to_dict(), "node_count": len(nodes_data)}

    @app.post("/memory/decay/sweep")
    def run_decay_sweep_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute project memory decay sweep and trigger cold archive."""
        if not _is_decay_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.project_memory_decay.enabled"},
            )
        provider = _get_decay_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Memory Decay provider registered")
        b = body or {}
        ts = b.get("timestamp")
        dry_run = bool(b.get("dry_run", False))
        res = provider.sweep(current_timestamp=float(ts) if ts is not None else None, dry_run=dry_run)
        return {"status": "ok", "result": res}

    @app.get("/memory/decay/archives")
    def list_decay_archives_route() -> Dict[str, Any]:
        """List all cold archives in .locus/memory/cold_archive/."""
        if not _is_decay_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.project_memory_decay.enabled"},
            )
        provider = _get_decay_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Memory Decay provider registered")
        archives = provider.list_archives()
        return {"status": "ok", "count": len(archives), "archives": archives}

    @app.get("/memory/decay/archives/{project_id}")
    def get_decay_archive_route(project_id: str) -> Dict[str, Any]:
        """Read and decompress cold archived memory cluster for a project."""
        if not _is_decay_enabled():
            return JSONResponse(
                status_code=503,
                content={"disabled": "locus.project_memory_decay.enabled"},
            )
        provider = _get_decay_provider()
        if not provider:
            raise HTTPException(status_code=404, detail="No Memory Decay provider registered")
        try:
            archive = provider.get_archive(project_id)
            return {"status": "ok", "archive": archive}
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"No cold archive found for project {project_id}")

    # Context Compression routes (SPEC §4.16 / F-0110 / US-55)
    from sidecar.compaction.context_engine import (
        CompactionConfig,
        DefaultCompactionProvider,
        DefaultContextEngine,
        HermesContextCompressor,
    )
    active_registry.register("compaction", "default", DefaultCompactionProvider)
    active_registry.register("compaction", "hermes_context_engine", DefaultCompactionProvider)
    active_registry.register("context_compression_engine", "default", DefaultCompactionProvider)

    _compaction_provider_instance: Optional[DefaultCompactionProvider] = None

    def _get_compaction_provider() -> DefaultCompactionProvider:
        nonlocal _compaction_provider_instance
        if _compaction_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider("compaction", default_name="default")
            if provider_cls:
                _compaction_provider_instance = provider_cls()
            else:
                _compaction_provider_instance = DefaultCompactionProvider()
        return _compaction_provider_instance

    def _is_compaction_feature_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("compaction"):
            return False
        val = config.get("locus.context_compression.enabled")
        if val is not None and not config.is_enabled("locus.context_compression.enabled"):
            return False
        val2 = config.get("locus.compaction.enabled")
        if val2 is not None and not config.is_enabled("locus.compaction.enabled"):
            return False
        return True

    @app.get("/compaction/config")
    def get_compaction_config_route() -> Dict[str, Any]:
        """Retrieve active configuration and status for Context Compression."""
        if not _is_compaction_feature_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.context_compression.enabled"})
        provider = _get_compaction_provider()
        return {
            "status": "ok",
            "provider": provider.name,
            "config": provider.config.to_dict(),
            "threshold_tokens": provider.get_engine().threshold_tokens,
            "compression_count": provider.get_engine().compression_count,
        }

    @app.post("/compaction/should-compress")
    def should_compress_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if prompt tokens exceed context compression threshold."""
        if not _is_compaction_feature_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.context_compression.enabled"})
        prompt_tokens = int(body.get("prompt_tokens", 0))
        provider = _get_compaction_provider()
        engine = provider.get_engine()
        should = engine.should_compress(prompt_tokens)
        return {
            "status": "ok",
            "prompt_tokens": prompt_tokens,
            "threshold_tokens": engine.threshold_tokens,
            "should_compress": should,
        }

    @app.post("/compaction/compress")
    def compress_context_flow_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Hermes 7-step context compression with session splitting."""
        if not _is_compaction_feature_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.context_compression.enabled"})
        messages = body.get("messages") or []
        focus_topic = body.get("focus_topic")
        old_session_id = body.get("session_id")

        provider = _get_compaction_provider()
        result = provider.compress_context(
            messages=messages,
            focus_topic=focus_topic,
            old_session_id=old_session_id,
        )
        return {"status": "ok", "result": result}

    @app.post("/compaction/engine/update-model")
    def update_model_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Update active model parameters and recalculate threshold tokens."""
        if not _is_compaction_feature_enabled():
            return JSONResponse(status_code=503, content={"disabled": "locus.context_compression.enabled"})
        model = str(body.get("model", "default"))
        context_length = int(body.get("context_length", 128000))
        threshold_percent = body.get("threshold_percent")
        if threshold_percent is not None:
            threshold_percent = float(threshold_percent)

        provider = _get_compaction_provider()
        engine = provider.get_engine()
        engine.update_model(model, context_length, threshold_percent)
        return {
            "status": "ok",
            "model": model,
            "context_length": engine.context_length,
            "threshold_percent": engine.threshold_percent,
            "threshold_tokens": engine.threshold_tokens,
        }

    # Headroom CCR routes (SPEC §4.17: Token Compression (Headroom CCR) / F-0026 / US-56)
    from sidecar.context.headroom_pipeline import CompressConfig, CompressResult, HeadroomPipeline
    from sidecar.providers.headroom_ccr import DefaultHeadroomCCRProvider
    active_registry.register("compression_headroom_ccr", "default_headroom_ccr", DefaultHeadroomCCRProvider)

    def _is_headroom_ccr_enabled() -> bool:
        val1 = config.get("locus.headroom_ccr.enabled")
        if val1 is not None and not config.is_enabled("locus.headroom_ccr.enabled"):
            return False
        val2 = config.get("locus.compression.enabled")
        if val2 is not None and not config.is_enabled("locus.compression.enabled"):
            return False
        return True

    def _get_headroom_provider() -> DefaultHeadroomCCRProvider:
        provider_cls = app.state.registry.get_active_provider(
            "compression_headroom_ccr", default_name="default_headroom_ccr"
        )
        if not provider_cls:
            return DefaultHeadroomCCRProvider()
        try:
            return provider_cls()
        except Exception:
            return DefaultHeadroomCCRProvider()

    @app.get("/compression/headroom/config")
    def get_headroom_ccr_config_route() -> Dict[str, Any]:
        """SPEC §4.17 line 690: Get Headroom CCR configuration knobs."""
        if not _is_headroom_ccr_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Headroom CCR is disabled", "disabled": "locus.headroom_ccr.enabled"},
            )
        provider = _get_headroom_provider()
        return provider.get_config()

    @app.post("/compression/headroom/compress")
    def compress_headroom_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §4.17 line 689: compress(messages, model, config) -> CompressResult"""
        if not _is_headroom_ccr_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Headroom CCR is disabled", "disabled": "locus.headroom_ccr.enabled"},
            )
        messages = body.get("messages") or []
        model = body.get("model")
        cfg_data = body.get("config")
        cfg = CompressConfig.from_dict(cfg_data) if isinstance(cfg_data, dict) else None

        provider = _get_headroom_provider()
        res = provider.compress(messages=messages, model=model, config=cfg)
        return {"status": "ok", "result": res.to_dict()}

    @app.get("/compression/headroom/retrieve/{cache_key}")
    def retrieve_headroom_route(cache_key: str) -> Dict[str, Any]:
        """SPEC §4.17 line 701: headroom_retrieve(cache_key) -> full original text."""
        if not _is_headroom_ccr_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Headroom CCR is disabled", "disabled": "locus.headroom_ccr.enabled"},
            )
        provider = _get_headroom_provider()
        original = provider.retrieve(cache_key)
        if original is None:
            raise HTTPException(status_code=404, detail=f"CCR cache key '{cache_key}' not found or expired")
        return {"status": "ok", "cache_key": cache_key, "original": original}

    @app.post("/compression/headroom/retrieve")
    def retrieve_headroom_post_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience POST endpoint for headroom_retrieve(cache_key)."""
        if not _is_headroom_ccr_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Headroom CCR is disabled", "disabled": "locus.headroom_ccr.enabled"},
            )
        cache_key = str(body.get("cache_key", ""))
        provider = _get_headroom_provider()
        original = provider.retrieve(cache_key)
        if original is None:
            raise HTTPException(status_code=404, detail=f"CCR cache key '{cache_key}' not found or expired")
        return {"status": "ok", "cache_key": cache_key, "original": original}

    # Memory Provider Interface & Stackable Memory Manager routes (SPEC §4.18 / F-0118 / US-57)
    from sidecar.memory.provider_interface import (
        DefaultMemoryProvider,
        MemoryManager,
        MemoryProvider,
    )
    _memory_manager_instance = MemoryManager()
    default_mem_provider = DefaultMemoryProvider(name="default_memory")
    _memory_manager_instance.register_provider(default_mem_provider, is_primary=True)
    active_registry.register("memory_provider_manager", "default_memory_manager", lambda **kw: _memory_manager_instance)

    def _is_memory_provider_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("memory_provider_manager"):
            return False
        val1 = config.get("locus.memory_provider.enabled")
        if val1 is not None and not config.is_enabled("locus.memory_provider.enabled"):
            return False
        val2 = config.get("locus.memory.enabled")
        if val2 is not None and not config.is_enabled("locus.memory.enabled"):
            return False
        return True

    def _get_memory_manager() -> MemoryManager:
        provider_cls = app.state.registry.get_active_provider(
            "memory_provider_manager", default_name="default_memory_manager"
        )
        if not provider_cls:
            return _memory_manager_instance
        try:
            res = provider_cls()
            if isinstance(res, MemoryManager):
                return res
            return _memory_manager_instance
        except Exception:
            return _memory_manager_instance

    @app.get("/memory/provider/config")
    def get_memory_provider_config_route() -> Dict[str, Any]:
        """SPEC §4.18 line 5253: Return active memory providers and status."""
        if not _is_memory_provider_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Memory provider is disabled", "disabled": "locus.memory_provider.enabled"},
            )
        mgr = _get_memory_manager()
        active = mgr.get_active_providers()
        primary = mgr.get_primary_provider()
        return {
            "status": "ok",
            "enabled": True,
            "primary": primary.name if primary else None,
            "active_providers": [p.name for p in active],
            "count": len(active),
        }

    @app.post("/memory/provider/prefetch")
    def prefetch_memory_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §4.18 lines 5260, 5292: prefetch_all(query)."""
        if not _is_memory_provider_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Memory provider is disabled", "disabled": "locus.memory_provider.enabled"},
            )
        query = str(body.get("query", ""))
        session_id = body.get("session_id")
        mgr = _get_memory_manager()
        context = mgr.prefetch_all(query=query, session_id=session_id)
        return {"status": "ok", "query": query, "context": context}

    @app.post("/memory/provider/sync-turn")
    def sync_turn_memory_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §4.18 lines 5267, 5298: sync_turn_all(user, assistant)."""
        if not _is_memory_provider_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Memory provider is disabled", "disabled": "locus.memory_provider.enabled"},
            )
        user_content = str(body.get("user_content", ""))
        assistant_content = str(body.get("assistant_content", ""))
        session_id = body.get("session_id")
        messages = body.get("messages")
        mgr = _get_memory_manager()
        mgr.sync_turn_all(
            user_content=user_content,
            assistant_content=assistant_content,
            session_id=session_id,
            messages=messages,
        )
        return {"status": "ok", "synced": True}

    @app.get("/memory/provider/tools")
    def get_memory_provider_tools_route() -> Dict[str, Any]:
        """SPEC §4.18 line 5270: get_tool_schemas() -> [tool_schema]."""
        if not _is_memory_provider_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Memory provider is disabled", "disabled": "locus.memory_provider.enabled"},
            )
        mgr = _get_memory_manager()
        tools = mgr.get_all_tool_schemas()
        return {"status": "ok", "tools": tools}

    @app.post("/memory/provider/tool-call")
    def handle_memory_provider_tool_call_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §4.18 line 5271: handle_tool_call(tool_name, args) -> json_string."""
        if not _is_memory_provider_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Memory provider is disabled", "disabled": "locus.memory_provider.enabled"},
            )
        tool_name = str(body.get("tool_name", ""))
        args = body.get("args") or {}
        mgr = _get_memory_manager()
        res_str = mgr.handle_tool_call(tool_name=tool_name, args=args)
        return {"status": "ok", "result": res_str}

    # Session Management & Telegram Bridge routes (SPEC §5.1-5.8: Session Management & Telegram Bridge / F-0027 / US-58)
    from sidecar.sessions.session_manager import SessionManager, TelegramSessionBridge, SessionEntry
    from sidecar.session_export import export_session
    from sidecar.providers.session_management import BaseSessionManagementProvider, DefaultSessionManagementProvider

    active_registry.register("session_management", "default_session_management", DefaultSessionManagementProvider)
    active_registry.register("sessions", "default_sessions", DefaultSessionManagementProvider)

    _session_provider_instance: Optional[BaseSessionManagementProvider] = None

    def _is_session_management_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("session_management"):
            return False
        val1 = config.get("locus.session_management.enabled")
        if val1 is not None and not config.is_enabled("locus.session_management.enabled"):
            return False
        val2 = config.get("locus.sessions.enabled")
        if val2 is not None and not config.is_enabled("locus.sessions.enabled"):
            return False
        return True

    def _get_session_provider() -> BaseSessionManagementProvider:
        nonlocal _session_provider_instance
        if _session_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "session_management", default_name="default_session_management"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseSessionManagementProvider):
                        _session_provider_instance = res
                    else:
                        _session_provider_instance = DefaultSessionManagementProvider()
                except Exception:
                    _session_provider_instance = DefaultSessionManagementProvider()
            else:
                _session_provider_instance = DefaultSessionManagementProvider()
        return _session_provider_instance

    @app.get("/sessions/config")
    def get_sessions_config_route() -> Dict[str, Any]:
        """SPEC §5.1-5.8: Get Session Management configuration & enabled state."""
        if not _is_session_management_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Session Management is disabled", "disabled": "locus.session_management.enabled"},
            )
        return {
            "status": "ok",
            "enabled": True,
            "provider": "default_session_management",
            "sessions_dir": str(_get_session_provider().session_manager.sessions_dir if hasattr(_get_session_provider(), "session_manager") else ""),
        }

    @app.post("/sessions/create")
    def create_session_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """SPEC §5.1-5.8 line 5747: create_session()."""
        if not _is_session_management_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Session Management is disabled", "disabled": "locus.session_management.enabled"},
            )
        data = body or {}
        session_id = data.get("session_id")
        parent_id = data.get("parent_id")
        fork_point = data.get("fork_point")
        provider = _get_session_provider()
        session = provider.create_session(session_id=session_id, parent_id=parent_id, fork_point=fork_point)
        return {
            "status": "ok",
            "session_id": session.session_id,
            "parent_session_id": session.parent_session_id,
            "fork_point": session.fork_point,
            "entries_count": len(session.entries),
            "storage_path": str(session.storage_path),
        }

    @app.get("/sessions/{session_id}")
    def get_session_route(session_id: str) -> Dict[str, Any]:
        """SPEC §5.1-5.8 line 5762: load_session(session_id)."""
        if not _is_session_management_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Session Management is disabled", "disabled": "locus.session_management.enabled"},
            )
        provider = _get_session_provider()
        try:
            session = provider.load_session(session_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {
            "status": "ok",
            "session_id": session.session_id,
            "parent_session_id": session.parent_session_id,
            "fork_point": session.fork_point,
            "entries_count": len(session.entries),
            "entries": [e.to_dict() for e in session.entries],
        }

    @app.post("/sessions/{session_id}/fork")
    def fork_session_route(session_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §5.1-5.8 lines 5746-5758: fork_session(parent_session_id, fork_point)."""
        if not _is_session_management_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Session Management is disabled", "disabled": "locus.session_management.enabled"},
            )
        fork_point = str(body.get("fork_point", ""))
        summary = body.get("summary")
        provider = _get_session_provider()
        try:
            new_session = provider.fork_session(
                parent_session_id=session_id,
                fork_point=fork_point,
                summary=summary,
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Parent session {session_id} not found")
        return {
            "status": "ok",
            "session_id": new_session.session_id,
            "parent_session_id": new_session.parent_session_id,
            "fork_point": new_session.fork_point,
            "entries_count": len(new_session.entries),
            "storage_path": str(new_session.storage_path),
        }

    @app.post("/sessions/{session_id}/resume")
    def resume_session_route(session_id: str) -> Dict[str, Any]:
        """SPEC §5.1-5.8 lines 5761-5769: resume_session(session_id)."""
        if not _is_session_management_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Session Management is disabled", "disabled": "locus.session_management.enabled"},
            )
        provider = _get_session_provider()
        try:
            result = provider.resume_session(session_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {"status": "ok", **result}

    @app.post("/sessions/{session_id}/export")
    def export_session_route(session_id: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """SPEC §5.1-5.8: Export session to markdown, json, or jsonl."""
        if not _is_session_management_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Session Management is disabled", "disabled": "locus.session_management.enabled"},
            )
        data = body or {}
        fmt = str(data.get("format", "markdown"))
        provider = _get_session_provider()
        try:
            return provider.export_session(session_id, format=fmt)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

    @app.post("/sessions/telegram/bridge")
    def telegram_bridge_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §5.1-5.8 lines 5771-5792: bridge_telegram_to_session(telegram_chat_id, user_message)."""
        if not _is_session_management_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Session Management is disabled", "disabled": "locus.session_management.enabled"},
            )
        chat_id = body.get("telegram_chat_id")
        user_message = body.get("user_message", "")
        if chat_id is None:
            raise HTTPException(status_code=400, detail="Missing required field: telegram_chat_id")
        provider = _get_session_provider()
        res = provider.bridge_telegram(telegram_chat_id=chat_id, user_message=str(user_message))
        return res

    # Context References routes (SPEC §6.2: Dynamic Context References (@file, @symbol, @git, @diff) / F-0028 / US-59)
    from sidecar.context.references import ContextReferenceResolver, ResolvedReference
    from sidecar.providers.context_references import BaseContextReferenceProvider, DefaultContextReferenceProvider

    active_registry.register("context_references", "default_context_references", DefaultContextReferenceProvider)

    _context_ref_provider_instance: Optional[BaseContextReferenceProvider] = None

    def _is_context_references_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("context_references"):
            return False
        val1 = config.get("locus.context_references.enabled")
        if val1 is not None and not config.is_enabled("locus.context_references.enabled"):
            return False
        val2 = config.get("locus.context.references.enabled")
        if val2 is not None and not config.is_enabled("locus.context.references.enabled"):
            return False
        return True

    def _get_context_references_provider() -> BaseContextReferenceProvider:
        nonlocal _context_ref_provider_instance
        if _context_ref_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "context_references", default_name="default_context_references"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseContextReferenceProvider):
                        _context_ref_provider_instance = res
                    else:
                        _context_ref_provider_instance = DefaultContextReferenceProvider()
                except Exception:
                    _context_ref_provider_instance = DefaultContextReferenceProvider()
            else:
                _context_ref_provider_instance = DefaultContextReferenceProvider()
        return _context_ref_provider_instance

    @app.get("/context/references/config")
    def get_context_references_config_route() -> Dict[str, Any]:
        """SPEC §6.2 line 2115: Get context references configuration & enabled state."""
        if not _is_context_references_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Context References is disabled", "disabled": "locus.context_references.enabled"},
            )
        return {
            "status": "ok",
            "enabled": True,
            "provider": "default_context_references",
        }

    @app.post("/context/references/resolve")
    def resolve_context_references_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §6.2 lines 2062-2101: Extract and resolve references from prompt."""
        if not _is_context_references_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Context References is disabled", "disabled": "locus.context_references.enabled"},
            )
        prompt = str(body.get("prompt", ""))
        max_budget = int(body.get("max_budget", 1500))
        provider = _get_context_references_provider()
        clean_prompt, refs = provider.resolve_references(prompt, max_budget=max_budget)
        xml = provider.format_xml(refs)
        return {
            "status": "ok",
            "clean_prompt": clean_prompt,
            "references": [r.to_dict() for r in refs],
            "xml_enclosure": xml,
        }

    @app.post("/context/references/format-xml")
    def format_context_references_xml_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §6.2 lines 2104-2110: Format references into <context_ref> XML."""
        if not _is_context_references_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Context References is disabled", "disabled": "locus.context_references.enabled"},
            )
        raw_refs = body.get("references") or []
        refs = [ResolvedReference.from_dict(r) for r in raw_refs]
        provider = _get_context_references_provider()
        xml = provider.format_xml(refs)
        return {"status": "ok", "xml": xml}

    # Coding Context Engine routes (SPEC §6.3: Coding Context Engine (Repo Map, AST Index, Active Diff) / F-0029 / US-60)
    from sidecar.context.coding_context import CodingContextEngine, WorkspaceCodingState
    from sidecar.providers.coding_context import BaseCodingContextProvider, DefaultCodingContextProvider

    active_registry.register("coding_context", "default_coding_context", DefaultCodingContextProvider)

    _coding_context_provider_instance: Optional[BaseCodingContextProvider] = None

    def _is_coding_context_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("coding_context"):
            return False
        val1 = config.get("locus.coding_context.enabled")
        if val1 is not None and not config.is_enabled("locus.coding_context.enabled"):
            return False
        val2 = config.get("locus.context.coding_map.enabled")
        if val2 is not None and not config.is_enabled("locus.context.coding_map.enabled"):
            return False
        return True

    def _get_coding_context_provider() -> BaseCodingContextProvider:
        nonlocal _coding_context_provider_instance
        if _coding_context_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "coding_context", default_name="default_coding_context"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseCodingContextProvider):
                        _coding_context_provider_instance = res
                    else:
                        _coding_context_provider_instance = DefaultCodingContextProvider()
                except Exception:
                    _coding_context_provider_instance = DefaultCodingContextProvider()
            else:
                _coding_context_provider_instance = DefaultCodingContextProvider()
        return _coding_context_provider_instance

    @app.get("/context/coding/config")
    def get_coding_context_config_route() -> Dict[str, Any]:
        """SPEC §6.3 line 2187: Get coding context configuration & enabled state."""
        if not _is_coding_context_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Coding Context is disabled", "disabled": "locus.coding_context.enabled"},
            )
        return {
            "status": "ok",
            "enabled": True,
            "provider": "default_coding_context",
        }

    @app.post("/context/coding/state")
    def get_coding_context_state_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """SPEC §6.3 lines 2146-2172: Generate workspace coding state."""
        if not _is_coding_context_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Coding Context is disabled", "disabled": "locus.coding_context.enabled"},
            )
        data = body or {}
        token_budget = int(data.get("token_budget", 500))
        provider = _get_coding_context_provider()
        state = provider.get_coding_context(token_budget=token_budget)
        return {
            "status": "ok",
            "state": state.to_dict(),
        }

    @app.post("/context/coding/format")
    def format_coding_context_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §6.3 lines 2174-2182: Format workspace coding state into text layer."""
        if not _is_coding_context_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "Coding Context is disabled", "disabled": "locus.coding_context.enabled"},
            )
        state_data = body.get("state") or {}
        state = WorkspaceCodingState.from_dict(state_data)
        provider = _get_coding_context_provider()
        formatted = provider.format_layer(state)
        return {"status": "ok", "formatted_layer": formatted}

    # TUI / Dashboard routes (SPEC §7.1-7.9: Terminal Interface & Native @earendil-works/pi-tui Augmentation / F-0030 / US-61)
    from sidecar.display.dashboard import DashboardState, LocusDashboardRenderer, TUIDashboardEngine
    from sidecar.providers.tui_dashboard import BaseTUIDashboardProvider, DefaultTUIDashboardProvider

    active_registry.register("tui_dashboard", "default_tui_dashboard", DefaultTUIDashboardProvider)

    _tui_dashboard_provider_instance: Optional[BaseTUIDashboardProvider] = None

    def _is_tui_dashboard_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("tui_dashboard"):
            return False
        val1 = config.get("locus.tui_dashboard.enabled")
        if val1 is not None and not config.is_enabled("locus.tui_dashboard.enabled"):
            return False
        return True

    def _get_tui_dashboard_provider() -> BaseTUIDashboardProvider:
        nonlocal _tui_dashboard_provider_instance
        if _tui_dashboard_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "tui_dashboard", default_name="default_tui_dashboard"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseTUIDashboardProvider):
                        _tui_dashboard_provider_instance = res
                    else:
                        _tui_dashboard_provider_instance = DefaultTUIDashboardProvider()
                except Exception:
                    _tui_dashboard_provider_instance = DefaultTUIDashboardProvider()
            else:
                _tui_dashboard_provider_instance = DefaultTUIDashboardProvider()
        return _tui_dashboard_provider_instance

    @app.get("/display/dashboard/config")
    def get_dashboard_config_route() -> Dict[str, Any]:
        """SPEC §7.1-7.9: Get TUI dashboard configuration & enabled state."""
        if not _is_tui_dashboard_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "TUI Dashboard is disabled", "disabled": "locus.tui_dashboard.enabled"},
            )
        return {
            "status": "ok",
            "enabled": True,
            "provider": "default_tui_dashboard",
        }

    @app.get("/display/dashboard/state")
    def get_dashboard_state_get_route() -> Dict[str, Any]:
        """SPEC §7.1-7.9 lines 5840-5858: Get current dashboard metrics state."""
        if not _is_tui_dashboard_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "TUI Dashboard is disabled", "disabled": "locus.tui_dashboard.enabled"},
            )
        provider = _get_tui_dashboard_provider()
        state = provider.get_dashboard_state()
        footer = provider.format_footer(width=80)
        return {
            "status": "ok",
            "state": state.to_dict(),
            "footer_preview": footer,
        }

    @app.post("/display/dashboard/state")
    def get_dashboard_state_post_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """SPEC §7.1-7.9 lines 5840-5858: Query or update dashboard metrics state."""
        if not _is_tui_dashboard_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "TUI Dashboard is disabled", "disabled": "locus.tui_dashboard.enabled"},
            )
        provider = _get_tui_dashboard_provider()
        if body and "state" in body:
            new_state = DashboardState.from_dict(body["state"])
            if hasattr(provider, "engine"):
                provider.engine.update_state(new_state)
        state = provider.get_dashboard_state()
        return {
            "status": "ok",
            "state": state.to_dict(),
        }

    @app.post("/display/dashboard/format")
    def format_dashboard_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §7.1-7.9 lines 5849-5858: Format 3-column footer and dashboard panel."""
        if not _is_tui_dashboard_enabled():
            return JSONResponse(
                status_code=503,
                content={"detail": "TUI Dashboard is disabled", "disabled": "locus.tui_dashboard.enabled"},
            )
        state_data = body.get("state") or {}
        state = DashboardState.from_dict(state_data) if state_data else None
        width = int(body.get("width", 80))
        provider = _get_tui_dashboard_provider()
        if state and hasattr(provider, "engine"):
            provider.engine.update_state(state)
        footer = provider.format_footer(width=width)
        dashboard_panel = provider.format_dashboard(width=width)
        return {
            "status": "ok",
            "footer": footer,
            "dashboard": dashboard_panel,
        }

    # CLI / Doctor Diagnostics routes (SPEC §8.1-8.10: CLI Commands, Multi-Surface Management, Telegram Settings & Headless VM Topology / F-0031 / US-62)
    from sidecar.providers.cli_doctor_diagnostics import (
        BaseCLIDoctorDiagnosticsProvider,
        DefaultCLIDoctorDiagnosticsProvider,
    )

    active_registry.register(
        "cli_doctor_diagnostics", "default_cli_doctor_diagnostics", DefaultCLIDoctorDiagnosticsProvider
    )

    _cli_doctor_provider_instance: Optional[BaseCLIDoctorDiagnosticsProvider] = None

    def _is_cli_doctor_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("cli_doctor_diagnostics"):
            return False
        val = config.get("locus.cli_doctor_diagnostics.enabled")
        if val is not None and not config.is_enabled("locus.cli_doctor_diagnostics.enabled"):
            return False
        return True

    def _get_cli_doctor_provider() -> BaseCLIDoctorDiagnosticsProvider:
        nonlocal _cli_doctor_provider_instance
        if _cli_doctor_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "cli_doctor_diagnostics", default_name="default_cli_doctor_diagnostics"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseCLIDoctorDiagnosticsProvider):
                        _cli_doctor_provider_instance = res
                except Exception:
                    pass
        if _cli_doctor_provider_instance is None:
            _cli_doctor_provider_instance = DefaultCLIDoctorDiagnosticsProvider()
        return _cli_doctor_provider_instance

    @app.get("/system/doctor")
    def system_doctor_route(full: bool = False, strict: bool = False) -> Dict[str, Any]:
        """SPEC §8.1-8.10 line 5606: Query diagnostic health probes across subsystems."""
        if not _is_cli_doctor_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "CLI Doctor Diagnostics is disabled",
                    "disabled": "locus.cli_doctor_diagnostics.enabled",
                },
            )
        provider = _get_cli_doctor_provider()
        return provider.run_diagnostics(full=full, strict=strict)

    @app.post("/system/reload")
    def system_reload_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §8.1-8.10 line 5598: Hot-reload subsystem provider."""
        if not _is_cli_doctor_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "CLI Doctor Diagnostics is disabled",
                    "disabled": "locus.cli_doctor_diagnostics.enabled",
                },
            )
        subsystem = str(body.get("subsystem", "all"))
        provider = _get_cli_doctor_provider()
        return provider.reload_subsystem(subsystem)

    @app.get("/system/config")
    def system_config_get_route(key: Optional[str] = None) -> Dict[str, Any]:
        """SPEC §8.1-8.10 line 5485: Export system configuration."""
        if not _is_cli_doctor_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "CLI Doctor Diagnostics is disabled",
                    "disabled": "locus.cli_doctor_diagnostics.enabled",
                },
            )
        provider = _get_cli_doctor_provider()
        cfg = provider.get_config(key)
        return {"status": "ok", "key": key, "config": cfg}

    @app.post("/system/config")
    def system_config_post_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §8.1-8.10 line 5655: Persist configuration update and trigger reload."""
        if not _is_cli_doctor_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "CLI Doctor Diagnostics is disabled",
                    "disabled": "locus.cli_doctor_diagnostics.enabled",
                },
            )
        key = str(body.get("key", ""))
        val = body.get("val")
        if not key:
            return JSONResponse(status_code=400, content={"detail": "Missing 'key' in request body"})
        provider = _get_cli_doctor_provider()
        return provider.set_config(key, val)

    # Skill System & Multi-Source Marketplace routes (SPEC §9.2: Skill System & Multi-Source Marketplace / F-0119 / US-63)
    from sidecar.providers.skill_marketplace import (
        BaseSkillMarketplaceProvider,
        DefaultSkillMarketplaceProvider,
    )

    active_registry.register(
        "skill_marketplace", "default_skill_marketplace", DefaultSkillMarketplaceProvider
    )

    _skill_marketplace_provider_instance: Optional[BaseSkillMarketplaceProvider] = None

    def _is_skill_marketplace_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("skill_marketplace"):
            return False
        val1 = config.get("locus.skill_system_multi_source_marketplace.enabled")
        if val1 is not None and not config.is_enabled("locus.skill_system_multi_source_marketplace.enabled"):
            return False
        val2 = config.get("locus.skills.marketplace.enabled")
        if val2 is not None and not config.is_enabled("locus.skills.marketplace.enabled"):
            return False
        return True

    def _get_skill_marketplace_provider() -> BaseSkillMarketplaceProvider:
        nonlocal _skill_marketplace_provider_instance
        if _skill_marketplace_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "skill_marketplace", default_name="default_skill_marketplace"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseSkillMarketplaceProvider):
                        _skill_marketplace_provider_instance = res
                except Exception:
                    pass
        if _skill_marketplace_provider_instance is None:
            _skill_marketplace_provider_instance = DefaultSkillMarketplaceProvider()
        return _skill_marketplace_provider_instance

    @app.get("/skills/marketplace/sources")
    def get_marketplace_sources_route() -> Dict[str, Any]:
        """SPEC §9.2 lines 6025-6031: List registered marketplace sources and URLs."""
        if not _is_skill_marketplace_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Skill Marketplace is disabled",
                    "disabled": "locus.skill_system_multi_source_marketplace.enabled",
                },
            )
        provider = _get_skill_marketplace_provider()
        return {"status": "ok", "sources": provider.get_sources()}

    @app.get("/skills/marketplace/manifest")
    def get_skill_manifest_route(source: str, skill_name: str) -> Dict[str, Any]:
        """SPEC §9.2 lines 6033-6035: Fetch remote skill manifest."""
        if not _is_skill_marketplace_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Skill Marketplace is disabled",
                    "disabled": "locus.skill_system_multi_source_marketplace.enabled",
                },
            )
        provider = _get_skill_marketplace_provider()
        manifest = provider.get_manifest(source, skill_name)
        prereqs = provider.validate_prerequisites(manifest)
        return {"status": "ok", "manifest": manifest, "prerequisites": prereqs}

    @app.post("/skills/marketplace/install")
    def install_skill_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §9.2 lines 6024-6048: Install skill from remote marketplace."""
        if not _is_skill_marketplace_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Skill Marketplace is disabled",
                    "disabled": "locus.skill_system_multi_source_marketplace.enabled",
                },
            )
        source = str(body.get("source", "pi-gallery"))
        skill_name = str(body.get("skill_name", ""))
        if not skill_name:
            return JSONResponse(status_code=400, content={"detail": "Missing 'skill_name' in request body"})
        provider = _get_skill_marketplace_provider()
        return provider.install_skill(source, skill_name)

    @app.get("/skills/marketplace/installed")
    def list_installed_skills_route() -> Dict[str, Any]:
        """SPEC §9.2 line 6046: List installed skill bundles."""
        if not _is_skill_marketplace_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Skill Marketplace is disabled",
                    "disabled": "locus.skill_system_multi_source_marketplace.enabled",
                },
            )
        provider = _get_skill_marketplace_provider()
        return {"status": "ok", "installed": provider.list_installed()}

    # ACP Protocol routes (SPEC §9.4: Agent Communication Protocol (ACP Client & Transport) / F-0033 / US-64)
    from sidecar.providers.acp_protocol import (
        BaseACPClientProvider,
        DefaultACPClientProvider,
    )

    active_registry.register(
        "acp_protocol", "default_acp_protocol", DefaultACPClientProvider
    )

    _acp_provider_instance: Optional[BaseACPClientProvider] = None

    def _is_acp_protocol_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("acp_protocol"):
            return False
        val1 = config.get("locus.acp_protocol.enabled")
        if val1 is not None and not config.is_enabled("locus.acp_protocol.enabled"):
            return False
        val2 = config.get("locus.protocols.acp.enabled")
        if val2 is not None and not config.is_enabled("locus.protocols.acp.enabled"):
            return False
        return True

    def _get_acp_provider() -> BaseACPClientProvider:
        nonlocal _acp_provider_instance
        if _acp_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "acp_protocol", default_name="default_acp_protocol"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseACPClientProvider):
                        _acp_provider_instance = res
                except Exception:
                    pass
        if _acp_provider_instance is None:
            _acp_provider_instance = DefaultACPClientProvider()
        return _acp_provider_instance

    @app.post("/protocols/acp/initialize")
    def acp_initialize_route(body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """SPEC §9.4 lines 6071-6088: Capability negotiation handshake."""
        if not _is_acp_protocol_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "ACP Protocol is disabled",
                    "disabled": "locus.acp_protocol.enabled",
                },
            )
        client_info = body.get("client_info") if body else None
        provider = _get_acp_provider()
        return provider.initialize(client_info=client_info)

    @app.post("/protocols/acp/execute")
    def acp_execute_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §9.4 lines 6090-6111: Dispatch task to target agent."""
        if not _is_acp_protocol_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "ACP Protocol is disabled",
                    "disabled": "locus.acp_protocol.enabled",
                },
            )
        target = str(body.get("target_agent_id", "default-agent"))
        prompt = str(body.get("prompt", ""))
        tools = list(body.get("tools") or [])
        provider = _get_acp_provider()
        return provider.execute(target_agent_id=target, prompt=prompt, tools=tools)

    @app.post("/protocols/acp/cancel")
    def acp_cancel_route(body: Dict[str, Any]) -> Dict[str, Any]:
        """SPEC §9.4 lines 6113-6119: Send request cancellation notification."""
        if not _is_acp_protocol_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "ACP Protocol is disabled",
                    "disabled": "locus.acp_protocol.enabled",
                },
            )
        request_id = int(body.get("request_id", 0))
        provider = _get_acp_provider()
        return provider.cancel(request_id)

    # Plugin LLM Sandboxing & Auxiliary Bridge routes (SPEC §9.9: Plugin LLM Sandboxing & Auxiliary Bridge / F-0034 / US-65)
    from sidecar.plugins.llm_bridge import (
        AuxiliaryTimeoutError,
        PluginLLMBridge,
        QuotaExceededError,
    )
    from sidecar.providers.plugin_llm import (
        BasePluginLLMProvider,
        DefaultPluginLLMProvider,
    )

    active_registry.register("plugin_llm", "default_plugin_llm", DefaultPluginLLMProvider)

    _plugin_llm_provider_instance: Optional[BasePluginLLMProvider] = None

    def _is_plugin_llm_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("plugin_llm"):
            return False
        val1 = config.get("locus.plugin_llm.enabled")
        if val1 is not None and not config.is_enabled("locus.plugin_llm.enabled"):
            return False
        val2 = config.get("locus.plugins.auxiliary_llm.enabled")
        if val2 is not None and not config.is_enabled("locus.plugins.auxiliary_llm.enabled"):
            return False
        return True

    def _get_plugin_llm_provider() -> BasePluginLLMProvider:
        nonlocal _plugin_llm_provider_instance
        if _plugin_llm_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "plugin_llm", default_name="default_plugin_llm"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BasePluginLLMProvider):
                        _plugin_llm_provider_instance = res
                except Exception:
                    pass
        if _plugin_llm_provider_instance is None:
            _plugin_llm_provider_instance = DefaultPluginLLMProvider()
        return _plugin_llm_provider_instance

    @app.post("/plugins/llm/generate")
    def plugin_llm_generate_route(body: Dict[str, Any]) -> Any:
        """SPEC §9.9 lines 6165-6187: Execute sandboxed plugin LLM call."""
        if not _is_plugin_llm_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Plugin LLM Sandboxing is disabled",
                    "disabled": "locus.plugin_llm.enabled",
                },
            )
        plugin_id = str(body.get("plugin_id", "default-plugin"))
        messages = list(body.get("messages") or [])
        max_tokens = int(body.get("max_tokens", 500))
        temperature = float(body.get("temperature", 0.2))
        timeout = float(body.get("timeout", 15.0))

        provider = _get_plugin_llm_provider()
        res = provider.generate(
            plugin_id=plugin_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )
        if res.get("status") == "error":
            if res.get("error") == "quota_exceeded":
                return JSONResponse(status_code=429, content=res)
            return JSONResponse(status_code=400, content=res)
        return res

    @app.get("/plugins/llm/quota")
    def plugin_llm_quota_route(plugin_id: str = "default-plugin") -> Any:
        """SPEC §9.9 lines 6162-6164: Get plugin daily quota and usage."""
        if not _is_plugin_llm_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Plugin LLM Sandboxing is disabled",
                    "disabled": "locus.plugin_llm.enabled",
                },
            )
        provider = _get_plugin_llm_provider()
        return provider.get_quota(plugin_id=plugin_id)

    @app.post("/plugins/llm/reset")
    def plugin_llm_reset_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §9.9 line 6188: Reset plugin daily token counter."""
        if not _is_plugin_llm_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Plugin LLM Sandboxing is disabled",
                    "disabled": "locus.plugin_llm.enabled",
                },
            )
        plugin_id = str((body or {}).get("plugin_id", "default-plugin"))
        provider = _get_plugin_llm_provider()
        return provider.reset_quota(plugin_id=plugin_id)

    @app.get("/plugins/llm/usage")
    def plugin_llm_usage_route() -> Any:
        """SPEC §9.9 lines 6189-6190: Get aggregated usage across all plugins."""
        if not _is_plugin_llm_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Plugin LLM Sandboxing is disabled",
                    "disabled": "locus.plugin_llm.enabled",
                },
            )
        provider = _get_plugin_llm_provider()
        return provider.get_all_usage()

    # Self-Evolving Architect Bot routes (SPEC §10.8: Self-Evolving Architect Bot / F-0120 / US-66)
    from sidecar.architect.engine import (
        ArchitectCandidate,
        ArchitectEngine,
        RiskClass,
        SignalBundle,
        TargetClass,
    )
    from sidecar.providers.architect import (
        BaseArchitectProvider,
        DefaultArchitectProvider,
    )

    active_registry.register("architect", "default_architect", DefaultArchitectProvider)

    _architect_provider_instance: Optional[BaseArchitectProvider] = None

    def _is_architect_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("architect"):
            return False
        val = config.get("locus.architect.enabled")
        if val is not None and not config.is_enabled("locus.architect.enabled"):
            return False
        return True

    def _get_architect_provider() -> BaseArchitectProvider:
        nonlocal _architect_provider_instance
        if _architect_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "architect", default_name="default_architect"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseArchitectProvider):
                        _architect_provider_instance = res
                except Exception:
                    pass
        if _architect_provider_instance is None:
            _architect_provider_instance = DefaultArchitectProvider()
        return _architect_provider_instance

    @app.post("/architect/scan")
    def architect_scan_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §10.8 line 6319: Scan signals and propose improvement candidates."""
        if not _is_architect_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Architect Bot is disabled",
                    "disabled": "locus.architect.enabled",
                },
            )
        b = body or {}
        provider = _get_architect_provider()
        return provider.scan(
            reward_model=b.get("reward_model"),
            hebbian_weights=b.get("hebbian_weights"),
            experiences=b.get("experiences"),
            life_os_metrics=b.get("life_os_metrics"),
        )

    @app.get("/architect/candidates")
    def architect_candidates_route() -> Any:
        """SPEC §10.8 lines 6319-6334: Get list of active improvement candidates."""
        if not _is_architect_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Architect Bot is disabled",
                    "disabled": "locus.architect.enabled",
                },
            )
        provider = _get_architect_provider()
        return {
            "status": "ok",
            "candidates": provider.get_candidates(),
        }

    @app.post("/architect/apply")
    def architect_apply_route(body: Dict[str, Any]) -> Any:
        """SPEC §10.8 lines 6330-6337: Apply or stage candidate patch based on risk gate."""
        if not _is_architect_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Architect Bot is disabled",
                    "disabled": "locus.architect.enabled",
                },
            )
        candidate_id = str(body.get("candidate_id", ""))
        provider = _get_architect_provider()
        try:
            return provider.apply_candidate(candidate_id=candidate_id)
        except KeyError as e:
            return JSONResponse(status_code=404, content={"status": "error", "detail": str(e)})
        except Exception as e:
            return JSONResponse(status_code=400, content={"status": "error", "detail": str(e)})

    @app.get("/architect/history")
    def architect_history_route() -> Any:
        """SPEC §10.8 lines 6335-6337: Get history of patch applications and outcomes."""
        if not _is_architect_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Architect Bot is disabled",
                    "disabled": "locus.architect.enabled",
                },
            )
        provider = _get_architect_provider()
        return {
            "status": "ok",
            "history": provider.get_history(),
        }

    # Agent Experience Tracking (Procedural Memory) routes (SPEC §10.9: Agent Experience Tracking / F-0121 / US-67)
    from sidecar.experience.procedural import (
        AgentExperience,
        AgentExperienceCaptureHook,
        ExperienceStore,
        prepend_experience_block,
        redact_text,
        render_experience_hits,
        stable_experience_id,
    )
    from sidecar.providers.agent_experience import (
        BaseAgentExperienceProvider,
        DefaultAgentExperienceProvider,
    )

    active_registry.register("agent_experience", "default_agent_experience", DefaultAgentExperienceProvider)

    _agent_experience_provider_instance: Optional[BaseAgentExperienceProvider] = None

    def _is_agent_experience_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("agent_experience"):
            return False
        v1 = config.get("locus.agent_experience_tracking_procedural_memory.enabled")
        if v1 is not None and not config.is_enabled("locus.agent_experience_tracking_procedural_memory.enabled"):
            return False
        v2 = config.get("locus.experience.enabled")
        if v2 is not None and not config.is_enabled("locus.experience.enabled"):
            return False
        return True

    def _get_agent_experience_provider() -> BaseAgentExperienceProvider:
        nonlocal _agent_experience_provider_instance
        if _agent_experience_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "agent_experience", default_name="default_agent_experience"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseAgentExperienceProvider):
                        _agent_experience_provider_instance = res
                except Exception:
                    pass
        if _agent_experience_provider_instance is None:
            _agent_experience_provider_instance = DefaultAgentExperienceProvider()
        return _agent_experience_provider_instance

    @app.post("/experience/record")
    def experience_record_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §10.9 lines 6386-6415: Capture candidates from turn tool loop."""
        if not _is_agent_experience_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Agent Experience Tracking is disabled",
                    "disabled": "locus.experience.enabled",
                },
            )
        b = body or {}
        provider = _get_agent_experience_provider()
        return provider.record_turn(turn_context=b)

    @app.post("/experience/query")
    def experience_query_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §10.9 lines 6417-6425: Query scored procedural experiences."""
        if not _is_agent_experience_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Agent Experience Tracking is disabled",
                    "disabled": "locus.experience.enabled",
                },
            )
        b = body or {}
        fp = str(b.get("task_fingerprint") or "")
        limit = int(b.get("limit") or 5)
        provider = _get_agent_experience_provider()
        return {
            "status": "ok",
            "experiences": provider.query_experiences(task_fingerprint=fp, limit=limit),
        }

    @app.post("/experience/render")
    def experience_render_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §10.9 lines 6417-6425: Render Relevant Operating Experience block prepended to message."""
        if not _is_agent_experience_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Agent Experience Tracking is disabled",
                    "disabled": "locus.experience.enabled",
                },
            )
        b = body or {}
        fp = str(b.get("task_fingerprint") or "")
        limit = int(b.get("limit") or 5)
        message = str(b.get("message") or "")
        provider = _get_agent_experience_provider()
        return provider.render_block(task_fingerprint=fp, limit=limit, message=message)

    @app.get("/experience/list")
    def experience_list_route(limit: int = 50) -> Any:
        """SPEC §10.9 lines 6370-6385: List stored experiences."""
        if not _is_agent_experience_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Agent Experience Tracking is disabled",
                    "disabled": "locus.experience.enabled",
                },
            )
        provider = _get_agent_experience_provider()
        return {
            "status": "ok",
            "experiences": provider.list_experiences(limit=limit),
        }

    # Prompt Injection Protection (Injection Filter) routes (SPEC §13.1: Prompt Injection Protection / F-0037 / US-68)
    from sidecar.security.injection_filter import (
        NormalizedPrompt,
        PromptEnforcementDecision,
        enforce_prompt_input,
        normalize_prompt,
        scan_tool_definition,
    )
    from sidecar.providers.injection_filter import (
        BaseInjectionFilterProvider,
        DefaultInjectionFilterProvider,
    )

    active_registry.register("injection_filter", "default_injection_filter", DefaultInjectionFilterProvider)

    _injection_filter_provider_instance: Optional[BaseInjectionFilterProvider] = None

    def _is_injection_filter_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("injection_filter"):
            return False
        v1 = config.get("locus.injection_filter.enabled")
        if v1 is not None and not config.is_enabled("locus.injection_filter.enabled"):
            return False
        v2 = config.get("locus.security.prompt_injection.enabled")
        if v2 is not None and not config.is_enabled("locus.security.prompt_injection.enabled"):
            return False
        return True

    def _get_injection_filter_provider() -> BaseInjectionFilterProvider:
        nonlocal _injection_filter_provider_instance
        if _injection_filter_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "injection_filter", default_name="default_injection_filter"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseInjectionFilterProvider):
                        _injection_filter_provider_instance = res
                except Exception:
                    pass
        if _injection_filter_provider_instance is None:
            _injection_filter_provider_instance = DefaultInjectionFilterProvider()
        return _injection_filter_provider_instance

    @app.post("/security/injection/enforce")
    def injection_enforce_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.1: Screen prompt input and return enforcement decision."""
        if not _is_injection_filter_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Injection Filter is disabled",
                    "disabled": "locus.injection_filter.enabled",
                },
            )
        b = body or {}
        text = str(b.get("input_text") or "")
        ctx = b.get("context")
        provider = _get_injection_filter_provider()
        return provider.enforce(input_text=text, context=ctx)

    @app.post("/security/injection/scan_tool")
    def injection_scan_tool_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.1: Scan tool metadata definition."""
        if not _is_injection_filter_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Injection Filter is disabled",
                    "disabled": "locus.injection_filter.enabled",
                },
            )
        b = body or {}
        name = str(b.get("name") or "")
        description = str(b.get("description") or "")
        provider = _get_injection_filter_provider()
        return provider.scan_tool(name=name, description=description)

    @app.post("/security/injection/normalize")
    def injection_normalize_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.1: Normalize input prompt."""
        if not _is_injection_filter_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Injection Filter is disabled",
                    "disabled": "locus.injection_filter.enabled",
                },
            )
        b = body or {}
        text = str(b.get("input_text") or "")
        provider = _get_injection_filter_provider()
        return provider.normalize(input_text=text)

    # File Safety routes (SPEC §13.2: File Safety / F-0107 / US-69)
    from sidecar.security.file_safety import (
        CwdJail,
        FileStateRecord,
        FileStateTracker,
        PathValidationDecision,
    )
    from sidecar.providers.file_safety import (
        BaseFileSafetyProvider,
        DefaultFileSafetyProvider,
    )

    active_registry.register("file_safety", "default_file_safety", DefaultFileSafetyProvider)

    _file_safety_provider_instance: Optional[BaseFileSafetyProvider] = None

    def _is_file_safety_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("file_safety"):
            return False
        v1 = config.get("locus.file_safety.enabled")
        if v1 is not None and not config.is_enabled("locus.file_safety.enabled"):
            return False
        v2 = config.get("locus.security.file_safety.enabled")
        if v2 is not None and not config.is_enabled("locus.security.file_safety.enabled"):
            return False
        return True

    def _get_file_safety_provider() -> BaseFileSafetyProvider:
        nonlocal _file_safety_provider_instance
        if _file_safety_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "file_safety", default_name="default_file_safety"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseFileSafetyProvider):
                        _file_safety_provider_instance = res
                except Exception:
                    pass
        if _file_safety_provider_instance is None:
            _file_safety_provider_instance = DefaultFileSafetyProvider()
        return _file_safety_provider_instance

    @app.post("/security/file/validate")
    def file_validate_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.2: Validate path against cwd_jail and blocked patterns."""
        if not _is_file_safety_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "File Safety is disabled",
                    "disabled": "locus.file_safety.enabled",
                },
            )
        b = body or {}
        path_str = str(b.get("path") or "")
        op = str(b.get("operation") or "read")
        cwd = b.get("cwd")
        provider = _get_file_safety_provider()
        return provider.validate_path(path=path_str, operation=op, cwd=cwd)

    @app.post("/security/file/record")
    def file_record_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.2: Track file modification."""
        if not _is_file_safety_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "File Safety is disabled",
                    "disabled": "locus.file_safety.enabled",
                },
            )
        b = body or {}
        path_str = str(b.get("path") or "")
        op = str(b.get("operation") or "modify")
        content = b.get("content")
        provider = _get_file_safety_provider()
        return provider.record_modification(path=path_str, operation=op, content=content)

    @app.get("/security/file/history")
    def file_history_route(limit: int = 50) -> Any:
        """SPEC §13.2: Get file state modification history."""
        if not _is_file_safety_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "File Safety is disabled",
                    "disabled": "locus.file_safety.enabled",
                },
            )
        provider = _get_file_safety_provider()
        return {
            "status": "ok",
            "history": provider.get_history(limit=limit),
        }

    # Autonomy Tiers routes (SPEC §13.4: Autonomy Tiers / F-0108 / US-70)
    from sidecar.security.autonomy_tiers import (
        AutonomyTier,
        AutonomyTierManager,
        TierEvaluationDecision,
        ToolCategory,
    )
    from sidecar.providers.autonomy_tiers import (
        BaseAutonomyTiersProvider,
        DefaultAutonomyTiersProvider,
    )

    active_registry.register("autonomy_tiers", "default_autonomy_tiers", DefaultAutonomyTiersProvider)

    _autonomy_tiers_provider_instance: Optional[BaseAutonomyTiersProvider] = None

    def _is_autonomy_tiers_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("autonomy_tiers"):
            return False
        v1 = config.get("locus.autonomy_tiers.enabled")
        if v1 is not None and not config.is_enabled("locus.autonomy_tiers.enabled"):
            return False
        v2 = config.get("locus.security.autonomy_tiers.enabled")
        if v2 is not None and not config.is_enabled("locus.security.autonomy_tiers.enabled"):
            return False
        return True

    def _get_autonomy_tiers_provider() -> BaseAutonomyTiersProvider:
        nonlocal _autonomy_tiers_provider_instance
        if _autonomy_tiers_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "autonomy_tiers", default_name="default_autonomy_tiers"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseAutonomyTiersProvider):
                        _autonomy_tiers_provider_instance = res
                except Exception:
                    pass
        if _autonomy_tiers_provider_instance is None:
            _autonomy_tiers_provider_instance = DefaultAutonomyTiersProvider()
        return _autonomy_tiers_provider_instance

    @app.get("/security/autonomy/tier")
    def autonomy_get_tier_route() -> Any:
        """SPEC §13.4: Get current autonomy tier."""
        if not _is_autonomy_tiers_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Autonomy Tiers is disabled",
                    "disabled": "locus.autonomy_tiers.enabled",
                },
            )
        provider = _get_autonomy_tiers_provider()
        return {
            "status": "ok",
            "tier": provider.get_tier(),
        }

    @app.post("/security/autonomy/tier")
    def autonomy_set_tier_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.4: Set current autonomy tier."""
        if not _is_autonomy_tiers_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Autonomy Tiers is disabled",
                    "disabled": "locus.autonomy_tiers.enabled",
                },
            )
        b = body or {}
        tier = str(b.get("tier") or "supervised")
        provider = _get_autonomy_tiers_provider()
        return provider.set_tier(tier)

    @app.post("/security/autonomy/evaluate")
    def autonomy_evaluate_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.4: Evaluate tool call against autonomy tier permissions."""
        if not _is_autonomy_tiers_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Autonomy Tiers is disabled",
                    "disabled": "locus.autonomy_tiers.enabled",
                },
            )
        b = body or {}
        tool_name = str(b.get("tool_name") or "")
        has_approval = bool(b.get("has_approval", False))
        category = b.get("category")
        tier = b.get("tier")
        provider = _get_autonomy_tiers_provider()
        return provider.evaluate_tool(
            tool_name=tool_name,
            has_approval=has_approval,
            category=category,
            tier=tier,
        )

    @app.post("/security/autonomy/classify")
    def autonomy_classify_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.4: Classify tool category."""
        if not _is_autonomy_tiers_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Autonomy Tiers is disabled",
                    "disabled": "locus.autonomy_tiers.enabled",
                },
            )
        b = body or {}
        tool_name = str(b.get("tool_name") or "")
        explicit_category = b.get("category")
        provider = _get_autonomy_tiers_provider()
        return provider.classify_tool(tool_name=tool_name, explicit_category=explicit_category)

    @app.get("/security/autonomy/tiers")
    def autonomy_list_tiers_route() -> Any:
        """SPEC §13.4: List all available autonomy tiers and policy definitions."""
        if not _is_autonomy_tiers_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Autonomy Tiers is disabled",
                    "disabled": "locus.autonomy_tiers.enabled",
                },
            )
        provider = _get_autonomy_tiers_provider()
        return {
            "status": "ok",
            "tiers": provider.get_tiers_info(),
        }

    # Approval Gate routes (SPEC §13.5: Approval Gate / F-0109 / US-71)
    from sidecar.security.approval_store import (
        ApprovalRequest,
        ApprovalStatus,
        ApprovalStore,
    )
    from sidecar.providers.approval_gate import (
        BaseApprovalGateProvider,
        DefaultApprovalGateProvider,
    )

    active_registry.register("approval_gate", "default_approval_gate", DefaultApprovalGateProvider)

    _approval_gate_provider_instance: Optional[BaseApprovalGateProvider] = None

    def _is_approval_gate_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("approval_gate"):
            return False
        v1 = config.get("locus.approval_gate.enabled")
        if v1 is not None and not config.is_enabled("locus.approval_gate.enabled"):
            return False
        v2 = config.get("locus.security.approval_gate.enabled")
        if v2 is not None and not config.is_enabled("locus.security.approval_gate.enabled"):
            return False
        return True

    def _get_approval_gate_provider() -> BaseApprovalGateProvider:
        nonlocal _approval_gate_provider_instance
        if _approval_gate_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "approval_gate", default_name="default_approval_gate"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseApprovalGateProvider):
                        _approval_gate_provider_instance = res
                except Exception:
                    pass
        if _approval_gate_provider_instance is None:
            _approval_gate_provider_instance = DefaultApprovalGateProvider()
        return _approval_gate_provider_instance

    @app.post("/security/approval/request")
    def approval_request_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.5: Queue an approval request with 10-minute default TTL."""
        if not _is_approval_gate_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Approval Gate is disabled",
                    "disabled": "locus.approval_gate.enabled",
                },
            )
        b = body or {}
        task_id = str(b.get("task_id") or "")
        changes = b.get("changes")
        ttl = b.get("ttl")
        provider = _get_approval_gate_provider()
        return provider.queue_approval(task_id=task_id, changes=changes, ttl=ttl)

    @app.get("/security/approval/status")
    def approval_status_route(task_id: str = "") -> Any:
        """SPEC §13.5: Get approval request status."""
        if not _is_approval_gate_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Approval Gate is disabled",
                    "disabled": "locus.approval_gate.enabled",
                },
            )
        provider = _get_approval_gate_provider()
        return provider.get_status(task_id=task_id)

    @app.post("/security/approval/resolve")
    def approval_resolve_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.5: Resolve pending approval request (approve or reject)."""
        if not _is_approval_gate_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Approval Gate is disabled",
                    "disabled": "locus.approval_gate.enabled",
                },
            )
        b = body or {}
        task_id = str(b.get("task_id") or "")
        status = str(b.get("status") or "rejected")
        resolved_by = b.get("resolved_by")
        provider = _get_approval_gate_provider()
        return provider.resolve(task_id=task_id, status=status, resolved_by=resolved_by)

    @app.post("/security/approval/wait")
    def approval_wait_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.5: Wait for approval resolution."""
        if not _is_approval_gate_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Approval Gate is disabled",
                    "disabled": "locus.approval_gate.enabled",
                },
            )
        b = body or {}
        task_id = str(b.get("task_id") or "")
        timeout = b.get("timeout")
        provider = _get_approval_gate_provider()
        return provider.wait(task_id=task_id, timeout=timeout)

    @app.get("/security/approval/pending")
    def approval_pending_route() -> Any:
        """SPEC §13.5: List active pending approvals."""
        if not _is_approval_gate_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Approval Gate is disabled",
                    "disabled": "locus.approval_gate.enabled",
                },
            )
        provider = _get_approval_gate_provider()
        return {
            "status": "ok",
            "pending": provider.list_pending(),
        }

    # Shell Blocklist routes (SPEC §13.7: Shell Blocklist / F-0040 / US-72)
    from sidecar.security.shell_policy import (
        DEFAULT_BLOCKED_PATTERNS as DEFAULT_BLOCKED_SHELL_PATTERNS,
        SENSITIVE_HOME_DIRS,
        SENSITIVE_HOME_FILES,
        ShellInspectionDecision,
        ShellPolicyEngine,
    )
    from sidecar.providers.shell_blocklist import (
        BaseShellBlocklistProvider,
        DefaultShellBlocklistProvider,
    )

    active_registry.register("shell_blocklist", "default_shell_blocklist", DefaultShellBlocklistProvider)

    _shell_blocklist_provider_instance: Optional[BaseShellBlocklistProvider] = None

    def _is_shell_blocklist_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("shell_blocklist"):
            return False
        v1 = config.get("locus.shell_blocklist.enabled")
        if v1 is not None and not config.is_enabled("locus.shell_blocklist.enabled"):
            return False
        v2 = config.get("locus.security.shell_blocklist.enabled")
        if v2 is not None and not config.is_enabled("locus.security.shell_blocklist.enabled"):
            return False
        return True

    def _get_shell_blocklist_provider() -> BaseShellBlocklistProvider:
        nonlocal _shell_blocklist_provider_instance
        if _shell_blocklist_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "shell_blocklist", default_name="default_shell_blocklist"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseShellBlocklistProvider):
                        _shell_blocklist_provider_instance = res
                except Exception:
                    pass
        if _shell_blocklist_provider_instance is None:
            _shell_blocklist_provider_instance = DefaultShellBlocklistProvider()
        return _shell_blocklist_provider_instance

    @app.post("/security/shell/check")
    def shell_check_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.7: Inspect shell command against destructive and sensitive patterns."""
        if not _is_shell_blocklist_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Shell Blocklist is disabled",
                    "disabled": "locus.shell_blocklist.enabled",
                },
            )
        b = body or {}
        command = str(b.get("command") or "")
        provider = _get_shell_blocklist_provider()
        return provider.check_command(command)

    @app.post("/security/shell/check_path")
    def shell_check_path_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.7: Inspect path against sensitive home dirs and files."""
        if not _is_shell_blocklist_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Shell Blocklist is disabled",
                    "disabled": "locus.shell_blocklist.enabled",
                },
            )
        b = body or {}
        path_str = str(b.get("path") or "")
        operation = str(b.get("operation") or "read")
        outside_boundary = bool(b.get("outside_boundary", False))
        provider = _get_shell_blocklist_provider()
        if operation == "write":
            return provider.is_write_denied(path=path_str, outside_boundary=outside_boundary)
        return provider.is_read_blocked(path=path_str)

    @app.get("/security/shell/patterns")
    def shell_patterns_route() -> Any:
        """SPEC §13.7: List active blocked shell patterns."""
        if not _is_shell_blocklist_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Shell Blocklist is disabled",
                    "disabled": "locus.shell_blocklist.enabled",
                },
            )
        provider = _get_shell_blocklist_provider()
        return {
            "status": "ok",
            "patterns": provider.list_blocked_patterns(),
        }

    # Data Redaction routes (SPEC §13.8: Data Redaction / F-0041 / US-73)
    from sidecar.security.redact import (
        KEY_PATTERNS,
        SENSITIVE_BODY_KEYS,
        SENSITIVE_QUERY_PARAMS,
        DataRedactor,
        mask_token,
    )
    from sidecar.providers.data_redaction import (
        BaseDataRedactionProvider,
        DefaultDataRedactionProvider,
    )

    active_registry.register("data_redaction", "default_data_redaction", DefaultDataRedactionProvider)

    _data_redaction_provider_instance: Optional[BaseDataRedactionProvider] = None

    def _is_data_redaction_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("data_redaction"):
            return False
        v1 = config.get("locus.data_redaction.enabled")
        if v1 is not None and not config.is_enabled("locus.data_redaction.enabled"):
            return False
        v2 = config.get("locus.security.data_redaction.enabled")
        if v2 is not None and not config.is_enabled("locus.security.data_redaction.enabled"):
            return False
        v3 = config.get("locus.security.redaction.enabled")
        if v3 is not None and not config.is_enabled("locus.security.redaction.enabled"):
            return False
        return True

    def _get_data_redaction_provider() -> BaseDataRedactionProvider:
        nonlocal _data_redaction_provider_instance
        if _data_redaction_provider_instance is None:
            provider_cls = app.state.registry.get_active_provider(
                "data_redaction", default_name="default_data_redaction"
            )
            if provider_cls:
                try:
                    res = provider_cls()
                    if isinstance(res, BaseDataRedactionProvider):
                        _data_redaction_provider_instance = res
                except Exception:
                    pass
        if _data_redaction_provider_instance is None:
            _data_redaction_provider_instance = DefaultDataRedactionProvider()
        return _data_redaction_provider_instance

    @app.post("/security/redact/text")
    def redact_text_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.8: Redact sensitive API keys, tokens, and query params from text."""
        if not _is_data_redaction_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Data Redaction is disabled",
                    "disabled": "locus.data_redaction.enabled",
                },
            )
        b = body or {}
        text = str(b.get("text") or "")
        provider = _get_data_redaction_provider()
        return {
            "status": "ok",
            "redacted": provider.redact_text(text),
        }

    @app.post("/security/redact/structure")
    def redact_structure_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.8: Redact sensitive fields in nested JSON dictionaries and lists."""
        if not _is_data_redaction_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Data Redaction is disabled",
                    "disabled": "locus.data_redaction.enabled",
                },
            )
        b = body or {}
        payload = b.get("payload")
        provider = _get_data_redaction_provider()
        return {
            "status": "ok",
            "redacted": provider.redact_payload(payload),
        }

    @app.get("/security/redact/patterns")
    def redact_patterns_route() -> Any:
        """SPEC §13.8: List active vendor and custom redaction patterns."""
        if not _is_data_redaction_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Data Redaction is disabled",
                    "disabled": "locus.data_redaction.enabled",
                },
            )
        provider = _get_data_redaction_provider()
        return {
            "status": "ok",
            "patterns": provider.list_patterns(),
        }

    # =========================================================================
    # SPEC §13.9: Think Token Scrubbing (F-0042 / US-74)
    # =========================================================================
    from sidecar.security.think_scrubber import (
        SUPPORTED_TAGS as SUPPORTED_THINK_TAGS,
        ScrubState,
        StreamingThinkScrubber,
        ThinkTokenScrubber,
    )
    from sidecar.providers.think_scrubber import (
        BaseThinkScrubberProvider,
        DefaultThinkScrubberProvider,
    )

    active_registry.register("think_scrubber", "default_think_scrubber", DefaultThinkScrubberProvider)

    _think_scrubber_provider_instance: Optional[BaseThinkScrubberProvider] = None

    def _is_think_scrubber_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("think_scrubber"):
            return False
        v1 = config.get("locus.think_token_scrubbing.enabled")
        if v1 is not None and not config.is_enabled("locus.think_token_scrubbing.enabled"):
            return False
        v2 = config.get("locus.security.think_scrubbing.enabled")
        if v2 is not None and not config.is_enabled("locus.security.think_scrubbing.enabled"):
            return False
        return True

    def _get_think_scrubber_provider() -> BaseThinkScrubberProvider:
        nonlocal _think_scrubber_provider_instance
        if _think_scrubber_provider_instance is None:
            try:
                res = app.state.registry.get_active_provider(
                    "think_scrubber", default_name="default_think_scrubber"
                )
                if isinstance(res, BaseThinkScrubberProvider):
                    _think_scrubber_provider_instance = res
                elif isinstance(res, type) and issubclass(res, BaseThinkScrubberProvider):
                    _think_scrubber_provider_instance = res()
            except Exception:
                pass
        if _think_scrubber_provider_instance is None:
            _think_scrubber_provider_instance = DefaultThinkScrubberProvider()
        return _think_scrubber_provider_instance

    @app.post("/security/think_scrubber/feed")
    def think_scrubber_feed_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.9: Feed a delta text chunk through the streaming think scrubber."""
        if not _is_think_scrubber_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Think Token Scrubbing is disabled",
                    "disabled": "locus.think_token_scrubbing.enabled",
                },
            )
        b = body or {}
        delta = str(b.get("delta") if "delta" in b else (b.get("text") or ""))
        provider = _get_think_scrubber_provider()
        return {
            "status": "ok",
            "visible": provider.feed_chunk(delta),
        }

    @app.post("/security/think_scrubber/flush")
    def think_scrubber_flush_route() -> Any:
        """SPEC §13.9: Flush held-back stream buffer at end of assistant turn."""
        if not _is_think_scrubber_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Think Token Scrubbing is disabled",
                    "disabled": "locus.think_token_scrubbing.enabled",
                },
            )
        provider = _get_think_scrubber_provider()
        return {
            "status": "ok",
            "visible": provider.flush(),
        }

    @app.post("/security/think_scrubber/scrub_complete")
    def think_scrubber_scrub_complete_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.9: Batch scrub thinking blocks from a complete text payload."""
        if not _is_think_scrubber_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Think Token Scrubbing is disabled",
                    "disabled": "locus.think_token_scrubbing.enabled",
                },
            )
        b = body or {}
        text = str(b.get("text") or "")
        provider = _get_think_scrubber_provider()
        return {
            "status": "ok",
            "scrubbed": provider.scrub_text(text),
        }

    @app.post("/security/think_scrubber/reset")
    def think_scrubber_reset_route() -> Any:
        """SPEC §13.9: Reset streaming scrubber state for a new turn."""
        if not _is_think_scrubber_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Think Token Scrubbing is disabled",
                    "disabled": "locus.think_token_scrubbing.enabled",
                },
            )
        provider = _get_think_scrubber_provider()
        provider.reset()
        return {"status": "ok"}

    @app.get("/security/think_scrubber/tags")
    def think_scrubber_tags_route() -> Any:
        """SPEC §13.9: List supported thinking token tags."""
        if not _is_think_scrubber_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Think Token Scrubbing is disabled",
                    "disabled": "locus.think_token_scrubbing.enabled",
                },
            )
        provider = _get_think_scrubber_provider()
        return {
            "status": "ok",
            "tags": provider.list_tags(),
        }

    # =========================================================================
    # SPEC §13.10: Message Sanitization (F-0043 / US-75)
    # =========================================================================
    from sidecar.security.sanitizer import (
        MessageSanitizer,
        SURROGATE_RE,
        sanitize_messages,
        sanitize_structure_surrogates,
        sanitize_surrogates,
    )
    from sidecar.providers.message_sanitizer import (
        BaseMessageSanitizerProvider,
        DefaultMessageSanitizerProvider,
    )

    active_registry.register("message_sanitization", "default_message_sanitizer", DefaultMessageSanitizerProvider)
    active_registry.register("sanitizer", "default", DefaultMessageSanitizerProvider)

    _message_sanitizer_provider_instance: Optional[BaseMessageSanitizerProvider] = None

    def _is_message_sanitizer_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("message_sanitization"):
            return False
        v1 = config.get("locus.message_sanitization.enabled")
        if v1 is not None and not config.is_enabled("locus.message_sanitization.enabled"):
            return False
        v2 = config.get("locus.security.message_sanitization.enabled")
        if v2 is not None and not config.is_enabled("locus.security.message_sanitization.enabled"):
            return False
        return True

    def _get_message_sanitizer_provider() -> BaseMessageSanitizerProvider:
        nonlocal _message_sanitizer_provider_instance
        if _message_sanitizer_provider_instance is None:
            try:
                res = app.state.registry.get_active_provider(
                    "message_sanitization", default_name="default_message_sanitizer"
                )
                if isinstance(res, BaseMessageSanitizerProvider):
                    _message_sanitizer_provider_instance = res
                elif isinstance(res, type) and issubclass(res, BaseMessageSanitizerProvider):
                    _message_sanitizer_provider_instance = res()
            except Exception:
                pass
        if _message_sanitizer_provider_instance is None:
            _message_sanitizer_provider_instance = DefaultMessageSanitizerProvider()
        return _message_sanitizer_provider_instance

    @app.post("/security/sanitize/text")
    def sanitize_text_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.10: Sanitize string text, replacing lone surrogates with U+FFFD."""
        if not _is_message_sanitizer_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Message Sanitization is disabled",
                    "disabled": "locus.message_sanitization.enabled",
                },
            )
        b = body or {}
        text = str(b.get("text") or "")
        provider = _get_message_sanitizer_provider()
        return {
            "status": "ok",
            "sanitized": provider.sanitize_text(text),
        }

    @app.post("/security/sanitize/structure")
    def sanitize_structure_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.10: Recursively sanitize nested dictionary and list payloads."""
        if not _is_message_sanitizer_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Message Sanitization is disabled",
                    "disabled": "locus.message_sanitization.enabled",
                },
            )
        b = body or {}
        payload = b.get("payload")
        provider = _get_message_sanitizer_provider()
        sanitized, found = provider.sanitize_structure(payload)
        return {
            "status": "ok",
            "sanitized": sanitized,
            "found": found,
        }

    @app.post("/security/sanitize/messages")
    def sanitize_messages_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §13.10: Sanitize full message history prior to LLM API dispatch."""
        if not _is_message_sanitizer_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Message Sanitization is disabled",
                    "disabled": "locus.message_sanitization.enabled",
                },
            )
        b = body or {}
        messages = b.get("messages") or []
        provider = _get_message_sanitizer_provider()
        return {
            "status": "ok",
            "messages": provider.sanitize_messages(messages),
        }

    # -------------------------------------------------------------------------
    # SPEC §14.1-14.4: Voice Pipeline (F-0044 / US-76)
    # -------------------------------------------------------------------------
    import base64
    from sidecar.voice.pipeline import VoicePipelineManager
    from sidecar.voice.stt import (
        BaseSTTProvider,
        GroqWhisperSTTProvider,
        WhisperLocalSTTProvider,
        OpenAISTTProvider,
        AzureSTTProvider,
        MockSTTProvider,
    )
    from sidecar.voice.tts import (
        BaseTTSProvider,
        EdgeTTSProvider,
        ElevenLabsTTSProvider,
        PiperTTSProvider,
        OpenAITTSProvider,
        MockTTSProvider,
    )
    from sidecar.providers.voice import (
        BaseVoiceProvider,
        DefaultVoiceProvider,
    )

    active_registry.register("voice", "default_voice", DefaultVoiceProvider)

    _voice_provider_instance: Optional[BaseVoiceProvider] = None

    def _is_voice_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("voice"):
            return False
        v1 = config.get("locus.voice.enabled")
        if v1 is not None and not config.is_enabled("locus.voice.enabled"):
            return False
        return True

    def _is_stt_enabled() -> bool:
        if not _is_voice_enabled():
            return False
        v = config.get("locus.stt.enabled")
        if v is not None and not config.is_enabled("locus.stt.enabled"):
            return False
        return True

    def _is_tts_enabled() -> bool:
        if not _is_voice_enabled():
            return False
        v = config.get("locus.tts.enabled")
        if v is not None and not config.is_enabled("locus.tts.enabled"):
            return False
        return True

    def _get_voice_provider() -> BaseVoiceProvider:
        nonlocal _voice_provider_instance
        if _voice_provider_instance is None:
            res = app.state.registry.get_active_provider(
                "voice", default_name="default_voice"
            )
            if isinstance(res, BaseVoiceProvider):
                _voice_provider_instance = res
            elif callable(res):
                _voice_provider_instance = res()
        if _voice_provider_instance is None:
            _voice_provider_instance = DefaultVoiceProvider()
        return _voice_provider_instance

    @app.post("/voice/stt/transcribe")
    def voice_stt_transcribe_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §14.1: Speech-to-Text transcription route."""
        if not _is_stt_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "STT is disabled",
                    "disabled": "locus.stt.enabled",
                },
            )
        b = body or {}
        raw_audio = b.get("audio") or b.get("audio_base64") or ""
        language = b.get("language") or "en"
        model = b.get("model")
        if isinstance(raw_audio, str):
            try:
                audio_bytes = base64.b64decode(raw_audio)
            except Exception:
                audio_bytes = raw_audio.encode("utf-8")
        elif isinstance(raw_audio, bytes):
            audio_bytes = raw_audio
        else:
            audio_bytes = b""

        provider = _get_voice_provider()
        transcript = provider.transcribe(audio_bytes, language=language, model=model)
        active_name = (
            provider.pipeline.active_stt.name
            if hasattr(provider, "pipeline") and hasattr(provider.pipeline, "active_stt")
            else "stt"
        )
        return {
            "status": "ok",
            "text": transcript,
            "provider": active_name,
        }

    @app.post("/voice/tts/synthesize")
    def voice_tts_synthesize_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §14.2: Text-to-Speech synthesis route."""
        if not _is_tts_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "TTS is disabled",
                    "disabled": "locus.tts.enabled",
                },
            )
        b = body or {}
        text = b.get("text") or ""
        voice = b.get("voice")

        provider = _get_voice_provider()
        audio_bytes = provider.synthesize(text, voice=voice)
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        active_name = (
            provider.pipeline.active_tts.name
            if hasattr(provider, "pipeline") and hasattr(provider.pipeline, "active_tts")
            else "tts"
        )
        return {
            "status": "ok",
            "audio": audio_b64,
            "format": "wav",
            "provider": active_name,
        }

    @app.post("/voice/process_message")
    def voice_process_message_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §14.3: Telegram Voice Message Flow (Audio → STT → Process → TTS → Audio)."""
        if not _is_voice_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Voice pipeline is disabled",
                    "disabled": "locus.voice.enabled",
                },
            )
        b = body or {}
        raw_audio = b.get("audio") or b.get("audio_base64") or ""
        voice = b.get("voice")
        if isinstance(raw_audio, str):
            try:
                audio_bytes = base64.b64decode(raw_audio)
            except Exception:
                audio_bytes = raw_audio.encode("utf-8")
        elif isinstance(raw_audio, bytes):
            audio_bytes = raw_audio
        else:
            audio_bytes = b""

        provider = _get_voice_provider()
        transcript, response_text, out_bytes = provider.process_voice_message(
            audio_bytes, voice=voice
        )
        return {
            "status": "ok",
            "transcript": transcript,
            "response": response_text,
            "audio": base64.b64encode(out_bytes).decode("ascii"),
            "format": "wav",
        }

    @app.get("/voice/providers")
    def voice_providers_route() -> Any:
        """SPEC §14.1-14.4: List registered STT and TTS providers."""
        if not _is_voice_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Voice pipeline is disabled",
                    "disabled": "locus.voice.enabled",
                },
            )
        provider = _get_voice_provider()
        active_stt = (
            provider.pipeline.active_stt.name
            if hasattr(provider, "pipeline") and hasattr(provider.pipeline, "active_stt")
            else "unknown"
        )
        active_tts = (
            provider.pipeline.active_tts.name
            if hasattr(provider, "pipeline") and hasattr(provider.pipeline, "active_tts")
            else "unknown"
        )
        return {
            "status": "ok",
            "stt_providers": provider.list_stt_providers(),
            "tts_providers": provider.list_tts_providers(),
            "default_stt": active_stt,
            "default_tts": active_tts,
        }

    @app.get("/voice/voices")
    def voice_voices_route() -> Any:
        """SPEC §14.2: List available voices for active TTS provider."""
        if not _is_voice_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Voice pipeline is disabled",
                    "disabled": "locus.voice.enabled",
                },
            )
        provider = _get_voice_provider()
        active_tts = (
            provider.pipeline.active_tts.name
            if hasattr(provider, "pipeline") and hasattr(provider.pipeline, "active_tts")
            else "unknown"
        )
        return {
            "status": "ok",
            "voices": provider.list_voices(),
            "active_tts": active_tts,
        }

    # -------------------------------------------------------------------------
    # SPEC §15.1: Web Search (8 Providers) (F-0105 / US-77)
    # -------------------------------------------------------------------------
    from sidecar.search.manager import WebSearchManager
    from sidecar.search.providers import (
        BaseSearchProvider,
        BraveSearchProvider,
        ExaSearchProvider,
        FullContentFetchProvider,
        GeminiSearchProvider,
        MockSearchProvider,
        OpenAISearchProvider,
        ParallelSearchProvider,
        PerplexitySearchProvider,
        SearchResult,
        TavilySearchProvider,
    )
    from sidecar.providers.web_search import (
        BaseWebSearchProvider,
        DefaultWebSearchProvider,
    )

    active_registry.register(
        "web_search_8_providers", "default_web_search", DefaultWebSearchProvider
    )
    active_registry.register(
        "web_search", "default_web_search", DefaultWebSearchProvider
    )

    _web_search_provider_instance: Optional[BaseWebSearchProvider] = None

    def _is_web_search_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("web_search_8_providers"):
            return False
        v1 = config.get("locus.web_search_8_providers.enabled")
        if v1 is not None and not config.is_enabled("locus.web_search_8_providers.enabled"):
            return False
        v2 = config.get("locus.web_search.enabled")
        if v2 is not None and not config.is_enabled("locus.web_search.enabled"):
            return False
        return True

    def _get_web_search_provider() -> BaseWebSearchProvider:
        nonlocal _web_search_provider_instance
        if _web_search_provider_instance is None:
            res = app.state.registry.get_active_provider(
                "web_search_8_providers", default_name="default_web_search"
            )
            if isinstance(res, BaseWebSearchProvider):
                _web_search_provider_instance = res
            elif callable(res):
                _web_search_provider_instance = res()
        if _web_search_provider_instance is None:
            _web_search_provider_instance = DefaultWebSearchProvider()
        return _web_search_provider_instance

    @app.post("/search/query")
    def search_query_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §15.1: Execute web search across 8 providers."""
        if not _is_web_search_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Web search is disabled",
                    "disabled": "locus.web_search_8_providers.enabled",
                },
            )
        b = body or {}
        query = b.get("query") or ""
        max_results = int(b.get("max_results") or 5)
        req_provider = b.get("provider")

        provider = _get_web_search_provider()
        try:
            results = provider.search(query=query, max_results=max_results, provider=req_provider)
            active_name = (
                req_provider
                or (provider.manager.active_provider.name if hasattr(provider, "manager") else "default")
            )
            return {
                "status": "ok",
                "query": query,
                "provider": active_name,
                "results": [r.to_dict() for r in results],
            }
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(e)},
            )

    @app.post("/search/fetch")
    def search_fetch_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §15.1: Full content fetch route for document / webpage parsing."""
        if not _is_web_search_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Web search is disabled",
                    "disabled": "locus.web_search_8_providers.enabled",
                },
            )
        b = body or {}
        url = b.get("url") or ""
        provider = _get_web_search_provider()
        res = provider.fetch_content(url)
        return res

    @app.get("/search/providers")
    def search_providers_route() -> Any:
        """SPEC §15.1: List registered and available search providers."""
        if not _is_web_search_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Web search is disabled",
                    "disabled": "locus.web_search_8_providers.enabled",
                },
            )
        provider = _get_web_search_provider()
        active_name = (
            provider.manager.active_provider.name
            if hasattr(provider, "manager") and hasattr(provider.manager, "active_provider")
            else "unknown"
        )
        available = (
            provider.manager.list_available_providers()
            if hasattr(provider, "manager")
            else []
        )
        return {
            "status": "ok",
            "providers": provider.list_providers(),
            "available_providers": available,
            "active_provider": active_name,
        }

    # -------------------------------------------------------------------------
    # SPEC §16.1-16.2 + §20.1-20.3: Browser Automation & Desktop Control (F-0045 / US-78)
    # -------------------------------------------------------------------------
    from sidecar.browser.automation import (
        BaseBrowserEngine,
        BrowserbaseProvider,
        BrowserResult,
        BrowserTask,
        MockBrowserProvider,
        PlaywrightBrowserProvider,
        UIElement,
    )
    from sidecar.browser.manager import BrowserAutomationManager
    from sidecar.browser.screen_intelligence import ScreenIntelligence
    from sidecar.providers.browser import (
        BaseBrowserProvider,
        DefaultBrowserProvider,
    )
    from sidecar.providers.screen import (
        BaseScreenProvider,
        DefaultScreenProvider,
    )
    from sidecar.providers.graceful_restart import (
        BaseGracefulRestartProvider,
        DefaultGracefulRestartProvider,
    )
    from sidecar.providers.mcp import (
        BaseMcpProvider,
        DefaultMcpProvider,
    )
    from sidecar.providers.vnc import (
        BaseVNCProvider,
        DefaultVNCProvider,
    )
    from sidecar.providers.calendar import (
        BaseCalendarProvider,
        DefaultCalendarProvider,
    )
    from sidecar.providers.ci_cd_docker import (
        BaseDeploymentProvider,
        DefaultDeploymentProvider,
    )
    from sidecar.providers.pi_utilities import (
        BasePiUtilitiesProvider,
        DefaultPiUtilitiesProvider,
    )
    from sidecar.providers.scheduler import (
        BaseSchedulerProvider,
        DefaultSchedulerProvider,
    )
    from sidecar.providers.emergency import (
        BaseEmergencyTaskProvider,
        DefaultEmergencyTaskProvider,
    )
    from sidecar.providers.exhaustion import (
        BaseExhaustionPredictorProvider,
        DefaultExhaustionPredictorProvider,
    )
    from sidecar.providers.rebalance import (
        BaseWeeklyFactionRebalanceProvider,
        DefaultWeeklyFactionRebalanceProvider,
    )
    from sidecar.providers.goal_tracker import (
        BaseGoalTrackerProvider,
        DefaultGoalTrackerProvider,
    )
    from sidecar.providers.reviews import (
        BaseReviewCadenceProvider,
        DefaultReviewCadenceProvider,
    )
    from sidecar.providers.goal_enforcement import (
        BaseGoalStackEnforcementProvider,
        DefaultGoalStackEnforcementProvider,
    )
    from sidecar.providers.cross_faction import (
        BaseCrossFactionEfficiencyProvider,
        DefaultCrossFactionEfficiencyProvider,
    )
    from sidecar.providers.emergency_protocol import (
        BaseFourLevelEmergencyProtocolProvider,
        DefaultFourLevelEmergencyProtocolProvider,
    )
    from sidecar.providers.pageindex import (
        BasePageIndexRetrievalProvider,
        DefaultPageIndexRetrievalProvider,
    )
    from sidecar.providers.shorthand import (
        BaseShorthandCompressorProvider,
        DefaultShorthandCompressorProvider,
    )
    from sidecar.providers.tag_manager import (
        BaseTagHierarchyProvider,
        DefaultTagHierarchyProvider,
    )
    from sidecar.providers.rough_note_parser import (
        BaseRoughNoteParserProvider,
        DefaultRoughNoteParserProvider,
    )
    from sidecar.providers.link_logger import (
        BaseLinkDumpLoggerProvider,
        DefaultLinkDumpLoggerProvider,
    )
    from sidecar.providers.excalidraw import (
        BaseDiagramGeneratorProvider,
        DefaultDiagramGeneratorProvider,
    )
    from sidecar.providers.dual_interface import (
        BaseDualInterfaceProvider,
        DefaultDualInterfaceProvider,
    )
    from sidecar.providers.error_classifier import (
        BaseErrorClassifierProvider,
        DefaultErrorClassifierProvider,
    )
    from sidecar.providers.auxiliary_llm import (
        BaseAuxiliaryLLMProvider,
        DefaultAuxiliaryLLMProvider,
    )
    from sidecar.screen.capture import ScreenCaptureResult
    from sidecar.screen.desktop_control import DesktopAction, DesktopActionResult
    from sidecar.screen.screen_intelligence import ScreenElement

    active_registry.register(
        "browser_automation", "default_browser", DefaultBrowserProvider
    )
    active_registry.register(
        "browser", "default_browser", DefaultBrowserProvider
    )

    _browser_provider_instance: Optional[BaseBrowserProvider] = None

    def _is_browser_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("browser_automation"):
            return False
        v1 = config.get("locus.browser.enabled")
        if v1 is not None and not config.is_enabled("locus.browser.enabled"):
            return False
        v2 = config.get("locus.browser_automation.enabled")
        if v2 is not None and not config.is_enabled("locus.browser_automation.enabled"):
            return False
        return True

    def _get_browser_provider() -> BaseBrowserProvider:
        nonlocal _browser_provider_instance
        if _browser_provider_instance is None:
            res = app.state.registry.get_active_provider(
                "browser_automation", default_name="default_browser"
            )
            if isinstance(res, BaseBrowserProvider):
                _browser_provider_instance = res
            elif callable(res):
                _browser_provider_instance = res()
        if _browser_provider_instance is None:
            _browser_provider_instance = DefaultBrowserProvider()
        return _browser_provider_instance

    @app.post("/browser/navigate")
    def browser_navigate_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1: Navigate to target URL in browser engine."""
        if not _is_browser_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Browser automation is disabled",
                    "disabled": "locus.browser_automation.enabled",
                },
            )
        b = body or {}
        url = b.get("url") or "about:blank"
        provider = _get_browser_provider()
        res = provider.navigate(url)
        return {"status": "ok", **res.to_dict()}

    @app.post("/browser/click")
    def browser_click_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1: Click element by selector or coordinate."""
        if not _is_browser_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Browser automation is disabled",
                    "disabled": "locus.browser_automation.enabled",
                },
            )
        b = body or {}
        selector = b.get("selector")
        x = b.get("x")
        y = b.get("y")
        provider = _get_browser_provider()
        res = provider.click(selector=selector, x=x, y=y)
        return {"status": "ok", **res.to_dict()}

    @app.post("/browser/type")
    def browser_type_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1: Type text into browser page element."""
        if not _is_browser_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Browser automation is disabled",
                    "disabled": "locus.browser_automation.enabled",
                },
            )
        b = body or {}
        text = b.get("text") or ""
        selector = b.get("selector")
        provider = _get_browser_provider()
        res = provider.type_text(text, selector=selector)
        return {"status": "ok", **res.to_dict()}

    @app.post("/browser/screenshot")
    def browser_screenshot_route() -> Any:
        """SPEC §16.1: Capture screenshot of current page."""
        if not _is_browser_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Browser automation is disabled",
                    "disabled": "locus.browser_automation.enabled",
                },
            )
        provider = _get_browser_provider()
        shot = provider.screenshot()
        return {
            "status": "ok",
            "screenshot": base64.b64encode(shot).decode("ascii"),
            "format": "png",
        }

    @app.post("/browser/analyze")
    def browser_analyze_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1: Analyze screen elements via Screen Intelligence."""
        if not _is_browser_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Browser automation is disabled",
                    "disabled": "locus.browser_automation.enabled",
                },
            )
        b = body or {}
        raw_shot = b.get("screenshot")
        shot_bytes = base64.b64decode(raw_shot) if raw_shot else None
        provider = _get_browser_provider()
        elements = provider.analyze_screen(shot_bytes)
        return {
            "status": "ok",
            "elements": [e.to_dict() for e in elements],
        }

    @app.post("/browser/automate")
    def browser_automate_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1: Execute multi-step automated browser task flow."""
        if not _is_browser_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Browser automation is disabled",
                    "disabled": "locus.browser_automation.enabled",
                },
            )
        b = body or {}
        url = b.get("url") or "about:blank"
        actions = b.get("actions") or []
        capture_shot = bool(b.get("capture_screenshot", True))
        task = BrowserTask(url=url, actions=actions, capture_screenshot=capture_shot)
        provider = _get_browser_provider()
        res = provider.automate_task(task)
        return {"status": "ok", **res.to_dict()}

    @app.get("/browser/providers")
    def browser_providers_route() -> Any:
        """SPEC §16.1: List browser automation engines and active driver."""
        if not _is_browser_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Browser automation is disabled",
                    "disabled": "locus.browser_automation.enabled",
                },
            )
        provider = _get_browser_provider()
        active_name = (
            provider.manager.active_engine.name
            if hasattr(provider, "manager") and hasattr(provider.manager, "active_engine")
            else "unknown"
        )
        return {
            "status": "ok",
            "engines": provider.list_engines(),
            "active_engine": active_name,
        }

    # Computer Use / Screen Provider registration (F-0051 / US-79)
    active_registry.register("screen", "default_screen", DefaultScreenProvider)
    active_registry.register("computer_use", "default_screen", DefaultScreenProvider)
    active_registry.register("desktop_control", "default_screen", DefaultScreenProvider)

    _screen_provider_instance: Optional[BaseScreenProvider] = None

    def _is_screen_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("screen"):
            return False
        v1 = config.get("locus.screen.enabled")
        if v1 is not None and not config.is_enabled("locus.screen.enabled"):
            return False
        v2 = config.get("locus.computer_use.enabled")
        if v2 is not None and not config.is_enabled("locus.computer_use.enabled"):
            return False
        v3 = config.get("locus.desktop_control.enabled")
        if v3 is not None and not config.is_enabled("locus.desktop_control.enabled"):
            return False
        return True

    def _get_screen_provider() -> BaseScreenProvider:
        nonlocal _screen_provider_instance
        if _screen_provider_instance is None:
            res = app.state.registry.get_active_provider(
                "screen", default_name="default_screen"
            )
            if isinstance(res, BaseScreenProvider):
                _screen_provider_instance = res
            elif callable(res):
                _screen_provider_instance = res()
        if _screen_provider_instance is None:
            _screen_provider_instance = DefaultScreenProvider()
        return _screen_provider_instance

    @app.post("/screen/capture")
    def screen_capture_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1 line 6535: Native desktop screen capture."""
        if not _is_screen_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Screen capture is disabled",
                    "disabled": "locus.screen.enabled",
                },
            )
        b = body or {}
        display_id = int(b.get("display_id", 0))
        region = b.get("region")
        if region and isinstance(region, list) and len(region) == 4:
            region = tuple(region)
        else:
            region = None
        window_title = b.get("window_title")

        provider = _get_screen_provider()
        res = provider.capture_screen(display_id=display_id, region=region, window_title=window_title)
        return {"status": "ok", **res.to_dict()}

    @app.post("/screen/control")
    def screen_control_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1 lines 6529-6537: Native desktop control actions (click, type, window_focus)."""
        if not _is_screen_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Desktop control is disabled",
                    "disabled": "locus.desktop_control.enabled",
                },
            )
        b = body or {}
        action = DesktopAction(
            action_type=b.get("action_type") or b.get("type") or "click",
            x=b.get("x"),
            y=b.get("y"),
            text=b.get("text"),
            key=b.get("key"),
            keys=b.get("keys") or [],
            window_title=b.get("window_title"),
            delta_y=b.get("delta_y"),
            metadata=b.get("metadata") or {},
        )
        provider = _get_screen_provider()
        res = provider.control_desktop(action)
        return {"status": "ok", **res.to_dict()}

    @app.post("/screen/analyze")
    def screen_analyze_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1 lines 6516-6526: Analyze screen screenshot with Screen Intelligence."""
        if not _is_screen_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Screen intelligence is disabled",
                    "disabled": "locus.screen.enabled",
                },
            )
        b = body or {}
        shot_b64 = b.get("screenshot") or b.get("screenshot_base64")
        prompt = b.get("prompt")
        provider = _get_screen_provider()
        elements = provider.analyze_screen(screenshot_base64=shot_b64, prompt=prompt)
        return {
            "status": "ok",
            "elements": [e.to_dict() for e in elements],
            "count": len(elements),
        }

    @app.post("/screen/execute")
    def screen_execute_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §16.1: Execute multi-action computer use workflow."""
        if not _is_screen_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Computer use workflow is disabled",
                    "disabled": "locus.computer_use.enabled",
                },
            )
        b = body or {}
        raw_actions = b.get("actions") or []
        actions: List[DesktopAction] = []
        for a in raw_actions:
            if isinstance(a, dict):
                actions.append(
                    DesktopAction(
                        action_type=a.get("action_type") or a.get("type") or "click",
                        x=a.get("x"),
                        y=a.get("y"),
                        text=a.get("text"),
                        key=a.get("key"),
                        keys=a.get("keys") or [],
                        window_title=a.get("window_title"),
                        delta_y=a.get("delta_y"),
                        metadata=a.get("metadata") or {},
                    )
                )
        provider = _get_screen_provider()
        results = provider.execute_workflow(actions)
        return {
            "status": "ok",
            "results": [r.to_dict() for r in results],
            "count": len(results),
        }

    @app.get("/screen/status")
    def screen_status_route() -> Any:
        """SPEC §16.1: Get computer use subsystem status."""
        if not _is_screen_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Screen / Computer Use is disabled",
                    "disabled": "locus.screen.enabled",
                },
            )
        provider = _get_screen_provider()
        return {"status": "ok", **provider.get_status()}

    # Graceful Gateway Restart & State Snapshotting (F-0047 / US-80)
    active_registry.register(
        "graceful_restart", "default_graceful_restart", DefaultGracefulRestartProvider
    )
    active_registry.register(
        "gateway_lifecycle", "default_graceful_restart", DefaultGracefulRestartProvider
    )

    _graceful_restart_instance: Optional[BaseGracefulRestartProvider] = None

    def _is_graceful_restart_enabled() -> bool:
        if not app.state.registry.is_feature_enabled("graceful_restart"):
            return False
        v1 = config.get("locus.graceful_restart.enabled")
        if v1 is not None and not config.is_enabled("locus.graceful_restart.enabled"):
            return False
        v2 = config.get("locus.gateway.graceful_restart.enabled")
        if v2 is not None and not config.is_enabled("locus.gateway.graceful_restart.enabled"):
            return False
        return True

    def _get_graceful_restart_provider() -> BaseGracefulRestartProvider:
        nonlocal _graceful_restart_instance
        if _graceful_restart_instance is None:
            res = app.state.registry.get_active_provider(
                "graceful_restart", default_name="default_graceful_restart"
            )
            if isinstance(res, BaseGracefulRestartProvider):
                _graceful_restart_instance = res
            elif callable(res):
                _graceful_restart_instance = res()
        if _graceful_restart_instance is None:
            _graceful_restart_instance = DefaultGracefulRestartProvider()
        return _graceful_restart_instance

    @app.post("/gateway/restart/initiate")
    def gateway_restart_initiate_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §17.10: Initiate graceful gateway shutdown / drain sequence."""
        if not _is_graceful_restart_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Graceful restart is disabled",
                    "disabled": "locus.graceful_restart.enabled",
                },
            )
        b = body or {}
        signal_type = b.get("signal_type") or "SIGTERM"
        dry_run = bool(b.get("dry_run", True))
        provider = _get_graceful_restart_provider()
        res = provider.initiate_shutdown(signal_type=signal_type, dry_run=dry_run)
        return {"status": "ok", **res}

    @app.post("/gateway/restart/drain")
    def gateway_restart_drain_route() -> Any:
        """SPEC §17.10: Drain active in-flight requests."""
        if not _is_graceful_restart_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Graceful restart is disabled",
                    "disabled": "locus.graceful_restart.enabled",
                },
            )
        provider = _get_graceful_restart_provider()
        remaining = provider.drain_connections()
        return {"status": "ok", "remaining_in_flight": remaining}

    @app.post("/gateway/restart/snapshot")
    def gateway_restart_snapshot_route() -> Any:
        """SPEC §17.10: Snapshot active in-memory session states to recovery directory."""
        if not _is_graceful_restart_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Graceful restart is disabled",
                    "disabled": "locus.graceful_restart.enabled",
                },
            )
        provider = _get_graceful_restart_provider()
        saved = provider.snapshot_sessions()
        return {"status": "ok", "snapshots_saved": len(saved), "files": saved}

    @app.get("/gateway/restart/recovery")
    def gateway_restart_recovery_route() -> Any:
        """SPEC §17.10: List recovered session states from disk."""
        if not _is_graceful_restart_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Graceful restart is disabled",
                    "disabled": "locus.graceful_restart.enabled",
                },
            )
        provider = _get_graceful_restart_provider()
        recovered = provider.recover_sessions()
        return {"status": "ok", "recovered_sessions": recovered, "count": len(recovered)}

    @app.get("/gateway/restart/status")
    def gateway_restart_status_route() -> Any:
        """SPEC §17.10: Get diagnostic status of gateway lifecycle."""
        if not _is_graceful_restart_enabled():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Graceful restart is disabled",
                    "disabled": "locus.graceful_restart.enabled",
                },
            )
        provider = _get_graceful_restart_provider()
        return {"status": "ok", **provider.get_status()}

    # Model Context Protocol (MCP Server/Client) (F-0048 / US-81)
    active_registry.register(
        "mcp_server_client", "default_mcp", DefaultMcpProvider
    )
    active_registry.register(
        "mcp", "default_mcp", DefaultMcpProvider
    )

    def _is_mcp_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.mcp_server_client.enabled")
        if v1 is not None and not config.is_enabled("locus.mcp_server_client.enabled"):
            return False, "locus.mcp_server_client.enabled"
        v2 = config.get("locus.mcp.enabled")
        if v2 is not None and not config.is_enabled("locus.mcp.enabled"):
            return False, "locus.mcp.enabled"
        if not app.state.registry.is_feature_enabled("mcp_server_client") and not app.state.registry.is_feature_enabled("mcp"):
            return False, "locus.mcp_server_client.enabled"
        return True, ""

    def _get_mcp_provider() -> BaseMcpProvider:
        if not hasattr(app.state, "mcp_provider") or app.state.mcp_provider is None:
            res = app.state.registry.get_active_provider(
                "mcp_server_client", default_name="default_mcp"
            )
            if isinstance(res, BaseMcpProvider):
                app.state.mcp_provider = res
            elif callable(res):
                app.state.mcp_provider = res()
            else:
                app.state.mcp_provider = DefaultMcpProvider()
        return app.state.mcp_provider

    @app.post("/mcp/servers/connect")
    async def mcp_server_connect_route(body: Dict[str, Any]) -> Any:
        """SPEC §18.1-18.4: Connect to an external MCP server."""
        enabled, switch = _is_mcp_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "MCP server/client is disabled",
                    "disabled": switch,
                },
            )
        server_id = body.get("server_id")
        if not server_id:
            raise HTTPException(status_code=400, detail="Missing required field: server_id")
        provider = _get_mcp_provider()
        res = await provider.connect_server(server_id)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/mcp/servers/disconnect")
    async def mcp_server_disconnect_route(body: Dict[str, Any]) -> Any:
        """SPEC §18.1-18.4: Disconnect from an external MCP server."""
        enabled, switch = _is_mcp_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "MCP server/client is disabled",
                    "disabled": switch,
                },
            )
        server_id = body.get("server_id")
        if not server_id:
            raise HTTPException(status_code=400, detail="Missing required field: server_id")
        provider = _get_mcp_provider()
        res = await provider.disconnect_server(server_id)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/mcp/servers/list")
    def mcp_servers_list_route() -> Any:
        """SPEC §18.1-18.4: List configured MCP servers and status."""
        enabled, switch = _is_mcp_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "MCP server/client is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_mcp_provider()
        res = provider.list_servers()
        if isinstance(res, list) and res and isinstance(res[0], dict) and res[0].get("status_code") == 503:
            return JSONResponse(status_code=503, content=res[0])
        return {"status": "ok", "servers": res}

    @app.get("/mcp/tools/list")
    async def mcp_tools_list_route() -> Any:
        """SPEC §18.1-18.4: List all sanitized tools from connected servers."""
        enabled, switch = _is_mcp_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "MCP server/client is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_mcp_provider()
        res = await provider.list_tools()
        if isinstance(res, list) and res and isinstance(res[0], dict) and res[0].get("status_code") == 503:
            return JSONResponse(status_code=503, content=res[0])
        return {"status": "ok", "tools": res}

    @app.post("/mcp/tools/call")
    async def mcp_tools_call_route(body: Dict[str, Any]) -> Any:
        """SPEC §18.1-18.4: Call a tool on a connected MCP server."""
        enabled, switch = _is_mcp_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "MCP server/client is disabled",
                    "disabled": switch,
                },
            )
        server_id = body.get("server_id")
        tool_name = body.get("tool_name")
        if not server_id or not tool_name:
            raise HTTPException(status_code=400, detail="Missing server_id or tool_name")
        provider = _get_mcp_provider()
        res = await provider.call_tool(server_id, tool_name, body.get("arguments"))
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return {"status": "ok", "result": res}

    @app.post("/mcp/server/jsonrpc")
    def mcp_server_jsonrpc_route(body: Dict[str, Any]) -> Any:
        """SPEC §18.1-18.4: JSON-RPC 2.0 endpoint for Locus-as-MCP-Server."""
        enabled, switch = _is_mcp_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "MCP server/client is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_mcp_provider()
        res = provider.handle_server_jsonrpc(body, client_info="remote-http-client")
        if isinstance(res, dict) and res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/mcp/status")
    def mcp_status_route() -> Any:
        """SPEC §18.1-18.4: Get status of MCP provider and supervisor."""
        enabled, switch = _is_mcp_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "MCP server/client is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_mcp_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # VNC Remote Desktop Protocol Control (F-0052 / US-82 / SPEC §20.3)
    active_registry.register(
        "vnc_remote", "default_vnc", DefaultVNCProvider
    )
    active_registry.register(
        "vnc", "default_vnc", DefaultVNCProvider
    )

    def _is_vnc_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.vnc.enabled")
        if v1 is not None and not config.is_enabled("locus.vnc.enabled"):
            return False, "locus.vnc.enabled"
        v2 = config.get("locus.tools.vnc.enabled")
        if v2 is not None and not config.is_enabled("locus.tools.vnc.enabled"):
            return False, "locus.tools.vnc.enabled"
        if not app.state.registry.is_feature_enabled("vnc_remote") and not app.state.registry.is_feature_enabled("vnc"):
            return False, "locus.vnc.enabled"
        return True, ""

    def _get_vnc_provider() -> BaseVNCProvider:
        if not hasattr(app.state, "vnc_provider") or app.state.vnc_provider is None:
            res = app.state.registry.get_active_provider(
                "vnc_remote", default_name="default_vnc"
            )
            if isinstance(res, BaseVNCProvider):
                app.state.vnc_provider = res
            elif callable(res):
                app.state.vnc_provider = res()
            else:
                app.state.vnc_provider = DefaultVNCProvider()
        return app.state.vnc_provider

    @app.post("/vnc/connect")
    def vnc_connect_route(body: Dict[str, Any] = Body(default={})) -> Any:
        """SPEC §20.3: Establish connection to remote VNC display."""
        enabled, switch = _is_vnc_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "VNC remote control is disabled",
                    "disabled": switch,
                },
            )
        host = body.get("host", "127.0.0.1")
        port = int(body.get("port", 5900))
        password = body.get("password", "")
        provider = _get_vnc_provider()
        res = provider.connect(host=host, port=port, password=password)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/vnc/disconnect")
    def vnc_disconnect_route() -> Any:
        """SPEC §20.3: Disconnect from remote VNC display."""
        enabled, switch = _is_vnc_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "VNC remote control is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_vnc_provider()
        res = provider.disconnect()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/vnc/capture")
    def vnc_capture_route() -> Any:
        """SPEC §20.3: Capture current display framebuffer."""
        enabled, switch = _is_vnc_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "VNC remote control is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_vnc_provider()
        res = provider.capture_framebuffer()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/vnc/click")
    def vnc_click_route(body: Dict[str, Any]) -> Any:
        """SPEC §20.3: Perform mouse move and click within safe boundary."""
        enabled, switch = _is_vnc_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "VNC remote control is disabled",
                    "disabled": switch,
                },
            )
        if "x" not in body or "y" not in body:
            raise HTTPException(status_code=400, detail="Missing required x or y coordinates")
        x = int(body["x"])
        y = int(body["y"])
        button = str(body.get("button", "left"))
        steps = int(body.get("steps", 5))
        provider = _get_vnc_provider()
        res = provider.click(x=x, y=y, button=button, steps=steps)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        if res.get("status_code") == 403:
            return JSONResponse(status_code=403, content=res)
        return res

    @app.post("/vnc/type")
    def vnc_type_route(body: Dict[str, Any]) -> Any:
        """SPEC §20.3: Inject keystrokes into remote desktop."""
        enabled, switch = _is_vnc_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "VNC remote control is disabled",
                    "disabled": switch,
                },
            )
        text = body.get("text", "")
        provider = _get_vnc_provider()
        res = provider.type_keys(text=text)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/vnc/status")
    def vnc_status_route() -> Any:
        """SPEC §20.3: Get diagnostic status of VNC remote controller."""
        enabled, switch = _is_vnc_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "VNC remote control is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_vnc_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Google Calendar, Gmail, Webhooks (F-0053 / US-83 / SPEC §21.1-21.3)
    active_registry.register(
        "google_calendar", "default_calendar", DefaultCalendarProvider
    )
    active_registry.register(
        "calendar", "default_calendar", DefaultCalendarProvider
    )
    active_registry.register(
        "webhooks", "default_calendar", DefaultCalendarProvider
    )

    def _is_calendar_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.integrations.calendar.enabled")
        if v1 is not None and not config.is_enabled("locus.integrations.calendar.enabled"):
            return False, "locus.integrations.calendar.enabled"
        v2 = config.get("locus.google_calendar.enabled")
        if v2 is not None and not config.is_enabled("locus.google_calendar.enabled"):
            return False, "locus.google_calendar.enabled"
        if not app.state.registry.is_feature_enabled("google_calendar") and not app.state.registry.is_feature_enabled("calendar"):
            return False, "locus.integrations.calendar.enabled"
        return True, ""

    def _get_calendar_provider() -> BaseCalendarProvider:
        if not hasattr(app.state, "calendar_provider") or app.state.calendar_provider is None:
            res = app.state.registry.get_active_provider(
                "google_calendar", default_name="default_calendar"
            )
            if isinstance(res, BaseCalendarProvider):
                app.state.calendar_provider = res
            elif callable(res):
                app.state.calendar_provider = res()
            else:
                app.state.calendar_provider = DefaultCalendarProvider()
        return app.state.calendar_provider

    @app.post("/integrations/calendar/auth-url")
    def calendar_auth_url_route(body: Dict[str, Any] = Body(default={})) -> Any:
        """SPEC §21.1: Generate OAuth 2.0 authorization URL."""
        enabled, switch = _is_calendar_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Google Calendar integration is disabled",
                    "disabled": switch,
                },
            )
        redirect_uri = body.get("redirect_uri", "urn:ietf:wg:oauth:2.0:oob")
        provider = _get_calendar_provider()
        res = provider.get_auth_url(redirect_uri=redirect_uri)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/integrations/calendar/exchange")
    def calendar_exchange_route(body: Dict[str, Any]) -> Any:
        """SPEC §21.1: Exchange auth code for Google OAuth tokens."""
        enabled, switch = _is_calendar_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Google Calendar integration is disabled",
                    "disabled": switch,
                },
            )
        code = body.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Missing required code parameter")
        redirect_uri = body.get("redirect_uri", "urn:ietf:wg:oauth:2.0:oob")
        provider = _get_calendar_provider()
        res = provider.exchange_code(code=code, redirect_uri=redirect_uri)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/integrations/calendar/events")
    def calendar_events_route(time_min: Optional[str] = None, time_max: Optional[str] = None) -> Any:
        """SPEC §21.1: List calendar events."""
        enabled, switch = _is_calendar_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Google Calendar integration is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_calendar_provider()
        res = provider.list_events(time_min=time_min, time_max=time_max)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/integrations/calendar/events")
    def calendar_create_event_route(body: Dict[str, Any]) -> Any:
        """SPEC §21.1: Create scheduled event in calendar."""
        enabled, switch = _is_calendar_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Google Calendar integration is disabled",
                    "disabled": switch,
                },
            )
        summary = body.get("summary")
        start_time = body.get("start_time")
        end_time = body.get("end_time")
        if not summary or not start_time or not end_time:
            raise HTTPException(status_code=400, detail="Missing required fields: summary, start_time, end_time")
        provider = _get_calendar_provider()
        res = provider.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=body.get("description", ""),
            location=body.get("location", ""),
            attendees=body.get("attendees", []),
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/integrations/calendar/temporal")
    def calendar_temporal_context_route() -> Any:
        """SPEC §21.1: Get formatted schedule for Context Forge temporal layer."""
        enabled, switch = _is_calendar_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Google Calendar integration is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_calendar_provider()
        res = provider.get_temporal_context()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/integrations/webhooks/register")
    def webhook_register_route(body: Dict[str, Any]) -> Any:
        """SPEC §21.3: Register outgoing webhook endpoint."""
        enabled, switch = _is_calendar_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Google Calendar integration is disabled",
                    "disabled": switch,
                },
            )
        url = body.get("url")
        events = body.get("events")
        if not url or not events:
            raise HTTPException(status_code=400, detail="Missing required fields: url, events")
        provider = _get_calendar_provider()
        res = provider.register_webhook(url=url, events=events, secret=body.get("secret"))
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/integrations/webhooks/fire")
    def webhook_fire_route(body: Dict[str, Any]) -> Any:
        """SPEC §21.3: Dispatch event notification to subscribed webhooks."""
        enabled, switch = _is_calendar_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Google Calendar integration is disabled",
                    "disabled": switch,
                },
            )
        event_type = body.get("event_type")
        payload = body.get("payload", {})
        if not event_type:
            raise HTTPException(status_code=400, detail="Missing required field: event_type")
        provider = _get_calendar_provider()
        res = provider.fire_webhook(event_type=event_type, payload=payload)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/integrations/calendar/status")
    def calendar_status_route() -> Any:
        """SPEC §21.1-21.3: Get diagnostic status of calendar & webhook integrations."""
        enabled, switch = _is_calendar_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Google Calendar integration is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_calendar_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # CI/CD, Docker Deployment & Batch Runner (F-0054 / US-84 / SPEC §23.1-23.5)
    active_registry.register(
        "ci_cd_docker", "default_deployment", DefaultDeploymentProvider
    )
    active_registry.register(
        "deployment", "default_deployment", DefaultDeploymentProvider
    )

    def _is_deployment_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.ci_cd_docker.enabled")
        if v1 is not None and not config.is_enabled("locus.ci_cd_docker.enabled"):
            return False, "locus.ci_cd_docker.enabled"
        v2 = config.get("locus.deployment.enabled")
        if v2 is not None and not config.is_enabled("locus.deployment.enabled"):
            return False, "locus.deployment.enabled"
        if not app.state.registry.is_feature_enabled("ci_cd_docker") and not app.state.registry.is_feature_enabled("deployment"):
            return False, "locus.ci_cd_docker.enabled"
        return True, ""

    def _get_deployment_provider() -> BaseDeploymentProvider:
        if not hasattr(app.state, "deployment_provider") or app.state.deployment_provider is None:
            res = app.state.registry.get_active_provider(
                "ci_cd_docker", default_name="default_deployment"
            )
            if isinstance(res, BaseDeploymentProvider):
                app.state.deployment_provider = res
            elif callable(res):
                app.state.deployment_provider = res()
            else:
                app.state.deployment_provider = DefaultDeploymentProvider()
        return app.state.deployment_provider

    @app.get("/deployment/docker/status")
    def docker_topology_status_route() -> Any:
        """SPEC §23.2: Inspect and validate 5-container Docker topology."""
        enabled, switch = _is_deployment_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "CI/CD & Docker deployment is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_deployment_provider()
        res = provider.inspect_docker_topology()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/deployment/systemd/generate")
    def systemd_generate_route(body: Dict[str, Any] = Body(default={})) -> Any:
        """SPEC §23.1: Generate hardened systemd unit file."""
        enabled, switch = _is_deployment_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "CI/CD & Docker deployment is disabled",
                    "disabled": switch,
                },
            )
        service_type = body.get("service_type", "sidecar")
        working_dir = body.get("working_dir", "/opt/locus/locus-os")
        user = body.get("user", "locus")
        env_file = body.get("env_file", "/opt/locus/.locus/.env")
        provider = _get_deployment_provider()
        res = provider.generate_systemd_unit(
            service_type=service_type,
            working_dir=working_dir,
            user=user,
            env_file=env_file,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/deployment/batch/evaluate")
    def batch_evaluate_route(body: Dict[str, Any]) -> Any:
        """SPEC §23.5: Execute batch evaluation across multiple trajectory runs."""
        enabled, switch = _is_deployment_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "CI/CD & Docker deployment is disabled",
                    "disabled": switch,
                },
            )
        prompt = body.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="Missing required field: prompt")
        n_runs = int(body.get("n_runs", 3))
        provider = _get_deployment_provider()
        res = provider.evaluate_batch(prompt=prompt, n_runs=n_runs)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/deployment/status")
    def deployment_status_route() -> Any:
        """SPEC §23.1-23.5: Get diagnostic status of deployment subsystems."""
        enabled, switch = _is_deployment_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "CI/CD & Docker deployment is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_deployment_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Pi Utilities (Clipboard, Syntax Highlighting, Frontmatter, File Watcher) (F-0106 / US-85 / SPEC §24.1)
    active_registry.register(
        "pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher", "default_pi_utilities", DefaultPiUtilitiesProvider
    )
    active_registry.register(
        "pi_utilities", "default_pi_utilities", DefaultPiUtilitiesProvider
    )
    active_registry.register(
        "utilities", "default_pi_utilities", DefaultPiUtilitiesProvider
    )

    def _is_utilities_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled")
        if v1 is not None and not config.is_enabled("locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled"):
            return False, "locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled"
        v2 = config.get("locus.pi_utilities.enabled")
        if v2 is not None and not config.is_enabled("locus.pi_utilities.enabled"):
            return False, "locus.pi_utilities.enabled"
        if not app.state.registry.is_feature_enabled("pi_utilities") and not app.state.registry.is_feature_enabled("utilities"):
            return False, "locus.pi_utilities.enabled"
        return True, ""

    def _get_utilities_provider() -> BasePiUtilitiesProvider:
        if not hasattr(app.state, "utilities_provider") or app.state.utilities_provider is None:
            res = app.state.registry.get_active_provider(
                "pi_utilities", default_name="default_pi_utilities"
            )
            if isinstance(res, BasePiUtilitiesProvider):
                app.state.utilities_provider = res
            elif callable(res):
                app.state.utilities_provider = res()
            else:
                app.state.utilities_provider = DefaultPiUtilitiesProvider()
        return app.state.utilities_provider

    @app.post("/utils/clipboard/copy")
    def clipboard_copy_route(body: Dict[str, Any]) -> Any:
        """SPEC §24.1: Copy text to clipboard."""
        enabled, switch = _is_utilities_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Pi utilities are disabled",
                    "disabled": switch,
                },
            )
        text = str(body.get("text", ""))
        provider = _get_utilities_provider()
        res = provider.copy_clipboard(text=text)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/utils/clipboard/paste")
    def clipboard_paste_route() -> Any:
        """SPEC §24.1: Paste text from clipboard."""
        enabled, switch = _is_utilities_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Pi utilities are disabled",
                    "disabled": switch,
                },
            )
        provider = _get_utilities_provider()
        res = provider.paste_clipboard()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/utils/frontmatter/parse")
    def frontmatter_parse_route(body: Dict[str, Any]) -> Any:
        """SPEC §24.1: Parse frontmatter from content."""
        enabled, switch = _is_utilities_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Pi utilities are disabled",
                    "disabled": switch,
                },
            )
        content = str(body.get("content", ""))
        provider = _get_utilities_provider()
        res = provider.parse_frontmatter(content=content)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/utils/syntax/highlight")
    def syntax_highlight_route(body: Dict[str, Any]) -> Any:
        """SPEC §24.1: Syntax highlight code snippet."""
        enabled, switch = _is_utilities_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Pi utilities are disabled",
                    "disabled": switch,
                },
            )
        code = str(body.get("code", ""))
        language = str(body.get("language", "text"))
        provider = _get_utilities_provider()
        res = provider.highlight_syntax(code=code, language=language)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/utils/watcher/poll")
    def watcher_poll_route() -> Any:
        """SPEC §24.1: Poll file watcher for change events."""
        enabled, switch = _is_utilities_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Pi utilities are disabled",
                    "disabled": switch,
                },
            )
        provider = _get_utilities_provider()
        res = provider.poll_file_changes()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/utils/status")
    def utilities_status_route() -> Any:
        """SPEC §24.1: Get diagnostic status of utility subsystems."""
        enabled, switch = _is_utilities_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Pi utilities are disabled",
                    "disabled": switch,
                },
            )
        provider = _get_utilities_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Operating Modes / Scheduler (§25.5-25.8 & §25.12 / F-0056 / US-86)
    active_registry.register(
        "operating_modes_scheduler", "default_scheduler", DefaultSchedulerProvider
    )
    active_registry.register(
        "scheduler_engine", "default_scheduler", DefaultSchedulerProvider
    )

    def _is_scheduler_enabled(feature: str = "scheduler") -> tuple[bool, str]:
        v1 = config.get("locus.operating_modes_scheduler.enabled")
        if v1 is not None and not config.is_enabled("locus.operating_modes_scheduler.enabled"):
            return False, "locus.operating_modes_scheduler.enabled"
        v2 = config.get("locus.scheduler.enabled")
        if v2 is not None and not config.is_enabled("locus.scheduler.enabled"):
            return False, "locus.scheduler.enabled"

        sub_switches = {
            "goal_stack": "locus.life_os.goal_stack.enabled",
            "action_gap": "locus.life_os.action_gap.enabled",
            "deferral": "locus.life_os.deferral.enabled",
        }
        if feature in sub_switches:
            sub = sub_switches[feature]
            val = config.get(sub)
            if val is not None and not config.is_enabled(sub):
                return False, sub

        if not app.state.registry.is_feature_enabled("operating_modes_scheduler") and not app.state.registry.is_feature_enabled("scheduler_engine"):
            return False, "locus.operating_modes_scheduler.enabled"
        return True, ""

    def _get_scheduler_provider() -> BaseSchedulerProvider:
        if not hasattr(app.state, "operating_modes_scheduler_provider") or app.state.operating_modes_scheduler_provider is None:
            res = app.state.registry.get_active_provider(
                "operating_modes_scheduler", default_name="default_scheduler"
            )
            if isinstance(res, BaseSchedulerProvider):
                app.state.operating_modes_scheduler_provider = res
            elif callable(res):
                app.state.operating_modes_scheduler_provider = res()
            else:
                app.state.operating_modes_scheduler_provider = DefaultSchedulerProvider()
        return app.state.operating_modes_scheduler_provider

    @app.post("/scheduler/goal-stack/validate")
    def scheduler_goal_stack_validate_route() -> Any:
        """SPEC §25.5: Validate three-layer goal stack hierarchy."""
        enabled, switch = _is_scheduler_enabled("goal_stack")
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal stack validation is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_scheduler_provider()
        res = provider.validate_goal_stack()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/scheduler/goal-stack/orphans")
    def scheduler_goal_stack_orphans_route() -> Any:
        """SPEC §25.5: Identify orphan tasks without valid project/outcome parents."""
        enabled, switch = _is_scheduler_enabled("goal_stack")
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal stack validation is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_scheduler_provider()
        res = provider.validate_goal_stack()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return {"status": "ok", "orphans": res.get("orphans", []), "orphan_count": res.get("orphan_count", 0)}

    @app.post("/scheduler/action-gap/evaluate")
    def scheduler_action_gap_evaluate_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.6: Evaluate action gaps across factions."""
        enabled, switch = _is_scheduler_enabled("action_gap")
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Action gap tracking is disabled",
                    "disabled": switch,
                },
            )
        factions_data = body.get("factions", {})
        provider = _get_scheduler_provider()
        res = provider.evaluate_action_gaps(factions_data=factions_data)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/scheduler/deferral/record")
    def scheduler_deferral_record_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.7: Record task deferral and apply 3/5/8+ escalation thresholds."""
        enabled, switch = _is_scheduler_enabled("deferral")
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Deferral tracking is disabled",
                    "disabled": switch,
                },
            )
        task_id = str(body.get("task_id", ""))
        reason = str(body.get("reason", ""))
        provider = _get_scheduler_provider()
        res = provider.record_deferral(task_id=task_id, reason=reason)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/scheduler/deferral/status/{task_id}")
    def scheduler_deferral_status_route(task_id: str) -> Any:
        """SPEC §25.7: Retrieve deferral history and status for a task."""
        enabled, switch = _is_scheduler_enabled("deferral")
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Deferral tracking is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_scheduler_provider()
        if hasattr(provider, "deferral_tracker"):
            rec = provider.deferral_tracker.get_record(task_id)
            return {"status": "ok", "record": rec.to_dict()}
        return {"status": "ok", "record": {"task_id": task_id, "deferral_count": 0}}

    @app.post("/scheduler/lag/bonus")
    def scheduler_lag_bonus_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.8: Calculate TWS lag bonus from lag hours."""
        enabled, switch = _is_scheduler_enabled("scheduler")
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Scheduler is disabled",
                    "disabled": switch,
                },
            )
        lag_hours = float(body.get("lag_hours", 0.0))
        provider = _get_scheduler_provider()
        res = provider.compute_lag_bonus(lag_hours=lag_hours)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/scheduler/schedule/generate")
    def scheduler_schedule_generate_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.12: Generate daily dispatch schedule via deterministic 6-step engine."""
        enabled, switch = _is_scheduler_enabled("scheduler")
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Scheduler is disabled",
                    "disabled": switch,
                },
            )
        dcs = float(body.get("dcs", 5.0))
        tasks = body.get("tasks", [])
        enforce_goal_stack = bool(body.get("enforce_goal_stack", True))
        provider = _get_scheduler_provider()
        res = provider.generate_schedule(
            dcs=dcs,
            candidate_tasks=tasks,
            enforce_goal_stack=enforce_goal_stack,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/scheduler/status")
    def scheduler_status_route() -> Any:
        """SPEC §25.5: Get diagnostic status of operating modes & scheduler subsystem."""
        enabled, switch = _is_scheduler_enabled("scheduler")
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Scheduler is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_scheduler_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Emergency Task Injection (F-0111 / US-87 / SPEC §25.9)
    active_registry.register(
        "emergency_task_injection", "default_emergency", DefaultEmergencyTaskProvider
    )
    active_registry.register(
        "emergency", "default_emergency", DefaultEmergencyTaskProvider
    )

    def _is_emergency_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.emergency_task_injection.enabled")
        if v1 is not None and not config.is_enabled("locus.emergency_task_injection.enabled"):
            return False, "locus.emergency_task_injection.enabled"
        v2 = config.get("locus.life_os.emergency.enabled")
        if v2 is not None and not config.is_enabled("locus.life_os.emergency.enabled"):
            return False, "locus.life_os.emergency.enabled"
        if not app.state.registry.is_feature_enabled("emergency_task_injection") and not app.state.registry.is_feature_enabled("emergency"):
            return False, "locus.emergency_task_injection.enabled"
        return True, ""

    def _get_emergency_provider() -> BaseEmergencyTaskProvider:
        if not hasattr(app.state, "emergency_task_provider") or app.state.emergency_task_provider is None:
            res = app.state.registry.get_active_provider(
                "emergency_task_injection", default_name="default_emergency"
            )
            if isinstance(res, BaseEmergencyTaskProvider):
                app.state.emergency_task_provider = res
            elif callable(res):
                app.state.emergency_task_provider = res()
            else:
                app.state.emergency_task_provider = DefaultEmergencyTaskProvider()
        return app.state.emergency_task_provider

    @app.post("/emergency/prioritize")
    def emergency_prioritize_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.9: Prioritize task pool with emergency bypass and faction crisis ordering."""
        enabled, switch = _is_emergency_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Emergency task injection is disabled",
                    "disabled": switch,
                },
            )
        tasks = body.get("tasks", [])
        bypass_tws = body.get("bypass_tws")
        provider = _get_emergency_provider()
        res = provider.prioritize_tasks(tasks=tasks, bypass_tws=bypass_tws)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/emergency/inject")
    def emergency_inject_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.9: Inject emergency task into active schedule timeline."""
        enabled, switch = _is_emergency_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Emergency task injection is disabled",
                    "disabled": switch,
                },
            )
        timeline = body.get("timeline", [])
        task = body.get("task", {})
        at_index = int(body.get("at_index", 0))
        provider = _get_emergency_provider()
        res = provider.inject_task(timeline=timeline, task=task, at_index=at_index)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/emergency/status")
    def emergency_status_route() -> Any:
        """SPEC §25.9: Get status of emergency task injection subsystem."""
        enabled, switch = _is_emergency_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Emergency task injection is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_emergency_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Exhaustion Predictor (F-0112 / US-88 / SPEC §25.10)
    active_registry.register(
        "exhaustion_predictor", "default_exhaustion", DefaultExhaustionPredictorProvider
    )
    active_registry.register(
        "exhaustion", "default_exhaustion", DefaultExhaustionPredictorProvider
    )

    def _is_exhaustion_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.exhaustion_predictor.enabled")
        if v1 is not None and not config.is_enabled("locus.exhaustion_predictor.enabled"):
            return False, "locus.exhaustion_predictor.enabled"
        v2 = config.get("locus.life_os.exhaustion.enabled")
        if v2 is not None and not config.is_enabled("locus.life_os.exhaustion.enabled"):
            return False, "locus.life_os.exhaustion.enabled"
        if not app.state.registry.is_feature_enabled("exhaustion_predictor") and not app.state.registry.is_feature_enabled("exhaustion"):
            return False, "locus.exhaustion_predictor.enabled"
        return True, ""

    def _get_exhaustion_provider() -> BaseExhaustionPredictorProvider:
        if not hasattr(app.state, "exhaustion_predictor_provider") or app.state.exhaustion_predictor_provider is None:
            res = app.state.registry.get_active_provider(
                "exhaustion_predictor", default_name="default_exhaustion"
            )
            if isinstance(res, BaseExhaustionPredictorProvider):
                app.state.exhaustion_predictor_provider = res
            elif callable(res):
                app.state.exhaustion_predictor_provider = res()
            else:
                app.state.exhaustion_predictor_provider = DefaultExhaustionPredictorProvider()
        return app.state.exhaustion_predictor_provider

    @app.post("/exhaustion/predict")
    def exhaustion_predict_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.10: Forecast 24h DCS drop and evaluate pre-emptive survival mode."""
        enabled, switch = _is_exhaustion_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Exhaustion predictor is disabled",
                    "disabled": switch,
                },
            )
        metrics = body.get("metrics", body)
        provider = _get_exhaustion_provider()
        res = provider.predict_exhaustion(metrics=metrics)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/exhaustion/status")
    def exhaustion_status_route() -> Any:
        """SPEC §25.10: Get diagnostic status of exhaustion predictor."""
        enabled, switch = _is_exhaustion_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Exhaustion predictor is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_exhaustion_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Weekly Faction Rebalance (F-0113 / US-89 / SPEC §25.11)
    active_registry.register(
        "weekly_faction_rebalance", "default_rebalance", DefaultWeeklyFactionRebalanceProvider
    )
    active_registry.register(
        "rebalance", "default_rebalance", DefaultWeeklyFactionRebalanceProvider
    )

    def _is_rebalance_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.weekly_faction_rebalance.enabled")
        if v1 is not None and not config.is_enabled("locus.weekly_faction_rebalance.enabled"):
            return False, "locus.weekly_faction_rebalance.enabled"
        v2 = config.get("locus.life_os.rebalance.enabled")
        if v2 is not None and not config.is_enabled("locus.life_os.rebalance.enabled"):
            return False, "locus.life_os.rebalance.enabled"
        if not app.state.registry.is_feature_enabled("weekly_faction_rebalance") and not app.state.registry.is_feature_enabled("rebalance"):
            return False, "locus.weekly_faction_rebalance.enabled"
        return True, ""

    def _get_rebalance_provider() -> BaseWeeklyFactionRebalanceProvider:
        if not hasattr(app.state, "rebalance_provider") or app.state.rebalance_provider is None:
            res = app.state.registry.get_provider(
                "weekly_faction_rebalance", default_name="default_rebalance"
            )
            if isinstance(res, BaseWeeklyFactionRebalanceProvider):
                app.state.rebalance_provider = res
            elif callable(res):
                app.state.rebalance_provider = res()
            else:
                app.state.rebalance_provider = DefaultWeeklyFactionRebalanceProvider()
        return app.state.rebalance_provider

    @app.post("/rebalance/calculate")
    def rebalance_calculate_route(body: Optional[Dict[str, Any]] = None) -> Any:
        """SPEC §25.11: Calculate weekly faction rebalance and adjust weights."""
        enabled, switch = _is_rebalance_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Weekly faction rebalance is disabled",
                    "disabled": switch,
                },
            )
        payload = body or {}
        actual_hours = payload.get("actual_hours")
        base_weights = payload.get("base_weights")
        target_percentages = payload.get("target_percentages")
        correction_factor = payload.get("correction_factor")

        provider = _get_rebalance_provider()
        res = provider.calculate_rebalance(
            actual_hours=actual_hours,
            base_weights=base_weights,
            target_percentages=target_percentages,
            correction_factor=correction_factor,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/rebalance/weights")
    def rebalance_weights_route() -> Any:
        """SPEC §25.11: Retrieve active faction scheduling weights."""
        enabled, switch = _is_rebalance_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Weekly faction rebalance is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_rebalance_provider()
        res = provider.get_active_weights()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/rebalance/duration")
    def rebalance_duration_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.11: Log completed task duration for faction."""
        enabled, switch = _is_rebalance_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Weekly faction rebalance is disabled",
                    "disabled": switch,
                },
            )
        faction = body.get("faction", "Craft/Skills")
        duration_hours = float(body.get("duration_hours", 0.0))
        provider = _get_rebalance_provider()
        res = provider.record_duration(faction=faction, duration_hours=duration_hours)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/rebalance/status")
    def rebalance_status_route() -> Any:
        """SPEC §25.11: Get diagnostic status of weekly faction rebalancer."""
        enabled, switch = _is_rebalance_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Weekly faction rebalance is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_rebalance_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Goal Tracker (3-Layer Stack) & Faction Balancer (F-0057 / US-90 / SPEC §25.12)
    active_registry.register(
        "goal_tracker_3_layer_stack", "default_goal_tracker", DefaultGoalTrackerProvider
    )
    active_registry.register(
        "goal_tracker", "default_goal_tracker", DefaultGoalTrackerProvider
    )

    def _is_goal_tracker_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.goal_tracker_3_layer_stack.enabled")
        if v1 is not None and not config.is_enabled("locus.goal_tracker_3_layer_stack.enabled"):
            return False, "locus.goal_tracker_3_layer_stack.enabled"
        v2 = config.get("locus.life_os.goal_tracker.enabled")
        if v2 is not None and not config.is_enabled("locus.life_os.goal_tracker.enabled"):
            return False, "locus.life_os.goal_tracker.enabled"
        if not app.state.registry.is_feature_enabled("goal_tracker_3_layer_stack") and not app.state.registry.is_feature_enabled("goal_tracker"):
            return False, "locus.goal_tracker_3_layer_stack.enabled"
        return True, ""

    def _get_goal_tracker_provider() -> BaseGoalTrackerProvider:
        if not hasattr(app.state, "goal_tracker_provider") or app.state.goal_tracker_provider is None:
            res = app.state.registry.get_provider(
                "goal_tracker_3_layer_stack", default_name="default_goal_tracker"
            )
            if isinstance(res, BaseGoalTrackerProvider):
                app.state.goal_tracker_provider = res
            elif callable(res):
                app.state.goal_tracker_provider = res()
            else:
                app.state.goal_tracker_provider = DefaultGoalTrackerProvider()
        return app.state.goal_tracker_provider

    @app.post("/goal-tracker/validate")
    def goal_tracker_validate_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.12 Step 6: Validate 3-layer hierarchy (Outcome -> Project -> Task)."""
        enabled, switch = _is_goal_tracker_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal tracker is disabled",
                    "disabled": switch,
                },
            )
        task_id = body.get("task_id", "")
        provider = _get_goal_tracker_provider()
        res = provider.validate_task_hierarchy(task_id=task_id)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/goal-tracker/orphans")
    def goal_tracker_orphans_route() -> Any:
        """SPEC §25.12 Step 6: Detect orphan tasks/projects lacking parents."""
        enabled, switch = _is_goal_tracker_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal tracker is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_goal_tracker_provider()
        res = provider.detect_orphans()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/goal-tracker/balance-check")
    def goal_tracker_balance_check_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.12 Step 4: Evaluate weekly faction distribution report."""
        enabled, switch = _is_goal_tracker_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal tracker is disabled",
                    "disabled": switch,
                },
            )
        allocations = body.get("allocations_minutes", body)
        provider = _get_goal_tracker_provider()
        res = provider.evaluate_faction_balance(allocations_minutes=allocations)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/goal-tracker/assignment-allowed")
    def goal_tracker_assignment_allowed_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.12 Step 4: Check if greedy task assignment complies with faction balance."""
        enabled, switch = _is_goal_tracker_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal tracker is disabled",
                    "disabled": switch,
                },
            )
        cand_faction = body.get("candidate_faction", "Craft")
        proposed_mins = float(body.get("proposed_minutes", 90.0))
        current_allocs = body.get("current_allocations", {})
        waiting_factions = body.get("waiting_factions", [])
        provider = _get_goal_tracker_provider()
        res = provider.check_assignment_allowed(
            candidate_faction=cand_faction,
            proposed_minutes=proposed_mins,
            current_allocations=current_allocs,
            waiting_factions=waiting_factions,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/goal-tracker/status")
    def goal_tracker_status_route() -> Any:
        """SPEC §25.12: Get diagnostic status of goal tracker and faction balancer."""
        enabled, switch = _is_goal_tracker_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal tracker is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_goal_tracker_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Review Cadence System (F-0114 / US-91 / SPEC §25.13)
    active_registry.register(
        "review_cadence_system", "default_review_cadence", DefaultReviewCadenceProvider
    )
    active_registry.register(
        "reviews", "default_review_cadence", DefaultReviewCadenceProvider
    )

    def _is_reviews_enabled() -> tuple[bool, str]:
        v1 = config.get("locus.review_cadence_system.enabled")
        if v1 is not None and not config.is_enabled("locus.review_cadence_system.enabled"):
            return False, "locus.review_cadence_system.enabled"
        v2 = config.get("locus.life_os.reviews.enabled")
        if v2 is not None and not config.is_enabled("locus.life_os.reviews.enabled"):
            return False, "locus.life_os.reviews.enabled"
        if not app.state.registry.is_feature_enabled("review_cadence_system") and not app.state.registry.is_feature_enabled("reviews"):
            return False, "locus.review_cadence_system.enabled"
        return True, ""

    def _get_reviews_provider() -> BaseReviewCadenceProvider:
        if not hasattr(app.state, "reviews_provider") or app.state.reviews_provider is None:
            res = app.state.registry.get_provider(
                "review_cadence_system", default_name="default_review_cadence"
            )
            if isinstance(res, BaseReviewCadenceProvider):
                app.state.reviews_provider = res
            elif callable(res):
                app.state.reviews_provider = res()
            else:
                app.state.reviews_provider = DefaultReviewCadenceProvider()
        return app.state.reviews_provider

    @app.post("/reviews/generate")
    def reviews_generate_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.13: Generate review prompt and briefing for specified cadence."""
        enabled, switch = _is_reviews_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Review cadence system is disabled",
                    "disabled": switch,
                },
            )
        cadence = body.get("cadence", "daily_standup")
        context = body.get("context")
        provider = _get_reviews_provider()
        res = provider.generate_review(cadence=cadence, context=context)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/reviews/scheduled")
    def reviews_scheduled_route() -> Any:
        """SPEC §25.13: List active review cadences and schedules."""
        enabled, switch = _is_reviews_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Review cadence system is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_reviews_provider()
        res = provider.list_cadences()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/reviews/status")
    def reviews_status_route() -> Any:
        """SPEC §25.13: Get diagnostic status of review cadence system."""
        enabled, switch = _is_reviews_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Review cadence system is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_reviews_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # -------------------------------------------------------------------------
    # SPEC §25.14 lines 4897-4909: Goal Stack Enforcement
    # -------------------------------------------------------------------------
    active_registry.register(
        "goal_stack_enforcement", "default_goal_enforcement", DefaultGoalStackEnforcementProvider
    )
    active_registry.register(
        "goal_enforcement", "default_goal_enforcement", DefaultGoalStackEnforcementProvider
    )

    def _is_goal_enforcement_enabled() -> Tuple[bool, str]:
        for switch in (
            "locus.goal_stack_enforcement.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def _get_goal_enforcement_provider() -> BaseGoalStackEnforcementProvider:
        if not hasattr(app.state, "goal_enforcement_provider") or app.state.goal_enforcement_provider is None:
            prov_cls = active_registry.get("goal_stack_enforcement", "default_goal_enforcement")
            if prov_cls:
                app.state.goal_enforcement_provider = prov_cls()
            else:
                app.state.goal_enforcement_provider = DefaultGoalStackEnforcementProvider()
        return app.state.goal_enforcement_provider

    @app.post("/goal-enforcement/enforce-task")
    def goal_enforcement_task_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.14: Enforce task parenting to project (milestone) and outcome (vision)."""
        enabled, switch = _is_goal_enforcement_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal stack enforcement is disabled",
                    "disabled": switch,
                },
            )
        task_id = body.get("task_id", "")
        stack_nodes = body.get("stack_nodes")
        provider = _get_goal_enforcement_provider()
        res = provider.enforce_task(task_id=task_id, stack_nodes=stack_nodes)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/goal-enforcement/enforce-project")
    def goal_enforcement_project_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.14: Enforce project parenting to outcome (vision)."""
        enabled, switch = _is_goal_enforcement_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal stack enforcement is disabled",
                    "disabled": switch,
                },
            )
        project_id = body.get("project_id", "")
        stack_nodes = body.get("stack_nodes")
        provider = _get_goal_enforcement_provider()
        res = provider.enforce_project(project_id=project_id, stack_nodes=stack_nodes)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/goal-enforcement/briefing-orphans")
    def goal_enforcement_briefing_orphans_get_route() -> Any:
        """SPEC §25.14: Surface orphan tasks and projects formatted for morning briefing."""
        enabled, switch = _is_goal_enforcement_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal stack enforcement is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_goal_enforcement_provider()
        res = provider.surface_briefing_orphans()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/goal-enforcement/briefing-orphans")
    def goal_enforcement_briefing_orphans_post_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.14: Surface orphan tasks and projects formatted for morning briefing with custom stack."""
        enabled, switch = _is_goal_enforcement_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal stack enforcement is disabled",
                    "disabled": switch,
                },
            )
        stack_nodes = body.get("stack_nodes")
        provider = _get_goal_enforcement_provider()
        res = provider.surface_briefing_orphans(stack_nodes=stack_nodes)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/goal-enforcement/audit")
    def goal_enforcement_audit_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.14: Audit full stack for orphan tasks and projects."""
        enabled, switch = _is_goal_enforcement_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal stack enforcement is disabled",
                    "disabled": switch,
                },
            )
        stack_nodes = body.get("stack_nodes")
        provider = _get_goal_enforcement_provider()
        res = provider.audit_stack(stack_nodes=stack_nodes)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/goal-enforcement/status")
    def goal_enforcement_status_route() -> Any:
        """SPEC §25.14: Diagnostic status of goal stack enforcement."""
        enabled, switch = _is_goal_enforcement_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Goal stack enforcement is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_goal_enforcement_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # -------------------------------------------------------------------------
    # SPEC §25.15 lines 4910-4922: Cross-Faction Efficiency
    # -------------------------------------------------------------------------
    active_registry.register(
        "cross_faction_efficiency", "default_cross_faction", DefaultCrossFactionEfficiencyProvider
    )
    active_registry.register(
        "cross_faction", "default_cross_faction", DefaultCrossFactionEfficiencyProvider
    )

    def _is_cross_faction_enabled() -> Tuple[bool, str]:
        for switch in (
            "locus.cross_faction_efficiency.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def _get_cross_faction_provider() -> BaseCrossFactionEfficiencyProvider:
        if not hasattr(app.state, "cross_faction_provider") or app.state.cross_faction_provider is None:
            prov_cls = active_registry.get("cross_faction_efficiency", "default_cross_faction")
            if prov_cls:
                app.state.cross_faction_provider = prov_cls()
            else:
                app.state.cross_faction_provider = DefaultCrossFactionEfficiencyProvider()
        return app.state.cross_faction_provider

    @app.post("/cross-faction/split")
    def cross_faction_split_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.15: Calculate weighted primary/secondary split for a task without double-counting."""
        enabled, switch = _is_cross_faction_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Cross-faction efficiency is disabled",
                    "disabled": switch,
                },
            )
        task_id = body.get("task_id", "task")
        duration = float(body.get("duration", 0.0))
        primary_faction = body.get("primary_faction", "Craft")
        secondary_factions = body.get("secondary_factions")
        weights = body.get("weights")
        provider = _get_cross_faction_provider()
        res = provider.calculate_task_split(
            task_id=task_id,
            duration=duration,
            primary_faction=primary_faction,
            secondary_factions=secondary_factions,
            custom_weights=weights,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/cross-faction/aggregate")
    def cross_faction_aggregate_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.15: Aggregate multiple task durations applying cross-faction efficiency."""
        enabled, switch = _is_cross_faction_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Cross-faction efficiency is disabled",
                    "disabled": switch,
                },
            )
        tasks = body.get("tasks", [])
        provider = _get_cross_faction_provider()
        res = provider.aggregate_tasks(tasks=tasks)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/cross-faction/status")
    def cross_faction_status_route() -> Any:
        """SPEC §25.15: Diagnostic status of cross-faction efficiency."""
        enabled, switch = _is_cross_faction_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Cross-faction efficiency is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_cross_faction_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    active_registry.register(
        "four_level_emergency_protocol", "default_emergency_protocol", DefaultFourLevelEmergencyProtocolProvider
    )
    active_registry.register(
        "emergency_protocol", "default_emergency_protocol", DefaultFourLevelEmergencyProtocolProvider
    )

    def _is_emergency_protocol_enabled() -> Tuple[bool, str]:
        switch = "locus.four_level_emergency_protocol.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_emergency_protocol_provider() -> BaseFourLevelEmergencyProtocolProvider:
        if not hasattr(app.state, "emergency_protocol_provider") or app.state.emergency_protocol_provider is None:
            prov_cls = active_registry.get("four_level_emergency_protocol", "default_emergency_protocol")
            if prov_cls:
                app.state.emergency_protocol_provider = prov_cls()
            else:
                app.state.emergency_protocol_provider = DefaultFourLevelEmergencyProtocolProvider()
        return app.state.emergency_protocol_provider

    @app.post("/emergency-protocol/evaluate")
    def emergency_protocol_evaluate_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.16: Evaluate disruption and return emergency level recommendation."""
        enabled, switch = _is_emergency_protocol_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Four-level emergency protocol is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_emergency_protocol_provider()
        res = provider.evaluate_situation(
            disruption_hours=float(body.get("disruption_hours", 0.0)),
            disruption_days=int(body.get("disruption_days", 0)),
            is_life_event=bool(body.get("is_life_event", False)),
            trigger_reason=str(body.get("trigger_reason", "")),
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/emergency-protocol/activate")
    def emergency_protocol_activate_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.16: Activate emergency protocol level."""
        enabled, switch = _is_emergency_protocol_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Four-level emergency protocol is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_emergency_protocol_provider()
        try:
            res = provider.activate_protocol(
                level=int(body.get("level", 1)),
                reason=str(body.get("reason", "")),
            )
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/emergency-protocol/deactivate")
    def emergency_protocol_deactivate_route() -> Any:
        """SPEC §25.16: Deactivate emergency protocol and restore standard operation."""
        enabled, switch = _is_emergency_protocol_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Four-level emergency protocol is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_emergency_protocol_provider()
        res = provider.deactivate_protocol()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/emergency-protocol/apply-overrides")
    def emergency_protocol_apply_overrides_route(body: Dict[str, Any]) -> Any:
        """SPEC §25.16: Apply scheduling overrides based on active or specified level."""
        enabled, switch = _is_emergency_protocol_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Four-level emergency protocol is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_emergency_protocol_provider()
        tasks = body.get("tasks", [])
        lvl = body.get("level")
        level_int = int(lvl) if lvl is not None else None
        res = provider.apply_scheduling_overrides(tasks=tasks, level=level_int)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/emergency-protocol/status")
    def emergency_protocol_status_route() -> Any:
        """SPEC §25.16: Diagnostic status of four-level emergency protocol."""
        enabled, switch = _is_emergency_protocol_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Four-level emergency protocol is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_emergency_protocol_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    active_registry.register(
        "pageindex_retrieval", "default_pageindex", DefaultPageIndexRetrievalProvider
    )
    active_registry.register(
        "pageindex", "default_pageindex", DefaultPageIndexRetrievalProvider
    )

    def _is_pageindex_enabled() -> Tuple[bool, str]:
        switch = "locus.pageindex_retrieval.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_pageindex_provider() -> BasePageIndexRetrievalProvider:
        if not hasattr(app.state, "pageindex_provider") or app.state.pageindex_provider is None:
            prov_cls = active_registry.get("pageindex_retrieval", "default_pageindex")
            if prov_cls:
                app.state.pageindex_provider = prov_cls()
            else:
                app.state.pageindex_provider = DefaultPageIndexRetrievalProvider()
        return app.state.pageindex_provider

    @app.post("/pageindex/build-tree")
    def pageindex_build_tree_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.1: Build hierarchical PageIndex tree over markdown content."""
        enabled, switch = _is_pageindex_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "PageIndex retrieval is disabled",
                    "disabled": switch,
                },
            )
        content = body.get("content", "")
        doc_name = body.get("doc_name", "document.md")
        min_node_token = int(body.get("min_node_token", 50))
        summary_token_threshold = int(body.get("summary_token_threshold", 200))
        provider = _get_pageindex_provider()
        res = provider.build_tree(
            content=content,
            doc_name=doc_name,
            min_node_token=min_node_token,
            summary_token_threshold=summary_token_threshold,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/pageindex/retrieve")
    def pageindex_retrieve_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.1: Perform vectorless reasoning tree search."""
        enabled, switch = _is_pageindex_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "PageIndex retrieval is disabled",
                    "disabled": switch,
                },
            )
        query = body.get("query", "")
        doc_name = body.get("doc_name")
        tree_data = body.get("tree_data")
        provider = _get_pageindex_provider()
        res = provider.retrieve(
            query=query,
            doc_name=doc_name,
            tree_data=tree_data,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/pageindex/status")
    def pageindex_status_route() -> Any:
        """SPEC §27.1: Diagnostic status of PageIndex retrieval."""
        enabled, switch = _is_pageindex_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "PageIndex retrieval is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_pageindex_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    active_registry.register(
        "locus_shorthand_4_text_compressor", "default_shorthand", DefaultShorthandCompressorProvider
    )
    active_registry.register(
        "shorthand_compressor", "default_shorthand", DefaultShorthandCompressorProvider
    )

    def _is_shorthand_compressor_enabled() -> Tuple[bool, str]:
        switch = "locus.locus_shorthand_4_text_compressor.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_shorthand_compressor_provider() -> BaseShorthandCompressorProvider:
        if not hasattr(app.state, "shorthand_compressor_provider") or app.state.shorthand_compressor_provider is None:
            prov_cls = active_registry.get("locus_shorthand_4_text_compressor", "default_shorthand")
            if prov_cls:
                app.state.shorthand_compressor_provider = prov_cls()
            else:
                app.state.shorthand_compressor_provider = DefaultShorthandCompressorProvider()
        return app.state.shorthand_compressor_provider

    @app.post("/compression/shorthand/compress")
    def shorthand_compress_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.3: Compress text using LOCUS_SHORTHAND pipeline."""
        enabled, switch = _is_shorthand_compressor_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                    "disabled": switch,
                },
            )
        text = str(body.get("text", ""))
        strip_articles = bool(body.get("strip_articles", True))
        provider = _get_shorthand_compressor_provider()
        res = provider.compress(text=text, strip_articles=strip_articles)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/compression/shorthand/decompress")
    def shorthand_decompress_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.3: Decompress shorthand tokens back to readable words."""
        enabled, switch = _is_shorthand_compressor_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                    "disabled": switch,
                },
            )
        text = str(body.get("text", ""))
        provider = _get_shorthand_compressor_provider()
        res = provider.decompress(text=text)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/compression/shorthand/compress-event")
    def shorthand_compress_event_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.3: Compress behavioral event into shorthand schema."""
        enabled, switch = _is_shorthand_compressor_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                    "disabled": switch,
                },
            )
        event_type = str(body.get("event_type", "generic"))
        data = body.get("data", {})
        provider = _get_shorthand_compressor_provider()
        res = provider.compress_event(event_type=event_type, data=data)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/compression/shorthand/decoder")
    def shorthand_decoder_route() -> Any:
        """SPEC §27.3: Retrieve decoder dictionary for system prompt prepending."""
        enabled, switch = _is_shorthand_compressor_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_shorthand_compressor_provider()
        res = provider.get_decoder_dictionary()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/compression/shorthand/status")
    def shorthand_status_route() -> Any:
        """SPEC §27.3: Diagnostic status of LOCUS_SHORTHAND compressor."""
        enabled, switch = _is_shorthand_compressor_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_shorthand_compressor_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    active_registry.register(
        "3_level_tag_hierarchy_semantic_indexing", "default_tag_hierarchy", DefaultTagHierarchyProvider
    )
    active_registry.register(
        "tag_hierarchy", "default_tag_hierarchy", DefaultTagHierarchyProvider
    )

    def _is_tag_hierarchy_enabled() -> Tuple[bool, str]:
        switch = "locus.3_level_tag_hierarchy_semantic_indexing.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_tag_hierarchy_provider() -> BaseTagHierarchyProvider:
        if not hasattr(app.state, "tag_hierarchy_provider") or app.state.tag_hierarchy_provider is None:
            prov_cls = active_registry.get("3_level_tag_hierarchy_semantic_indexing", "default_tag_hierarchy")
            if prov_cls:
                app.state.tag_hierarchy_provider = prov_cls()
            else:
                app.state.tag_hierarchy_provider = DefaultTagHierarchyProvider()
        return app.state.tag_hierarchy_provider

    @app.post("/vault/tags/normalize")
    def vault_tags_normalize_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.4: Normalize tags to 3-level taxonomy."""
        enabled, switch = _is_tag_hierarchy_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "3-Level tag hierarchy is disabled",
                    "disabled": switch,
                },
            )
        tags = body.get("tags", [])
        provider = _get_tag_hierarchy_provider()
        res = provider.normalize_tags(tags=tags)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/vault/tags/validate")
    def vault_tags_validate_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.4: Validate single tag against 3-level hierarchy."""
        enabled, switch = _is_tag_hierarchy_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "3-Level tag hierarchy is disabled",
                    "disabled": switch,
                },
            )
        tag = str(body.get("tag", ""))
        provider = _get_tag_hierarchy_provider()
        res = provider.validate_tag(tag=tag)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/vault/tags/index")
    def vault_tags_index_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.4: Index note tags and calculate domain distribution."""
        enabled, switch = _is_tag_hierarchy_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "3-Level tag hierarchy is disabled",
                    "disabled": switch,
                },
            )
        note_path = str(body.get("note_path", "note.md"))
        tags = body.get("tags", [])
        provider = _get_tag_hierarchy_provider()
        res = provider.index_note(note_path=note_path, tags=tags)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/vault/tags/status")
    def vault_tags_status_route() -> Any:
        """SPEC §27.4: Diagnostic status of tag hierarchy manager."""
        enabled, switch = _is_tag_hierarchy_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "3-Level tag hierarchy is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_tag_hierarchy_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    active_registry.register(
        "rough_note_parser", "default_rough_note_parser", DefaultRoughNoteParserProvider
    )

    def _is_rough_note_parser_enabled() -> Tuple[bool, str]:
        switch = "locus.rough_note_parser.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_rough_note_parser_provider() -> BaseRoughNoteParserProvider:
        if not hasattr(app.state, "rough_note_parser_provider") or app.state.rough_note_parser_provider is None:
            prov_cls = active_registry.get("rough_note_parser", "default_rough_note_parser")
            if prov_cls:
                app.state.rough_note_parser_provider = prov_cls()
            else:
                app.state.rough_note_parser_provider = DefaultRoughNoteParserProvider()
        return app.state.rough_note_parser_provider

    @app.post("/ingestion/rough-note/parse")
    def ingestion_rough_note_parse_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.5: Parse raw thought stream and generate structured Obsidian note."""
        enabled, switch = _is_rough_note_parser_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Rough note parser is disabled",
                    "disabled": switch,
                },
            )
        raw_text = str(body.get("raw_text", ""))
        source = body.get("source")
        save_to_vault = bool(body.get("save_to_vault", True))
        vault_root = body.get("vault_root")
        provider = _get_rough_note_parser_provider()
        res = provider.parse_note(
            raw_text=raw_text,
            source=source,
            save_to_vault=save_to_vault,
            vault_root=vault_root,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        elif res.get("status_code") == 400:
            return JSONResponse(status_code=400, content=res)
        return res

    @app.get("/ingestion/rough-note/status")
    def ingestion_rough_note_status_route() -> Any:
        """SPEC §27.5: Diagnostic status of rough note parser."""
        enabled, switch = _is_rough_note_parser_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Rough note parser is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_rough_note_parser_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    active_registry.register(
        "link_dump_logger", "default_link_dump_logger", DefaultLinkDumpLoggerProvider
    )

    def _is_link_dump_logger_enabled() -> Tuple[bool, str]:
        switch = "locus.link_dump_logger.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_link_dump_logger_provider() -> BaseLinkDumpLoggerProvider:
        if not hasattr(app.state, "link_dump_logger_provider") or app.state.link_dump_logger_provider is None:
            prov_cls = active_registry.get("link_dump_logger", "default_link_dump_logger")
            if prov_cls:
                app.state.link_dump_logger_provider = prov_cls()
            else:
                app.state.link_dump_logger_provider = DefaultLinkDumpLoggerProvider()
        return app.state.link_dump_logger_provider

    @app.post("/ingestion/link/process")
    def ingestion_link_process_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.6: Scrape URL, synthesize 3 takeaways, and archive to vault."""
        enabled, switch = _is_link_dump_logger_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Link dump logger is disabled",
                    "disabled": switch,
                },
            )
        url = str(body.get("url", ""))
        user_commentary = str(body.get("user_commentary", ""))
        html_content = body.get("html_content")
        save_to_vault = bool(body.get("save_to_vault", True))
        vault_root = body.get("vault_root")
        provider = _get_link_dump_logger_provider()
        res = provider.process_link(
            url=url,
            user_commentary=user_commentary,
            html_content=html_content,
            save_to_vault=save_to_vault,
            vault_root=vault_root,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        elif res.get("status_code") == 400:
            return JSONResponse(status_code=400, content=res)
        return res

    @app.get("/ingestion/link/status")
    def ingestion_link_status_route() -> Any:
        """SPEC §27.6: Diagnostic status of link dump logger."""
        enabled, switch = _is_link_dump_logger_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Link dump logger is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_link_dump_logger_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    active_registry.register(
        "excalidraw_builder", "default_diagram_generator", DefaultDiagramGeneratorProvider
    )
    active_registry.register(
        "diagram_generator", "default_diagram_generator", DefaultDiagramGeneratorProvider
    )

    def _is_diagram_generator_enabled() -> Tuple[bool, str]:
        switch = "locus.tools.excalidraw.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_diagram_generator_provider() -> BaseDiagramGeneratorProvider:
        if not hasattr(app.state, "diagram_generator_provider") or app.state.diagram_generator_provider is None:
            prov_cls = active_registry.get("excalidraw_builder", "default_diagram_generator")
            if prov_cls:
                app.state.diagram_generator_provider = prov_cls()
            else:
                app.state.diagram_generator_provider = DefaultDiagramGeneratorProvider()
        return app.state.diagram_generator_provider

    @app.post("/diagrams/excalidraw/generate")
    def diagrams_excalidraw_generate_route(body: Dict[str, Any]) -> Any:
        """SPEC §27.7: Generate Excalidraw architecture diagram and save to vault."""
        enabled, switch = _is_diagram_generator_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Excalidraw diagram generator is disabled",
                    "disabled": switch,
                },
            )
        system_spec = str(body.get("system_spec", ""))
        output_filename = str(body.get("output_filename", "architecture_diagram"))
        save_to_vault = bool(body.get("save_to_vault", True))
        vault_root = body.get("vault_root")
        provider = _get_diagram_generator_provider()
        res = provider.generate_diagram(
            system_spec=system_spec,
            output_filename=output_filename,
            save_to_vault=save_to_vault,
            vault_root=vault_root,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        elif res.get("status_code") == 400:
            return JSONResponse(status_code=400, content=res)
        return res

    @app.get("/diagrams/excalidraw/status")
    def diagrams_excalidraw_status_route() -> Any:
        """SPEC §27.7: Diagnostic status of Excalidraw diagram generator."""
        enabled, switch = _is_diagram_generator_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Excalidraw diagram generator is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_diagram_generator_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    active_registry.register(
        "dual_interface_checkins", "default_dual_interface", DefaultDualInterfaceProvider
    )
    active_registry.register(
        "dual_interface", "default_dual_interface", DefaultDualInterfaceProvider
    )

    def _is_dual_interface_enabled() -> Tuple[bool, str]:
        switch = "locus.dual_interface_checkins.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_dual_interface_provider() -> BaseDualInterfaceProvider:
        if not hasattr(app.state, "dual_interface_provider") or app.state.dual_interface_provider is None:
            prov_cls = active_registry.get("dual_interface_checkins", "default_dual_interface")
            if prov_cls:
                app.state.dual_interface_provider = prov_cls()
            else:
                app.state.dual_interface_provider = DefaultDualInterfaceProvider()
        return app.state.dual_interface_provider

    @app.post("/gateway/interface/message")
    def gateway_interface_message_route(body: Dict[str, Any]) -> Any:
        """SPEC §28.1: Route TUI/Telegram message into unified session state."""
        enabled, switch = _is_dual_interface_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Dual interface / check-ins is disabled",
                    "disabled": switch,
                },
            )
        channel = str(body.get("channel", "tui"))
        session_id = str(body.get("session_id", "default_session"))
        content = str(body.get("content", ""))
        sender = str(body.get("sender", "user"))
        provider = _get_dual_interface_provider()
        res = provider.route_interface_message(channel, session_id, content, sender)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/gateway/checkin/keyboard")
    def gateway_checkin_keyboard_route(slot: str = "07:30_MORNING") -> Any:
        """SPEC §28.2: Get 4 daily check-in inline keyboard."""
        enabled, switch = _is_dual_interface_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Dual interface / check-ins is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_dual_interface_provider()
        res = provider.get_checkin_keyboard(slot=slot)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.post("/gateway/checkin/submit")
    def gateway_checkin_submit_route(body: Dict[str, Any]) -> Any:
        """SPEC §28.2: Submit structured check-in and calculate DCS operating mode."""
        enabled, switch = _is_dual_interface_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Dual interface / check-ins is disabled",
                    "disabled": switch,
                },
            )
        slot = str(body.get("slot", "07:30_MORNING"))
        energy = float(body.get("energy", 7.0))
        stress = float(body.get("stress", 3.0))
        mood = float(body.get("mood", 0.5))
        readiness = str(body.get("readiness", "Ready to go!"))
        notes = str(body.get("notes", ""))
        provider = _get_dual_interface_provider()
        res = provider.submit_checkin(
            slot=slot,
            energy=energy,
            stress=stress,
            mood=mood,
            readiness=readiness,
            notes=notes,
        )
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/gateway/cost/budget")
    def gateway_cost_budget_route() -> Any:
        """SPEC §28.3: Retrieve zero-cost constraint status and budget checks."""
        enabled, switch = _is_dual_interface_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Dual interface / check-ins is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_dual_interface_provider()
        res = provider.get_budget_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/gateway/interface/status")
    def gateway_interface_status_route() -> Any:
        """SPEC §28.1-28.6: Diagnostic status of dual-interface manager."""
        enabled, switch = _is_dual_interface_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Dual interface / check-ins is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_dual_interface_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Error Classifier routes (SPEC §29.1 / F-0065 / US-102)
    active_registry.register(
        "error_classifier", "default_error_classifier", DefaultErrorClassifierProvider
    )

    def _is_error_classifier_enabled() -> Tuple[bool, str]:
        switch = "locus.error_classifier.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_error_classifier_provider() -> BaseErrorClassifierProvider:
        if not hasattr(app.state, "error_classifier_provider") or app.state.error_classifier_provider is None:
            prov_cls = active_registry.get("error_classifier", "default_error_classifier")
            if prov_cls:
                app.state.error_classifier_provider = prov_cls()
            else:
                app.state.error_classifier_provider = DefaultErrorClassifierProvider()
        return app.state.error_classifier_provider

    @app.post("/diagnostics/error/classify")
    def diagnostics_error_classify_route(body: Dict[str, Any]) -> Any:
        """SPEC §29.1: Classify error into 7-category taxonomy and recovery strategy."""
        enabled, switch = _is_error_classifier_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Error classifier is disabled",
                    "disabled": switch,
                },
            )
        error_payload = body.get("error", body)
        provider = _get_error_classifier_provider()
        res = provider.classify_error(error_payload)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/diagnostics/error/taxonomy")
    def diagnostics_error_taxonomy_route() -> Any:
        """SPEC §29.1: Retrieve 7-category error taxonomy and recovery strategy definitions."""
        enabled, switch = _is_error_classifier_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Error classifier is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_error_classifier_provider()
        res = provider.get_taxonomy()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/diagnostics/error/status")
    def diagnostics_error_status_route() -> Any:
        """SPEC §29.1: Error classifier diagnostic and operational status."""
        enabled, switch = _is_error_classifier_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Error classifier is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_error_classifier_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    # Auxiliary LLM Client routes (SPEC §29.2 / F-0124 / US-103)
    active_registry.register(
        "auxiliary_llm", "default_auxiliary_llm", DefaultAuxiliaryLLMProvider
    )

    def _is_auxiliary_llm_enabled() -> Tuple[bool, str]:
        switch = "locus.auxiliary_llm_client.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _get_auxiliary_llm_provider() -> BaseAuxiliaryLLMProvider:
        if not hasattr(app.state, "auxiliary_llm_provider") or app.state.auxiliary_llm_provider is None:
            prov_cls = active_registry.get("auxiliary_llm", "default_auxiliary_llm")
            if prov_cls:
                app.state.auxiliary_llm_provider = prov_cls()
            else:
                app.state.auxiliary_llm_provider = DefaultAuxiliaryLLMProvider()
        return app.state.auxiliary_llm_provider

    @app.post("/auxiliary/llm/generate")
    def auxiliary_llm_generate_route(body: Dict[str, Any]) -> Any:
        """SPEC §29.2: Execute background generation with auxiliary client."""
        enabled, switch = _is_auxiliary_llm_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Auxiliary LLM client is disabled",
                    "disabled": switch,
                },
            )
        prompt = str(body.get("prompt", ""))
        system_prompt = body.get("system_prompt")
        model = body.get("model")
        provider = _get_auxiliary_llm_provider()
        res = provider.generate(prompt=prompt, system_prompt=system_prompt, model=model)
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/auxiliary/llm/model")
    def auxiliary_llm_model_route() -> Any:
        """SPEC §29.2: Get active auxiliary model configuration."""
        enabled, switch = _is_auxiliary_llm_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Auxiliary LLM client is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_auxiliary_llm_provider()
        res = provider.get_model_info()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

    @app.get("/auxiliary/llm/status")
    def auxiliary_llm_status_route() -> Any:
        """SPEC §29.2: Auxiliary LLM client operational status."""
        enabled, switch = _is_auxiliary_llm_enabled()
        if not enabled:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Auxiliary LLM client is disabled",
                    "disabled": switch,
                },
            )
        provider = _get_auxiliary_llm_provider()
        res = provider.get_status()
        if res.get("status_code") == 503:
            return JSONResponse(status_code=503, content=res)
        return res

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
