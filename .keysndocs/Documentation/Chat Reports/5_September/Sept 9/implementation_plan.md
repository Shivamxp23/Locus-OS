# Locus OS — Feature Audit & Master Implementation Plan (v3)

Audited against:
- `locus-os/.keysndocs/Documentation/Implementation Plans` (`LOCUS_FEATURE_LOGIC_DECOMPOSITION.md`, `LOCUS_MASTER_IMPLEMENTATION_PLAN_v2.md`)
- `locus-os/.keysndocs/Documentation/Chat Reports/5_September` (`Sept 7`, `Sept 8`)
- `locus-os/.keysndocs/Documentation/Ideas and System` (`locus_features.md` #1–#161, `Ideas.md`, `Comprehensive Locus System Design.html`)
- `deps/` (9 reference repositories)
- Active Codebase: 194 core Python files (1.18 MB), 9 gateway files (112 KB), 9 FastAPI routers with 33 endpoints, 6 master integration tests passing.

---

## 1. Feature Implementation Audit Summary

| Status | Count | % | Notes |
| :--- | :---: | :---: | :--- |
| **Fully Implemented** | **104** | **64.6%** | Core turn loop, 6-layer Context Forge, Headroom CCR, 22 APScheduler jobs, FastAPI (9 routers / 33 endpoints), SQLite fallback + PG migrations, Local-First Obsidian sync, 4 check-in flows, 4 review cadences, TUI, Telegram bot deep patterns, PageIndex, Chat archiver, Rough note parser, Link logger, Excalidraw builder, Error classifier, System doctor. |
| **Partially Implemented** | **31** | **19.3%** | Code exists (>3KB) with foundational classes and fallbacks, but missing an external daemon, live training loop, or OS-level containerization. (e.g. Personal reward model auto-trainer, Neo4j live container traversal, subagent process isolation, Polymarket live reader). |
| **Not Implemented / Deferred** | **26** | **16.1%** | Planned in spec or raw ideas with either no code or only minimal interface stubs (<1KB). (e.g. ACP server for IDEs, Inter-harness bridge, Multi-agent Kanban queue, Animated SVG avatar, Achievements engine). |
| **Total Features** | **161** | **100.0%** | Full catalog of canonical features from `locus_features.md`. |

---

## 2. Proposed Implementation Plan (4 Execution Phases)

The complete, self-contained implementation plan has been written to:
[LOCUS_MASTER_IMPLEMENTATION_PLAN_v3.md](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Implementation%20Plans/LOCUS_MASTER_IMPLEMENTATION_PLAN_v3.md).

### Phase A: Core High-Priority Refinements (Partial $\to$ 100%)
- **Task A1: Personal Reward Model Auto-Trainer**:
  - `core/learning/reward_model.py`: Implement `auto_train_from_db()` fitting LogisticRegression on user feedback signals (👍/👎, latency, prompt tokens).
  - `core/scheduler_wiring.py`: Register weekly retraining job on Sundays at 03:00.
- **Task A2: Subagent Isolated Process Runner**:
  - `core/delegation/process_runner.py`: Add `SubagentProcessRunner` spawning isolated worker processes (`asyncio.create_subprocess_exec`) with stdout/stderr pipes, timeout management, and in-process fallback.
- **Task A3: LOCUS_SHORTHAND Tool Registration**:
  - `core/locus_tools.py`: Register `locus_compress_context` tool wrapping `core.context.shorthand` for dynamic prompt token pruning.
- **Task A4: Single-Provider Council Debate Engine**:
  - `core/council.py`: Multi-persona debate board (Architect, Skeptic, Pragmatist) for deliberating critical architectural decisions.

### Phase B: External Protocols & Work Queues (Missing $\to$ 100%)
- **Task B1: Multi-Agent Durable Kanban Work Queue**:
  - `core/database/migrations/004_kanban_queue.sql`: Create `kanban_tasks` table.
  - `core/scheduler/kanban_queue.py`: SQLite-backed state machine (`BACKLOG` $\to$ `READY` $\to$ `RUNNING` $\to$ `DONE`) with worker dispatch.
- **Task B2: Agent Communication Protocol (ACP) Server**:
  - `core/acp_server.py`: JSON-RPC 2.0 server over STDIO for VS Code, Cursor, and JetBrains IDE extensions.
- **Task B3: Inter-Harness Auto-Bridge**:
  - `core/inter_harness_bridge.py`: Auto-discover sibling harnesses in `../deps/` (`deepseek-harness`, `autoresearch`, `hermes-agent`) and route tasks.
- **Task B4: Polymarket Prediction Intelligence**:
  - `core/integrations/polymarket.py`: Query public Gamma API for live outcome probabilities and forecast calibration.

### Phase C: Obsidian Ambient & Gamification (Specs $\to$ 100%)
- **Task C1: Obsidian Animated Avatar & State Publisher**:
  - `core/vault/avatar_publisher.py`: Programmatic SVG generator reflecting DCS, Mode, and Faction health published to `vault/00-System/Avatar.md`.
- **Task C2: Gamification & Milestone Achievement Engine**:
  - `core/gamification/achievements.py`: Streak and milestone evaluator awarding badges (`CENTURION`, `FLOW_MASTER`, `POLY_SCHOLAR`).
- **Task C3: Real-Time Audio Journaling Daemon**:
  - `core/voice/audio_journal_daemon.py`: Scheduled evening voice prompts with Whisper transcription saving into `vault/03-Journal/`.

### Phase D: Master Integration & Verification
- **Task D1: Master Integration Test Suite Expansion**:
  - `core/test_integration_master.py`: Add tests 07 (reward model train), 08 (Kanban queue), 09 (ACP protocol), 10 (Avatar & gamification).
- **Task D2: CLI Doctor Diagnostics Expansion**:
  - `locus_cli/main.py doctor`: Validate ACP server and Kanban DB health.
- **Task D3: Knowledge Graph Sync**:
  - Run `graphify update .` to keep knowledge graph in sync.

---

## 3. Verification Plan

### Automated Tests
- Run `python -m pytest core/test_integration_master.py -v` (Must pass all 10 tests).
- Run `python -m pytest core/tests/ -v` (Must pass all unit tests).
- Run `python locus_cli/main.py doctor` (Must return `[HEALTHY]`).

### Manual Verification
- Test ACP server initialize handshake:
  `echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}' | python -m core.acp_server`
- Inspect generated `vault/00-System/Avatar.md` SVG in Obsidian.
