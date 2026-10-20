# US-39 Spec Trace: Subagents / AutoResearch (§3.7 + §11.1-11.5)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 6433 | `## Feature §11.1-11.5: Subagent Spawning, Archetypes, Depth Limiting` | AUGMENT | `sidecar/providers/subagents.py:1` | `tests/unit/test_subagents_autoresearch.py:25` |
| 6451 | `LOCUS 4 FACTION AGENTS: Planner — task planning, scheduling, goal tracking; Curator — memory management, skill maintenance, vault organization; Analyst — pattern detection, behavioral analysis, reporting; Builder — coding delegation, project management, harness coordination` | AUGMENT | `sidecar/subagents.py:40` | `tests/unit/test_subagents_autoresearch.py:40` |
| 6445 | `OPENHUMAN 15 ARCHETYPES: orchestrator, planner, researcher, critic, implementer, debugger, reviewer, documenter, tester, deployer, security_auditor, performance_analyst, data_engineer, designer, communicator` | AUGMENT | `sidecar/subagents.py:70` | `tests/unit/test_subagents_autoresearch.py:65` |
| 6459 | `IF current_depth >= MAX_SPAWN_DEPTH (default 3): RETURN error("Maximum subagent depth reached")` | AUGMENT | `sidecar/subagents.py:120` | `tests/unit/test_subagents_autoresearch.py:90` |
| 6467 | `skip_memory: true, // subagents don't write to memory; skip_review: true, // no post-turn review; parent_session_id: current_session.id; depth: current_depth + 1` | AUGMENT | `sidecar/subagents.py:140` | `tests/unit/test_subagents_autoresearch.py:115` |
| 6476 | `memory_provider.on_delegation(task, result, child_session_id=agent.session_id)` | AUGMENT | `sidecar/subagents.py:165` | `tests/unit/test_subagents_autoresearch.py:135` |
| 2748 | `FUNCTION delegate_to_harness(task_brief, codebase_path):` | AUGMENT | `sidecar/harness/delegation.py:125`, `sidecar/subagents.py:180` | `tests/unit/test_subagents_autoresearch.py:160` |
| Criteria 1 | `Module implementing Subagents / AutoResearch per §11.1-11.5 and §3.7 created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/subagents.py`, `locus-extension/src/subagents.ts` | `tests/unit/test_subagents_autoresearch.py:25` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.subagents_autoresearch.enabled returning 503.` | LOCUS-NEW | `sidecar/providers/subagents.py:1`, `sidecar/service.py:1650` | `tests/unit/test_subagents_autoresearch.py:180`, `tests/integration/test_subagents_service.py:50` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_subagents_autoresearch.py` | `tests/unit/test_subagents_autoresearch.py:25-220` |
