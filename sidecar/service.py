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
