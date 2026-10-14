# Locus OS — Gap Closure Task List

## Milestone 1: Database & Event Bus Foundation 🔴 CRITICAL — ✅ DONE
- [x] 1.1 — PostgreSQL integration layer (`core/database/postgres.py`)
- [x] 1.2 — Initial schema migration (`001_initial_schema.sql`)
- [x] 1.3 — pgvector migration (`002_pgvector.sql`)
- [x] 1.4 — Behavioral Event Bus (`core/event_bus.py`)
- [x] 1.5 — Update `docker-compose.yml` with health checks + limits

## Milestone 2: Life OS Core System Completion 🟠 HIGH — ✅ DONE
- [x] 2.1 — Faction Weekly Stats Cron (#6) → `core/life_os_persistent.py`
- [x] 2.2 — Action Gap Tracking with Alerts (#8)
- [x] 2.3 — Deferral Detection Escalation (#9)
- [x] 2.4 — Dead Node Detection (#10)
- [x] 2.5 — Lag Score + TWS Lag Bonus Wiring (#11)
- [x] 2.6 — Emergency Task Injection Protocol (#12)
- [x] 2.7 — Exhaustion Predictor (#13) → in `life_os_persistent.py`
- [x] 2.8 — Weekly Faction Rebalance (#14)
- [x] 2.9 — Momentum Score Surfacing (#15)
- [x] 2.10 — Three-Birds-One-Stone Cross-Faction (#17)
- [x] 2.11 — Review Cadence System Completion (#18)
- [x] 2.12 — 4-Daily Structured Check-ins (#52) → check-in persistence

## Milestone 3: Memory Subsystem Gaps 🟡 HIGH — PARTIAL
- [x] 3.1 — Memory Tree (§4.5) → `core/memory/memory_tree.py`
- [ ] 3.2 — Memory Sync (§4.7)
- [x] 3.3 — Memory Queue (§4.8) → `core/memory/queue.py`
- [ ] 3.4 — Memory Diff (§4.9)
- [ ] 3.5 — Full STDP Reinforcement (§4.12)
- [ ] 3.6 — Project Memory Decay (§4.14)
- [ ] 3.7 — Neo4j handle_tool_call Fix (§4.1-4.2)

## Milestone 4: Learning & Reward Model 🟢 MEDIUM — PARTIAL
- [x] 4.1 — Personal Reward Model (#94) → `core/learning/reward_model.py`
- [ ] 4.2 — User Identity Profile Deepening (#93)
- [ ] 4.3 — Reflector Enhancement (§10.1)
- [ ] 4.4 — Tool Usage Tracker Enhancement (§10.3)

## Milestone 5: Proactive Reasoning Completion 🟢 MEDIUM — PARTIAL
- [ ] 5.1 — Full 7-Subsystem Proactive Chain (§26.1-26.7)
- [x] 5.2 — Weekly Full Vault Synthesis (#32) → `core/heartbeat/vault_synthesis.py`
- [x] 5.3 — LOCUS_SHORTHAND Compression (#96) → `core/context/shorthand.py`

## Milestone 6: Scheduling & Workflow Engine 🔵 MEDIUM
- [ ] 6.1 — Full 6-Step Scheduling Algorithm (§25.12)
- [ ] 6.2 — Parallel Task Execution Optimizer (#16)
- [ ] 6.3 — Workflow Engine (§29.8)

## Milestone 7: MCP & Extension System 🟣 MEDIUM — PARTIAL
- [x] 7.1 — Locus MCP Server (#85) → `core/mcp/server.py`
- [ ] 7.2 — Obsidian MCP Server (#84)
- [ ] 7.3 — MCP Client Enhancement (§18.4-18.5)
- [ ] 7.4 — Skill & MCP Toolkit Layer (#83)
- [x] 7.5 — Trajectory Recording (§19.2) → `core/learning/trajectory.py`

## Milestone 8: Infrastructure & DevOps 🟢 MEDIUM — PARTIAL
- [x] 8.1 — Vault Sync via Git (#23) → `core/vault/git_sync.py`
- [ ] 8.2 — Self-Maintenance System (#26)
- [x] 8.3 — Database Diagnostic Script (#103) → `core/diagnostics/db_health.py`
- [ ] 8.4 — Full System Health Checks (§29.3)

## Milestone 9: Stub Deepening & Integration Wiring 🔵 MEDIUM
- [ ] 9.1 — System Prompt Builder (§1.2)
- [ ] 9.2 — TUI Dashboard Keybindings (§7.1-7.5)
- [ ] 9.3 — Shell Sandbox Multi-Backend (§13.3)
- [ ] 9.4 — Telegram Gateway Deep Patterns (§17.1)
- [ ] 9.5 — Polymarket & Webhooks Completion (§21.2-21.3)
- [ ] 9.6 — Nightly Vault Diff Cron Wiring (#31)
- [ ] 9.7 — Personality Profile Building (#33)
- [ ] 9.8 — Deduplicate Desktop/Screen/Computer-Use

## Milestone 10: FastAPI REST Layer 🔵 DEFERRABLE
- [ ] 10.1 — FastAPI Application Scaffold
- [ ] 10.2 — API Routers (9 domains)
- [ ] 10.3 — Wire Telegram Gateway to FastAPI
