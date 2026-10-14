# Make Locus Fully Functional — Implementation Plan

## Current State Assessment

Session 1 built the **skeleton** of Locus across ~40 files. Here's what exists vs. what's broken or stub:

### ✅ Already Functional (just needs wiring fixes)
| Component | Files | Status |
|-----------|-------|--------|
| CLI entry point | `locus_cli/main.py` (548 lines) | **Works** — `locus setup`, `locus gateway run`, etc. |
| Config system | `locus_cli/config.py` (644 lines) | **Works** — `~/.locus/config.yaml` + `.env` |
| Setup wizard | `locus_cli/setup.py` (19K) | **Works** — interactive provider/memory setup |
| Gateway bot | `gateway/bot.py` (396 lines) | **Works** — Telegram polling, auth, slash commands |
| Slash commands | `gateway/slash_commands.py` (48K) | **Works** — 30+ commands for Telegram |
| MemoryStore (SQLite) | `core/memory.py` (191 lines) | **Works** — sessions, docs, conversations, cron_jobs |
| Cost tracker | `core/cost_tracker.py` (143 lines) | **Works** — pricing table, budget enforcement |
| Observability | `core/observability.py` (102 lines) | **Works** — Sentry, OTEL, structured logging |
| Session manager | `core/session_manager.py` (104 lines) | **Works** — create/resume/evict sessions |

### ⚠️ Exists But Has Issues (needs fixes to be functional)
| Component | Files | Issue |
|-----------|-------|-------|
| Agent turn loop | `core/agent.py` (463 lines) | `to_openai_tools()` returns raw ToolDef tuples instead of dicts — **broken tool registration** |
| Gateway agent | `gateway/agent.py` (243 lines) | Missing `Any` import (line 18), memory init race condition with asyncio |
| Locus tools | `core/locus_tools.py` (755 lines) | Tools 5-8 are **stubs** returning prompts, not executing real logic |
| Neo4j backend | `core/neo4j_memory.py` (194 lines) | Client instantiation works, but `handle_tool_call` method is **missing** |
| Cron runner | `core/cron_runner.py` (131 lines) | References `get_or_init_agent` but the async loop handling is fragile |

### 🔴 Stub / Non-Functional (needs real implementation)
| Component | Files | What's Missing |
|-----------|-------|---------------|
| Holographic retrieval | `core/holographic/retrieval.py` (20K) | Has HRR vector math but **no embedding generation** — search falls back to keyword-only |
| Inner Loop (Proactive) | `core/locus_tools.py` `_locus_brain()` | Returns a **prompt string**, doesn't actually invoke the LLM or run background reasoning |
| Research pipeline | `core/locus_tools.py` `_locus_research()` | Returns a **prompt template**, no actual web search → synthesis pipeline |
| Code delegation | `core/locus_tools.py` `_locus_delegate_code()` | Returns a **static string**, no actual subprocess invocation of Pi/Codex/Gemini |
| Vault search | `core/locus_tools.py` `_locus_vault()` | Uses raw ripgrep, **no PageIndex integration** |
| Learning system | `core/learning/` (4 files) | `reflector.py`, `user_profile.py`, `tool_tracker.py` are **minimal stubs** |
| Heartbeat system | `core/heartbeat/` | Listed in dir but contents unknown — likely stub |
| Context compaction | `core/context/compactor.py` | **No Headroom CCR integration** — just truncation |
| Security sandbox | `core/agent.py` L280-353 | Shell blocklist, data redaction, think-token scrubbing **all missing** |
| Pattern Engine | — | **Not created** (§10.7 in spec) |
| State Engine persistence | `core/life_os.py` `LocusState` | In-memory only — **no persistence across restarts** |
| Cause Chain Engine | — | **Not created** (§30.2 in spec) |
| SOUL.md / Wants Engine | — | **Not created** (§30.3 in spec) |
| Content Engine | — | **Not created** (§30.4 in spec) |
| Spaced Repetition | — | **Not created** (§30.5 in spec) |
| Master Conductor | — | **Not created** (§30.7 — the 12-stage reactive loop orchestrator) |

---

## Open Questions

> [!IMPORTANT]
> **Scope decision needed**: The spec describes ~85 features. Making ALL of them "fully functional" is a multi-week effort. I recommend a **phased approach** focusing on making the existing code work end-to-end first, then adding missing subsystems.

> [!IMPORTANT]  
> **Testing approach**: Should I run `pytest` against existing tests, or focus purely on making `locus gateway run` work end-to-end via Telegram?

> [!WARNING]
> **API keys**: The gateway needs at least one LLM provider API key and a `TELEGRAM_BOT_TOKEN` in `~/.locus/.env`. Do you have these configured?

---

## Proposed Changes — Phase 1: Make Core Loop Functional

The goal: `locus gateway run` starts → Telegram messages work → tools execute → memory persists → DCS/Life OS works. Fix every bug in the critical path.

---

### Component 1: Agent Engine Fixes

#### [MODIFY] [agent.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/agent.py)

1. **Fix `to_openai_tools()`** (line 64-72): Currently iterates `self._tools.values()` which yields `(ToolDef, Callable)` tuples, then tries to access `.name` on the tuple. Fix to destructure correctly.
2. **Fix message serialization** (line 248): `Message(**m)` fails when `m` contains `tool_calls` key since `Message.tool_calls` expects a `list[dict]` but the dict may have extra keys. Add proper message conversion.
3. **Add missing `tool_call_id` handling**: Tool result messages need the correct format for the OpenAI API.

#### [MODIFY] [gateway/agent.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/gateway/agent.py)

1. **Add missing `Any` import** (line 18).
2. **Fix asyncio memory init** — use a proper pattern that works whether or not an event loop is already running.
3. **Add Locus Life OS system prompt injection** — the current system prompt is generic, needs to include DCS/mode context.

---

### Component 2: Tool System Fixes

#### [MODIFY] [locus_tools.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/locus_tools.py)

1. **Fix `_locus_vault()`** — use the actual configured vault path from `LOCUS_VAULT_PATH` env var instead of hardcoded `~/.locus/vault`.
2. **Make `_locus_brain()` actually invoke the LLM** — instead of returning a prompt string, use the agent's LLM provider to run the reasoning cycle and return the result.
3. **Make `_locus_research()` trigger real web search** — chain `web_search` → `web_fetch` → synthesis.
4. **Make `_locus_delegate_code()` invoke subprocess** — detect available harnesses (pi, codex, gemini) and spawn them.

---

### Component 3: Memory System Completion

#### [MODIFY] [neo4j_memory.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/neo4j_memory.py)

1. **Add `handle_tool_call()` method** — dispatch `add_entity`, `add_relationship`, `search_entities`, `get_context` actions to the Neo4j client.
2. **Add `save_message()` method** — extract entities from messages and store in the graph.
3. **Add `get_context()` method** — query the graph for relevant context given a user message.

#### [MODIFY] [holographic/retrieval.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/holographic/retrieval.py)

1. **Add lightweight embedding generation** — use TF-IDF or a sentence-transformers model for vector search instead of keyword-only fallback.

---

### Component 4: State Persistence

#### [MODIFY] [life_os.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/life_os.py)

1. **Add `LocusState.save()` and `LocusState.load()`** — persist DCS, mode, last check-in to `~/.locus/state.json` so it survives restarts.
2. **Auto-load state on startup** — `get_state()` should load from disk if in-memory state is default.

#### [MODIFY] [locus_tools.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/locus_tools.py)

1. **Persist tasks to SQLite** — add `_persist_tasks()` and `_load_tasks()` similar to `_persist_goals()`.
2. **Auto-load goals and tasks on first access** — lazy initialization from the memory store.

---

### Component 5: Security Hardening

#### [NEW] [core/security.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/security.py)

Centralize security logic currently scattered in `agent.py`:
1. **Shell blocklist** (§13.7) — block `rm -rf /`, `dd`, `mkfs`, etc.
2. **Data redaction** (§13.8) — scrub API keys, passwords from tool outputs before sending to LLM.
3. **Think-token scrubbing** (§13.9) — remove `<think>` blocks from Anthropic responses before showing to user.
4. **Message sanitization** (§13.10) — strip injection attempts from user input.

---

### Component 6: Learning System

#### [MODIFY] [learning/reflector.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/learning/reflector.py)

1. **Implement `run_reflection()`** — extract key decisions, preferences, and learnings from conversation history; store as facts in the memory backend.

#### [MODIFY] [learning/user_profile.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/learning/user_profile.py)

1. **Implement `update_user_profile()`** — extract and persist user preferences, communication style, and expertise areas.

#### [MODIFY] [learning/tool_tracker.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/learning/tool_tracker.py)

1. **Implement `record_session_tools()`** — track which tools were used, their success rates, and patterns.

---

### Component 7: Context Forge Integration

#### [MODIFY] [context/__init__.py](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/context/__init__.py)

1. **Wire Context Forge into the agent loop** — currently `agent.py` manually injects Locus state, but doesn't use the full 6-layer `assemble_context_forge()`. Connect all 6 layers.

---

## Proposed Changes — Phase 2: Missing Subsystems (Future)

These are the larger subsystems from the spec that don't exist yet:

| Subsystem | §ID | Priority | Effort |
|-----------|-----|----------|--------|
| Master Conductor (12-stage reactive loop) | §30.7 | HIGH | 2-3 days |
| Pattern Engine | §10.7 | MEDIUM | 1-2 days |
| Cause Chain Engine | §30.2 | MEDIUM | 1 day |
| SOUL.md / Wants Engine | §30.3 | LOW | 1 day |
| Content Engine | §30.4 | LOW | 1 day |
| Spaced Repetition | §30.5 | LOW | 1 day |
| QLoRA Pipeline | §30.6 | LOW | 2+ days |

---

## Verification Plan

### Automated Tests
```bash
cd c:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os
python -m pytest core/test_core.py core/test_memory_backends.py -v
```

### Manual Verification
1. Run `locus setup` — verify wizard completes without errors
2. Run `locus gateway run` — verify bot starts and connects to Telegram
3. Send a message via Telegram — verify agent responds
4. Send `/checkin` — verify DCS calculation and mode assignment
5. Send `/goals` — verify goal CRUD works
6. Send `/status` — verify Life OS state display
7. Restart gateway — verify state persists (DCS, goals, tasks)
