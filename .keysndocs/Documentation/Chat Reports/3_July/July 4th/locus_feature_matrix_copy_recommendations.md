# Locus Feature Matrix — What to Copy From Where

Working through `full_feature_matrix.md` section by section. For every feature row, I've picked one primary source — a codebase to copy the pattern from, "Locus (keep)" if what you have is already the best option, or "Locus (own design)" if nothing else implements it — per your instruction that every feature needs at least one selection. 312 rows across 29 sections.

**⚠️ CORRECTION NOTICE (applied after codebase verification):** The original version of this document assumed Locus was single-provider (DeepSeek V4 Flash only), based on what the matrix's Section 28 stated. After inspecting Locus's actual source code (`core/agent.py`, `locus_cli/config.py`), that assumption is **incorrect**. Locus already has:
- 11 provider endpoints in `PROVIDER_ENDPOINTS`
- `LlmProvider` abstraction class for API-agnostic LLM calls
- `resolve_provider(config, task_category)` with 9 task-category-specific provider slots (chat, reasoning, coding, agentic, memory, embeddings, heartbeat, learning, subconscious)
- 11+ API key env vars configured (OpenAI, Anthropic, Google, OpenRouter, DeepSeek, Mistral, Together, Groq, xAI, Cohere, Perplexity)

So Locus is **multi-provider from the ground up**. The "DeepSeek V4 Flash only" statement in the matrix is stale — the codebase has evolved past it. Every recommendation below has been corrected to account for this. Where "single-provider" was originally used as a pruning criterion (skip provider features, dismiss routing, call something N/A), those picks have been replaced with proper multi-provider recommendations.

---

## How I made these calls, and where I'm not sure

A few things worth being upfront about, since these are judgment calls on top of your data, not independently verified facts:

- **I'm working entirely from your matrix's own descriptions** — module names, brief annotations, the ✅/📐/🔧/⬜/❌ symbols you already assigned. I have not inspected the actual Pi, Hermes, or OpenHuman source code, so I can't verify anything about them beyond what's written in your matrix. Where a cell's description is thin (e.g., just "✅ (built-in)"), my confidence in that pick is correspondingly lower — treat those as weaker recommendations than ones backed by a specific module name or design detail.
- **Stack inference**: I inferred Pi = TypeScript/Node, Hermes = Python, OpenHuman = Rust core + Tauri (React/TS frontend), from your own CI/CD section (23) and the file extensions used throughout your matrix ( vs  vs "cargo test"/"clippy") — not from outside knowledge of these specific projects. Locus is Python/FastAPI, per your existing architecture.
- **Decision order I applied**: (1) if Locus already has a solid ✅/🔧 implementation with no clear reason to change it, keep it; (2) when comparing external options, I weighted Python-native Hermes higher on close calls, since that's what actually ports into your FastAPI codebase rather than needing a from-scratch rewrite; (3) I checked fit against your stated design constraints (deterministic over LLM-driven, single-user self-hosted, zero-cost, no redundant infra) and flagged anything enterprise/multi-tenant-shaped as low-priority even where I had to name a source to satisfy full coverage; (4) for anything genuinely Locus-only (Life OS metrics, Brain Engine, Vault Intelligence), nothing exists elsewhere to copy, so the answer is "build from your own spec" every time.
- **A naming ambiguity I can't resolve for you**: "Pi" in this matrix looks like it could be the same "Pi Agent" you've mentioned running elsewhere (OpenRouter, qwen3-coder). If it is, "copy from Pi" for a given feature is less "port this code" and more "you already have this tool — decide whether Hermes Agent should invoke it directly rather than reimplementing its internals." I flag it again at Section 11 where it matters most, but only you can confirm whether it's actually the same tool.
- **A data discrepancy I noticed, not resolved**: this matrix (Sections 4 and 28) describes Locus's vector store as pgvector, explicitly replacing Qdrant. That doesn't match what I have from other conversations, where the more recent memory-infrastructure decision was Qdrant directly (alongside Neo4j/neo4j-agent-memory), not pgvector. I don't know which is actually current — this matrix may predate that later decision, or my picture could be the stale one — so treat every pgvector reference below as provisional until you confirm which is live.
- Where a feature doesn't fit Locus's model at all (enterprise billing, a TUI, etc.), I still named a source per your instructions, but marked it low-priority/N/A rather than pretending it's worth building right now.

---

## 1. Agent Core / Runtime

Locus's own agent core is still mostly 🔧/⬜ here — this is the section with the most raw building left, and where Hermes's Python patterns port most directly.

| Feature | → Copy From | Why |
|---|---|---|
| **Main agent loop** | Hermes | Python conversation-loop + background-review design is the closest structural match to `core/agent.py`. OpenHuman's 5-seam dispatcher is more sophisticated but is a Rust rewrite, not a port. |
| **Turn context management** | OpenHuman | Its fork/memory/sandbox/**worktree** context model lines up directly with the git-worktree multi-agent orchestration you're designing for Hermes Agent — copy the concept, not the Rust code. |
| **Turn retry / error recovery** | Hermes | `turn_retry_state.py` is a plain deterministic state machine, which fits "deterministic over LLM-driven" better than OpenHuman's LLM-assisted self-healing (ToolMaker polyfill). |
| **System prompt builder** | Hermes | `system_prompt.py` + `prompt_builder.py` is a two-stage Python design close to what a FastAPI service needs. Pi's dynamic assembly + skills injection is worth a skim if you build a skills system later. |
| **Prompt caching** | Hermes | `prompt_caching.py` is provider-agnostic Python; Pi's is written against OpenAI's cache API specifically in TS. |
| **Iteration budget / limits** | **OpenHuman** | `token_budget` — **Locus is multi-provider** (confirmed in source: 11 endpoints, task-category routing). Different providers have different token costs and rate limits. OpenHuman's per-provider budget logic is what Locus needs — route expensive calls to cheap providers, cap total spend per task category. Hermes's `iteration_budget.py` is simpler but doesn't handle provider-aware budgeting. |
| **Background review / post-turn** | OpenHuman | Its 4 post-turn hook types are the closest existing pattern to a *reactive* complement to your already-designed *proactive* Inner Loop, if you ever want both. |
| **Stream diagnostics** | Hermes | `stream_diag.py` — low-effort Python utility, low priority until your streaming layer matures. |
| **Rate limit tracking** | **Hermes** | `rate_limit_tracker.py` — Locus is multi-provider (11 endpoints, each with different rate limits and tier levels). Hermes's per-provider tracker is exactly what Locus needs. OpenHuman's 30s-TTL health probe is too lightweight for this use case. Track each provider separately to avoid hitting limits on the cheap/fast models you route to. |
| **Usage / cost tracking** | Hermes | Three focused Python modules (usage/credits/account). Worth copying given how central the ~$4/year budget is to Locus's design. |
| **Title generation** | Hermes | Only implementation that exists (`title_generator.py`). Low priority for a Telegram-first single-thread bot, but reusable for vault note naming. |
| **Onboarding flow** | Locus (keep) | You already have a CLI wizard plus a planned in-chat wizard. Peek at Hermes's `onboarding.py` only if the in-chat flow needs richer branching. |
| **Agent initialization** | Locus (keep) | `core/agent.py` already exists — this is infrastructure glue, not a differentiator worth porting. |

---

## 2. LLM Providers

Locus is **multi-provider** — confirmed in source code: 11 provider endpoints, `LlmProvider` abstraction, task-category routing with 9 dedicated provider slots. This section is directly relevant, not bloat to skip. My picks below account for which provider architecture patterns extend Locus's existing infrastructure best.

| Feature | → Copy From | Why |
|---|---|---|
| **Provider count** | Locus (keep) | Already have 11 — no need to copy. |
| **OpenAI / OpenAI-compatible** | **Hermes** | Generic adapter pattern — Locus's `LlmProvider` already follows this structure. Hermes's `generic_adapter.py` is the cleanest Python reference for adding more OpenAI-compatible providers (Together, Groq, Perplexity — all already configured in Locus). |
| **Anthropic** | **Pi** | `anthropic.ts` has the most robust Anthropic-specific handling (separate messages format, thinking blocks, tool_use). Hermes's `anthropic_adapter.py` is Python but thinner. Pi's architecture for non-OpenAI-compatible SDKs is worth porting — Anthropic's API is structurally different from the rest. |
| **Google Gemini** | **Pi** | `google.ts` + `google-vertex.ts` — Pi has the most comprehensive Gemini handling (grounding, search, vision features). Locus already has Google in `PROVIDER_ENDPOINTS` — copy Pi's adapter patterns. |
| **AWS Bedrock** | **Hermes** | `bedrock_adapter.py` — Python-native AWS integration. Low priority for Locus (zero-cost model favors cheap providers over AWS), but useful if you need the option. |
| **Azure OpenAI** | N/A / skip | Enterprise-cloud. Low relevance to Locus's deployment model. |
| **Cloudflare** | **Pi** | `cloudflare.ts` — Pi is the only one with Cloudflare Workers AI. Locus already has Cloudflare Tunnel for networking — adding Cloudflare as an LLM provider is a natural fit. |
| **Mistral** | **Pi** | `mistral.ts` — Pi's implementation handles La Plateforme features beyond OpenAI-compatible basics. Locus already has Mistral in endpoints. |
| **Moonshot / Kimi** | **Hermes** | `moonshot_schema.py` — Hermes is the only one with this. Useful if you add free-tier Chinese models as budget options. |
| **LM Studio (local)** | **Hermes** | `lmstudio_reasoning.py` — Python-native local model support. **High priority for zero-cost constraint**: run local models for cheap tasks (title generation, simple classification) and route expensive reasoning to paid APIs. |
| **GitHub Copilot** | N/A / skip | Pi-specific integration, not aligned with Locus. |
| **Intelligent routing (auto-select)** | **OpenHuman** | `IntelligentRouting` with local+cloud fallback — **the most important pattern to copy in this entire section**. Locus already has `resolve_provider()` with task-category routing. OpenHuman adds cost-weighted selection, capability-based routing, and fallback chains. This is the natural evolution of what you already built — don't skip it. |
| **Refusal detection** | **OpenHuman** | Aho-Corasick DFA refusal detection — pattern-matches model refusals. **More important with multi-provider**: different providers have different refusal patterns. Essential for reliability in an autonomous system. |
| **Provider registry** | **Pi** | `api-registry.ts` + auto-register pattern. Locus's `resolve_provider()` is static — Pi's auto-discovery (scan for configured API keys, register available providers dynamically) is the next step. Hermes's `model_metadata.py` is useful for the metadata layer (capabilities, pricing, context windows per model). |
| **OAuth (device code, PKCE)** | N/A / skip | API keys only for LLM providers — separate from Google OAuth for Calendar/Gmail. |
| **Model list / discovery** | **Hermes** | `model_metadata.py` — **critical for multi-provider routing**. Maintains a registry of available models with capabilities, pricing, context windows. Without this, you can't make informed routing decisions. Locus's routing is task-category-based but lacks model metadata to optimize cost. |
| **Image generation providers** | N/A / low priority | Not a stated Locus need currently. If added, Pi's `images.ts` + registry is the reference. |
| **Mock / test provider** | **Pi** | `faux.ts` — a fake provider for tests. Essential for Locus to get a test suite (Section 23 is empty). Port to Python. |
| **Streaming (SSE)** | **Hermes** | `stream_consumer.py` + `stream_dispatch.py` — Python-native, directly relevant to Telegram real-time message updates. Multi-provider means handling different SSE formats — Hermes's dispatcher normalizes this. |

---

## 3. Tools / Tool Execution

Locus is already ahead on most commodity tools here. The real gaps are a handful of specific rows below.

| Feature | → Copy From | Why |
|---|---|---|
| **File read** | Locus (keep) | Already implemented — commodity feature, not worth touching. |
| **File write / create** | Locus (keep) | Same. |
| **File edit (precise)** | Locus (keep) | You already have both `edit` and `edit_file`. Pi's separate `edit-diff.ts` is worth a look only if you want diff-preview UX later. |
| **Shell / bash execution** | Locus (keep/extend) | Your blocklist sandbox exists. OpenHuman's 4-backend sandbox (bubblewrap/docker/firejail/landlock) is the reference for defense-in-depth beyond a blocklist. |
| **Grep / search files** | Pi | `grep.ts`'s concept is simple and directly needed. Locus currently substitutes `web_search`, which isn't the same as local-file grep — a real, low-effort gap to close. |
| **List directory** | Locus (keep) | Already implemented. |
| **Find files** | Pi | `find.ts` — simple, currently missing (⬜), low-effort port. |
| **Web search** | Locus (keep) | 5 providers already beats all three references. |
| **Web fetch / scrape** | Locus (keep) | Already implemented. |
| **Git status** | Locus (keep) | Already implemented. |
| **Git diff** | Locus (keep) | Already implemented. |
| **Git commit** | Locus (keep) | Already implemented. |
| **System info** | Locus (keep) | Only Locus has this at all. |
| **Tool call validation** | Hermes | `tool_guardrails.py`, Python, the most direct extension of your current "basic validation." |
| **Tool result classification** | Hermes | `tool_result_classification.py` — only implementation that exists; medium priority. |
| **Tool output accumulator** | OpenHuman | Its 16 KiB tool-result budget is a concrete, simple cap — easier to copy than Pi's streaming `output-accumulator.ts` design. |
| **File mutation queue** | Pi | `file-mutation-queue.ts` is the only implementation. Genuinely relevant once Hermes Agent has multiple sub-agents writing to the same worktree concurrently — flag as medium priority, not just nice-to-have. |
| **Tool timeout / budget** | OpenHuman | `tool_timeout` — simple, directly missing from Locus today. |
| **XML tool dispatch** | **OpenHuman** (low priority) | Not needed if *all* your providers support native function-calling. But multi-provider means some models (especially local/cheap ones via LM Studio) may lack native tool calls — OpenHuman's XML dispatcher is the fallback to keep those providers usable. |
| **Compact tool dispatch** | **OpenHuman** (low priority) | Same reasoning — token-efficient format for models with weak function-calling. Keep as fallback for cheap local models. |

---

## 4. Memory & Persistence

This is the section where your own recent, very deliberate infrastructure decisions (the Mem0 / neo4j-agent-memory / Cognee comparison) matter more than anything in this matrix — most of the "designed" rows below are already spoken for by that work, not blank slates.

| Feature | → Copy From | Why |
|---|---|---|
| **Primary storage** | Locus (keep) | SQLite (WAL) already suits single-user scale. Hermes's SQLite+FTS5 combo (see the full-text-search row below) is the piece worth borrowing, not a storage-engine swap. |
| **In-memory backend** | N/A / skip | Only Pi has this (ephemeral store, mainly for tests/dev). Low priority. |
| **Graph memory** | Locus (keep/extend) | You've already committed to Neo4j via neo4j-agent-memory. OpenHuman's `memory_graph` is worth a skim for schema ideas, but the infra decision is already made. |
| **Vector embeddings** | Locus (keep/extend) | Per this matrix, pgvector + 📐 PageIndex — **but see my note above about a possible discrepancy with a later Qdrant decision.** OpenHuman's `embeddings` module is a secondary reference for pipeline structure only. |
| **Full-text search** | Hermes | FTS5 is SQLite-native and directly complements your existing SQLite (WAL) store — a real, currently-missing capability worth adding. |
| **Memory tree / cascade** | N/A / low priority | OpenHuman's bucket-seal cascade is a specific memory-organization strategy that doesn't obviously fit your already-chosen graph+vector approach. Skip unless you hit a concrete problem it solves. |
| **Entity extraction** | Locus (own spec) | You've already decided on spaCy/GLiNER-based deterministic extraction feeding Neo4j — more aligned with your stated determinism preference than copying OpenHuman's `memory_entities` (method unspecified in the matrix). |
| **Memory sync** | N/A / low priority | OpenHuman only; unclear fit — this seems to solve multi-device memory-state sync, which isn't the same problem as your Syncthing/Git vault-file sync. |
| **Memory queue** | N/A / low priority | OpenHuman only; no concrete Locus need stated. |
| **Memory diff** | N/A / low priority | OpenHuman only; relevant only if you want memory-change auditing later. |
| **Holographic HRR** | Locus (own design) | No other codebase has anything like this — your own SHA-256 deterministic vector-binding design, nothing to copy. |
| **Hebbian pathway weighting** | Locus (own design) | Locus-only (📐); build from your own spec. |
| **STDP** | Locus (own design) | Same. |
| **Spaced repetition reinforcement** | Locus (own design) | Same. |
| **Project-specific memory decay** | Locus (own design) | Same. |
| **User modeling store** | Hermes | Honcho's "dialectic modeling" — as your matrix describes it — is the most purpose-built existing match for this problem versus building a PG single-row rolling-average model from scratch. I don't have independent knowledge of Honcho beyond what's in your matrix, so this is worth a quick check of its current state before you treat it as adoptable. OpenHuman's "ambient profile facets + stability detector" is a reasonable dependency-free alternative. |
| **Memory orchestrator** | Locus (keep) | `memory_manager.py` already exists. |
| **Approval store** | Locus (keep) | `approval_store.py` already exists. OpenHuman's 10-min TTL is worth borrowing if yours doesn't already time out. |
| **Session manager** | Locus (keep) | `session_manager.py` already exists. |

---

## 5. Sessions

| Feature | → Copy From | Why |
|---|---|---|
| **Session format** | Hermes | SQLite sessions is the most natural extension of your existing SQLite (conversations/sessions/documents) tables. Pi's tree-based JSONL is powerful but a bigger structural change than you likely need. |
| **Session branching / fork** | N/A / low priority | Only Pi has this (`--fork`). Doesn't map to a stated Locus need — single-user, not exploring alternate conversation branches. |
| **Session resume** | Hermes | Closest existing pattern to what a Telegram-first single-user bot needs. Pi's `--resume`/`--continue` are CLI-specific UX Locus doesn't need in the same form. |
| **Session naming** | Hermes | Same `title_generator.py` flagged in Section 1. Low priority. |
| **Session picker UI** | N/A / skip | Pi-only, CLI-specific UX. Not applicable — Locus is Telegram-first. |
| **Session compression** | Hermes | `conversation_compression.py`, Python — directly relevant since Locus's own `compression.py` is 🔧 basic and needs real work. |
| **Session export** | N/A / low priority | Pi's HTML/JSON/MD export is nice-to-have, but redundant with your more ambitious Daily AI Chat Archiver (Section 19), which you've already built. |
| **No-session mode** | N/A / skip | Pi-only CLI flag, not applicable to a Telegram-first bot. |
| **Custom session directory** | N/A / skip | Pi-only CLI flag, low relevance to a single server-side deployment. |

---

## 6. Context Management

| Feature | → Copy From | Why |
|---|---|---|
| **Context window management** | Hermes | `context_engine.py` + `context_compressor.py` — directly relevant since Locus's own is 🔧 (token counter only, no real compaction yet). A real gap. |
| **Context references** | Hermes | `context_references.py`, only implementation. Medium priority — useful once your Context Forge assembler needs to cite specific chunks. |
| **Coding-specific context** | Hermes | `coding_context.py`, only implementation. Relevant once Hermes Agent needs to hand context to spawned coding agents. |
| **Manual compression feedback** | Hermes | Only implementation. Low-to-medium priority — lets a user manually trigger/tune compression. |
| **Token overflow handling** | OpenHuman | Reuse the same 16 KiB cap concept already borrowed for tool-output accumulation (Section 3), for consistency, rather than Pi's separate `overflow.ts` approach. |
| **Context Forge (multi-source assembly)** | Locus (own design) | No other codebase attempts a 6-layer assembler like this. Nothing to copy — build from your own spec. |
| **Query Router / Intent Classifier** | Locus (own design) | Same — Locus-only design. |

---

## 7. TUI / Terminal Interface

Locus deliberately has no TUI/GUI (❌) — Telegram is the interface. Two rows below aren't a clean ❌ though (Locus shows 🔧), so I've called those out separately rather than blanket-labeling the whole section.

| Feature | → Copy From | Why |
|---|---|---|
| **Full TUI framework** | N/A (Locus ❌) | Deliberately rejected — nothing to copy. |
| **Multiline editing** | N/A (Locus ❌) | Same. |
| **Keyboard shortcuts** | N/A (Locus ❌) | Same. |
| **Themes (dark/light/custom)** | N/A (Locus ❌) | Same. |
| **Slash command autocomplete** | Locus (keep) | Already handled differently — Telegram `/commands` instead of TUI autocomplete. |
| **Streaming tool output** | Locus (keep, low priority) | You already have `streaming_tui.py` (🔧) even though it's not primary — looks like leftover dev tooling. Fine to keep as a debug utility, not worth more investment given the TUI rejection. |
| **Voice recording in TUI** | N/A (Locus ❌) | Rejected — Telegram already has native voice-message support. |
| **Paste support** | N/A (Locus ❌) | Not applicable. |
| **Editor integration ($EDITOR)** | N/A (Locus ❌) | Not applicable. |
| **Session picker** | N/A (Locus ❌) | Not applicable. |
| **Status bar / footer** | N/A (Locus ❌) | Not applicable. |
| **Provider attribution display** | N/A (Locus ❌) | Not applicable. |
| **Diagnostics UI** | N/A / low priority | No TUI to attach one to right now, though Hermes's `hermes doctor` concept (Section 8) covers the same diagnostic need differently. |
| **Curses fallback TUI** | Locus (keep, low priority) | Same situation as streaming tool output — `curses_ui.py` (🔧) exists but isn't primary. Keep as minimal debug fallback only. |

---

## 8. CLI

| Feature | → Copy From | Why |
|---|---|---|
| **CLI flags count** | Locus (keep) | 18 commands already exist — not a gap. |
| **Run modes** | Locus (keep) | CLI + Gateway already matches your actual deployment model (systemd service + CLI). Pi's Interactive/Print/RPC/JSON is more modes than a single-user tool needs. |
| **Batch mode (one-shot)** | Pi | `--print` flag — simple, low-effort if you want scriptable one-shot invocation. |
| **RPC / daemon mode** | N/A / low priority | Mainly useful for IDE/tool integration. Not a stated Locus need since Telegram + Gateway already serve as your always-on interface. |
| **Self-update** | Hermes | `hermes update` — simple, Python, worth having for a systemd-deployed service. |
| **Doctor / diagnostics** | Hermes | `hermes doctor` — directly useful for debugging your Oracle VM deployment. |
| **Config management** | Locus (keep) | `locus config show/set/path/env-path/check/migrate` already exceeds Pi/Hermes in breadth. OpenHuman's ~70 schema files is overkill for single-user scale. |
| **Gateway lifecycle** | Locus (keep) | Already matches Hermes's command set almost 1:1 (and exceeds it — `restart/status/install/uninstall` vs. Hermes's `run/start/stop`). You're already ahead here. |
| **Setup wizard** | Locus (keep) | Already covered — same feature as Section 1's onboarding-flow row. |

---

## 9. Extensions / Plugins / Skills

| Feature | → Copy From | Why |
|---|---|---|
| **Extension system** | N/A / low priority | Pi's framework (loader/runner/wrapper/25+ lifecycle events) is the most complete, but given you're already planning an MCP client (Section 18) and Obsidian-plugin work, a full extension framework on top may be redundant. Flag as low priority unless a concrete need emerges. |
| **Skills system** | Hermes | Its skill-bundle + command + 15-category system is the most complete Python reference — relevant to your own recent "Understand Anything" plugin work and to the Claude-style SKILL.md pattern you already use. |
| **Skills marketplace** | N/A / low priority | Only matters once you have a skills system worth distributing — premature for a single-user system. |
| **Prompt templates** | Pi | `prompt-templates.ts` — simple, only implementation, low priority. |
| **ACP protocol** | N/A / skip | Hermes's chosen protocol for editor/IDE integration — not clearly needed given Locus's Telegram-first, non-IDE interface. |
| **Plugin LLM** | N/A / low priority | Hermes-only, unclear concrete Locus need. |
| **Register custom tools** | Hermes | Its "via skills" pattern is the closest match to how you'd want Hermes Agent to register new tools dynamically for spawned coding agents. |
| **Register custom commands** | Locus (keep) | Telegram `/commands` already covers this. |
| **Context file loading** | Locus (keep) | `SOUL.md` already serves this role. Pi's AGENTS.md/CLAUDE.md auto-discovery is worth a skim only if you want directory-scoped context files for Hermes Agent's spawned coding sessions specifically. |

---

## 10. Learning & Self-Improvement

| Feature | → Copy From | Why |
|---|---|---|
| **Post-session learning** | OpenHuman | Its 4 distinct post-turn hooks (Archivist, Reflection, ToolTracker, UserProfile) is a cleaner separation of concerns than Hermes's single curator pipeline, and more advanced than Locus's current basic `reflector.py`. |
| **Cross-session search / recall** | Hermes | FTS5 + LLM summarization is directly portable (same DB engine you already use) and simpler than OpenHuman's dedicated `memory_search` module. |
| **User profile building** | Hermes | Same Honcho caveat as Section 4 — its dialectic-modeling concept is the most purpose-built match for your planned 📐 User Identity Profile, but verify Honcho's current state before adopting it as a dependency. |
| **Stability detection** | OpenHuman | Only implementation (30-min stability detector). Relevant if your Inner Loop needs to avoid over-reacting to noisy short-term signals. |
| **Tool usage tracking** | Locus (keep) | `tool_tracker.py` already exists, matches OpenHuman's `ToolTrackerHook` concept. |
| **Personal Reward Model** | Locus (own design) | No other codebase attempts a sklearn-based reward model from 👍/👎 feedback — build from your own spec. |
| **Hebbian learning rules** | Locus (own design) | Same — Locus-only. |
| **Multi-horizon pattern detection** | Locus (own design) | Same. |
| **Self-evolving Architect Bot** | Locus (own design) | Same, and worth flagging: this is the most architecturally ambitious/risky item in the whole matrix. No reference implementation exists anywhere here for an agent that writes and deploys its own patches — there's no proven pattern to lean on, so lean on your own risk-gating carefully. |
| **Agent experience tracking** | OpenHuman | Only implementation (`agent_experience` module). Low-to-medium priority. |

---

## 11. Subagents / Delegation

This section is directly relevant to Hermes Agent's design (spawning coding agents across worktrees), so a few picks here carry more weight than usual.

**Naming note, worth resolving before you act on any of these**: the "Pi" column in this section describes a full coding-agent package — if that's the same "Pi Agent" you already run (OpenRouter, qwen3-coder), then for the "Coding agent" row specifically, there may be nothing to *copy*; you may just want Hermes Agent to *invoke* Pi directly as one of its spawned tools, alongside Antigravity/OpenCode/Claude Code. I can't tell from the matrix alone whether that's the intent — worth confirming.

| Feature | → Copy From | Why |
|---|---|---|
| **Subagent spawning** | OpenHuman | Its 3-tier hierarchy is the most directly relevant existing pattern for spawning multiple CLI coding agents in parallel — more relevant than Pi's single built-in subagent tool or Hermes's simpler `agent_init.py` + `process_bootstrap.py`. |
| **Subagent archetypes** | OpenHuman | 15 built-in archetypes (orchestrator/planner/researcher/critic/etc.) is a good reference shape for your planned 4 faction sub-agents (Planner/Curator/Analyst/Builder) — you don't need 15, but the archetype-registry pattern is worth copying. |
| **Depth limiting** | OpenHuman | `MAX_SPAWN_DEPTH=3` is a simple, concrete safety rail worth adopting directly for Hermes Agent's worktree-spawning, to avoid runaway recursive spawning. |
| **RPC-based subagents** | N/A / low priority | Relevant only if Hermes Agent talks to spawned agents over RPC rather than CLI subprocess. Worth revisiting once the orchestrator's actual IPC mechanism is decided. |
| **Coding agent** | Locus (keep/extend) | `delegation/coding_agent.py` (🔧) already exists. Pi's "full coding agent package" is the most mature reference for what yours needs to grow into — but see the naming note above; don't conflate "copy Pi's pattern" with "Pi is one of the tools you're spawning." |
| **ACP client for subagents** | N/A / skip | ACP is Hermes's specific protocol choice — only relevant if you adopt ACP as your orchestration protocol, which isn't currently part of the Postgres + git-worktree design for Hermes Agent. |

---

## 12. Scheduling & Cron

| Feature | → Copy From | Why |
|---|---|---|
| **Cron / scheduled tasks** | Locus (keep/extend) | `cron_runner.py` exists. Hermes's "natural language cron scheduling" is a nice UX layer worth borrowing if you want to type "every Tuesday" instead of cron syntax. |
| **Task sources** | Locus (keep) | `scheduler/task_sources.py` already exists, matches OpenHuman's concept. |
| **Scheduled automations** | Locus (own scope) | Your planned nightly-ingestion/weekly-synthesis/daily-check-in set is more specific to your architecture than Hermes's generic reports/backups/audits. Use Hermes's cron mechanism, but the content is yours. |
| **Inner Loop (proactive, unprompted)** | Locus (own design) | No other codebase has an unprompted proactive reasoning loop — genuinely novel, nothing to copy. |
| **Structured check-in reminders** | Locus (own design) | Same — Locus-only. |
| **Heartbeat / notification** | Locus (keep/extend) | You already have both `heartbeat/notification.py` and `subconscious.py`. OpenHuman's `heartbeat` module is a secondary reference only if yours needs restructuring. |

---

## 13. Security & Sandboxing

Several real, currently-missing gaps in this section — worth prioritizing given how much untrusted content (web fetch, browser automation, multi-channel input) Locus already ingests.

| Feature | → Copy From | Why |
|---|---|---|
| **Project trust management** | N/A / low priority | Pi's "is this a trusted project directory" prompt is less relevant to a server-side single-user bot — though worth revisiting specifically for Hermes Agent's worktree spawning. |
| **Shell command blocklist** | Locus (keep) | `shell_exec.py` BLOCKED_PATTERNS already exists. OpenHuman's policy-engine classification is a more structured reference if you want to move beyond simple blocklisting. |
| **File safety checks** | Hermes | `file_safety.py`, Python, directly portable. Currently a real gap (⬜) in Locus. |
| **Sandbox backends** | OpenHuman | The 4-backend approach (bubblewrap/docker/firejail/landlock) is the most concrete reference for hardening `run_shell` beyond blocklisting. |
| **Autonomy tiers** | OpenHuman | readonly/supervised/full is a clean three-tier model worth adopting directly — especially relevant once Hermes Agent grants spawned coding agents varying autonomy. |
| **Approval gate** | Locus (keep) | `approval_store.py` already exists. OpenHuman's 10-min TTL parameter is worth borrowing if yours doesn't already time out. |
| **Data redaction** | Hermes | `redact.py`, only implementation, real gap in Locus — relevant given you archive full chat exports (Chat Vault) that may contain sensitive data. |
| **Prompt injection protection** | OpenHuman | Only implementation (`prompt_injection` module). Genuinely important gap given your web_fetch/web_search/browser-automation tools already ingest untrusted external content. |
| **Think token scrubbing** | Hermes | `think_scrubber.py`, only implementation — relevant if you ever surface raw model reasoning traces to Telegram and want to strip them. |
| **Message sanitization** | Hermes | `message_sanitization.py`, only implementation, Python. A real, currently-missing gap. |
| **Secret prompt encryption** | Locus (keep) | `secret_prompt.py` already exists — only Locus has this at all. |
| **Proxy support** | Locus (keep) | `proxy.py` already exists. |
| **Encryption / keyring** | OpenHuman | `encryption` + `keyring` modules, only implementation — relevant for storing your multi-account credentials (Chat Vault's 5 accounts, various API keys) more safely than plain config. |
| **TLS** | N/A / low priority | OpenHuman-only; likely already handled at your Cloudflare Tunnel layer, so probably redundant. |

---

## 14. Voice

| Feature | → Copy From | Why |
|---|---|---|
| **STT (Speech-to-Text)** | Locus (keep) | 4 backends already exceeds Hermes (via plugins) and OpenHuman's single voice-inference module. |
| **TTS (Text-to-Speech)** | Locus (keep) | Same — 4 backends already exceeds the references, and matches your Kokoro-TTS work from the TTS-on-Vercel project. |
| **Voice recording in-app** | N/A / skip | Hermes's Ctrl+R is TUI-specific — Telegram already has native voice-message support. |
| **Voice call interface** | Locus (own design) | No other codebase has a full voice-call pipeline. Your Groq Whisper → Kokoro TTS design is novel — build from spec. |
| **Dictation** | Locus (keep) | `dictation.py` already exists, matches OpenHuman's concept. |

---

## 15. Web Search

| Feature | → Copy From | Why |
|---|---|---|
| **Search provider count** | Locus (keep) | 5 providers already far exceeds all three references. |
| **Brave Search** | Locus (keep) | Already implemented; no reference has this. |
| **Exa** | Locus (keep) | Same. |
| **Firecrawl** | Locus (keep) | Same. |
| **SearXNG** | Locus (keep) | Same. |
| **Tavily** | Locus (keep) | Same — this whole section is already a Locus strength, nothing to copy. |

---

## 16. Browser Automation

| Feature | → Copy From | Why |
|---|---|---|
| **Browser automation** | Locus (keep) | Playwright (`browserbase.py`, `playwright_backend.py`) already implemented. OpenHuman's `screen_intelligence` is a different (vision-based, not DOM-based) approach — complementary, not a replacement. |
| **Screenshot** | Locus (keep) | `screenshot.py` exists. |
| **Vision / screen analysis** | Locus (keep/extend) | `vision.py` exists. OpenHuman's overlay-based screen intelligence is worth a look if you want to visually annotate what the agent is looking at, for debugging. |

---

## 17. Channels / Gateway / Messaging

Locus already has channel modules for nearly everything here — this section is mostly "keep," with a handful of genuinely useful Hermes utilities worth adding on top.

| Feature | → Copy From | Why |
|---|---|---|
| **Telegram** | Locus (keep) | Already your primary, most mature channel (PTB, auth, inline keyboards) — more developed than any reference's Telegram integration. |
| **Discord** | Locus (keep) | Channel module exists. |
| **Slack** | Locus (keep) | Channel module exists. |
| **WhatsApp** | Locus (keep) | Channel module exists. Hermes's `whatsapp_identity.py` (identity-linking specifically) is worth a peek if yours doesn't handle multi-number identity resolution yet. |
| **Signal** | Locus (keep) | Channel module exists. |
| **IRC** | Locus (keep) | Only Locus has this at all. |
| **Matrix** | Locus (keep) | Channel module exists. |
| **Mattermost** | Locus (keep) | Channel module exists. |
| **Teams** | Locus (keep) | Channel module exists. |
| **Lark** | Locus (keep) | Channel module exists. |
| **DingTalk** | Locus (keep) | Channel module exists. |
| **Google Chat** | Locus (keep) | Channel module exists. |
| **Email** | Locus (keep) | Channel module exists. |
| **iMessage** | Locus (keep) | Channel module exists. |
| **CLI / Terminal** | Locus (keep) | Basic CLI exists. |
| **Desktop app** | N/A (Locus ❌) | Deliberately rejected, consistent with the TUI rejection in Section 7. |
| **Web interface** | N/A / low priority | Only OpenHuman has this. You already have a PWA (though Section 28 shows it's being replaced by Obsidian) — likely not worth adding a separate web interface on top. |
| **Platform registry** | Locus (keep) | Already exists, matches Hermes's `platform_registry.py` concept. |
| **Cross-platform message mirroring** | Hermes | `mirror.py`, only implementation — genuinely useful given you have 14 channel modules; mirroring lets one conversation surface consistently across them. |
| **Channel-specific display config** | Hermes | `display_config.py`, only implementation — formatting differs a lot between, say, Telegram inline keyboards and plain-text IRC. |
| **Device pairing** | OpenHuman | Its `devices` module is the more directly relevant reference (Hermes's `pairing.py` reads more like chat-account pairing). Low-to-medium priority. |
| **Sticker / media cache** | Hermes | `sticker_cache.py`, only implementation, low priority. |
| **Graceful restart** | Hermes | `restart.py`, only implementation — genuinely useful for a systemd-managed always-on service. |
| **Shutdown forensics** | Hermes | `shutdown_forensics.py`, only implementation — useful for debugging crashes on your Oracle VM. |
| **Kanban watchers** | N/A / low priority | Hermes-only; no obvious mapping since you use a PG-based goal stack (Section 25) rather than a kanban board. |
| **Memory monitor** | Hermes | `memory_monitor.py` — worth flagging this is very likely *RAM/process monitoring*, not "agent memory," so don't confuse it with Section 4. Relevant given your 24GB RAM VM budget. |
| **Gateway hooks** | Hermes | `hooks.py`, only implementation — a useful extensibility point for your own Gateway. |
| **Slash access control** | Hermes | `slash_access.py`, only implementation — relevant for permissioning who can invoke which Telegram commands, especially if family/friends start using Locus-adjacent tools. |

---

## 18. MCP (Model Context Protocol)

| Feature | → Copy From | Why |
|---|---|---|
| **MCP client** | Locus (keep/extend) | `mcp_client.py` already exists. OpenHuman's dual-transport support (HTTP + stdio, protocol 2024–2025) is the reference if yours doesn't handle both yet. |
| **MCP server** | N/A / low priority | Only OpenHuman has this — relevant only if you want other tools (e.g., Claude Desktop) calling *into* Locus, not a stated current need. |
| **MCP registry** | N/A / low priority | OpenHuman's dynamic-install/Smithery.ai approach is more of a marketplace feature. Loosely related to your Composio multi-tenant-account research, but low priority at single-user scale. |
| **MCP audit** | N/A / low priority | OpenHuman-only, no concrete need stated yet. |
| **Obsidian MCP** | Locus (own design) | Your own design (📐 vault_read/write/search/tag/stats) — no other codebase attempts this, nothing to copy. |

---

## 19. Export & Artifacts

| Feature | → Copy From | Why |
|---|---|---|
| **HTML session export** | N/A / low priority | Pi-only. Your Chat Vault → Markdown ambition already supersedes this. |
| **JSON session export** | N/A / low priority | Same reasoning. |
| **Markdown session export** | Pi | Worth a glance since Markdown is your actual target format — though your `sync_chats.py` (Playwright-based, cross-account) already solves the export problem more thoroughly for your specific case; Pi's version is simpler/narrower. |
| **Trajectory recording** | Hermes | `trajectory.py` (1321 lines) is a serious, mature implementation — relevant if you want structured replay/debugging logs of what each spawned coding agent did, directly useful for debugging Hermes Agent orchestration. |
| **ANSI → HTML conversion** | N/A / skip | Pi-only, terminal-output-specific — not applicable without a TUI. |
| **Daily AI Chat Archiver** | Locus (keep — already built) | Your own `setup_auth.py`/`sync_chats.py` system, already delivered. Nothing to copy — you're ahead of all three references here. |

---

## 20. Computer Use

| Feature | → Copy From | Why |
|---|---|---|
| **Native desktop control** | Locus (keep) | `native.py` already exists. OpenHuman's `desktop_companion` + `overlay` is a secondary reference for an interactive overlay UI. |
| **VNC remote control** | Locus (keep) | `vnc.py` already exists — only Locus has this. |
| **Screen capture** | Locus (keep) | `capture.py` exists. |
| **Screen intelligence / vision** | Locus (keep/extend) | `vision.py` exists. OpenHuman's overlay-based screen intelligence is worth a look for visual debugging, same note as Section 16. |

---

## 21. Integrations

| Feature | → Copy From | Why |
|---|---|---|
| **Composio** | Locus (reconsider) | You're already mid-pivot away from Composio toward manual OAuth, per your own recent evaluation. OpenHuman's `integrations` module doesn't obviously solve the multi-tenant-per-user-account problem you hit — this is more "your own path forward" than a copy-from situation. |
| **Polymarket** | Locus (keep) | Only Locus has this. |
| **Webhooks** | Locus (keep) | `webhooks.py` exists. OpenHuman's module is a secondary reference only. |
| **Google Calendar** | Locus (own plan) | Manual-OAuth plan is already your decided path — no other codebase implements this feature anyway. |
| **Gmail** | Locus (own plan) | Same reasoning. |
| **Calendly** | Locus (own plan) | Same. |
| **Web3 / wallet** | N/A / skip | OpenHuman-only. Doesn't fit a Life-OS assistant — your own prediction-markets research already treated wallet/small-capital limits with appropriate skepticism. |
| **Billing** | N/A / skip | Enterprise/commercial feature, not applicable to a single-user self-hosted tool. |
| **Meet / video calls** | N/A / skip | Not a stated need — your Voice Call Interface (Section 14) is a different, simpler concept (audio pipeline, not video conferencing). |
| **Team collaboration** | N/A / skip | Doesn't fit the single-user model. |
| **Referral system** | N/A / skip | Commercial feature, not applicable. |

---

## 22. Configuration

| Feature | → Copy From | Why |
|---|---|---|
| **Config format** | Locus (keep) | SETTINGS.md (56KB, 28 sections) already exceeds Pi/Hermes in scope. OpenHuman's ~70 JSON schema files is a more rigid, schema-validated approach — worth considering only if SETTINGS.md's freeform structure starts causing bugs. |
| **Config migration** | Locus (keep) | `locus config migrate` exists. |
| **Environment variable management** | Locus (keep) | `locus config env-path` exists. |
| **Config section count** | N/A | This is a metric row, not a feature to copy. |

---

## 23. CI/CD & Testing

Locus is at ⬜ across the board here — this is arguably the single highest-leverage gap in the entire matrix, since roughly 73 implemented features currently have zero automated test coverage.

| Feature | → Copy From | Why |
|---|---|---|
| **Unit tests** | Hermes | pytest is the standard, directly-applicable choice for a Python codebase. Highest priority item in this whole document, given zero coverage today. |
| **CI pipeline** | Hermes | Its lint/test/typecheck/docker/nix/security pipeline is the most complete Python-native reference. OpenHuman's is comparably thorough but Rust-specific tooling. |
| **Linting** | Hermes | Ruff — increasingly the Python-ecosystem default — over flake8. |
| **Type checking** | Hermes | mypy is the standard choice for Python. |
| **Docker** | Hermes | Docker builds, directly reusable given you already run Docker Compose on your Oracle VM. |
| **Nix** | N/A / low priority | Hermes-only; adds real complexity (a second packaging system) for a single-dev project. Skip unless reproducibility becomes a genuine pain point. |
| **Batch trajectory runner** | Hermes | Same `trajectory.py` flagged in Section 19 — doubles as a testing/replay tool. |

---

## 24. Utilities

| Feature | → Copy From | Why |
|---|---|---|
| **Clipboard** | N/A / skip | Pi-only, CLI/TUI-specific — not applicable to a Telegram-first server. |
| **Git integration** | Locus (keep) | `git_ops.py` exists. |
| **Image handling** | Pi | Resize/convert/EXIF/Photon is the most complete reference — currently ⬜ in Locus and a real gap, given Telegram messages routinely include images. |
| **Syntax highlighting** | N/A / skip | Pi-only, TUI-specific — not applicable without a terminal UI. |
| **MIME detection** | Pi | `mime.ts` — simple, currently missing, low-effort port for handling arbitrary Telegram attachments correctly. |
| **Open browser** | N/A / skip | Pi-only, desktop/CLI-specific — not applicable to a headless VM. |
| **ANSI escape handling** | N/A / skip | Pi-only, terminal-specific. |
| **Shell integration** | N/A / low priority | Pi's `shell.ts` is CLI-shell-specific (e.g., shell completions) — low relevance to Locus. |
| **Frontmatter parser** | Pi | `frontmatter.ts` — genuinely relevant since your Obsidian vault notes are frontmatter-heavy Markdown. Currently missing, real gap. |
| **File system watcher** | Pi | `fs-watch.ts` — relevant for detecting when you (or Syncthing) change vault files, to trigger re-ingestion. |
| **Unicode sanitization** | Pi | `sanitize-unicode.ts` — simple, worth having anywhere you ingest external chat exports. |
| **JSON safe parsing** | Pi | `json-parse.ts` — simple, low-effort, good practice for a system this JSON-heavy (config, tool calls, memory records). |
| **Schema validation** | Locus (keep, already covered) | Pi's TypeBox helpers are TS-specific and don't port. The equivalent concept is already covered by FastAPI/Pydantic, which Locus already uses. |
| **Colors / output formatting** | Locus (keep) | `colors.py`/`cli_output.py` exist. |
| **Slash commands handler** | Locus (keep) | `slash_commands.py` exists. |
| **SSH deployment** | Locus (keep) | `deployment` module exists, matches your actual Oracle VM SSH-key-based deploy process. |

---

## 25. Life OS — Behavioral Metrics *(Locus-only domain)*

Pi, Hermes, and OpenHuman show ⬜ across every row here — this entire section is your own invented Life-OS metrics system with zero precedent in any reference codebase. Every row's answer is the same: build from your own spec.

| Feature | → Copy From | Why |
|---|---|---|
| **Four Factions Framework** | Locus (own design) | No external reference exists. |
| **Daily Capacity Score (DCS)** | Locus (own design) | Same. |
| **Five Operating Modes** | Locus (own design) | Same. |
| **Task Weight Score (TWS)** | Locus (own design) | Same. |
| **Three-Layer Goal Stack** | Locus (own design) | Same. |
| **Action Gap Tracking** | Locus (own design) | Same. |
| **Deferral Detection (3/5/8+)** | Locus (own design) | Same. |
| **Lag Score + TWS Lag Bonus** | Locus (own design) | Same. |
| **Emergency Task Injection** | Locus (own design) | Same. |
| **Exhaustion Predictor** | Locus (own design) | Same. |
| **Weekly Faction Rebalance** | Locus (own design) | Same. |
| **Cross-Faction Efficiency** | Locus (own design) | Same. |
| **Review Cadence System** | Locus (own design) | Same. |
| **Goal Stack Enforcement** | Locus (own design) | Same. |
| **6-Step Scheduling Algorithm** | Locus (own design) | Same. |
| **4-Level Emergency Protocol** | Locus (own design) | Same. |

---

## 26. Proactive Reasoning / Brain Engine *(Locus-only domain)*

Same situation as Section 25 — nothing in Pi/Hermes/OpenHuman resembles unprompted proactive reasoning.

| Feature | → Copy From | Why |
|---|---|---|
| **Inner Loop (Proactive Thinker)** | Locus (own design) | No external reference exists. |
| **State Engine + Inferred Cause Chain** | Locus (own design) | Same. |
| **Multi-Horizon Pattern Engine** | Locus (own design) | Same. |
| **Context Forge** | Locus (own design) | Same (duplicate of Section 6's entry). |
| **Query Router / Intent Classifier** | Locus (own design) | Same (duplicate of Section 6's entry). |
| **Inferred Cause Chain Engine** | Locus (own design) | Same. |
| **Personality + "Wants" Engine** | Locus (own design) | Same. |
| **Weekly Full Vault Synthesis** | Locus (own design) | Same. |

---

## 27. Vault & Knowledge Intelligence *(Locus-only domain)*

Same pattern — with one precision note: PageIndex is a real external tool you've separately evaluated and are incorporating, not something invented from scratch. It's just not one of the three codebases being compared *in this matrix*, so there's still nothing here to copy from Pi/Hermes/OpenHuman specifically.

| Feature | → Copy From | Why |
|---|---|---|
| **PageIndex (whole-note embedding)** | Locus (own design, using the external PageIndex tool) | Not sourced from Pi/Hermes/OpenHuman — already a deliberate external-tool choice on your part. |
| **Nightly Vault Ingestion Pipeline** | Locus (own design) | No external reference exists. |
| **LOCUS_SHORTHAND** | Locus (own design) | Same. |
| **Obsidian as Primary Dashboard** | Locus (own design) | Same. |
| **3-Level Tag Hierarchy** | Locus (own design) | Same. |
| **Rough Note Parser / Idea Tracker** | Locus (own design) | Same. |
| **Link Dump / Resource Logger** | Locus (own design) | Same. |
| **Excalidraw MCP Skill** | Locus (own design) | Same. |

---

## 28. Interface Philosophy & Infrastructure Decisions *(Locus-only domain)*

These are architectural decisions you've already made, not features to build — so "copy from" mostly means "keep the decision," with one flag.

| Feature | → Copy From | Why |
|---|---|---|
| **Telegram-native headless** | Locus (keep — own decision) | Already implemented. |
| **4 Daily Structured Check-ins** | Locus (own design) | No external reference. |
| **Voice Call Interface** | Locus (own design) | Duplicate of Section 14's entry. |
| **Obsidian Dashboard replaces PWA** | Locus (keep — own decision) | Already decided. |
| **Git for vault sync** | Locus (own design) | No external reference. |
| **Manual Google OAuth** | Locus (keep — own decision, in progress) | Already your path (see Section 21). |
| **pgvector replaces Qdrant+ChromaDB** | Locus (keep — own decision) | **Flagging again**: this may conflict with a later decision (per other conversations) to use Qdrant directly alongside Neo4j. Worth confirming which is actually current before treating this row as settled. |
| **Redis optional** | Locus (keep — own decision) | Already decided. |
| **DeepSeek V4 Flash as primary** | Locus (keep — own decision) | Locus defaults to DeepSeek as the most cost-effective provider, but has 10 other providers available via config and task-category routing. This is "primary, not only" — confirmed in source code. |
| **Zero-cost 1st-class constraint** | Locus (keep — own decision) | Already implemented. |
| **Minimum AI in harness** | Locus (keep — own decision) | Already implemented. |

---

## 29. Miscellaneous / Uncategorized

| Feature | → Copy From | Why |
|---|---|---|
| **Telemetry** | N/A / low priority | Genuinely useful for a systemd-deployed service on a resource-constrained VM, but lower priority than Section 23's testing gap. Pi's `telemetry.ts` / OpenHuman's `observability` config are the references if you pick this up. |
| **Experimental features flag** | N/A / low priority | Pi-only, nice-to-have. |
| **Auth storage** | Hermes | `authz_mixin.py` — currently a real gap (⬜), surprising given how many channels/integrations Locus already has. |
| **Resource loader** | N/A / low priority | Pi-only, unclear concrete Locus need. |
| **Error classifier** | Hermes | `error_classifier.py`, only implementation — directly useful given Locus's varied tool/channel/provider surface. |
| **Auxiliary LLM client** | **OpenHuman** | `auxiliary_client.py` is simple, but Locus's multi-provider infrastructure means `model_council` (multi-model committee) is actually more relevant. Use Hermes's `auxiliary_client.py` as the lightweight end, OpenHuman's `model_council` as the pattern if you want concurrent multi-provider responses. |
| **Model council / committee** | **OpenHuman** (medium priority) | Locus is multi-provider — a model council (multiple LLMs debating/verifying each other's outputs) is actually a natural fit, not a conflict. Route the same prompt to different providers and compare results. Medium priority, not a skip. |
| **Accessibility** | N/A / skip | OpenHuman-only, GUI-specific (Tauri desktop) — not applicable to a Telegram-first headless system. |
| **Connectivity checks** | OpenHuman | `connectivity` module, only implementation — simple, useful given your VM's dependency on Cloudflare Tunnel staying up. |
| **Code graph analysis** | N/A / medium priority for Hermes Agent specifically | OpenHuman-only. Could matter once Hermes Agent needs to reason about spawned agents' codebases structurally — low priority for Locus core, worth a second look for the orchestrator. |
| **Runtime JS/Python** | N/A / skip | OpenHuman-only, embedded-runtime feature. Locus already *is* Python, and `run_shell` already covers arbitrary execution — redundant. |
| **About app** | N/A / skip | OpenHuman-only, GUI-specific — not applicable. |
| **Workflows** | N/A / low priority | OpenHuman-only; unclear mapping versus your existing cron/scheduler + Inner Loop combination, which may already cover this under different names. |
| **Health checks** | Hermes | `gateway/status.py`, directly relevant to your own Gateway. OpenHuman's `health` module is a secondary reference. |
| **Notifications** | Locus (keep) | `heartbeat/notification.py` already exists, matches OpenHuman's concept. |
| **Socket/WebSocket** | Hermes | `gateway/stream_consumer.py`, relevant to your own Gateway architecture. OpenHuman's `socket` module is Tauri-desktop-specific, less relevant. |
| **Redirect links** | N/A / skip | OpenHuman-only, unclear Locus need. |
| **Provider surfaces** | N/A / skip | OpenHuman-only, unclear concrete mapping. |
| **Service orchestration** | N/A / low priority | OpenHuman-only — possibly relevant to Hermes Agent's multi-agent coordination, worth a skim, no concrete need stated yet. |
| **Workspace management** | N/A / medium priority for Hermes Agent specifically | OpenHuman-only — possibly relevant to the git-worktree-per-agent model Hermes Agent needs. |
| **Agent tool policy** | OpenHuman | `agent_tool_policy` module — relevant for governing what tools each spawned sub-agent can access, directly useful for Hermes Agent. |
| **Test support** | Hermes | Ties back to Section 23's testing gap — pytest fixtures/test-support tooling. |
| **Subconscious background** | Locus (keep) | You already have both `subconscious.py` and the planned Inner Loop — more developed than what's described for OpenHuman's `subconscious` module. |

---

## Cross-cutting notes

A short summary of the things worth reading even if you skip the row-by-row tables above:

1. **Biggest single gap**: Section 23 (CI/CD & Testing) is empty across the board. ~73 implemented features with no automated tests is the highest-risk item in this whole matrix, independent of any "what to copy" question — pytest + Ruff + mypy (all from Hermes, all standard Python tooling) would close most of it.
2. **Two items worth resolving before you act on my picks**: the possible Pi = "Pi Agent" identity question (Section 11), and the pgvector-vs-Qdrant discrepancy between this matrix and more recent conversations (Sections 4 and 28). I flagged both inline but they're easy to miss in a 300-row document.
3. **OpenHuman punches above its weight for anything Hermes-Agent-orchestration-shaped**: worktree contexts, subagent hierarchy/archetypes, depth limiting, autonomy tiers, agent tool policy, **and now intelligent multi-provider routing**. Even though it's Rust and not directly portable, its patterns map unusually well onto what you're actively designing.
4. **Hermes is the default "port this" answer for Python-native features**: system prompts, providers, FTS5, session compression, file safety, trajectory recording, graceful restart, health checks. Straightforward Python ports.
5. **The original single-provider assumption affected ~20 picks across 5 sections** (1, 2, 3, 28, 29). All have been corrected in this version. The most consequential change is **Section 2** — which went from "mostly skip" to "OpenHuman's IntelligentRouting is the most important pattern to copy."

Happy to re-cut this — e.g., a version filtered to just the "real gap, worth building soon" rows, or one grouped by priority instead of by section — if the full 312-row version is more than you wanted.
