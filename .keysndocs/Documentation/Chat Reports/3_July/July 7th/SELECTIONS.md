# SELECTIONS.md — Final Verdict: Best Codebase to Copy From Per Feature

> **Generated:** July 10, 2026
> **Judge:** Locus Architecture Analysis
> **Scope:** Sections 1–37 from ALL FEATURES POSSIBLE.md
> **Codebases evaluated:** Pi (TypeScript), Hermes (Python), OpenHuman (Rust+React), Locus (Python)
> **Selection principle:** Laziness first — prefer Python &gt; reuse existing Locus &gt; adapt from Hermes/OpenHuman &gt; design from scratch
> **User-prescribed additions:** neo4j-agent-memory + headroom + PageIndex + karpathy/autoresearch + native harness interoperability

---

## Legend

| Symbol | Meaning                                                    |
|--------|------------------------------------------------------------|
| ✅     | Locus already has this, keep/improve                      |
| 🔄 H   | Copy from **Hermes** (Python, closest lang match)         |
| 🔄 O   | Copy from **OpenHuman** (Rust, adapt logic to Python)     |
| 🔄 P   | Copy from **Pi** (TypeScript, adapt logic to Python)       |
| 📦     | Use pre-built package (install, don't rebuild)             |
| 🆕     | Design from scratch (nothing good to copy)                 |
| 🔀     | Hybrid: combine multiple sources                           |
| ⏭️     | Skip for now (defer to Phase 2+)                           |

---

## 1. Core Runtime & Architecture

### 1A. Tech Stack

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Language / runtime                 | ✅        | Python — already chosen, aligned with AI model API compatibility                                                                        |
| Package structure                  | 🔄 H     | Hermes's monolithic Python layout (`agent/`, `tools/`, `gateway/`, `cron/`, `skills/`) is closest to Locus's current structure         |
| Transport layer                    | ✅        | HTTP + Telegram webhook — already built                                                                                               |
| Lazy imports / cold-start          | 🔄 H     | Hermes's `lazy_deps.py` — 57% faster cold-start via lazy agent init, lazy imports, mtime-cached config, memoized tool defs            |
| Diff-based terminal rendering       | ⏭️       | Locus is Telegram-native, no TUI needed                                                                                                |
| Supply-chain hardening             | 🔄 H     | Hermes's pip dependency management pattern + Docker-based pinning                                                                      |
| Core runs in-process                | ✅        | Already in-process (no sidecar needed at single-user scale)                                                                            |
| Frontend ↔ core IPC                | ✅        | Gateway ↔ Core via function calls, not IPC (single-user VM)                                                                            |
| Event bus (typed pub/sub)           | 🔄 O     | OpenHuman's `event_bus/` — typed publish_global/subscribe_global pattern. Critical for Inner Loop. Adapt to Python with asyncio.Queues |

### 1B. Agent Loop

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Main agent loop                     | ✅        | `core/agent.py` — ToolRegistry + LlmProvider turn loop, works well. Enhance with Hermes patterns                                       |
| Turn context management             | 🔄 H     | Hermes's `turn_context.py` — per-turn state tracking. Better than Locus's basic request/response                                       |
| Turn retry / error recovery         | 🔄 H     | Hermes's `turn_retry_state.py` — exponential backoff, circuit breakers. OpenHuman's self-healing is in Rust                            |
| System prompt builder               | 🔄 H     | Hermes's `system_prompt.py` + `prompt_builder.py` — dynamic assembly with tool-aware injection                                         |
| Streaming + non-streaming           | 🔄 H     | Hermes's `stream_consumer.py` + `stream_dispatch.py` — clean dual-path architecture                                                    |
| Iteration budget / limits           | 🔄 H     | Hermes's `iteration_budget` module — default 90 iterations + grace call                                                                |
| Grace-turn after budget             | 🔄 H     | Hermes's pattern: one extra LLM call to produce final answer with context of exhaustion                                                |
| Interrupt checks                    | 🔄 H     | Hermes's per-iteration `_interrupt_requested` — enables safe cancellation                                                              |
| Tool-call dispatch & coercion       | 🔄 H     | Hermes's `handle_function_call()` with JSON Schema type coercion. More robust than Locus's current approach                            |
| Reasoning content                   | 🔄 H     | Hermes's thinking prefill continuation + `assistant_msg["reasoning"]` storage                                                           |
| Token tracking per turn             | ✅ 🔄 H  | Locus has `cost_tracker.py` — enhance with Hermes's `usage_pricing.py` + `credits_tracker.py` patterns                                 |
| Hint-based model routing            | 🔄 O     | OpenHuman's `hint:reasoning`, `hint:fast`, `hint:vision`, `hint:summarize`, `hint:code` — elegant but needs Python adaptation          |

### 1C. Configuration

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Config format                      | ✅        | SETTINGS.md (56KB, 28 sections) — keep. Add YAML companion for machine-readable config                                                 |
| Config migration                   | 🔄 H     | Hermes's `config migrate` pattern with version-aware migrations                                                                         |
| Config management CLI              | 🔄 H     | Hermes's `config show/set/path/env-path/check/migrate` — comprehensive CLI                                                             |
| Environment variable management     | 🔄 H     | Hermes's 19+ provider keys pattern. Locus already has `locus config env-path`                                                           |

### 1D. Startup & Lifecycle

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Onboarding flow                    | 🔄 H     | Hermes's `onboarding.py` + interactive wizard pattern. Locus already has setup wizard — enhance                                         |
| Agent initialization               | ✅        | `core/agent.py` + `create_agent()` works                                                                                              |
| Self-update                        | 🔄 P     | Pi's `version-check.ts` + `windows-self-update.ts` — clean version check pattern adaptable to Python                                   |
| Doctor / diagnostics               | 🔄 H     | Hermes's `hermes doctor [--fix]` — dependency/config diagnostics                                                                       |
| Status command                     | 🔄 H     | Hermes's `hermes status [--all]` — component-by-component health check                                                                 |

### 1E. Prompt Caching

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Prompt cache                       | 🔄 H     | Hermes's `prompt_caching.py` — configurable TTL (5min default, 1h opt-in). Adapt for AI model provider                                 |

### 1F. Background Review & Post-Turn

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Background review                  | 🔄 H     | Hermes's background review fork per turn — rubric-based skill review. Perfect for Locus's self-improvement                              |
| Autonomous Curator                 | 🔄 H     | Hermes's curator system — 7-day cycle, grades/consolidates/prunes skills. Can be adapted for Locus's skill ecosystem                   |

---

## 2. LLM Providers & Model System

### 2A. Provider Architecture

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Provider registry                  | ✅        | `resolve_provider()` in `core/agent.py` — 10+ providers already. Keep but modularize                                                   |
| Cross-provider fallback            | 🔄 H     | Hermes's automatic fallback chain. Even if Locus uses single-provider (AI model), having fallback is critical for reliability          |
| Live mid-session model switching   | 🔄 H     | Hermes's `/model` slash command pattern — inline button picker on Telegram                                                            |
| Mock / test provider               | 🔄 P     | Pi's `faux.ts` — mock provider for testing without API calls. Python adaptation needed                                                 |

### 2B. Provider Specifics

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| AI model (primary)                 | ✅        | Already the primary provider. Keep                                                                                                      |
| OpenAI compatible                  | ✅        | `LlmProvider` already handles OpenAI-compatible APIs. Keep                                                                             |

---

## 3. Tool System

### 3A. Tool Architecture

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Tool registry                      | ✅        | `ToolRegistry` in `core/agent.py` works. Enhance with Hermes patterns                                                                  |
| Tool policy / user filter           | 🔄 O     | OpenHuman's `tool_filter` + `classify_command` → `CommandClass`. Hermes's toolsets system (enable/disable). Combine both              |
| Tool timeout / budget              | 🔄 O     | OpenHuman's `tool_timeout` module — timeout per tool call. Python adaptation needed                                                    |
| Tool output limits                 | 🔄 H     | Hermes's `tool_output_limits.py` — save oversized results to file instead of destructive truncation                                    |
| Path security                      | 🔄 H     | Hermes's `path_security.py` for path sandboxing. OpenHuman's `cwd_jail` + `is_workspace_internal_path` (fail-closed)                   |
| Schema sanitization                | 🔄 H     | Hermes's `schema_sanitizer.py` — tool schema sanitization                                                                              |
| File mutation queue                | 🔄 P     | Pi's `file-mutation-queue.ts` — debounced, ordered file operations. Python adaptation                                                   |

### 3B. File & Code Tools

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| File read/write/edit               | ✅        | Already have these in `core/coding/`. Pi has the cleanest patterns for precise edit matching — use for reference                       |
| Shell / bash execution             | 🔄 H     | Hermes's terminal tool + PTY mode + background + multi-backend (docker/SSH/Modal). Keep Locus's BLOCKED_PATTERNS + add PTY             |
| Grep / search files                | 🔄 P     | Pi's ripgrep-backed grep. Already in Locus but works. Improve pattern matching                                                          |
| Apply patch                        | 🔄 H     | Hermes's V4A multi-file patch format + `patch_parser.py`                                                                              |
| LSP query                          | 🔄 H     | Hermes's full LSP stack (client, manager, workspace, protocol, servers). For code intelligence in coding harness delegation             |
| Tool stats / self-reflection       | ✅        | `tool_tracker.py` already built                                                                                                        |
| Sandboxed Python execution         | 🔄 H     | Hermes's `execute_code` tool — only if needed for sub-agents. Otherwise skip                                                           |

### 3C. Web & Network Tools

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Web search                         | ✅        | Already have 5 providers (Brave, Exa, Firecrawl, SearXNG, Tavily). Pi has the best multi-provider web_search pattern for reference     |
| Web fetch / scrape                 | ✅        | Already have `web_fetch`                                                                                                               |
| Get search content                 | 🔄 P     | Pi's `get_search_content` — retrieve stored content from prior searches. Python adaptation                                             |

### 3D. Toolsets (For Modularity)

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Toolsets system                    | 🔄 H     | Hermes's enable/disable toolsets per agent. Essential for modular architecture. Adapt for Locus                                        |

---

## 4. Memory & Persistence

### 4A. Primary Storage

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Primary storage                    | ✅        | SQLite (WAL) — already built. Keep                                                                                                     |
| Graph memory                       | 📦        | **neo4j-labs/agent-memory** — user-prescribed. Already integrated via `neo4j_memory.py`. Keep + deepen integration                     |
| Vector embeddings                  | 📦        | **pgvector** — user-prescribed. Simple, single-container, <50K vectors. Installed via setup wizard                                     |
| Full-text search                   | 🔄 H     | Hermes's SQLite FTS5 session search via `session_search` tool                                                                          |

### 4B. Token Compression (User-Prescribed)

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Token compression                  | 📦        | **headroomlabs-ai/headroom** — user-prescribed. Semantic token compression engine. Integrate as Python package + API wrapper           |

### 4C. Smart Retrieval (User-Prescribed)

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| PageIndex (vectorless tree index)  | 📦        | **VectifyAI/PageIndex** — user-prescribed. Markdown headers→tree structure, LLM reasoning-based retrieval, no vectors. Approach: clone + adapt |

### 4D. Memory Sub-Modules to Copy

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Memory orchestrator                | ✅        | `memory_manager.py` already built. Extend for multi-backend routing                                                                   |
| Entity extraction                  | 🔄 O     | OpenHuman's `memory_entities` module — entity extraction and tracking. Python adaptation from Rust logic                               |
| Memory queue                       | 🔄 O     | OpenHuman's `memory_queue` — durable job queue for follow-up work. Concept: PostgreSQL-backed task queue for background processing     |
| Memory diff                        | 🔄 O     | OpenHuman's `memory_diff` — change tracking. Use Git-diff approach (Locus already uses git for vault)                                  |
| Memory sources                     | 🔄 O     | OpenHuman's `memory_sources` — source adapter registry for multi-input ingestion. Adapt for vault sources                              |
| Memory tools (agent-facing)        | 🔄 O     | OpenHuman's `recall` (search by query/source/topic), `store`, `forget`. Python adaptation needed                                       |
| User modeling store                | 🔄 H     | Hermes's Honcho dialectic modeling + OpenHuman's ambient profile facets. Combine for Locus's User Identity Profile                     |
| Approval store                     | ✅        | `approval_store.py` already built. Keep                                                                                               |
| Session manager                    | ✅        | `session_manager.py` already built. Keep                                                                                               |

### 4E. Memory Providers to Offer (Modular Choice)

| Provider                            | Selection | Rationale                                                                                                                              |
|-------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Neo4j Agent Memory (default)        | 📦        | User-prescribed default                                                                                                                |
| Mem0                                | 📦        | Install pip package, wrap as Locus backend                                                                                             |
| Supermemory                         | 📦        | Install pip package, wrap as Locus backend                                                                                             |
| Honcho                              | 📦        | Install pip package, wrap as Locus backend                                                                                             |
| Mastra                              | 📦        | Evaluate — may be JS-only                                                                                                              |
| Cognee                              | 📦        | Install pip package, wrap as Locus backend                                                                                             |
| Holographic (Locus built-in)        | ✅        | Already built. Keep as lightweight option                                                                                              |

### 4F. Locus-Only Memory Features

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Holographic HRR                    | ✅        | Already built in `core/holographic/`                                                                                                  |
| Hebbian pathway weighting          | 🆕        | Design from scratch — Neo4j edge weight reinforcement. No existing open-source implementation to copy                                 |
| STDP reinforcement                 | 🆕        | Design from scratch — Response latency correlation. Locus-specific neuroscience model                                                 |
| Spaced repetition reinforcement    | 🆕        | Design from scratch — Modified Leitner system in Neo4j. No suitable open-source match                                                 |
| Project-specific memory decay      | 🆕        | Design from scratch — Cypher-based decay rule. Locus-specific                                                                          |

---

## 5. Sessions

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Session format                     | ✅        | SQLite (conversations, sessions, documents). Keep                                                                                      |
| Session compression                | 🔄 H     | Hermes's `conversation_compression.py` + OpenHuman's microcompact + summarizer. Significant improvement over Locus's basic compactor   |
| Session export                     | 🔄 P     | Pi's HTML/JSON/MD export with ANSI→HTML conversion. Python adaptation                                                                 |
| Session resume / naming            | 🔄 H     | Hermes's `title_generator.py` + session history. Simple Python adaptation                                                              |

---

## 6. Context Management

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Context window management          | 🔀        | **Hermes's `context_engine.py` + `context_compressor.py`** (pluggable engines) + **OpenHuman's Guard (0.90/0.95 thresholds)** + **Headroom (user-prescribed token compression)** |
| Token overflow handling            | 🔄 H     | Hermes's save oversized tool results to file + sandbox-aware persistence                                                               |
| TokenJuice (smart compression)     | 🔄 O     | OpenHuman's `tokenjuice` — 3-layer rule overlay, strategies: truncate, dedup, fold whitespace, drop regex, summarize. Up to 80% reduction |
| Context Forge                      | 🆕        | Locus-specific 800-token 6-layer assembler. No equivalent in any codebase. Design from scratch                                         |
| Query Router / Intent Classifier   | 🆕        | Locus-specific 8 intent types + source routing matrix. Design from scratch                                                             |
| Context file loading               | ✅        | SOUL.md loading. Keep                                                                                                                  |
| Coding-specific context            | 🔄 H     | Hermes's `coding_context.py` — for coding harness delegation mode                                                                      |

---

## 7. TUI / Terminal Interface

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| All TUI features                   | ⏭️       | **Locus is Telegram-native by deliberate design.** No TUI to build. Skip entirely                                                      |

---

## 8. CLI

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| CLI flags count                    | ✅        | 18 CLI commands already. Add more as needed                                                                                           |
| Run modes                          | ✅        | CLI + Gateway already built. Keep                                                                                                      |
| Setup wizard                       | ✅        | `locus setup` + `locus setup gateway` already exist                                                                                   |
| Doctor / diagnostics               | 🔄 H     | `hermes doctor [--fix]` — dependency/config diagnostics                                                                               |
| Config management                  | ✅        | Already comprehensive                                                                                                                   |
| Gateway lifecycle                  | ✅        | `locus gateway run/start/stop/restart/status/install/uninstall`                                                                       |

---

## 9. Extensions / Plugins / Skills

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Skills system                      | 🔄 H     | Hermes's skills system is the most comprehensive: SKILL.md + marketplace indexes + install/search/manage. Python, same language        |
| Skills marketplace                 | 🔄 H     | Hermes's 4 marketplace indexes (Anthropic, Claude, LobeHub, OpenAI). Direct adaptation                                                 |
| Plugin system (providers)          | 🔄 H     | Hermes's plugin-based approach for memory providers, context engines, web search, model providers — all Python, all adaptable         |
| Register custom tools              | 🔀        | Combine Hermes's skills approach (declarative) + Pi's extensions (programmatic events). For Locus, skills are the primary mechanism    |

---

## 10. Learning & Self-Improvement

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Post-session learning              | 🔄 O     | OpenHuman's post-turn hooks (Archivist, Reflection, ToolTracker, UserProfile). Python adaptation from Rust patterns                    |
| Cross-session search / recall      | 🔄 H     | Hermes's FTS5 full-text search + LLM summarization                                                                                     |
| User profile building              | 🔀        | Hermes's Honcho dialectic modeling + OpenHuman's ambient profile facets (`user_profile.rs`, `reflection.rs`, `stability_detector.rs`). Adapt to Python |
| Tool usage tracking                | ✅        | `tool_tracker.py` already built                                                                                                       |
| Agent experience tracking          | 🔄 O     | OpenHuman's `agent_experience` module. Python adaptation                                                                               |
| Personal Reward Model              | 🆕        | Locus-specific sklearn LogisticRegression. Design from scratch                                                                         |
| Hebbian learning rules             | 🆕        | Locus-specific. Design from scratch                                                                                                    |
| Multi-horizon pattern detection    | 🆕        | Locus-specific 5-horizon engine. Design from scratch                                                                                   |
| Self-evolving Architect Bot        | 🆕        | Locus-specific. Design from scratch                                                                                                    |

---

## 11. Subagents / Delegation

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Subagent spawning                  | 🔄 H     | Hermes's `delegate_task` — single/batch parallel, isolated context + terminal per child, same provider pool as parent                   |
| Subagent archetypes                | 🔄 O     | OpenHuman's 14 archetypes (`.claude/agents/`). Adapt philosophy, not code (Rust→Python)                                               |
| Depth limiting                     | 🔄 H     | Hermes's depth=1 default. Simple parameter                                                                                             |
| Coding agent                       | 🔄 P     | Pi's full coding agent package — most polished coding-specific subagent patterns. Python adaptation                                     |
| **Harness Interoperability**       | 🆕        | **User-prescribed.** Locus should detect user's environment (deadlines, preferences from SOUL.md) and invoke: Claude Code, Antigravity, OpenCode, Pi, Gemini CLI, etc. No own harness to code. Design from scratch |

---

## 12. Scheduling & Cron

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Cron / scheduled tasks             | 🔄 H     | Hermes's comprehensive cron: duration/NL/cron/ISO schedules, per-job overrides, 3-min hard interrupt, `.tick.lock`, skip_memory        |
| Task sources                       | ✅        | `scheduler/task_sources.py` already built                                                                                             |
| Webhooks                           | ✅        | `webhooks.py` already built. Hermes has safe-tools-only execution — add that                                                           |
| Inner Loop (proactive, unprompted) | 🆕        | Locus-specific APScheduler every 90min. Design from scratch                                                                            |
| Heartbeat / notification           | ✅        | `heartbeat/notification.py` + `subconscious.py` already built                                                                         |

---

## 13. Security & Sandboxing

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Shell command blocklist            | ✅        | `shell_exec.py` BLOCKED_PATTERNS already built                                                                                         |
| Approval gate                      | ✅        | `approval_store.py` already built                                                                                                       |
| Secret prompt encryption           | ✅        | `secret_prompt.py` already built                                                                                                       |
| Proxy support                      | ✅        | `proxy.py` already built                                                                                                               |
| Autonomy tiers                     | 🔄 O     | OpenHuman's 3-tier security policy (readonly/supervised/full). Python adaptation                                                       |
| Path security                      | 🔄 H     | Hermes's `path_security.py` + `tirith_security.py` for website/shell blocklists                                                        |
| Data redaction                     | 🔄 H     | Hermes's `redact.py` — secrets and PII redaction                                                                                       |
| Prompt injection protection        | 🔄 O     | OpenHuman's `prompt_injection` module. Python adaptation                                                                               |
| Encryption / keyring               | 🔄 O     | OpenHuman's OS keyring integration (Apple Keychain, Windows Credential Manager, Linux Secret Service). Python adaptation using `keyring` |
| TLS                                | 🆕        | If needed for gateway HTTPS. Use certbot + nginx — standard infra                                                                      |

---

## 14. Voice

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| STT (Speech-to-Text)               | ✅        | 4 backends already built (Whisper local, Azure, Groq, OpenAI). Keep                                                                    |
| TTS (Text-to-Speech)               | ✅        | 4 backends already built (Edge TTS, ElevenLabs, OpenAI, Piper). Keep                                                                   |
| Dictation                          | ✅        | `dictation.py` already built                                                                                                         |
| Voice call interface               | 🆕        | Locus-specific Audio → Groq Whisper → Kokoro TTS → vault transcript. Design from scratch. Hermes has Google Meet patterns to reference |

---

## 15. Web Search

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| All search providers               | ✅        | 5 providers already built (Brave, Exa, Firecrawl, SearXNG, Tavily). Keep                                                               |

---

## 16. Browser Automation

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Browser automation                 | ✅        | Playwright already integrated (`browserbase.py`, `playwright_backend.py`). Hermes has additional patterns for CDP + auto-spawn          |
| Screenshot / vision                | ✅        | `screenshot.py` + `vision.py` already built                                                                                           |

---

## 17. Channels / Gateway / Messaging

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| All messaging channels             | ✅        | 15+ channels already built. Hermes has the richest platform patterns for reference (especially Telegram primary pattern)                |
| Gateway architecture               | 🔄 H     | Hermes's gateway is the gold standard: session management, inactivity timeout, dedup, caption exact-line match, typing indicator, hooks |
| Cross-platform message mirroring   | 🔄 H     | Hermes's `mirror.py` — elegant cross-platform sync. Good for when user is on multiple platforms                                         |
| Channel-specific display config    | 🔄 H     | Hermes's `display_config.py` — platform-specific formatting rules                                                                      |
| Slash access control               | 🔄 H     | Hermes's `slash_access.py` — per-platform command gating                                                                               |
| Platform registry                  | ✅        | Already built. Keep                                                                                                                    |

---

## 18. MCP (Model Context Protocol)

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| MCP client                         | ✅        | `mcp_client.py` already built. OpenHuman has the most comprehensive Rust implementation for reference patterns                          |
| Obsidian MCP                       | 🆕        | Locus-specific vault_read/write/search/tag/stats. Design from scratch                                                                  |

---

## 19. Export & Artifacts

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Daily AI Chat Archiver             | 🆕        | Locus-specific nightly Telegram → vault .md → git commit. Design from scratch                                                          |
| Session export                     | 🔄 P     | Pi's HTML/JSON/MD export patterns. Python adaptation                                                                                    |

---

## 20. Computer Use

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Native desktop control             | ✅        | `native.py` already built                                                                                                             |
| VNC remote control                 | ✅        | `vnc.py` already built                                                                                                                |
| Screen capture / vision            | ✅        | `capture.py` + `vision.py` already built                                                                                              |

---

## 21. Integrations

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Composio                           | ✅        | `composio.py` already built. Marked for replacement with manual OAuth per architecture doc. Keep for now                              |
| Polymarket                         | ✅        | `polymarket.py` already built                                                                                                         |
| Webhooks                           | ✅        | `webhooks.py` already built                                                                                                           |
| Google Calendar / Gmail / Calendly | 🆕        | Manual OAuth integration — 50 lines per. Design from scratch                                                                           |

---

## 22. Configuration

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| All configuration                  | ✅        | SETTINGS.md + `locus config` already comprehensive. Keep                                                                               |

---

## 23. CI/CD & Testing

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| All CI/CD                          | ⏭️       | Defer to Phase 2+. Focus on building features first                                                                                    |

---

## 24. Utilities

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Various utilities                  | ✅        | `colors.py`, `cli_output.py`, `git_ops.py`, `slash_commands.py` already built. Keep                                                    |

---

## 25. Life OS — Behavioral Metrics *(Locus-only)*

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| **All Life OS metrics**            | 🆕        | **100% Locus-specific.** No equivalent in any codebase. Design all 16 sub-features from scratch: Four Factions, DCS, Operating Modes, TWS, Goal Stack, Action Gap, Deferral Detection, Lag Score, Emergency Injection, Exhaustion Predictor, Faction Rebalance, Cross-Faction Efficiency, Review Cadence, Goal Stack Enforcement, Scheduling Algorithm, Emergency Protocol |

---

## 26. Proactive Reasoning / Brain Engine *(Locus-only)*

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| **All Brain Engine features**      | 🆕        | **100% Locus-specific.** Design from scratch: Inner Loop, State Engine, Multi-Horizon Pattern Engine, Context Forge, Query Router, Inferred Cause Chain, Personality Engine, Weekly Vault Synthesis |

---

## 27. Vault & Knowledge Intelligence *(Locus-only)*

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| PageIndex (vectorless tree)        | 📦        | User-prescribed: VectifyAI/PageIndex                                                                                                   |
| Nightly Vault Ingestion            | 🆕        | Locus-specific multi-account Playwright scraping. Design from scratch                                                                   |
| LOCUS_SHORTHAND                    | 🆕        | Locus-specific token compression. Design from scratch                                                                                  |
| Obsidian Dashboard                 | 🆕        | Locus-specific 8-panel Dataview setup. Design from scratch                                                                             |
| 3-Level Tag Hierarchy             | 🆕        | Locus-specific faction/domain/specific tagging. Design from scratch                                                                     |
| Rough Note Parser / Idea Tracker   | 🆕        | Locus-specific /idea → expand → promote pipeline. Design from scratch                                                                  |
| Link Dump / Resource Logger        | 🆕        | Locus-specific /link → captures table → vault note. Design from scratch                                                                |
| Excalidraw MCP Skill               | 🆕        | Locus-specific autonomous diagram generation. Design from scratch                                                                       |

---

## 28. Interface Philosophy *(Locus-only)*

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Telegram-native headless           | ✅        | Already the deliberate architecture. Keep                                                                                              |
| 4 Daily Structured Check-ins       | 🆕        | Locus-specific inline keyboard flows. Design from scratch                                                                               |
| Voice Call Interface               | 🆕        | Locus-specific. Design from scratch (reference Hermes Google Meet plugin)                                                              |
| Obsidian Dashboard replaces PWA    | ✅        | Already the deliberate architecture. Keep                                                                                              |
| Git for vault sync                 | ✅        | Already decided. Keep                                                                                                                 |
| Manual Google OAuth                | 🆕        | 50 lines. Design from scratch                                                                                                           |
| pgvector replaces Qdrant/ChromaDB  | ✅        | Already decided. Keep                                                                                                                 |
| Redis optional                     | ✅        | Already decided. Keep                                                                                                                 |
| AI model V4 Flash only             | ✅        | Already decided. Keep                                                                                                                 |
| Zero-cost 1st-class constraint     | ✅        | $5 credit → ~416 days. Keep                                                                                                           |
| Minimum AI in harness              | ✅        | Already the deliberate architecture. Keep                                                                                              |

---

## 29. Auto-Research (User-Prescribed)

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| autoresearch integration           | 📦        | **karpathy/autoresearch** — user-prescribed. Invocable via `/research <query>` slash command. Clone + adapt as Locus skill             |

---

## 30. File Crawlers (User-Prescribed)

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| File crawlers for proactive work   | 🆕        | User-prescribed. Design from scratch. Needs to crawl vault files, find/retrieve right info for bot. Combine: OpenHuman's `memory_sources` pattern + Hermes's cron infrastructure + vault-specific crawlers |

---

## 31. Harness Interoperability (User-Prescribed)

| Sub-Feature                        | Selection | Rationale                                                                                                                              |
|------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------|
| Multi-harness delegation           | 🆕        | **User-prescribed. Key differentiator.** Locus analyzes user requirements, deadline, preferences from SOUL.md → selects best coding harness → dispatches task. Harnesses: Claude Code, Antigravity, OpenCode, Pi, Codex CLI, Gemini CLI. Design from scratch. Sub-agent spawn with harness-specific CLI wrapped as Locus tool |

---

## Summary: Selection Counts

| Selection Type | Count | Description                                                                  |
|----------------|-------|------------------------------------------------------------------------------|
| ✅ Keep         | 42    | Locus already has this — maintain, enhance                                  |
| 🔄 H (Hermes)  | 48    | Best source to copy from — Python, same language                            |
| 🔄 O (OpenHuman)| 16    | Excellent architecture to adapt from (Rust → Python)                       |
| 🔄 P (Pi)      | 11    | Clean patterns to adapt from (TypeScript → Python)                          |
| 📦 Package      | 8     | Use pre-built package, don't rebuild                                         |
| 🆕 From scratch | 29    | Purely Locus-specific — no suitable codebase to copy from                   |
| 🔀 Hybrid       | 3     | Combine best of multiple sources                                             |
| ⏭️ Deferred     | 3     | Skip for now, revisit Phase 2+                                              |
| **TOTAL**       | **160** |                                                                            |

---

## Key Architecture Decisions (Reinforced)

| Decision                                            | Implementation Approach                                                                                          |
|-----------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| Memory stack: Neo4j-AM + Headroom + PageIndex       | Priority #1. Neo4j-AM is already integrated. Headroom and PageIndex next. All three work as composable modules   |
| Auto-research (karpathy/autoresearch)                | Invocable via `/research` slash command. Wraps as a Locus skill                                                  |
| Harness interoperability                             | SOUL.md profile → detect context → select harness → dispatch. Pre-installed harnesses: Claude Code, Antigravity, OpenCode, Pi |
| File crawlers for proactive work                     | Built on cron infrastructure + OpenHuman's memory_sources pattern. Crawl vault directories for task-relevant info  |
| Modular architecture — everything swappable          | Achieved via: config-based backend selection, provider registry, toolset enable/disable, plugin architecture      |

---

## Implementation Priority (Recommended Order)

### Phase 1 — Foundation (Weeks 1-2)
1. **Memory stack integration** (Section 4): Complete Neo4j-AM integration + install Headroom + clone PageIndex
2. **Agent loop hardening** (Section 1B): Copy Hermes's turn context, retry, system prompt builder
3. **Context management upgrade** (Section 6): Context compressor + TokenJuice adaptation

### Phase 2 — Core Features (Weeks 3-4)
4. **Skills system** (Section 9): Hermes's skills architecture
5. **Scheduling & Cron** (Section 12): Enhanced cron + Inner Loop foundation
6. **Subagents & Harness Interop** (Sections 11, 31): Harness dispatcher + autoresearch

### Phase 3 — Locus Uniqueness (Weeks 5-6)
7. **Life OS Metrics** (Section 25): All 16 behavioral metric features
8. **Brain Engine** (Section 26): All 8 proactive reasoning features
9. **Vault Intelligence** (Section 27): PageIndex integration, nightly ingestion, SHORTHAND

### Phase 4 — Polish (Weeks 7-8)
10. **Security hardening** (Section 13): Redaction, prompt injection protection, encryption
11. **Learning engine** (Section 10): Reward model, pattern detection, Architect Bot
12. **MCP expansion** (Section 18): Obsidian MCP, additional MCP servers

---

## Files To Analyze Per Codebase (For Logic Stripping)

### Hermes (Python — most copyable)
| Directory / File                          | What to Extract                                                  |
|-------------------------------------------|------------------------------------------------------------------|
| `agent/turn_context.py`                   | Per-turn state management                                        |
| `agent/turn_retry_state.py`              | Exponential backoff + circuit breakers                           |
| `agent/system_prompt.py`                  | Dynamic system prompt assembly                                   |
| `agent/prompt_builder.py`                 | Structured prompt generation                                     |
| `agent/iteration_budget.py`               | Budget enforcement + grace turn                                  |
| `agent/stream_consumer.py`                | Streaming response consumption                                   |
| `agent/stream_dispatch.py`                | Streaming dispatch patterns                                      |
| `agent/conversation_compression.py`       | Old→new message compaction                                       |
| `agent/background_review.py`              | Post-turn self-improvement                                       |
| `agent/title_generator.py`                | Session title generation                                         |
| `gateway/session.py`                      | Gateway session management                                       |
| `gateway/run.py`                          | Gateway lifecycle                                                |
| `gateway/platforms/`                      | Per-platform adapter patterns                                    |
| `gateway/mirror.py`                       | Cross-platform message mirroring                                 |
| `gateway/hooks.py`                        | Gateway hook system                                              |
| `gateway/slash_access.py`                 | Slash command access control                                     |
| `hermes_cli/`                             | CLI patterns, config management                                  |
| `hermes_constants.py`                     | Constants and configuration                                      |
| `skills/`                                 | Skills system architecture                                       |
| `tools/registry.py`                       | Tool registry + auto-discovery                                   |
| `tools/*.py`                              | Tool implementations                                             |
| `cron/`                                   | Cron scheduling patterns                                         |
| `config/`                                 | Configuration management                                         |
| `context_engine.py`                       | Context window management                                        |
| `context_compressor.py`                   | Context compaction logic                                         |
| `prompt_caching.py`                       | Prompt caching TTL                                               |
| `credits_tracker.py`                      | Usage/cost tracking                                              |
| `rate_limit_tracker.py`                   | API rate limit tracking                                          |
| `stream_diag.py`                          | Stream diagnostics                                               |
| `curator/`                                | Autonomous curator engine                                        |
| `plugins/`                                | Plugin architecture patterns                                     |
| `lazy_deps.py`                            | Lazy dependency loading pattern                                  |
| `path_security.py`                        | Path sandboxing                                                  |
| `schema_sanitizer.py`                     | Tool schema sanitization                                         |
| `tool_output_limits.py`                   | Tool result truncation + file storage                            |
| `tool_result_storage.py`                  | Oversized result persistence                                     |
| `redact.py`                               | Secret/PII redaction                                             |
| `memory_manager.py`                       | Memory orchestrator pattern                                      |
| `onboarding.py`                           | Setup wizard patterns                                            |
| `hermes_state.py`                         | Application state management                                     |
| `pairing.py`                              | DM authorization patterns                                        |
| `display_config.py`                       | Channel-specific display rules                                   |
| `sticker_cache.py`                        | Media caching pattern                                            |
| `restart.py`                              | Graceful restart logic                                           |
| `shutdown_forensics.py`                   | Shutdown cleanup                                                 |

### OpenHuman (Rust — adapt logic, not code)
| Directory / File                          | What to Extract                                                  |
|-------------------------------------------|------------------------------------------------------------------|
| `src/openhuman/event_bus/`                | Typed pub/sub architecture                                       |
| `src/openhuman/tokenjuice/`              | Smart token compression (3-layer rules)                          |
| `src/openhuman/memory_entities/`         | Entity extraction + tracking                                     |
| `src/openhuman/memory_queue/`            | Durable background job queue                                     |
| `src/openhuman/memory_diff/`             | Change tracking via Git-diff                                     |
| `src/openhuman/memory_sources/`          | Multi-source adapter registry                                    |
| `src/openhuman/memory_search/`           | Agent-facing search patterns                                     |
| `src/openhuman/memory_store/`            | Persistence orchestration                                        |
| `src/openhuman/tool_registry/`           | Domain-owned tool registration                                   |
| `src/openhuman/tools/policy.rs`          | Tool gate + user filtering                                      |
| `src/openhuman/tool_timeout/`            | Per-tool timeout enforcement                                     |
| `src/openhuman/learning/user_profile.rs`| Ambient profile facets                                          |
| `src/openhuman/learning/reflection.rs`  | Post-turn reflection logic                                       |
| `src/openhuman/prompt_injection/`       | Injection detection + mitigation                                 |
| `src/openhuman/channels/`               | Multi-channel gateway architecture                               |

### Pi (TypeScript — adapt logic, not code)
| Directory / File                          | What to Extract                                                  |
|-------------------------------------------|------------------------------------------------------------------|
| `packages/pi-agent-core/src/agent-loop.ts`| Two-entry loop architecture                                      |
| `packages/pi-agent-core/src/agent-harness.ts` | Harness state machine                                       |
| `packages/pi-agent-core/src/system-prompt.ts` | Dynamic prompt assembly                                    |
| `packages/pi-agent-core/src/compaction/`  | Compaction engine + branch summarization                         |
| `packages/pi-coding-agent/src/tools/*.ts` | Tool implementation patterns (read, write, edit, bash, grep)     |
| `packages/pi-coding-agent/src/edit-diff.ts` | Precise find-and-replace logic                                |
| `packages/pi-coding-agent/src/export-html/` | Session export format                                          |
| `packages/pi-coding-agent/src/get_search_content.ts` | Search content retrieval                               |
| `packages/pi-coding-agent/src/web_search.ts` | Multi-provider web search dispatch                            |
| `packages/pi-coding-agent/src/memory/memory-storage.ts` | In-memory backend pattern                            |

---

## Pre-Built Packages to Install (Don't Rebuild)

| Package                           | Purpose                                          | Integration Method                 |
|-----------------------------------|--------------------------------------------------|------------------------------------|
| `neo4j-agent-memory`              | Graph memory (default)                           | Already integrated via `neo4j_memory.py` |
| `headroom` (headroomlabs-ai)      | Semantic token compression                       | pip install + Python API wrapper   |
| PageIndex (VectifyAI)             | Vectorless tree-based retrieval                  | Clone repo + adapt as Locus module |
| `karpathy/autoresearch`           | Deep research capability                         | Clone repo + wrap as `/research` skill |
| `mem0ai`                          | Alternative memory provider                      | pip install + wrap as backend      |
| `supermemory`                     | Alternative memory provider                      | pip install + wrap as backend      |
| `honcho`                          | Alternative memory provider                      | pip install + wrap as backend      |
| `cognee`                          | Alternative memory provider (evaluate)           | pip install + wrap as backend      |
| `keyring`                         | OS credential storage                            | pip install + Python API           |
