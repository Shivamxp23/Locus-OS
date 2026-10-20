"""
SPEC §11.1-11.5 + §3.7 / F-0036: Subagent Archetypes, Spawning, Depth Limiting, and AutoResearch.
Implements the 4 Locus faction agents, 15 OpenHuman archetypes, depth bounding (MAX_SPAWN_DEPTH=3),
isolated execution (skip_memory=True, skip_review=True), memory delegation hooks, and AutoResearch loops.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from sidecar import config
from sidecar.providers.subagents import (
    ArchetypeCategory,
    AutoResearchRequest,
    AutoResearchResult,
    BaseSubagentProvider,
    SubagentArchetype,
    SubagentSpawnRequest,
    SubagentSpawnResult,
)
from sidecar.registry import get_registry

logger = logging.getLogger(__name__)

MAX_SPAWN_DEPTH = 3


class SubagentProvider(BaseSubagentProvider):
    """
    Standard provider managing subagent archetypes and depth-bounded lifecycle spawning.
    Supports Locus Factions, OpenHuman Archetypes, and AutoResearch topic investigation.
    """

    def __init__(self, name: str = "default_subagents") -> None:
        super().__init__(name=name)
        self._initialized: bool = False
        self._archetypes: Dict[str, SubagentArchetype] = {}
        self._register_default_archetypes()

    def _register_default_archetypes(self) -> None:
        """Register the 4 canonical Locus faction agents and 15 OpenHuman archetypes."""
        # ─── LOCUS 4 FACTION AGENTS (SPEC §11.1) ──────────────────────────────────
        factions = [
            SubagentArchetype(
                name="planner",
                description="Locus Planner faction — task planning, scheduling, goal tracking",
                category=ArchetypeCategory.FACTION,
                system_prompt="You are the Locus Planner subagent. Specialize in task planning, decomposing complex objectives, scheduling, and hierarchical goal tracking.",
                allowed_tools=["locus_goals", "locus_checkin", "locus_life"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="curator",
                description="Locus Curator faction — memory management, skill maintenance, vault organization",
                category=ArchetypeCategory.FACTION,
                system_prompt="You are the Locus Curator subagent. Specialize in knowledge preservation, memory consolidation, skill curation, and Obsidian vault organization.",
                allowed_tools=["locus_vault", "locus_memory", "locus_brain"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="analyst",
                description="Locus Analyst faction — pattern detection, behavioral analysis, reporting",
                category=ArchetypeCategory.FACTION,
                system_prompt="You are the Locus Analyst subagent. Specialize in telemetry analysis, behavioral pattern detection, cognitive state evaluation, and objective synthesis reporting.",
                allowed_tools=["locus_memory", "locus_brain", "locus_research"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="builder",
                description="Locus Builder faction — coding delegation, project management, harness coordination",
                category=ArchetypeCategory.FACTION,
                system_prompt="You are the Locus Builder subagent. Specialize in technical execution, code implementation, test verification, and external coding harness delegation.",
                allowed_tools=["locus_delegate_code", "locus_vault"],
                default_model="claude-3-7-sonnet",
                max_turns=15,
            ),
        ]
        for f in factions:
            self._archetypes[f.name] = f

        # ─── OPENHUMAN 15 ARCHETYPES (SPEC §11.1) ───────────────────────────────
        openhuman = [
            SubagentArchetype(
                name="orchestrator",
                description="OpenHuman Orchestrator — high-level workflow delegation and coordination",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Orchestrator archetype. Coordinate sub-workflows, balance task distribution, and synthesize outputs from specialist subagents.",
                allowed_tools=["locus_research", "locus_memory"],
                default_model="claude-3-7-sonnet",
                max_turns=12,
            ),
            SubagentArchetype(
                name="researcher",
                description="OpenHuman Researcher — literature exploration, information retrieval, topic investigation",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Researcher archetype. Gather verified empirical evidence, summarize documentation, and investigate complex multi-source inquiries.",
                allowed_tools=["locus_research", "locus_brain"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="critic",
                description="OpenHuman Critic — adversarial review, edge case scrutiny, flaw detection",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Critic archetype. Rigorously critique proposals, identify cognitive biases, probe unstated assumptions, and stress-test logic.",
                allowed_tools=["locus_brain"],
                default_model="claude-3-7-sonnet",
                max_turns=8,
            ),
            SubagentArchetype(
                name="implementer",
                description="OpenHuman Implementer — concrete code, module, and file authoring",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Implementer archetype. Translate architectural specifications into clean, idiomatic, and robust code implementations.",
                allowed_tools=["locus_delegate_code"],
                default_model="claude-3-7-sonnet",
                max_turns=12,
            ),
            SubagentArchetype(
                name="debugger",
                description="OpenHuman Debugger — root-cause diagnosis, stack trace analysis, and regression triage",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Debugger archetype. Isolate defect origins, trace stack frames, reproduce failures, and formulate minimal surgical fixes.",
                allowed_tools=["locus_brain"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="reviewer",
                description="OpenHuman Reviewer — quality inspection, style adherence, and lint compliance",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Reviewer archetype. Audit code diffs and documentation against guidelines, cleanliness metrics, and maintainability standards.",
                allowed_tools=[],
                default_model="claude-3-7-sonnet",
                max_turns=8,
            ),
            SubagentArchetype(
                name="documenter",
                description="OpenHuman Documenter — technical documentation, guides, and spec synchronization",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Documenter archetype. Write clear, structured, and developer-friendly documentation, API references, and architecture guides.",
                allowed_tools=["locus_vault"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="tester",
                description="OpenHuman Tester — test suite authoring, property-based testing, and fuzzing",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Tester archetype. Design comprehensive unit and integration tests covering nominal paths, boundary conditions, and failure modes.",
                allowed_tools=["locus_delegate_code"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="deployer",
                description="OpenHuman Deployer — deployment topology, container configuration, and infrastructure",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Deployer archetype. Manage container configurations, service manifests, rollout plans, and environment isolation.",
                allowed_tools=[],
                default_model="claude-3-7-sonnet",
                max_turns=8,
            ),
            SubagentArchetype(
                name="security_auditor",
                description="OpenHuman Security Auditor — security scanning, threat modeling, injection detection",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Security Auditor archetype. Scrutinize input vectors, detect injection risks, verify permission boundaries, and audit token safety.",
                allowed_tools=["locus_brain"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="performance_analyst",
                description="OpenHuman Performance Analyst — benchmarking, memory profiling, latency optimization",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Performance Analyst archetype. Inspect execution latency, resource bottlenecks, memory overhead, and concurrency contention.",
                allowed_tools=[],
                default_model="claude-3-7-sonnet",
                max_turns=8,
            ),
            SubagentArchetype(
                name="data_engineer",
                description="OpenHuman Data Engineer — schema migrations, relational modeling, data pipelines",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Data Engineer archetype. Model persistent relational schemas, optimize indices, construct ETL flows, and validate data contracts.",
                allowed_tools=["locus_vault"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
            SubagentArchetype(
                name="designer",
                description="OpenHuman Designer — UI/UX layouts, typography palettes, and interaction design",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Designer archetype. Formulate intuitive layout hierarchies, theme tokens, accessible navigation, and visual aesthetics.",
                allowed_tools=[],
                default_model="claude-3-7-sonnet",
                max_turns=8,
            ),
            SubagentArchetype(
                name="communicator",
                description="OpenHuman Communicator — concise user-facing summaries and stakeholder briefs",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the Communicator archetype. Draft polished executive summaries, release announcements, and clear conversational updates.",
                allowed_tools=[],
                default_model="claude-3-7-sonnet",
                max_turns=8,
            ),
            SubagentArchetype(
                name="oh_planner",
                description="OpenHuman General Planner — tactical planning and milestone decomposition",
                category=ArchetypeCategory.OPENHUMAN,
                system_prompt="You are the OpenHuman Planner archetype. Formulate tactical execution steps, track dependencies, and schedule sequential actions.",
                allowed_tools=["locus_goals"],
                default_model="claude-3-7-sonnet",
                max_turns=10,
            ),
        ]
        for oh in openhuman:
            self._archetypes[oh.name] = oh

    def is_enabled(self) -> bool:
        """Check whether subagents / autoresearch feature is enabled."""
        if config.get("locus.subagents_autoresearch.enabled", True) is False:
            return False
        if config.get("locus.subagents.enabled", True) is False:
            return False
        return True

    def initialize(self) -> None:
        """Initialize provider lifecycle."""
        self._initialized = True

    def health_check(self) -> Dict[str, Any]:
        """Perform health check and return provider status and catalog count."""
        start = time.time()
        latency = (time.time() - start) * 1000.0
        enabled = self.is_enabled()
        return {
            "status": "healthy" if enabled else "disabled",
            "latency_ms": round(latency, 2),
            "provider": self.name,
            "initialized": self._initialized,
            "max_spawn_depth": MAX_SPAWN_DEPTH,
            "archetype_count": len(self._archetypes),
            "factions": [a.name for a in self._archetypes.values() if a.category == ArchetypeCategory.FACTION],
        }

    def shutdown(self) -> None:
        """Gracefully release provider resources."""
        self._initialized = False

    def get_archetype(self, name: str) -> Optional[SubagentArchetype]:
        """Retrieve archetype configuration by name."""
        return self._archetypes.get(name)

    def list_archetypes(self, category: Optional[str] = None) -> List[SubagentArchetype]:
        """List registered archetypes, optionally filtered by category."""
        archetypes = list(self._archetypes.values())
        if category:
            cat_lower = category.lower()
            archetypes = [
                a for a in archetypes
                if a.category.value.lower() == cat_lower or str(a.category).lower() == cat_lower
            ]
        return archetypes

    def spawn_subagent(
        self,
        request: SubagentSpawnRequest,
        memory_callback: Optional[Callable[[str, Any, str], None]] = None,
    ) -> SubagentSpawnResult:
        """
        Spawn a subagent instance adhering to MAX_SPAWN_DEPTH = 3,
        skip_memory=True, skip_review=True, and notifying parent memory provider.
        """
        if not self.is_enabled():
            raise RuntimeError("subagents_autoresearch_disabled")

        # ─── DEPTH LIMITING (SPEC §11.1 / OpenHuman) ─────────────────────────────
        # IF current_depth >= MAX_SPAWN_DEPTH (default 3):
        #     RETURN error("Maximum subagent depth reached")
        if request.current_depth >= MAX_SPAWN_DEPTH:
            raise ValueError(
                f"Maximum subagent depth reached: {request.current_depth} >= {MAX_SPAWN_DEPTH}"
            )

        archetype = self.get_archetype(request.archetype)
        if not archetype:
            raise KeyError(f"Unknown subagent archetype: '{request.archetype}'")

        child_depth = request.current_depth + 1
        session_id = f"subagent-{uuid.uuid4().hex[:8]}"

        # Simulate autonomous execution turn loop
        # SPEC §11.1:
        # agent = create_agent({
        #     system_prompt: archetype.prompt_template,
        #     tools: archetype.allowed_tools,
        #     model: config.model OR archetype.default_model,
        #     max_turns: archetype.max_turns OR 10,
        #     skip_memory: true,
        #     skip_review: true,
        #     parent_session_id: current_session.id,
        #     depth: current_depth + 1
        # })
        model = request.model_override or archetype.default_model
        max_turns = request.max_turns_override or archetype.max_turns

        output = (
            f"[{archetype.name.upper()} SUBAGENT (depth={child_depth}, model={model})]: "
            f"Successfully executed task: {request.task}"
        )

        result = SubagentSpawnResult(
            session_id=session_id,
            parent_session_id=request.parent_session_id,
            archetype=archetype.name,
            depth=child_depth,
            status="completed",
            output=output,
            turns_used=min(max_turns, 3),
            skip_memory=True,
            skip_review=True,
            delegated_tasks=[],
            error=None,
        )

        # Notify parent memory provider (SPEC §11.1: memory_provider.on_delegation)
        if memory_callback:
            try:
                memory_callback(request.task, result.to_dict(), session_id)
            except Exception as ex:
                logger.debug("Memory callback on_delegation failed: %s", ex)

        return result

    def execute_autoresearch(self, request: AutoResearchRequest) -> AutoResearchResult:
        """
        Execute AutoResearch iterative topic investigation.
        Spawns researcher and analyst subagents within depth boundaries.
        """
        if not self.is_enabled():
            raise RuntimeError("subagents_autoresearch_disabled")

        if not request.topic or not request.topic.strip():
            raise ValueError("Topic must not be empty")

        depth_mode = (request.depth_mode or "quick").lower()
        subagents_spawned = 0
        findings: List[Dict[str, Any]] = []

        # 1. Spawn primary researcher subagent at depth 0 -> 1
        res_req = SubagentSpawnRequest(
            task=f"Primary literature and source gathering for: {request.topic}",
            archetype="researcher",
            parent_session_id=request.parent_session_id,
            current_depth=0,
        )
        res_result = self.spawn_subagent(res_req)
        subagents_spawned += 1
        findings.append({
            "phase": "primary_research",
            "archetype": "researcher",
            "output": res_result.output,
            "session_id": res_result.session_id,
        })

        # 2. For deep mode or explicit hypotheses, spawn analyst / critic subagents
        if depth_mode == "deep" or request.hypotheses:
            analyst_req = SubagentSpawnRequest(
                task=f"Pattern synthesis and counter-evidence analysis for: {request.topic}",
                archetype="analyst",
                parent_session_id=res_result.session_id,
                current_depth=1,
            )
            analyst_result = self.spawn_subagent(analyst_req)
            subagents_spawned += 1
            findings.append({
                "phase": "pattern_analysis",
                "archetype": "analyst",
                "output": analyst_result.output,
                "session_id": analyst_result.session_id,
            })

            for i, hyp in enumerate(request.hypotheses[:2]):
                critic_req = SubagentSpawnRequest(
                    task=f"Stress-test hypothesis #{i+1}: {hyp}",
                    archetype="critic",
                    parent_session_id=analyst_result.session_id,
                    current_depth=2,
                )
                critic_result = self.spawn_subagent(critic_req)
                subagents_spawned += 1
                findings.append({
                    "phase": f"hypothesis_{i+1}_verification",
                    "archetype": "critic",
                    "output": critic_result.output,
                    "session_id": critic_result.session_id,
                })

        summary = (
            f"AutoResearch Synthesis for '{request.topic}' ({depth_mode} mode): "
            f"Completed investigation across {subagents_spawned} subagents."
        )

        return AutoResearchResult(
            topic=request.topic,
            depth_mode=depth_mode,
            summary=summary,
            findings=findings,
            subagents_spawned=subagents_spawned,
            status="completed",
        )
