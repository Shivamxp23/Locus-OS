# Atomic Selections from Antigravity

> **Generated:** July 13, 2026 — Antigravity Agent Session
> **Purpose:** Final verdict on all 37 feature sections from `ALL FEATURES POSSIBLE.md`. For every feature: which codebase(s) to steal logic from, what files to study, what the congruence is with Locus, the stripped atomic logic, and how it adapts to Locus's modular architecture.
> **Methodology:** "Laziness first" — never reinvent. "Steal logic/implementation strategy" — adapt, don't clone. "Never directly refer to any codebase" — use `/understand-anything` to trace actual implementations.
> **Constraints:** No code in this document. Pseudocode, algorithms, data contracts, and logic flows only. Everything must be swappable/configurable in Locus's modular architecture.

---

## Table of Contents

- [Part I: Section-by-Section Feature Verdicts (§1–§37)](#part-i-section-by-section-feature-verdicts-137)
- [Part II: Memory & Retrieval Standard — The Locus Tri-Stack](#part-ii-memory--retrieval-standard--the-locus-tri-stack)
- [Part III: Autoresearch Integration](#part-iii-autoresearch-integration)
- [Part IV: Harness Delegation Architecture](#part-iv-harness-delegation-architecture)

---

# Part I: Section-by-Section Feature Verdicts (§1–§37)

> For each section, every feature gets a verdict:
> - **Source(s):** Which codebase(s) to study
> - **Key Files:** Files to trace with `/understand-anything`
> - **Congruence:** How the source's implementation maps to Locus
> - **Atomic Logic:** The stripped implementation strategy (no code)
> - **Adaptation:** How it fits Locus's modular Python architecture

---

## §1 — Core Runtime & Architecture

### 1A. Tech Stack

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Language/runtime | ✅ **Keep Locus** — Python monolith is the right call for single-user PCOS | N/A |
| Package structure | **Study Hermes** — its `agent/`, `tools/`, `gateway/`, `plugins/`, `skills/` directory layout maps cleanly to Locus's modular needs | Hermes |
| Transport layer | ✅ **Keep Locus** — HTTP + Telegram webhook. Add WebSocket for future real-time channels | N/A |
| Lazy imports / cold-start | **Steal from Hermes** — `lazy_deps.py` pattern for conditional imports | Hermes |
| Event bus (typed pub/sub) | **Steal from OpenHuman** — `event_bus/` pattern but implement in Python with PG LISTEN/NOTIFY | OpenHuman + Pi |

**Key Files to Trace:**
- Hermes: `agent/lazy_deps.py` — lazy import wrapper pattern
- Hermes: top-level directory structure — modular organization
- OpenHuman: `src/core/event_bus/` — typed pub/sub with domain events
- Pi: `event-bus.ts` — simpler event bus reference

**Atomic Logic — Lazy Imports:**
- Python decorator `@lazy_import(module_path)` that returns a proxy object
- Proxy resolves on first attribute access via `importlib.import_module()`
- Cuts cold-start by deferring heavy deps (playwright, sklearn, neo4j driver) until actually needed

**Atomic Logic — Event Bus:**
- PG LISTEN/NOTIFY as the transport (already in architecture)
- Typed event classes: `BehavioralEvent`, `StateChangeEvent`, `TaskEvent`, `CheckInEvent`
- Subscriber registry: `{event_type: [handler_fn]}` — handlers registered at module init
- All FastAPI routes emit events through a single `emit(event)` function
- This IS feature #7 (Behavioral Event Stream) — foundational infrastructure

**Adaptation:** Locus already uses PG. Event bus = thin Python layer over PG LISTEN/NOTIFY. No external dependency. Lazy imports = simple decorator, zero cost.

---

### 1B. Agent Loop

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Main agent loop | **Steal from Hermes** — `AIAgent.run_conversation()` is the closest to Locus's single-model architecture | Hermes |
| Turn context management | **Steal from Hermes** — `turn_context.py` per-turn state is cleanest | Hermes |
| Turn retry / error recovery | **Combine Pi + Hermes** — Pi's exponential backoff config + Hermes's `turn_retry_state.py` | Pi + Hermes |
| System prompt builder | **Steal from Hermes** — `system_prompt.py` + `prompt_builder.py` dynamic assembly | Hermes |
| Streaming | ✅ **Keep Locus** — `streaming_tui.py` exists, extend for Telegram chunks | N/A |
| Iteration budget / limits | **Steal from Hermes** — `max_iterations` with grace call | Hermes |
| Interrupt checks | **Steal from Hermes** — `_interrupt_requested` per-iteration check | Hermes |
| Tool-call dispatch | **Steal from Hermes** — `handle_function_call()` dispatch with argument coercion | Hermes |
| Reasoning content | **Steal from Pi** — 6 thinking levels with custom token budgets | Pi |
| Token tracking per turn | **Steal from Hermes** — `usage_pricing.py` + `credits_tracker.py` | Hermes |

**Key Files to Trace:**
- Hermes: `agent/run_agent.py` — main agent loop
- Hermes: `agent/turn_context.py` — per-turn state management
- Hermes: `agent/turn_retry_state.py` — retry logic
- Hermes: `agent/system_prompt.py`, `agent/prompt_builder.py` — dynamic system prompt
- Hermes: `agent/iteration_budget.py` — iteration limits + grace turn
- Pi: `pi-agent-core/agent-loop.ts` — two-entry loop pattern
- Pi: `pi-ai/` — reasoning content levels

**Atomic Logic — Agent Loop:**
1. `run_conversation(messages, tools, max_iterations=90)` — entry point
2. Per-iteration: `turn_context` snapshot → tool dispatch → response → check budget
3. Budget exhaustion → grace turn (1 final call with "wrap up" system message)
4. Interrupt check: `if self._interrupt_requested: break`
5. Error recovery: exponential backoff `delay = base_delay * 2^attempt` capped at `max_delay`

**Atomic Logic — System Prompt Builder:**
1. Base template (SOUL.md equivalent)
2. Dynamic injection slots: `{tools_description}`, `{active_skills}`, `{user_identity_summary}`, `{current_state_summary}`
3. Assemble at request time, not at init — always fresh context
4. Token-aware: truncate injected context if total exceeds budget

**Adaptation:** Replace Hermes's multi-provider routing with Locus's single-model path. Keep the loop structure, add Locus-specific Context Forge (#58) integration at the context assembly step.

---

### 1C. Configuration

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Config format | ✅ **Keep Locus** — SETTINGS.md (56KB) already exceeds all others. Migrate to YAML for programmatic access | N/A |
| Config migration | ✅ **Keep Locus** — `locus config migrate` exists | N/A |
| Config management CLI | **Extend from Hermes** — add `config edit`, `config check`, `config set KEY VAL` subcommands | Hermes |
| Environment variable management | **Steal from Hermes** — centralized env key registry with validation | Hermes |
| Profile-aware config | **Steal from Hermes** — `get_hermes_home()` pattern for profile dirs | Hermes |

**Key Files to Trace:**
- Hermes: `hermes_cli/config.py` — CLI config commands
- Hermes: `agent/hermes_constants.py` — env key registry

**Atomic Logic — Config Check:**
- `locus config check` validates: all required env keys set, PG connection, Neo4j connection, vault path accessible, Telegram bot token valid
- Returns structured JSON health report
- Integrates with #71 (Database Diagnostic Script)

**Adaptation:** Locus already has a robust config. The main adoption is the CLI `check` and `edit` subcommands from Hermes, plus env key validation.

---

### 1D. Startup & Lifecycle

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Onboarding flow | **Steal from Hermes** — `hermes setup [section]` interactive wizard pattern | Hermes |
| Agent initialization | ✅ **Keep Locus** — `core/agent.py` exists | N/A |
| Core restart | **Steal from Hermes** — `/restart` slash command | Hermes |
| Self-update | **Steal from Pi** — `version-check.ts` logic (check remote version, compare semver, prompt upgrade) | Pi |
| Doctor / diagnostics | **Combine Hermes + Pi** — `hermes doctor [--fix]` + Pi's `diagnostics.ts` | Hermes + Pi |
| Status command | **Steal from Hermes** — `hermes status [--all]` component status | Hermes |

**Key Files to Trace:**
- Hermes: `hermes_cli/setup.py` — setup wizard
- Hermes: `hermes_cli/doctor.py` — diagnostics with auto-fix
- Pi: `pi-coding-agent/version-check.ts` — version check pattern

**Atomic Logic — Doctor Command:**
1. Check: Python version, pip deps up-to-date, PG reachable, Neo4j reachable, vault path exists, Telegram webhook registered, disk space, memory
2. For each check: `PASS`, `WARN`, `FAIL`
3. `--fix` flag: auto-fix known issues (e.g., missing tables → run migrations, missing dirs → mkdir)
4. Output: structured report + Telegram summary if `FAIL`

**Adaptation:** Maps directly to Locus's #71 (Database Diagnostic Script). Combine doctor + diagnostics into single `locus doctor` command.

---

### 1E. Prompt Caching

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Prompt cache | **Steal from Hermes** — `prompt_caching.py` with configurable TTL | Hermes |

**Key Files to Trace:**
- Hermes: `agent/prompt_caching.py` — cache TTL, hit tracking

**Atomic Logic:**
- Hash system prompt + tools definition → cache key
- If cache hit AND within TTL (5min default): reuse cached completion prefix
- Track hit rate → log to behavioral_events for cost optimization
- Locus-specific: single model = single cache path = high hit rate

---

### 1F. Background Review & Post-Turn

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Background review | **Steal from Hermes** — fork-based background grading of responses | Hermes |
| Self-improvement | **Steal from Hermes** — background fork grades/improves skills | Hermes |

**Key Files to Trace:**
- Hermes: `agent/self_improvement/` — background fork pattern

**Atomic Logic:**
- After response sent: spawn background task → grade response quality (0-1)
- If quality < 0.5: flag for Reward Model training data
- If quality > 0.8: extract pattern → store as positive example
- This feeds directly into #63 (Personal Reward Model)

**Adaptation:** Locus uses APScheduler + asyncio tasks for background work. No forking needed — just async.

---

## §2 — LLM Providers

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Provider architecture | **Steal from Hermes** — plugin-based provider registration, but strip multi-provider to single-primary + optional local fallback | Hermes |
| OpenAI-compatible wrapper | **Steal from Hermes** — single wrapper that works with any OpenAI-compatible endpoint | Hermes |
| Local model support (Ollama/LMStudio) | **Steal from Hermes** — same OpenAI wrapper, different `base_url` | Hermes |
| Provider fallback chain | **Steal from Hermes** — but simplify: primary (Gemini Flash) → local fallback (Ollama) → error | Hermes |
| Rotating credentials | **Steal from Hermes** — for future multi-key rotation (currently single key) | Hermes |

**Key Files to Trace:**
- Hermes: `agent/model_tools.py` — provider interface
- Hermes: `plugins/providers/` — plugin-based provider registration
- Hermes: `agent/auxiliary_client.py` — resolves named custom providers

**Atomic Logic — Provider Interface:**
```
interface LLMProvider:
  complete(messages, tools, temperature, max_tokens) → Response
  stream(messages, tools, temperature, max_tokens) → AsyncIterator[Chunk]
  get_model_info() → ModelInfo {name, context_window, supports_tools, supports_vision}
```
- All providers implement this interface
- Provider registry: `{name: ProviderClass}`
- Config: `providers: [{name, base_url, api_key, model_list}]`
- Fallback chain: try primary → if fails, try next → if all fail, error

**Adaptation:** Locus keeps Gemini Flash as primary. Provider interface enables #82 (First-Class Local Model Support) and future expansion. Single interface, multiple backends.

---

## §3 — Tools / Tool Execution

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Tool registry | **Combine Hermes + OpenHuman** — Hermes's central registry + OpenHuman's `tool_registry` pattern | Hermes + OpenHuman |
| Tool sandboxing | **Steal from Hermes** — path sandboxing, output limits, timeout enforcement | Hermes |
| Tool output truncation | **Steal from Hermes** — configurable max output length per tool | Hermes |
| Bash/shell tool | **Steal from Hermes** — subprocess execution with timeout, sandboxing | Hermes |
| File operations | **Steal from Pi** — read, write, patch, search tools | Pi |
| Web search | ✅ **Keep Locus** — already has 5 web search integrations | N/A |
| Browser automation | **Steal from Hermes** — CDP Playwright with persistent contexts | Hermes |
| Code execution backends | **Steal from Hermes** — local/Docker/SSH execution sandboxes | Hermes |
| Vision tool | **Steal from Hermes** — pass images to model for analysis | Hermes |
| Delegation tool | **Steal from Pi** — spawn sub-agents for parallel work | Pi |

**Key Files to Trace:**
- Hermes: `tools/` — tool implementations
- Hermes: `tools/tool_registry.py` — central registry pattern
- Hermes: `tools/sandbox.py` — path sandboxing
- Pi: `pi-agent-core/tools/` — file operation tools
- Pi: `pi-agent-core/sub-agents/` — delegation tools

**Atomic Logic — Tool Registry:**
- `skills_registry` table (PG): `{id, name, description, tool_schema (JSON Schema), trigger_conditions, priority, is_active, sandbox_config}`
- Every tool declares: input schema, output schema, timeout, sandbox rules
- Tool dispatch: Query Router intent → registry lookup → execute → format output → return
- Sandbox: allowlist of paths, deny dangerous commands, output truncation at 10K tokens default

**Adaptation:** Locus already has tools via `ToolRegistry`. The adoption is the registry table (PG-backed, not in-memory), sandbox config, and output truncation. Maps to #52 (Skill & MCP Toolkit Layer) and #99 (Tool Registry & Sandboxing).

---

## §4 — Memory & Persistence

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Graph memory | **Steal from OpenHuman** — `memory_graph`, `memory_entities` pattern + Neo4j Agent Memory library | OpenHuman + neo4j-labs/agent-memory |
| Conversation memory | **Steal from OpenHuman** — `memory_conversations` module | OpenHuman |
| Entity extraction | **Steal from neo4j-labs/agent-memory** — multi-stage pipeline (spaCy → GLiNER → LLM) | External: neo4j-labs/agent-memory |
| Memory search | **Steal from OpenHuman** — `memory_search` with vector + text + graph hybrid | OpenHuman |
| Memory archival | **Steal from OpenHuman** — `memory_archivist` for consolidation | OpenHuman |
| Hebbian memory | ✅ **Keep Locus** — unique Locus feature (#64), not in any other codebase | N/A |
| Memory tree | **Study OpenHuman** — `memory_tree` Obsidian-compatible wiki vault | OpenHuman |
| Memory diff | **Steal from OpenHuman** — `memory_diff` for change tracking | OpenHuman |
| Memory queue | **Steal from OpenHuman** — `memory_queue` for async processing | OpenHuman |
| Memory sync | **Steal from OpenHuman** — `memory_sync` for cross-device | OpenHuman |

**Key Files to Trace:**
- OpenHuman: `src/memory_graph/` — graph-based knowledge
- OpenHuman: `src/memory_entities/` — entity management
- OpenHuman: `src/memory_conversations/` — conversation history
- OpenHuman: `src/memory_search/` — hybrid search
- OpenHuman: `src/memory_archivist/` — memory consolidation
- OpenHuman: `src/memory_tree/` — markdown wiki vault (Obsidian-compatible)
- OpenHuman: `src/memory_diff/` — change tracking
- External: `neo4j-labs/agent-memory` Python SDK — short-term, long-term, reasoning memory

**Atomic Logic — See [Part II](#part-ii-memory--retrieval-standard--the-locus-tri-stack) for complete memory architecture.**

**Adaptation:** OpenHuman has the most mature memory system (20+ memory modules). Locus steals the *patterns* (not the Rust code) and implements in Python. The tri-stack (Neo4j Agent Memory + Headroom + PageIndex) replaces all vector-based approaches.

---

## §5 — Sessions

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Session persistence | **Steal from Hermes** — SQLite + FTS5 for session indexing | Hermes |
| Session branching/forking | **Steal from Pi** — `session.fork()` for parallel exploration | Pi |
| Session compaction | **Steal from Pi** — `session.compact()` summarize old turns | Pi |
| Session export (HTML/JSON/MD) | **Steal from Pi** — `export-html/`, `--export json`, `--export md` | Pi |

**Key Files to Trace:**
- Hermes: `agent/session_store.py` — SQLite + FTS5
- Pi: `pi-coding-agent/sessions/` — session management
- Pi: `pi-coding-agent/export-html/` — session export

**Atomic Logic — Session Compaction:**
1. When conversation exceeds `max_context_tokens` (configurable)
2. Take messages[0:N-recent] → summarize via LLM → single "summary" message
3. Replace old messages with summary + keep recent N messages
4. This is what Headroom's compression handles in the tri-stack — see Part II

**Atomic Logic — Session Export:**
- `locus export --format {html|json|md} --session {id}`
- HTML: template-based with syntax highlighting
- JSON: raw message array with metadata
- MD: formatted markdown with tool outputs collapsed

**Adaptation:** Locus stores sessions in PG (not SQLite). Session compaction integrates with Headroom compression. Export is a simple formatter over PG session data.

---

## §6 — Context Management

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Context compression | **Steal from Hermes** — `context_engine/` pluggable compressor + **Headroom** for production | Hermes + External: headroom-labs |
| Context window management | **Steal from Hermes** — auto-compress at token limit | Hermes |
| Pluggable context engines | **Steal from Hermes** — `plugins/context_engine/` directory pattern | Hermes |

**Key Files to Trace:**
- Hermes: `plugins/context_engine/` — pluggable context strategies
- Hermes: `agent/context_compression.py` — compression logic
- External: `headroomlabs-ai/headroom` — CCR (Cache-Compress-Retrieve) pipeline

**Atomic Logic — See [Part II, Headroom section](#headroom--context-compression-layer) for complete compression architecture.**

**Adaptation:** Context management = Context Forge (#58) + Headroom. The Context Forge assembles the 800-token block; Headroom compresses tool outputs and long responses before they enter the forge.

---

## §7 — TUI / Terminal

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| TUI interface | **Low Priority for Locus** — Telegram is primary interface. Study Hermes's Ink-React TUI for future CLI mode only | Hermes |
| Syntax highlighting | **Steal from Pi** — `syntax-highlight.ts` pattern (use `rich` library in Python) | Pi |
| Spinner/progress | **Steal from Hermes** — terminal spinner for long operations | Hermes |
| Markdown rendering | **Steal from Pi** — terminal markdown rendering (use `rich.markdown` in Python) | Pi |

**Key Files to Trace:**
- Hermes: `ui-tui/` — React terminal UI
- Pi: `pi-tui/syntax-highlight.ts` — syntax highlighting

**Atomic Logic:**
- For CLI mode: use Python `rich` library for markdown, syntax highlighting, spinners, tables
- No custom TUI framework needed — `rich` covers all cases
- Telegram renders markdown natively

**Adaptation:** Locus's primary UI is Telegram. CLI mode uses `rich`. No need for full TUI framework.

---

## §8 — CLI

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| CLI structure | **Steal from Hermes** — subcommand pattern: `locus {config|doctor|setup|models|mcp|cron|status}` | Hermes |
| Yolo mode | **Steal from Hermes** — auto-approve all tool calls | Hermes |
| Resume capability | **Steal from Pi** — `--resume` to continue last session | Pi |
| Non-interactive mode | **Steal from Pi** — `--print` mode for piped output | Pi |

**Key Files to Trace:**
- Hermes: `hermes_cli/cli.py` — CLI entry point with subcommands
- Pi: `pi-coding-agent/cli.ts` — CLI flags

**Atomic Logic — CLI Subcommands:**
```
locus config {show|set|check|migrate|edit|path|env-path}
locus doctor [--fix]
locus setup [section]
locus status [--all]
locus cron {list|add|remove}
locus mcp {list|add|remove|status}
locus export {--format html|json|md} {--session id}
locus chat [--yolo] [--resume]
```

**Adaptation:** Locus already has partial CLI. Extend with Hermes's subcommand structure using Python `click` or `typer`.

---

## §9 — Extensions / Plugins / Skills

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Skill registry | **Combine Hermes + Pi** — Hermes's SKILL.md YAML format + Pi's cross-harness `~/.agents/skills/` | Hermes + Pi |
| Skill auto-discovery | **Steal from Hermes** — startup directory scanning | Hermes |
| Skill lifecycle hooks | **Steal from Hermes** — pre_request, post_tool_call, on_startup, on_shutdown | Hermes |
| HTTP skill downloads | **Steal from Hermes** — download skills from URLs | Hermes |
| Bundled standard library | **Steal from Hermes** — pre-loaded data science, diagrams, productivity skills | Hermes |

**Key Files to Trace:**
- Hermes: `skills/` — SKILL.md format, auto-discovery
- Hermes: `plugins/hooks/` — lifecycle hook architecture
- Pi: `~/.agents/skills/` — cross-harness skill directory

**Atomic Logic — Skill Format:**
```yaml
# SKILL.md frontmatter
name: "web_search"
description: "Search the web for information"
version: "1.0"
trigger_conditions:
  intents: ["EXTERNAL_KNOWLEDGE"]
  keywords: ["search", "find", "look up"]
tools:
  - name: "web_search"
    schema: {query: string, num_results: int}
```
- Directory scan at startup: `skills/*/SKILL.md` → parse frontmatter → register in `skills_registry`
- Lifecycle hooks: Python decorator pattern `@on_startup`, `@pre_request`, `@post_tool_call`

**Adaptation:** Maps directly to Locus's #52 (Skill & MCP Toolkit Layer). Skills stored in PG `skills_registry` table. Pi's `~/.agents/skills/` enables cross-harness skill sharing.

---

## §10 — Learning & Self-Improvement

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Self-improvement loop | **Steal from Hermes** — background fork grades/improves skills | Hermes |
| Autonomous curator | **Steal from Hermes** — background agent curates skill library by usage telemetry | Hermes |
| Reward model | ✅ **Keep Locus** — #63 (Personal Reward Model) is Locus-unique | N/A |
| RLHF / fine-tuning | ✅ **Keep Locus** — #30 (Phase 3 QLoRA) is Locus-unique | N/A |
| Thinking pattern capture | ✅ **Keep Locus** — #49 is Locus-unique | N/A |

**Key Files to Trace:**
- Hermes: `agent/self_improvement/` — background improvement loop
- Hermes: `agent/autonomous_curator.py` — skill usage tracking

**Atomic Logic — Autonomous Curator:**
1. Track skill invocations: `skill_usage: {skill_id, count, last_used, avg_quality_score}`
2. Monthly cron: identify skills with `count < 5 AND last_used > 90d`
3. Options: archive (move to `archived_skills/`), merge (combine overlapping), delete
4. Log decisions for review

**Adaptation:** Feeds into Locus's #32 (Self-Evolving Architecture). The curator scans `skills_registry` table instead of files.

---

## §11 — Subagents / Orchestration

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Sub-agent spawning | **Steal from Pi** — subprocess-based isolated agents with restricted tool subsets | Pi |
| Agent types | **Steal from Pi** — Scout (read-only fs), Researcher (web), Worker (code) | Pi |
| Observability | **Steal from Pi** — indented logs with cost/tokens per sub-agent | Pi |
| Delegation protocol | **Steal from Hermes** — sync batch parallel delegation | Hermes |

**Key Files to Trace:**
- Pi: `pi-agent-core/sub-agents/` — agent types, spawning
- Hermes: `agent/delegation/` — parallel delegation

**Atomic Logic — Sub-Agent Spawning:**
1. Parent determines task type → select agent type → spawn subprocess
2. Agent types with tool restrictions:
   - **Scout:** `[grep, read_file, glob, list_dir]` — read-only filesystem exploration
   - **Researcher:** `[web_search, web_fetch, summarize]` — web research
   - **Worker:** `[bash_sandbox, code_edit, test_run]` — sandboxed code execution
3. Communication: parent passes task JSON → child returns result JSON via stdout
4. Parent aggregates results, tracks cost per child

**Adaptation:** Maps to Locus's #86 (Pi Sub-Agents) and #31 (Subagentic Capabilities). Use `subprocess.Popen` for isolation. MCP integration (#78) enables dynamic tool assignment.

---

## §12 — Scheduling & Cron

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Cron scheduler | ✅ **Keep Locus** — APScheduler already integrated | N/A |
| NL schedule parsing | **Steal from Hermes** — natural language to cron expression | Hermes |
| Webhook triggers | ✅ **Keep Locus** — `webhooks.py` exists | N/A |
| Override profiles | **Steal from Hermes** — schedule overrides per profile | Hermes |

**Key Files to Trace:**
- Hermes: `cron/` — NL cron parsing, schedule management

**Atomic Logic — NL Schedule Parsing:**
- User says "remind me every Monday at 9am" → LLM extracts → `{"cron": "0 9 * * 1", "action": "remind", "payload": "..."}`
- Maps directly to APScheduler job creation
- Store in `scheduled_jobs` PG table for persistence across restarts

**Adaptation:** Locus already uses APScheduler extensively. NL parsing is a thin LLM call. Already have #39 (Check-ins), #27 (Nightly Ingestion), #28 (Weekly Synthesis) as APScheduler jobs.

---

## §13 — Security & Sandboxing

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Smart approval | **Steal from Hermes** — risk-based approval (low=auto, high=ask) | Hermes |
| PII redaction | **Steal from Hermes** — regex + NER-based PII detection | Hermes |
| Path sandboxing | **Steal from Hermes** — tool output restricted to allowed paths | Hermes |
| Prompt injection | ✅ **Keep Locus** — #48 already designed (regex + AI two-layer) | N/A |

**Key Files to Trace:**
- Hermes: `tools/sandbox.py` — path sandboxing
- Hermes: `agent/security/` — PII redaction, smart approval

**Atomic Logic — Smart Approval:**
1. Tool call → classify risk: `LOW` (read ops), `MEDIUM` (write to sandboxed path), `HIGH` (bash, network, delete)
2. LOW → auto-approve
3. MEDIUM → auto-approve if yolo mode, else Telegram inline keyboard `[Approve] [Deny]`
4. HIGH → always Telegram approval unless yolo mode

**Adaptation:** Maps to Locus's #46-48 security stack. Smart approval adds Telegram-native approval flow.

---

## §14 — Voice & Meetings

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Voice transcription (STT) | **Steal from Hermes** — faster-whisper / Groq STT integration | Hermes |
| Text-to-speech (TTS) | ✅ **Keep Locus** — Kokoro TTS planned for Phase 3 | N/A |
| Meeting transcription | **Study Hermes + OpenHuman** — Google Meet plugin pattern | Hermes + OpenHuman |

**Key Files to Trace:**
- Hermes: `tools/speech/` — STT integration
- Hermes: `plugins/meet/` — Google Meet plugin
- OpenHuman: `src/meet/`, `src/meet_agent/` — meeting agent

**Atomic Logic — STT Pipeline:**
1. Audio arrives (Telegram voice note, uploaded file)
2. Route: Groq Whisper API (fast, free tier) → fallback: local whisper-cpp (slower)
3. Transcription → YAML frontmatter `.md` → vault → PageIndex tree rebuild
4. This IS #35 (Audio Transcription Pipeline)

**Adaptation:** Locus already designed #35 and #45 (Voice Call Interface). The Hermes STT integration pattern is the fastest path to implementation.

---

## §15 — Web Search

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Web search tools | ✅ **Keep Locus** — 5 integrations already built | N/A |

**Adaptation:** Locus already has the strongest web search coverage. No adoption needed.

---

## §16 — Browser Automation

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| CDP Playwright | **Steal from Hermes** — persistent browser contexts with stealth | Hermes |
| Multi-account scraping | ✅ **Keep Locus** — #27 already designed for multi-account Playwright | N/A |

**Key Files to Trace:**
- Hermes: `tools/browser/` — Playwright with Camofox/Chromium

**Atomic Logic — Browser Automation:**
- Playwright persistent context per account (cookies preserved)
- Stealth: Camofox or playwright-stealth for anti-detection
- Screenshot capture → vision model for page understanding
- This extends #27 (Nightly Vault Ingestion) and #101 (Smart Browser Automation)

**Adaptation:** Locus already plans Playwright for chat scraping (#27). Hermes's browser tool adds general-purpose browser automation.

---

## §17 — Channels / Gateway

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Multi-platform gateway | **Steal from Hermes** — 25 chat integrations architecture with dedup | Hermes |
| Telegram adapter | ✅ **Keep Locus** — primary interface, already built | N/A |
| Discord adapter | **Steal from Hermes** — as Phase 2 expansion | Hermes |
| Platform adapters | **Steal from Hermes** — abstract adapter pattern | Hermes |

**Key Files to Trace:**
- Hermes: `gateway/` — multi-platform gateway architecture
- Hermes: `gateway/adapters/` — per-platform adapters

**Atomic Logic — Platform Adapter Interface:**
```
interface PlatformAdapter:
  receive(raw_message) → NormalizedMessage
  send(response, channel_id) → DeliveryConfirmation
  get_capabilities() → {supports_inline_keyboards, supports_voice, supports_images, max_message_length}
```
- Normalize all incoming messages to `NormalizedMessage{text, sender_id, channel_id, platform, attachments, metadata}`
- Dedup: hash(sender_id + text + timestamp_bucket_5min) → skip if seen
- Route: NormalizedMessage → Query Router (#57) → response → adapter.send()

**Adaptation:** Locus already has 16 channel features listed. The adoption is the abstract adapter pattern for clean multi-platform expansion. Telegram stays primary; others are opt-in.

---

## §18 — MCP

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| MCP client | **Steal from Hermes** — native MCP with circuit breakers | Hermes |
| MCP server | ✅ **Keep Locus** — #54 (Locus as Universal MCP Server) already designed | N/A |
| Dynamic MCP registration | **Steal from Hermes** — runtime tool registration from MCP servers | Hermes |
| GitMCP | ✅ **Keep Locus** — #78 already includes GitMCP | N/A |

**Key Files to Trace:**
- Hermes: `plugins/mcp/` — MCP client with circuit breakers
- Hermes: `acp_adapter/` — Agent Communication Protocol

**Atomic Logic — MCP Client with Circuit Breakers:**
1. Connect to MCP server → list tools → register in `skills_registry`
2. Circuit breaker per server: `{state: CLOSED|OPEN|HALF_OPEN, failure_count, last_failure_time}`
3. CLOSED: normal operation. 5 consecutive failures → OPEN
4. OPEN: reject calls immediately, return cached error. After 30s → HALF_OPEN
5. HALF_OPEN: allow 1 probe call. Success → CLOSED. Failure → OPEN

**Adaptation:** Maps to Locus's #78 (Dynamic MCP) and #54 (Universal MCP Server). FastMCP is the library. Circuit breakers add resilience.

---

## §19 — Computer Use

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Screen intelligence | **Study OpenHuman** — `screen_intelligence` module | OpenHuman |
| Desktop companion | **Study OpenHuman** — `desktop_companion` module | OpenHuman |

**Atomic Logic:**
- Phase 3 feature. Study OpenHuman's approach but defer implementation.
- Locus already has 4 computer use features listed as existing.

---

## §20 — Health & Observability

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Health monitoring | **Steal from OpenHuman** — `health` module pattern | OpenHuman |
| Heartbeat | ✅ **Keep Locus** — `heartbeat/notification.py` exists | N/A |
| Langfuse observatory | **Steal from Hermes** — API/LLM request telemetry hooks | Hermes |
| Cost tracking | **Steal from Hermes** — `usage_pricing.py` + `credits_tracker.py` | Hermes |

**Key Files to Trace:**
- OpenHuman: `src/health/` — health monitoring
- Hermes: `agent/usage_pricing.py` — cost tracking
- Hermes: `agent/credits_tracker.py` — credit management

**Atomic Logic — Cost Tracking:**
- Per-request log: `{timestamp, model, input_tokens, output_tokens, cached_tokens, cost_usd}`
- Daily aggregation → `daily_cost` PG table
- Alert if daily cost exceeds threshold (default $0.05 for Gemini Flash at ~$0.012/day)
- Weekly cost report in #28 (Weekly Synthesis)

**Adaptation:** Locus already has heartbeat. Add cost tracking (simple PG table + per-request logging) and optional Langfuse integration.

---

## §21 — Wallet / Web3

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Web3 / wallet | **SKIP** — Not relevant for Locus's Life OS scope | N/A |

---

## §22 — Team / Billing

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Team / billing | **SKIP** — Single-user PCOS. Not applicable | N/A |

---

## §23 — i18n

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| i18n / Localization | **SKIP** — Single user (English + Hinglish). Not needed | N/A |

---

## §24 — Connectivity & Devices

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Multi-device | **SKIP for now** — Single-user, single VM. Phase 3 consideration | N/A |

---

## §25 — SDK (Pi-specific)

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| SDK | **Study Pi** — `createAgentSession()` factory pattern for future embeddable SDK | Pi |

**Key Files to Trace:**
- Pi: `pi-coding-agent/sdk/` — session factory, resource loader

**Atomic Logic:**
- Future: expose Locus as an importable Python package
- `locus.create_session(config)` → returns session object with `.prompt()`, `.cancel()`, `.set_model()`
- Not immediate priority but study Pi's pattern for clean API design

---

## §26 — Export & Artifacts

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| HTML session export | **Steal from Pi** — `export-html/` template | Pi |
| JSON session export | **Steal from Pi** — `--export json` | Pi |
| Markdown session export | **Steal from Pi** — `--export md` | Pi |
| Trajectory recording | **Steal from Hermes** — `trajectory.py` for batch evaluation | Hermes |
| Artifacts | **Steal from OpenHuman** — `artifacts/` module (store, ops, schemas, tools) | OpenHuman |

**Key Files to Trace:**
- Pi: `pi-coding-agent/export-html/` — HTML export template
- Hermes: `agent/trajectory.py` — trajectory recording
- OpenHuman: `src/artifacts/` — artifact management

**Atomic Logic — Trajectory Recording:**
- Every agent interaction = one trajectory entry: `{messages, tool_calls, tool_outputs, final_response, tokens, cost, duration}`
- Store in `trajectories` PG table
- Batch runner: replay trajectories for regression testing
- This enables #30 (RLHF) — trajectories become training data

**Adaptation:** Locus already plans the Daily AI Chat Archiver (#27). Trajectory recording is a superset — capture structured data, not just chat logs. Session export is simple formatters over trajectory data.

---

## §27 — Integrations

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Composio | ✅ **Keep Locus** — already migrating to manual OAuth | N/A |
| Polymarket | ✅ **Keep Locus** — `polymarket.py` exists | N/A |
| Webhooks | ✅ **Keep Locus** — `webhooks.py` exists | N/A |
| Google Calendar | ✅ **Keep Locus** — #42 already designed with manual OAuth | N/A |
| Gmail | ✅ **Keep Locus** — #44 already designed | N/A |
| Meet / video calls | **Steal from Hermes** — Google Meet plugin pattern | Hermes |
| Team collaboration | **Study OpenHuman** — `team`, `people` modules for future reference | OpenHuman |

**Adaptation:** Locus has strong integration coverage. Only missing: Meet plugin (steal from Hermes) and team collaboration (Phase 3, study OpenHuman).

---

## §28 — Install & Distribution

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| pip install | **Steal from Hermes** — standard Python packaging | Hermes |
| Docker | **Steal from Hermes** — Docker builds for deployment | Hermes |
| Self-update | **Steal from Pi** — `windows-self-update.ts` pattern (adapt for pip) | Pi |

**Atomic Logic — Distribution:**
- `pip install locus-os` — primary install method
- Docker: `docker-compose.yml` already designed (#20)
- Self-update: `locus update` → `pip install --upgrade locus-os` → restart systemd service

**Adaptation:** Locus is VM-based (Oracle Cloud). Distribution = pip install + systemd service. Docker is for the database stack only.

---

## §29 — CI/CD & Testing

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Unit tests | **Steal from Hermes** — pytest patterns | Hermes |
| CI pipeline | **Steal from Hermes** — full CI (lint, test, typecheck) | Hermes |
| Linting | **Steal from Hermes** — Ruff for Python linting | Hermes |
| Type checking | **Steal from Hermes** — mypy for type checking | Hermes |
| Batch trajectory runner | **Steal from Hermes** — `trajectory.py` for regression testing | Hermes |

**Key Files to Trace:**
- Hermes: `tests/` — pytest patterns
- Hermes: `scripts/` — CI scripts

**Atomic Logic:**
- `pytest` for unit tests, `ruff` for linting, `mypy` for type checking
- CI: GitHub Actions → lint → test → type check → Docker build
- Trajectory runner: replay saved trajectories, compare outputs, flag regressions

**Adaptation:** Standard Python CI. Hermes is the reference because it's also Python.

---

## §30 — Utilities

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Git integration | ✅ **Keep Locus** — `git_ops.py` exists | N/A |
| Clipboard | **Steal from Pi** — `clipboard.ts` pattern (Python: `pyperclip`) | Pi |
| Image handling | **Steal from Pi** — resize, convert, EXIF orientation | Pi |
| MIME detection | **Steal from Hermes** — `binary_extensions.py` binary detection | Hermes |
| Shell integration | **Steal from Pi** — `shell.ts` pattern for shell operations | Pi |
| Fuzzy matching | **Steal from Hermes** — `fuzzy_match.py` | Hermes |
| URL safety checks | **Steal from Hermes** — `url_safety.py` | Hermes |
| Error classifier | **Steal from Hermes** — `error_classifier.py` | Hermes |
| Auxiliary LLM client | **Steal from Hermes** — `auxiliary_client.py` | Hermes |
| Auth storage | **Combine Pi + Hermes** — encrypted credential storage | Pi + Hermes |

**Key Files to Trace:**
- Hermes: `tools/fuzzy_match.py`, `tools/url_safety.py`, `agent/error_classifier.py`, `agent/auxiliary_client.py`
- Pi: `pi-agent-core/clipboard.ts`, `pi-agent-core/shell.ts`

**Atomic Logic — Error Classifier:**
- Classify errors into categories: `NETWORK`, `AUTH`, `RATE_LIMIT`, `TIMEOUT`, `PERMISSION`, `NOT_FOUND`, `VALIDATION`, `UNKNOWN`
- Each category has a retry strategy and user-facing message
- Regex pattern matching on error strings + HTTP status codes

**Adaptation:** Utility functions are simple Python modules. Most are <100 lines each. Copy patterns, implement in Python.

---

## §31 — Life OS (Locus-only)

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| All 16 Life OS features | ✅ **Keep Locus** — entirely Locus-unique. No equivalent in Pi/Hermes/OpenHuman | N/A |

**No adoption needed.** These are Locus's core differentiators.

---

## §32 — Brain Engine (Locus-only)

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| All 8 Brain Engine features | ✅ **Keep Locus** — entirely Locus-unique | N/A |

**No adoption needed.**

---

## §33 — Vault & Knowledge Intelligence (Locus-only)

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| PageIndex | ✅ **Keep Locus** — #26 already designed. See [Part II](#pageindex--vectorless-retrieval) for enhanced version | N/A + External |
| Nightly Vault Ingestion | ✅ **Keep Locus** — #27 already designed | N/A |
| Obsidian Dashboard | ✅ **Keep Locus** — #36 already designed | N/A |

**No adoption from other codebases. Enhancement via PageIndex open-source library — see Part II.**

---

## §34 — Interface Philosophy (Locus-only)

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| All 11 Interface features | ✅ **Keep Locus** — Locus-specific architectural decisions | N/A |

**No adoption needed.**

---

## §35 — Obsidian & Note-Taking

| Feature | Verdict | Source(s) |
|---------|---------|-----------|
| Obsidian integration | **Combine Hermes + OpenHuman** — Hermes's `note-taking` skill (read/search/create/edit) + OpenHuman's Memory Tree (wikilinks/frontmatter) | Hermes + OpenHuman |
| Excalidraw | **Steal from Hermes** — `diagramming/excalidraw` skill | Hermes |

**Key Files to Trace:**
- Hermes: `skills/note-taking/` — Obsidian vault operations
- Hermes: `skills/diagramming/excalidraw/` — Excalidraw JSON generation
- OpenHuman: `src/memory_tree/` — Obsidian-compatible wiki

**Atomic Logic — Obsidian Integration:**
1. Vault operations via direct file I/O (not Obsidian Local REST API — per architecture decision)
2. Read: parse .md with YAML frontmatter → structured note object
3. Write: assemble frontmatter + content → write to vault path → git commit + push
4. Search: grep over vault (fast for <10K files) or PageIndex tree search (smart retrieval)
5. Wikilinks: `[[note-name]]` resolution via filename index

**Adaptation:** Locus already plans direct file I/O for vault operations (#22). Hermes's note-taking skill provides the tool interface (read/search/create/edit). OpenHuman's Memory Tree provides the Obsidian-compatible format patterns.

---

## §36 — Key Paths

No adoption needed — each agent has its own path conventions. Locus uses:
- `~/.locus/` — config root
- `/vault/` — Obsidian vault on VM
- PG + Neo4j — databases

---

## §37 — Summary Counts

**Adoption Summary:**

| Source | Features Adopted | Primary Use |
|--------|-----------------|-------------|
| **Hermes** | ~45 features | Agent loop, CLI, config, tools, skills, gateway, security, CI, browser, context compression, providers |
| **Pi** | ~15 features | Sub-agents, session management, export, reasoning levels, SDK pattern, clipboard/shell utilities |
| **OpenHuman** | ~12 features | Memory system patterns, artifacts, health monitoring, meeting integration, Obsidian compatibility |
| **External: neo4j-labs/agent-memory** | Core memory | Short-term + long-term + reasoning memory via graph |
| **External: headroomlabs-ai/headroom** | Core compression | Context compression (CCR pipeline) |
| **External: VectifyAI/PageIndex** | Core retrieval | Vectorless tree-based retrieval |
| **External: karpathy/autoresearch** | Research automation | Autonomous experiment loop |

---

# Part II: Memory & Retrieval Standard — The Locus Tri-Stack

> **The Standard:** Neo4j Agent Memory + Headroom + PageIndex
> **Alternative providers (user-configurable):** mem0, supermemory, honcho, mastra, cognee, personal integrations

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        QUERY ENTERS LOCUS                           │
│                                                                     │
│  User Message → Query Router (#57) → Intent + Source List           │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │   NEO4J AGENT       │  │    PAGEINDEX     │  │   HEADROOM    │  │
│  │   MEMORY            │  │                  │  │               │  │
│  │                     │  │  Vectorless      │  │  Context      │  │
│  │  Short-term:        │  │  Tree Index      │  │  Compression  │  │
│  │   • Conversations   │  │                  │  │               │  │
│  │   • Messages        │  │  1. MD headers   │  │  1. Cache     │  │
│  │   • Per-session     │  │     → tree       │  │     Aligner   │  │
│  │                     │  │  2. LLM reasons  │  │  2. Content   │  │
│  │  Long-term:         │  │     over tree    │  │     Router    │  │
│  │   • Entities        │  │  3. Returns      │  │  3. Smart     │  │
│  │   • Preferences     │  │     relevant     │  │     Crusher   │  │
│  │   • Facts           │  │     sections     │  │  4. Code      │  │
│  │   • Knowledge       │  │                  │  │     Compress   │  │
│  │     graph           │  │  No vectors      │  │  5. Kompress  │  │
│  │                     │  │  No chunking     │  │     v2-base   │  │
│  │  Reasoning:         │  │  No embeddings   │  │               │  │
│  │   • Traces          │  │                  │  │  CCR: Cache → │  │
│  │   • Tool usage      │  │  98.7% accuracy  │  │  Compress →   │  │
│  │   • Past decisions  │  │  on FinanceBench │  │  Retrieve     │  │
│  │                     │  │                  │  │               │  │
│  └────────┬────────────┘  └────────┬─────────┘  └──────┬────────┘  │
│           │                        │                    │           │
│           ▼                        ▼                    ▼           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              CONTEXT FORGE (#58) — 800-Token Assembler     │    │
│  │                                                             │    │
│  │  Layer 1: user_identity (80t) ← #62                       │    │
│  │  Layer 2: temporal_context (60t) ← #60 State Engine        │    │
│  │  Layer 3: pg_events (180t) ← #7 Behavioral Events         │    │
│  │  Layer 4: neo4j_pathways (150t) ← Neo4j Agent Memory      │    │
│  │  Layer 5: pageindex_content (300t) ← PageIndex tree search │    │
│  │  Layer 6: web_results (100t) ← if EXTERNAL_KNOWLEDGE      │    │
│  │  Buffer: 30t                                                │    │
│  │                                                             │    │
│  │  All layers compressed by Headroom before assembly          │    │
│  │  Truncate by relevance score, NOT recency                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│                    LLM Response Generation                          │
│                              │                                      │
│                              ▼                                      │
│              Headroom compresses response for storage               │
│                              │                                      │
│                              ▼                                      │
│         Neo4j Agent Memory stores conversation + entities           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Neo4j Agent Memory — Graph-Native Memory Layer

### What It Provides
- **Short-Term Memory:** Conversations & messages, per-session history, vector + text search
- **Long-Term Memory:** Entities, preferences, facts → knowledge graph (POLE+O model: Person, Object, Location, Event + Organization)
- **Reasoning Memory:** Reasoning traces & tool usage, learn from past decisions, similar task retrieval

### Data Model (POLE+O)
```
(Person) -[:WORKS_AT]→ (Organization)
(Person) -[:LOCATED_IN]→ (Location)
(Person) -[:PARTICIPATED_IN]→ (Event)
(Person) -[:PREFERS]→ (Object)
(Event) -[:OCCURRED_AT]→ (Location)
```

### Entity Extraction Pipeline
1. **Stage 1 — spaCy NER:** Fast, deterministic extraction of named entities (PERSON, ORG, GPE, DATE)
2. **Stage 2 — GLiNER:** Zero-shot NER for domain-specific entities not in spaCy's vocabulary
3. **Stage 3 — LLM:** Extract complex relationships and implicit entities that NER misses
4. **Entity Resolution:** Dedup via string similarity + graph connectivity — same entity with different mentions gets merged

### How Locus Uses It
- Replace Locus's current ad-hoc Neo4j entity extraction with the `neo4j-agent-memory` Python SDK
- `pip install neo4j-agent-memory` — single dependency
- Wraps existing Neo4j instance (Locus already runs Neo4j 5.x)
- `client.schema.adopt_existing_graph(...)` — adopt Locus's current graph schema without migration
- Multi-stage extraction replaces Locus's #27 (entity extraction step) with a production pipeline
- Reasoning memory enables #64 (Hebbian) — past reasoning traces feed reinforcement learning
- `client.buffered.submit(...)` — fire-and-forget writes for non-blocking ingestion

### Integration Points
- **#7 Behavioral Event Stream:** Every event → `client.short_term.add_message()`
- **#26 PageIndex:** Entity extraction during ingestion feeds → `client.long_term.add_entity()`
- **#27 Nightly Ingestion:** Batch extraction uses → `client.long_term.extract_entities(text)`
- **#49 Thinking Patterns:** Pattern storage as → ConceptNodes via `client.long_term`
- **#58 Context Forge:** `neo4j_pathways` layer uses → `client.get_context(query)`
- **#64 Hebbian Memory:** Edge weight operations via Neo4j Agent Memory's graph layer

### Swappability
The memory layer is behind a provider interface:
```
interface MemoryProvider:
  store_message(session_id, role, content, metadata)
  store_entity(name, type, properties)
  extract_entities(text) → List[Entity]
  get_context(query, session_id) → ContextBlock
  search(query, filters) → List[Result]
```
Alternative providers implement this same interface:
- `mem0` — managed memory service
- `supermemory` — open-source memory layer
- `honcho` — user context management
- `mastra` — AI agent memory
- `cognee` — cognitive memory engine
- Custom integrations via the interface

---

## PageIndex — Vectorless Retrieval

### What It Provides
- **No Vector DB:** Uses document structure + LLM reasoning for retrieval
- **No Chunking:** Documents organized into natural sections (headers → hierarchy)
- **Reasoning-Based Retrieval:** LLM navigates the tree structure like a human reading a table of contents
- **98.7% accuracy** on FinanceBench (state-of-the-art)

### How It Works
1. **Index Build Phase:**
   - Parse Markdown headers (# → ######) → flat node list `{title, line_num, level}`
   - Build hierarchical tree (parent/child via header depth)
   - Tree thinning: nodes < 500 tokens → merge into parent
   - Optional: LLM generates 1-sentence summaries per leaf node
   - Store tree as JSON in `pageindex_workspace/`

2. **Retrieval Phase:**
   - Query enters → LLM receives tree structure (like a table of contents)
   - LLM reasons: "Based on this query, which sections are relevant?"
   - LLM calls `get_page_content(pages="5-7")` to retrieve actual content
   - May iterate: read content → need more context → navigate tree further
   - Returns relevant sections with page references

3. **Three Agent Tools:**
   - `get_document()` — full document metadata
   - `get_document_structure()` — tree index (the "table of contents")
   - `get_page_content(pages="start-end")` — actual content by page range

### How Locus Uses It
- **#26 (PageIndex + Direct Retrieval)** — already designed in Locus
- Self-hosted PageIndex (local fork of `VectifyAI/PageIndex`)
- Every vault `.md` file gets a tree index
- PageIndex File System layer for corpus-scale search across all vault files
- Replaces all vector-based retrieval (Qdrant, ChromaDB already removed)
- Tree rebuilds trigger on git diff (vault file changes) during #27 (Nightly Ingestion)

### Integration Points
- **#22 Vault Sync:** Git diff triggers tree rebuild for changed files
- **#27 Nightly Ingestion:** New/changed files → PageIndex tree rebuild
- **#58 Context Forge:** `pageindex_content` layer (300 tokens) uses tree search results
- **#57 Query Router:** KNOWLEDGE_RETRIEVAL intent → PageIndex tree search

### Swappability
```
interface RetrievalProvider:
  index_document(path, content) → IndexResult
  search(query, context) → List[Section]
  get_document_structure(doc_id) → TreeNode
  get_content(doc_id, page_range) → str
```
Alternative: vector RAG (if user prefers), hybrid search, or managed PageIndex cloud service.

---

## Headroom — Context Compression Layer

### What It Provides
- **60-95% token reduction** on tool outputs, logs, RAG chunks, files, conversation history
- **Reversible compression (CCR):** Cache-Compress-Retrieve — originals stored locally, LLM can request uncompressed version
- **Content-aware:** Different compressors for JSON, code, prose, logs
- **KV cache optimization:** CacheAligner stabilizes message prefixes for provider-side cache hits

### Compression Pipeline
1. **CacheAligner:** Normalize dynamic content (timestamps, IDs) → stable prefixes → higher KV cache hit rate
2. **ContentRouter:** Auto-detect content type → route to specialized compressor:
   - **SmartCrusher:** JSON arrays/objects → structural compression
   - **CodeCompressor:** AST-aware compression (Python, JS, Go, Rust, Java, C++)
   - **Kompress-v2-base:** Custom HuggingFace model for prose/log compression
3. **CCR Retrieval Tool:** If LLM needs full content → `retrieve_original(content_id)` → fetch from local cache

### How Locus Uses It
- **Deployment mode: Library** — import directly into Python backend
- Sits between tool outputs and Context Forge (#58)
- Every tool output → Headroom compress → compressed version enters Context Forge
- Every LLM response → Headroom compress before storage (saves PG space)
- CCR tool registered in tool registry — LLM can request originals when reasoning

### Integration Points
- **#58 Context Forge:** All 5 layers pass through Headroom before assembly
- **#43 Telegram Bot:** Tool outputs compressed before context assembly
- **#88 Context Compression (Hermes feature):** Headroom IS the compression engine
- **#59 Inner Loop:** Compressed context for background reasoning (saves cost)
- **Session compaction:** When session exceeds token limit, Headroom compresses older messages

### Cost Impact
- Locus currently targets ~$0.012/day on Gemini Flash
- Headroom's 60-95% reduction means: even with expanded context windows and more aggressive retrieval, cost stays under $0.02/day
- The compression is the key enabler for larger context windows without cost explosion

### Swappability
```
interface CompressionProvider:
  compress(content, content_type) → CompressedContent
  retrieve_original(content_id) → str
  get_compression_stats() → {ratio, tokens_saved, cache_hit_rate}
```
Alternative: no compression (for development/debugging), custom compressor, or managed Headroom service.

---

## File Crawlers for Proactive Agent Work

### Concept
File crawlers enable Locus to proactively scan and process files without being asked — extending beyond the vault to any configured directory.

### Crawler Types
1. **Vault Crawler** (primary): Scans `/vault/` via git diff → triggers PageIndex rebuild + entity extraction
2. **AI Chat Crawler** (via Playwright): Scrapes ChatGPT/Claude/Gemini/Perplexity → `.md` files → vault
3. **Code Crawler** (future): Scans project directories for README, TODO, CHANGELOG → extract project context
4. **Media Crawler** (future): Process audio/video files → transcription → vault
5. **Email Crawler** (#44): Gmail API → extract actionable items

### Crawler Interface
```
interface Crawler:
  name: str
  schedule: cron_expression  # When to run
  source_path: str           # What to scan
  file_patterns: List[str]   # File glob patterns
  crawl() → List[CrawledItem]
  process(item: CrawledItem) → ProcessedItem  # Extract, transform
  store(item: ProcessedItem)  # Push to vault/PG/Neo4j
```

### How Crawlers Feed the Memory Stack
```
Crawler Output → PageIndex (tree index) + Neo4j Agent Memory (entities) + PG (metadata)
                         ↓                          ↓                         ↓
              Context Forge retrieves    Hebbian reinforces      Behavioral events
              via tree search            relevant pathways       logged for patterns
```

### Adaptation
- Crawlers are scheduled via APScheduler (Locus's existing scheduler)
- Each crawler is a Python class implementing the `Crawler` interface
- Registered in `skills_registry` as scheduled skills
- #27 (Nightly Vault Ingestion) is the primary crawler — already designed

---

## Memory Provider Alternatives

Locus uses Neo4j Agent Memory + PageIndex + Headroom as the **standard**, but users can swap any component:

| Provider | What It Replaces | Tradeoff |
|----------|-----------------|----------|
| **mem0** | Neo4j Agent Memory (long-term) | Managed service, simpler setup, less graph power |
| **supermemory** | Neo4j Agent Memory | Open-source, vector-based, easier horizontal scaling |
| **honcho** | Neo4j Agent Memory (user context) | Specialized for user profiles, less general knowledge graph |
| **mastra** | Full memory stack | AI-native framework, opinionated, less customizable |
| **cognee** | Neo4j Agent Memory (knowledge) | Cognitive engine, good for learning patterns |
| **Custom** | Any component | User implements the provider interface |

### Provider Configuration
```yaml
# In SETTINGS.yaml
memory:
  standard: "neo4j-agent-memory"  # Default
  alternatives:
    - name: "mem0"
      config:
        api_key: "..."
    - name: "honcho"
      config:
        base_url: "..."

retrieval:
  standard: "pageindex"  # Default
  alternatives:
    - name: "vector-rag"
      config:
        provider: "pgvector"

compression:
  standard: "headroom"  # Default
  alternatives:
    - name: "none"  # No compression (dev mode)
```

---

# Part III: Autoresearch Integration

> **Source:** `karpathy/autoresearch` — autonomous ML experiment loop
> **Purpose in Locus:** Make autoresearch invokeable as a skill for autonomous experimentation

## What Autoresearch Does
- Autonomous loop: modify code → run experiment → evaluate metric → keep/discard
- Git as memory: failed experiments → `git rollback`, successful → `git commit`
- "Research while you sleep" — define goal in `program.md`, agent iterates overnight
- 66K+ GitHub stars, community has generalized beyond ML training

## How Locus Invokes It

### Invocation Methods
1. **Telegram command:** `/research {goal} --metric {metric_name} --target {target_file}`
2. **Scheduled:** APScheduler cron → autonomous research during off-hours
3. **Inner Loop trigger:** #59 detects optimization opportunity → spawns research task

### Integration Architecture
```
User: /research "improve DCS prediction accuracy"
          --metric "mae"
          --target "prediction/dcs_model.py"
          --max_iterations 50
          --duration "4h"

Locus:
  1. Create program.md from user goal
  2. Create metric evaluation script
  3. Spawn autoresearch subprocess:
     - Working directory: isolated git branch
     - Coding agent: Locus delegates to external harness (see Part IV)
     - Evaluation: run metric script after each iteration
     - Git: commit improvements, rollback failures
  4. Monitor: progress logged to behavioral_events
  5. On completion: Telegram summary with results
  6. If improvements found: PR to main branch for review
```

### Autoresearch as a Locus Skill
```yaml
# SKILL.md
name: "autoresearch"
description: "Autonomous experimentation loop — modify code, evaluate, keep/discard"
trigger_conditions:
  intents: ["TASK_PLANNING"]
  keywords: ["research", "experiment", "optimize", "improve", "tune"]
tools:
  - name: "start_research"
    schema:
      goal: string
      metric_name: string
      target_file: string
      max_iterations: int (default: 100)
      max_duration_hours: float (default: 8)
  - name: "check_research"
    schema:
      research_id: string
  - name: "stop_research"
    schema:
      research_id: string
```

### Safety Rails
- Runs on isolated git branch (never touches main)
- Sandboxed execution: no network access during experiments
- Cost cap: maximum LLM spend per research session
- Duration cap: auto-stop after configured hours
- Telegram approval required before merging improvements to main

### Adaptation
- Autoresearch is a subprocess skill, not integrated into Locus's core
- Locus provides: goal definition, metric evaluation, progress monitoring, result reporting
- The actual code modification is delegated to external harness (see Part IV)
- Registered in `skills_registry` as an async skill

---

# Part IV: Harness Delegation Architecture

> **Principle:** Locus does NOT have its own coding harness. It delegates to external coding agents.
> **Supported Harnesses:** Antigravity (Gemini), Claude Code, OpenCode, Pi, Aider, Codex, Cursor

## Why Harness Delegation

Locus is a **Life OS** — its core competency is understanding the user, managing goals, and orchestrating work. Coding is delegated to purpose-built tools that are better at it:

1. **Avoid duplication:** Coding harnesses have thousands of hours of investment in sandboxing, file editing, code understanding, testing
2. **Best tool for the job:** Different harnesses excel at different tasks (Antigravity for complex refactors, Claude Code for quick edits, Aider for iterative work)
3. **User choice:** The user already has their preferred tools configured and authenticated
4. **Always up-to-date:** Harnesses update independently; Locus doesn't need to maintain code editing tools

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        LOCUS CORE                              │
│                                                                │
│  Task → Harness Selector → Prompt Generator → Harness Invoke  │
│                                    │                           │
│                     ┌──────────────┼──────────────┐            │
│                     ▼              ▼              ▼            │
│              ┌─────────┐   ┌─────────────┐  ┌──────────┐      │
│              │Antigrav- │   │ Claude Code │  │  Aider   │      │
│              │ity CLI   │   │    CLI      │  │   CLI    │      │
│              └─────────┘   └─────────────┘  └──────────┘      │
│                     │              │              │            │
│                     ▼              ▼              ▼            │
│              ┌─────────────────────────────────────────┐       │
│              │           Working Directory              │       │
│              │         (git branch isolation)           │       │
│              └─────────────────────────────────────────┘       │
│                                    │                           │
│                                    ▼                           │
│              Result Capture → Evaluation → Report to User      │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Harness Registry

```yaml
# In SETTINGS.yaml
harnesses:
  default: "antigravity"  # User's preferred harness
  available:
    - name: "antigravity"
      command: "gemini"  # or whatever the CLI command is
      invoke_pattern: "{command} -p '{prompt}'"
      capabilities: ["code_edit", "refactor", "debug", "test", "explain"]
      max_cost_per_invoke: 1.00  # USD

    - name: "claude_code"
      command: "claude"
      invoke_pattern: "{command} -p '{prompt}' --allowedTools '{tools}'"
      capabilities: ["code_edit", "refactor", "debug", "test"]
      max_cost_per_invoke: 2.00

    - name: "aider"
      command: "aider"
      invoke_pattern: "{command} --message '{prompt}'"
      capabilities: ["code_edit", "pair_program"]
      max_cost_per_invoke: 0.50

    - name: "opencode"
      command: "opencode"
      invoke_pattern: "{command} '{prompt}'"
      capabilities: ["code_edit", "debug"]
      max_cost_per_invoke: 0.50

    - name: "pi"
      command: "pi"
      invoke_pattern: "{command} -p '{prompt}' --yolo"
      capabilities: ["code_edit", "refactor", "debug", "test", "sub_agents"]
      max_cost_per_invoke: 1.50
```

## Harness Selection Logic

```
function select_harness(task):
  1. Parse task requirements: {type, complexity, language, files_affected}
  2. Filter available harnesses by capabilities
  3. If user has explicit preference → use it
  4. Else rank by:
     a. Task-type match score
     b. Historical success rate for similar tasks
     c. Cost efficiency
  5. Return top-ranked harness
```

## Prompt Generation for Harnesses

Locus generates rich prompts for external harnesses by assembling context from its memory stack:

```
function generate_harness_prompt(task, harness):
  1. Context from Context Forge:
     - Relevant code context (via PageIndex tree search over codebase)
     - User's coding preferences (from user_identity)
     - Project conventions (from vault/project docs)
  2. Task specification:
     - Clear objective
     - Success criteria
     - File scope (which files to touch)
     - Test expectations
  3. Constraints:
     - "Do not modify files outside {scope}"
     - "Run tests after changes"
     - "Commit with descriptive message"
  4. Format for specific harness CLI:
     - Escape special characters
     - Respect harness's max prompt length
     - Include harness-specific flags (e.g., --yolo for Pi)
```

## Result Capture

After harness execution:
1. Parse stdout/stderr for: files changed, tests run, errors encountered
2. `git diff` → capture actual code changes
3. Run project-specific validation (tests, lint, type check)
4. Log to behavioral_events: `{harness_used, task_type, success, duration, cost, files_changed}`
5. Report to user via Telegram:
   - Summary of changes
   - Test results
   - Cost
   - `[Approve] [Rollback] [Review]` inline keyboard

## Integration with Autoresearch

When autoresearch needs to modify code:
1. Autoresearch generates the modification goal
2. Locus's harness delegator selects appropriate harness
3. Harness makes the change on isolated branch
4. Autoresearch evaluates the metric
5. Keep (git commit) or discard (git rollback)
6. Loop

## Safety

- All harness invocations run on isolated git branches
- Cost caps per invocation and per session
- Telegram approval before merging any changes to main
- Audit log: every harness invocation logged with full context
- Rollback: `git revert` always available

---

# Appendix A: Master Cross-Reference

| Locus Feature # | This Document Section | Adoption Source |
|-----------------|----------------------|-----------------|
| #1–#18 | §31 (Life OS) | Keep Locus |
| #19–#25 | §1D (Startup), §29 (CI/CD) | Keep Locus |
| #26 | Part II (PageIndex) | External: VectifyAI/PageIndex |
| #27 | Part II (Crawlers) | Keep Locus + Hermes browser |
| #28 | §10 (Learning) | Keep Locus |
| #29 | §4 (Memory) | Keep Locus |
| #30 | §10 (Learning) | Keep Locus |
| #31 | §11 (Subagents) | Pi + Hermes |
| #32 | §10 (Learning) | Keep Locus + Hermes self-improvement |
| #33 | SCRAPPED | N/A |
| #34–#38 | §33 (Vault) | Keep Locus |
| #39 | §12 (Scheduling) | Keep Locus |
| #42–#44 | §27 (Integrations) | Keep Locus |
| #43 | §17 (Channels) | Keep Locus |
| #46–#48 | §13 (Security) | Keep Locus + Hermes security |
| #49 | §10 (Learning) | Keep Locus |
| #50–#54 | §18 (MCP) | Keep Locus + Hermes MCP client |
| #57 | §1B (Agent Loop) | Keep Locus |
| #58 | Part II (Context Forge) | Keep Locus + Headroom |
| #59 | §32 (Brain Engine) | Keep Locus |
| #60 | §32 (Brain Engine) | Keep Locus |
| #63 | §10 (Learning) | Keep Locus |
| #64 | §4 (Memory) | Keep Locus |
| #78 | §18 (MCP) | Hermes MCP client |
| #82 | §2 (Providers) | Hermes provider plugin |
| #86 | §11 (Subagents) | Pi sub-agents |
| #87–#123 | §37 (Hermes Copy Features) | Hermes — see individual verdicts |
| N/A | Part III | External: karpathy/autoresearch |
| N/A | Part IV | Locus-original architecture |

---

# Appendix B: Priority Order for Implementation

> Based on dependency analysis from ALL FEATURES POSSIBLE.md

### Phase 1: Foundation (Weeks 1-4)
1. Event Bus / Behavioral Event Stream (#7) — everything depends on this
2. Neo4j Agent Memory integration — replace ad-hoc graph operations
3. PageIndex local fork — vectorless retrieval operational
4. Agent Loop upgrade (Hermes patterns) — better iteration budget, retry, prompt building
5. Tool Registry upgrade — PG-backed, sandboxed

### Phase 2: Intelligence (Weeks 5-8)
6. Headroom integration — context compression operational
7. Context Forge enhancement — all 6 layers connected
8. Query Router (#57) — intent classification live
9. Skill registry (#52) — SKILL.md format, auto-discovery
10. CLI upgrade — doctor, status, config subcommands

### Phase 3: Autonomy (Weeks 9-12)
11. Harness Delegation — external coding agent integration
12. Autoresearch skill — autonomous experimentation
13. File crawlers — proactive agent work
14. Sub-agent spawning (Pi patterns)
15. MCP client with circuit breakers

### Phase 4: Polish (Weeks 13-16)
16. Session management — export, compaction, branching
17. Cost tracking + Langfuse
18. Trajectory recording — regression testing foundation
19. Browser automation (Hermes Playwright)
20. Self-improvement loop + autonomous curator

---

*End of Atomic Selections from Antigravity — July 13, 2026*
