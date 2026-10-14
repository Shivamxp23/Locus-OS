# ATOMIC SELECTIONS — Locus as a Pi Agent Augmentation (v4)

> **Date**: July 16th, 2026
> **Paradigm**: Locus **AUGMENTS** Pi Agent's codebase — a forked, extended runtime with its own `locus` CLI
> **Sources**: COMBINED_ATOMIC_FEATURES.md (July 7th) · Pi Agent (`5_Locus/pi/`) · Hermes (`5_Locus/hermes-agent/`) · OpenHuman (`5_Locus/openhuman/`) · Locus OS (`5_Locus/locus-os/`) · Ideas and System directory (15 documents)
> **Philosophy**: Laziness-first · Steal logic, never rebuild · Everything modular · Maximum user choice · **Locus doesn't code — it delegates**

---

## Table of Contents

- [Part 0 — The Augmentation Paradigm](#part-0--the-augmentation-paradigm)
- [Part I — Augmented Feature Matrix (§1-§33)](#part-i--augmented-feature-matrix-133)
- [Part II — Feature → Source Codebase Mapping](#part-ii--feature--source-codebase-mapping)
- [Part III — Atomic Logic Stripping](#part-iii--atomic-logic-stripping)
- [Part IV — Modularity Contract Specifications](#part-iv--modularity-contract-specifications)
- [Appendix A — Provider Registry](#appendix-a--provider-registry)
- [Appendix B — Config Schema](#appendix-b--config-schema)
- [Appendix C — Coding Harness Registry](#appendix-c--coding-harness-registry)
- [Appendix D — The Memory Tri-Stack](#appendix-d--the-memory-tri-stack)

---

# Part 0 — The Augmentation Paradigm

## 0.1 What "Augmenting Pi" Means

Locus is NOT a package that sits on top of Pi. Locus **is** Pi — augmented.

Technically, this means:

- **Fork Pi Agent's repository** as the starting point
- **Add Locus-specific modules** directly into the codebase (extensions, sidecar services, new CLI commands)
- **Preserve 100% of Pi's existing functionality** — every Pi feature still works
- **The `locus` binary** is a superset of `pi` — it mirrors all `pi` commands but adds Locus-specific scope and features
- Users can still run `pi` for pure Pi behavior, or `locus` for the full Life OS experience

This is NOT a wrapper. Locus augments Pi at the codebase level, like how a Linux distribution augments the Linux kernel.

## 0.2 Dual CLI Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Pi Agent Codebase                        │
│                   (100% inherited by Locus)                  │
│                                                              │
│  Agent Loop · 30+ Providers · 8 Tools · TUI · Sessions      │
│  Compaction · Extensions API · Skills · Themes · Packages    │
│  39 CLI flags · RPC/JSON modes · OAuth · Security            │
├──────────────────────────┬──────────────────────────────────┤
│     `pi` binary          │       `locus` binary              │
│     (original Pi)        │       (Pi + Locus augmentation)   │
│                          │                                    │
│  pi install X            │  locus install X                   │
│  (global scope)          │  (Locus-scoped packages/ext/MCPs) │
│                          │                                    │
│  pi help                 │  locus help                        │
│  pi config               │  locus config                      │
│  pi update               │  locus update                      │
│                          │  locus doctor                      │
│                          │  locus gateway run/start/stop      │
│                          │  locus setup                       │
│                          │  locus life                        │
│                          │  locus memory                      │
│                          │  locus vault                       │
│                          │  locus brain                       │
│                          │  locus research                    │
│                          │  locus delegate                    │
└──────────────────────────┴──────────────────────────────────┘
```

**Install scopes:**
- `pi install X` → installs globally, available to both `pi` and `locus`
- `locus install X` → installs for Locus scope only (Locus-specific extensions, MCPs, skills)

## 0.3 The Modularity Contract

**LITERALLY EVERYTHING is modular.** Every major subsystem in Locus follows this pattern:

```
INTERFACE MemoryProvider:
  store(content, metadata) → id
  query(query, limit) → results
  extract_entities(text) → entities
  update_weights(node_id, delta) → void

REGISTRY memory_providers:
  "memory-tri-stack" → MemoryTriStackProvider   (default — see §4 & Appendix D)
  "mem0"             → Mem0Provider
  "supermemory"      → SupermemoryProvider
  "honcho"           → HonchoProvider
  "mastra"           → MastraProvider
  "cognee"           → CogneeProvider
  "custom"           → user-provided adapter via config

CONFIG locus.memory:
  provider: "memory-tri-stack"   # or any registered provider
  enabled: true                   # toggle entire subsystem
  options: { ... }                # provider-specific config
```

This pattern applies to: **Memory, Brain/Reasoning, Learning, Voice, Channels, Search, Context Assembly, Scheduling, User Modeling, Coding Delegation** — every single subsystem.

Users can:
- **Swap** any provider for another
- **Disable** any subsystem entirely
- **Hook in** their own custom provider via a simple adapter interface
- **Stack** multiple providers (e.g., Neo4j + mem0 for memory)

## 0.4 The Coding Delegation Principle (NEW)

**Locus does NOT have its own coding harness. It DELEGATES.**

```
USER: "Build me a FastAPI app with auth"
                │
                ▼
LOCUS (understands user, requirements, deadline, complexity)
                │
    ┌───────────┴───────────────────────────┐
    │ HARNESS SELECTOR (selects best tool)  │
    │ Factors: complexity, language, stack,  │
    │ deadline, user preference, past perf  │
    └───────────┬───────────────────────────┘
                │
    ┌───────────┼────────────────────────┐
    ▼           ▼           ▼            ▼
 Antigravity  Claude Code  OpenCode     Pi Agent
 (pre-installed)  (pre-installed)  (pre-installed)  (inherited)
```

**Why**: Laziness-first. Coding harnesses are complex beasts. Antigravity, Claude Code, OpenCode, and Pi itself already do coding better than anything we could build. Locus' job is to:
1. **Understand** what the user wants (requirements, constraints, deadlines)
2. **Select** the best harness for the job
3. **Prompt** that harness with the right context
4. **Monitor** progress and report back
5. **Learn** which harness performs best for which task types

**Pre-installed harnesses:**
| Harness | Strength | When to use |
|---------|----------|-------------|
| **Antigravity** | Deep project understanding, multi-file, GSD | Complex multi-file projects, architectural work |
| **Claude Code** | Reasoning-heavy, agentic | Logic-intensive, debugging, refactoring |
| **OpenCode** | Lightweight, fast | Quick fixes, small scripts |
| **Pi Agent** | Inherited, extensible | General coding, extension development |
| **Aider** | Git-aware, diff-based | Incremental changes to existing code |
| **Custom** | User-provided | User-specific workflows |

## 0.5 Coding Philosophy

1. **Laziness-first**: If something already exists (Neo4j Agent Memory, Pi's providers, etc.), USE IT. Clone it. Don't rebuild.
2. **Steal logic**: For every feature we want, find the BEST implementation across Pi/Hermes/OpenHuman, understand its logic via `/understand-anything`, and adapt it for Locus.
3. **Never directly reference**: Don't copy-paste files. Understand the LOGIC and STRATEGY, then implement fresh for Locus' modular architecture.
4. **Maximum options**: For every subsystem, provide as many swappable providers as possible. The user should feel they can customize EVERYTHING.
5. **Delegate coding**: Locus is a life OS, not a coding tool. When code needs writing, delegate to the best coding harness.
6. **File crawlers first**: Before the agent can do proactive work, file crawlers must have already found the right information. Data in → intelligence out.

## 0.6 Available Codebases

| Codebase | Path | Language | Key Strengths |
|----------|------|----------|---------------|
| **Pi Agent** | `5_Locus/pi/` | TypeScript/Node.js | Agent loop, 30+ providers, TUI, extensions, packages, sessions, 75+ examples |
| **Hermes Agent** | `5_Locus/hermes-agent/` | Python | Gateway, channels (Telegram/Discord/Slack/WhatsApp), background review, curator, memory manager, usage tracking, ACP protocol, cron scheduling |
| **OpenHuman** | `5_Locus/openhuman/` | Rust + TypeScript | Memory graph, embeddings, subagent archetypes (15!), sandboxing (4 backends), MCP client/server, approval gates, post-turn hooks, desktop companion |
| **Locus OS** | `5_Locus/locus-os/` | Python | Life OS metrics, Brain Engine, vault intelligence, Telegram interface, voice pipeline, Neo4j memory, Context Forge |

## 0.7 System Design Documents (The Vision)

> These documents define WHAT Locus is. Everything in this Atomic Selections file must be traceable back to one of these documents or be an explicitly stated addition.

| Document | Path | Key Content |
|----------|------|-------------|
| **My Initial idea.txt** | `.../Ideas and System/` | Founding vision: "mechanisms work when emotions don't", bottom-to-top, metric-driven, 4 factions |
| **Prompt.txt** | `.../Ideas and System/` | Extended system prompt: factions, master algorithm, 3-layer goal stack, scheduling logic |
| **LOCUS_SYSTEM_v1.md** | `.../Ideas and System/` | The System Bible: 15 chapters, all formulas (DCS, TWS, LS, AG), operating modes, scheduling algorithm, review cadence |
| **LOCUS_MASTER_DOCUMENT.md** | `.../Ideas and System/` | Complete architecture: 883 lines, 9-layer pyramid, all services, 109 features, memory decisions, LLM strategy |
| **LOCUS_BRAIN_MODULE_PROMPT.md** | `.../Ideas and System/` | 9 sub-systems: Collector, Chunker, Reader, Retriever, Pattern Engine, Scheduler, Web Searcher, Goal Tracker, Generator |
| **Ideas.md** | `.../Ideas and System/` | 204 lines of raw ideas and feature requests |
| **locus_features.md** | `.../Ideas and System/` | 162 features annotated with architecture decisions |
| **Comprehensive Locus System Design.html** | `.../Ideas and System/` | Interactive pyramid visualization |
| **locus_microsystems.html** | `.../Ideas and System/` | Microsystem architecture visualization |
| **locus_pyramid.html** | `.../Ideas and System/` | Architecture pyramid interactive UI |

---

# Part I — Augmented Feature Matrix (§1-§33)

## Classification Legend

| Verdict | Meaning |
|---------|---------|
| ✅ **KEEP-PI** | Inherit directly from Pi's codebase. No changes needed. |
| 🔄 **AUGMENT** | Pi provides the base; Locus adds functionality on top. Specify what's added. |
| 🆕 **LOCUS-NEW** | Locus-unique feature. Specify source codebase to steal logic from, or mark as original. |
| 🔀 **MULTI-PROVIDER** | Feature where Locus offers MULTIPLE swappable providers. List all options. |
| ⚪ **SKIP** | Not needed or deliberately excluded. |

---

## §1. Agent Core / Runtime

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 1.1 | **Main agent loop** | ✅ KEEP-PI | Pi `agent-loop.ts` | — | Pi's two-entry agent loop (tooled + simple) is production-grade. |
| 1.2 | **Turn context management** | 🔄 AUGMENT | Pi `agent-harness.ts` + Hermes `turn_context.py` | — | Keep Pi's harness state machine. Add Locus lifecycle hooks for memory injection and context enrichment. Steal Hermes' per-turn state tracking pattern. |
| 1.3 | **Turn retry / error recovery** | 🔄 AUGMENT | Pi agent loop + OpenHuman self-healing | MemoryProvider | Pi has basic retry (3x, exponential backoff). Augment with OpenHuman's self-healing pattern: ToolMaker polyfill (auto-generate missing tools), circuit breakers for failing providers. |
| 1.4 | **System prompt builder** | 🔄 AUGMENT | Pi `system-prompt.ts` + Hermes `prompt_builder.py` | PromptAssembler | Pi assembles from templates + skills. Locus augments to inject: SOUL.md personality, Context Forge output, user profile, DCS/mode state. Steal Hermes' dynamic prompt builder pattern. |
| 1.5 | **Prompt caching** | ✅ KEEP-PI | Pi `openai-prompt-cache.ts` | — | Built-in for OpenAI. Anthropic cache via provider config. |
| 1.6 | **Iteration budget / limits** | 🔄 AUGMENT | Pi + Hermes `iteration_budget.py` | — | Pi has grace-turn after budget. Steal Hermes' configurable iteration budget with per-session overrides. |
| 1.7 | **Background review / post-turn** | 🔀 MULTI-PROVIDER | Hermes `background_review.py` · OpenHuman post-turn hooks · Locus Inner Loop | PostTurnProvider | **Options**: (a) Hermes curator → insights → memory nudge, (b) OpenHuman 4-hook system (Archivist, Reflection, ToolTracker, UserProfile), (c) Locus proactive Inner Loop, (d) Custom. |
| 1.8 | **Stream diagnostics** | ✅ KEEP-PI | Pi event stream utilities | — | Built-in. |
| 1.9 | **Rate limit tracking** | 🆕 LOCUS-NEW | Hermes `rate_limit_tracker.py` | — | Steal Hermes' pattern. Track rate limit headers from LLM responses. Surface in TUI footer / Telegram status. |
| 1.10 | **Usage / cost tracking** | 🆕 LOCUS-NEW | Hermes `usage_pricing.py` + `credits_tracker.py` | CostTracker | Steal Hermes' pricing table and accumulation logic. Display in footer widget. Target: ~$0.012/day with DeepSeek V4 Flash. |
| 1.11 | **Title generation** | 🆕 LOCUS-NEW | Hermes `title_generator.py` | — | Auto-generate session titles. Steal Hermes' implementation. |
| 1.12 | **Onboarding flow** | 🔄 AUGMENT | Pi project trust + Locus setup | — | Keep Pi's project trust. Add `locus setup` wizard for first-run config (Telegram token, Neo4j URI, DeepSeek key, vault path, timezone, coding harness preferences). |
| 1.13 | **Agent initialization** | 🔄 AUGMENT | Pi `agent-harness.ts` | — | Locus augments Pi's init to also initialize: sidecar connection, Memory Tri-Stack, channel bridges, file crawlers. |
| 1.14 | **Coding harness delegation** | 🆕 LOCUS-NEW | Locus-original | HarnessProvider | **Locus doesn't code — it delegates.** See §30 for full spec. Pre-installed: Antigravity, Claude Code, OpenCode, Pi, Aider, custom. |

---

## §2. LLM Providers

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 2.1 | **30+ Providers** | ✅ KEEP-PI | Pi `providers/` | — | Anthropic, OpenAI, Google, DeepSeek, Mistral, AWS, Azure, Cloudflare, + 22 more. |
| 2.2 | **OAuth flows** | ✅ KEEP-PI | Pi `oauth/` | — | Device code + PKCE. |
| 2.3 | **Custom / local models** | ✅ KEEP-PI | Pi `models.json` | — | Ollama, LM Studio, vLLM, any OpenAI-compatible. |
| 2.4 | **Provider registry** | ✅ KEEP-PI | Pi `api-registry.ts` | — | Auto-registration. |
| 2.5 | **Model selection** | ✅ KEEP-PI | Pi `/model`, Ctrl+P | — | Model cycling. |
| 2.6 | **Streaming (SSE)** | ✅ KEEP-PI | Pi `stream.ts` | — | Built-in. |
| 2.7 | **Intelligent routing** | 🔀 MULTI-PROVIDER | OpenHuman `IntelligentRouting` | RouterProvider | **Options**: (a) Single-provider (Locus default — DeepSeek V4 Flash), (b) OpenHuman's intelligent routing (local+cloud fallback), (c) Custom routing logic. |
| 2.8 | **Refusal detection** | 🆕 LOCUS-NEW | OpenHuman Aho-Corasick DFA | — | Steal OpenHuman's DFA-based refusal scanner. Runs post-LLM-call, triggers retry with rephrased prompt. |
| 2.9 | **Image generation** | ✅ KEEP-PI | Pi `images.ts` | — | Built-in image provider registry. |
| 2.10 | **LLM Capability Audit** | 🆕 LOCUS-NEW | locus_features #121 | — | Automated benchmark: scan and audit local/cloud LLMs, report task compatibility. |

**Default model config**: DeepSeek V4 Flash (~$0.012/day). User can change via `locus config set model <name>`.

---

## §3. Tools / Tool Execution

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 3.1 | **File read/write/edit** | ✅ KEEP-PI | Pi `read.ts`, `write.ts`, `edit.ts` | — | Built-in. |
| 3.2 | **Shell / bash** | ✅ KEEP-PI | Pi `bash.ts` | — | Built-in with output capture. |
| 3.3 | **Grep / search** | ✅ KEEP-PI | Pi `grep.ts` | — | Ripgrep-backed. |
| 3.4 | **List / find** | ✅ KEEP-PI | Pi `ls.ts`, `find.ts` | — | Built-in. |
| 3.5 | **Web search** | ✅ KEEP-PI | Pi `web_search` | — | 8 providers. |
| 3.6 | **Web fetch** | ✅ KEEP-PI | Pi `fetch_content` | — | URL→markdown, YouTube transcripts, GitHub repos. |
| 3.7 | **Git tools** | 🔄 AUGMENT | Pi `git.ts` + Locus `git_ops.py` | — | Pi has basic git. Augment with vault-aware git ops. |
| 3.8 | **Tool call validation** | 🔄 AUGMENT | Pi `tool-definition-wrapper.ts` + Hermes `tool_guardrails.py` | — | Keep Pi's wrapper. Steal Hermes' guardrails for safety. |
| 3.9 | **Tool result classification** | 🆕 LOCUS-NEW | Hermes `tool_result_classification.py` | — | Classify results as success/failure/partial. |
| 3.10 | **Tool output accumulator** | ✅ KEEP-PI | Pi `output-accumulator.ts` | — | Built-in truncation. |
| 3.11 | **Tool timeout / budget** | 🆕 LOCUS-NEW | OpenHuman `tool_timeout` | — | Per-tool timeout enforcement. |
| 3.12 | **Custom Locus tools** | 🆕 LOCUS-NEW | Locus-unique | ToolProvider | See custom tools list below. |

**Custom Locus Tools (registered by augmentation):**

| Tool | Description | Sidecar | Swappable |
|------|-------------|---------|-----------|
| `locus_memory_query` | Query Memory Tri-Stack | Yes | MemoryProvider |
| `locus_vault_search` | Search Obsidian vault via file crawlers | Yes | VaultProvider |
| `locus_checkin` | Capture check-in data (E, M, S, ST, T) | Yes | — |
| `locus_schedule` | View/create scheduled tasks via Scheduler | Yes | SchedulerProvider |
| `locus_life_status` | DCS, factions, operating mode, faction lag | Yes | LifeOSProvider |
| `locus_brain_think` | Trigger Inner Loop reasoning | Yes | BrainProvider |
| `locus_voice_transcribe` | Transcribe audio | Yes | VoiceProvider |
| `locus_user_profile` | Query/update user profile | Yes | UserModelProvider |
| `locus_delegate_code` | Delegate coding to best harness | No | HarnessProvider |
| `locus_research` | Invoke AutoResearch pipeline | Yes | ResearchProvider |
| `locus_crawl` | Trigger file crawler on demand | Yes | CrawlerProvider |
| `locus_goals` | CRUD on 3-layer goal stack | Yes | — |
| `locus_idea` | Capture rough idea → enhance → optional promote | Yes | — |
| `locus_link_dump` | Save + tag URL | Yes | — |

---

## §4. Memory & Persistence — The Memory Tri-Stack

> **DEFAULT: Neo4j Agent Memory + Headroom + PageIndex**
> **Memory** (graph/relational) + **Token Compression** (CCR pipeline) + **Smart Retrieval** (vectorless page-level)

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 4.1 | **Session storage** | ✅ KEEP-PI | Pi JSONL sessions | — | Tree-based JSONL, fork, resume. |
| 4.2 | **Graph memory (Layer 1: Memory)** | 🔀 MULTI-PROVIDER | Neo4j Agent Memory (default) + OpenHuman `memory_graph` | MemoryProvider | **DEFAULT**: Neo4j Agent Memory POLE+O model. 3-tier: sensory/short/long with entity extraction + relationship linking. **Options**: OpenHuman's `memory_graph`, mem0, Supermemory, Honcho, Mastra, Cognee, custom. |
| 4.3 | **Token compression (Layer 2: Compression)** | 🔀 MULTI-PROVIDER | Headroom (default) + Locus CCR | CompressionProvider | **DEFAULT**: Headroom CCR pipeline — Cache-Compress-Retrieve. 60-95% token reduction with zero information loss. **Options**: simple summarization, LOCUS_SHORTHAND (4× compression), custom. |
| 4.4 | **Smart retrieval (Layer 3: Retrieval)** | 🔀 MULTI-PROVIDER | PageIndex (default) + Hermes FTS5 | RetrievalProvider | **DEFAULT**: PageIndex — whole-note embedding, vectorless BM25+structure hybrid. For well-structured Obsidian notes (200-800 words), preserves context better than chunking. **Options**: Hermes FTS5, OpenHuman memory_search, pgvector semantic, custom. |
| 4.5 | **Memory tree / cascade** | 🆕 LOCUS-NEW | OpenHuman bucket-seal cascade | — | Steal OpenHuman's bucket-seal cascade for hierarchical memory organization. |
| 4.6 | **Entity extraction** | 🔀 MULTI-PROVIDER | OpenHuman `memory_entities` · Locus design | EntityExtractor | **Options**: spaCy → GLiNER → LLM pipeline, OpenHuman's `memory_entities`, DeepSeek entity extraction, custom. |
| 4.7 | **Memory sync** | 🆕 LOCUS-NEW | OpenHuman `memory_sync` | — | Steal OpenHuman's memory sync for cross-session consistency. |
| 4.8 | **Memory queue** | 🆕 LOCUS-NEW | OpenHuman `memory_queue` | — | Async memory write queue. Steal OpenHuman's pattern. |
| 4.9 | **Memory diff** | 🆕 LOCUS-NEW | OpenHuman `memory_diff` | — | Track memory state changes. |
| 4.10 | **Holographic HRR** | 🆕 LOCUS-NEW | Locus-original | — | SHA-256 deterministic vectors, bind/unbind/bundle. |
| 4.11 | **Hebbian pathway weighting** | 🆕 LOCUS-NEW | Locus-original | — | Neo4j edge weights: +0.1 traversal, ×1.3/×0.7 feedback, ×0.95 weekly decay. |
| 4.12 | **STDP reinforcement** | 🆕 LOCUS-NEW | Locus-original | — | Response latency < 2min = ×1.5 reinforcement. |
| 4.13 | **Spaced repetition** | 🆕 LOCUS-NEW | Locus-original | — | Nodes near decay + active outcomes → Inner Loop surfaces them. |
| 4.14 | **Project-specific memory decay** | 🆕 LOCUS-NEW | Locus-original | — | `SET r.weight = r.weight * 0.5` on project completion. |
| 4.15 | **User modeling store** | 🔀 MULTI-PROVIDER | Hermes Honcho · OpenHuman ambient profiling · Locus design | UserModelProvider | **Options**: Hermes' Honcho dialectic modeling, OpenHuman's ambient profiling + PROFILE.md + stability detector (30min), Locus rolling-average profile, custom. |
| 4.16 | **Memory orchestrator** | 🔄 AUGMENT | Hermes `memory_manager.py` · OpenHuman `memory_store` | — | Coordinates all three layers of the Memory Tri-Stack. |
| 4.17 | **LOCUS_SHORTHAND compression** | 🆕 LOCUS-NEW | Locus-original | — | `{e:N,t:HHMM,f:FACTION}` encoding. ~4× token reduction. Fed into Headroom CCR pipeline. |
| 4.18 | **Approval store** | 🆕 LOCUS-NEW | OpenHuman approval gate + Locus `approval_store.py` | — | 10-min TTL approval gate. |

**Memory Tri-Stack Architecture (DEFAULT):**

```
USER QUERY
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│              MEMORY TRI-STACK (DEFAULT)                   │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ LAYER 1: NEO4J AGENT MEMORY (Storage + Structure)   │ │
│  │                                                       │ │
│  │ • POLE+O entity model (Person, Object, Location,     │ │
│  │   Event, Observation)                                 │ │
│  │ • 3-tier: sensory → short-term → long-term           │ │
│  │ • adopt_existing_graph() on Locus's Neo4j             │ │
│  │ • Entity extraction + relationship linking            │ │
│  │ • Hebbian edge weights + STDP + spaced repetition     │ │
│  └───────────────────────┬─────────────────────────────┘ │
│                          │                                 │
│  ┌───────────────────────▼─────────────────────────────┐ │
│  │ LAYER 2: HEADROOM CCR (Token Compression)            │ │
│  │                                                       │ │
│  │ • Cache: store compressed representations             │ │
│  │ • Compress: 60-95% token reduction on retrieval       │ │
│  │ • Retrieve: decompress with zero information loss     │ │
│  │ • + LOCUS_SHORTHAND for behavioral events (~4×)       │ │
│  └───────────────────────┬─────────────────────────────┘ │
│                          │                                 │
│  ┌───────────────────────▼─────────────────────────────┐ │
│  │ LAYER 3: PAGEINDEX (Smart Retrieval)                  │ │
│  │                                                       │ │
│  │ • Whole-note embedding (200-800 word notes)           │ │
│  │ • Preserves full context (no chunking for short docs) │ │
│  │ • Long docs (>2000 words): sentence-boundary chunks   │ │
│  │ • BM25 + structural signals for precision             │ │
│  │ • pgvector integration (collapses Qdrant)             │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  OUTPUT: Compressed, high-relevance context (800 tokens)  │
└─────────────────────────────────────────────────────────┘
```

**All providers remain swappable. User can replace any layer independently.**

---

## §5. Sessions

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 5.1 | **Session format** | ✅ KEEP-PI | Pi JSONL v3 | — | 9 entry types, tree-based. |
| 5.2 | **Session branching / fork** | ✅ KEEP-PI | Pi `--fork` | — | Built-in. |
| 5.3 | **Session resume** | ✅ KEEP-PI | Pi `--resume` / `--continue` | — | Built-in. |
| 5.4 | **Session naming** | ✅ KEEP-PI | Pi `--name` | — | Built-in. |
| 5.5 | **Session picker UI** | ✅ KEEP-PI | Pi `session-picker.ts` | — | Interactive picker. |
| 5.6 | **Session compression** | 🔀 MULTI-PROVIDER | Pi compaction · Hermes compression · Headroom CCR | CompactionProvider | **Options**: Pi's compaction (default), Hermes' conversation compression, Headroom CCR, custom. |
| 5.7 | **Session export** | ✅ KEEP-PI | Pi HTML/JSON/MD | — | Built-in. |
| 5.8 | **Telegram session bridge** | 🆕 LOCUS-NEW | Locus-unique | ChannelProvider | Maps Telegram chats to Pi sessions. |
| 5.9 | **Stateless 24h session logs** | 🆕 LOCUS-NEW | locus_features #119 | — | Daily export: chat session + terminal logs + git commits → daily Obsidian file. |

---

## §6. Context Management

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 6.1 | **Context window management** | 🔄 AUGMENT | Pi compaction + Hermes `context_engine.py` | — | Keep Pi's compaction. Steal Hermes' context engine for more intelligent truncation decisions. |
| 6.2 | **Context references** | 🆕 LOCUS-NEW | Hermes `context_references.py` | — | Track which context was actually used. |
| 6.3 | **Coding-specific context** | 🆕 LOCUS-NEW | Hermes `coding_context.py` | — | Inject code-aware context. Delegated to coding harnesses. |
| 6.4 | **Token overflow handling** | ✅ KEEP-PI | Pi `overflow.ts` | — | Built-in. |
| 6.5 | **Context Forge (800-token assembler)** | 🆕 LOCUS-NEW | Locus-original + LOCUS_BRAIN_MODULE_PROMPT.md | ContextAssembler | 6-layer multi-source context assembly. THE anti-hallucination mechanism. |
| 6.6 | **Query Router / Intent Classifier** | 🆕 LOCUS-NEW | Locus-original + LOCUS_BRAIN_MODULE_PROMPT.md | IntentClassifier | 8 intent types → source routing matrix. ~50 tokens per classification. |
| 6.7 | **Pluggable context engines** | 🆕 LOCUS-NEW | locus_features #127 | ContextEngineProvider | Third-party engines can manage memory context. |

**Context Forge — Modular Layer Architecture (from LOCUS_BRAIN_MODULE_PROMPT.md):**

```
INTERFACE ContextLayer:
  name: string
  budget_tokens: int
  priority: int

  fetch(query: string, budget: int) → string
  compress(content: string, target_tokens: int) → string

DEFAULT LAYERS (all independently toggleable):
  identity_layer(80t)    → SOUL.md personality + top 3 behavioral tendencies
  temporal_layer(60t)    → current time, day, exam period, next 3 calendar events
  events_layer(180t)     → last 6h behavioral events via LOCUS_SHORTHAND
  graph_layer(150t)      → Neo4j top Hebbian pathways (increments weight +0.1 on traversal)
  retrieval_layer(200t)  → PageIndex top 5 semantic results (whole notes)
  web_layer(100t)        → web context (only if EXTERNAL_KNOWLEDGE intent)
  buffer(30t)            → overflow

CORE LAW: If ALL layers empty → tell LLM "No personal data found."
           NEVER skip to guessing. Silence > hallucination.
```

---

## §7. TUI / Terminal Interface

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 7.1 | **Full TUI framework** | ✅ KEEP-PI | Pi React/Ink | — | Full editor, message history, tool rendering. |
| 7.2 | **Multiline editing** | ✅ KEEP-PI | Pi | — | Built-in. |
| 7.3 | **Keyboard shortcuts** | ✅ KEEP-PI | Pi 15+ keybindings | — | Configurable. |
| 7.4 | **Themes** | 🔄 AUGMENT | Pi theme system | — | Add Locus branded themes (amber accents from design docs). |
| 7.5 | **Slash command autocomplete** | ✅ KEEP-PI | Pi `slash-commands.ts` | — | Locus commands auto-registered. |
| 7.6 | **Status bar / footer** | 🔄 AUGMENT | Pi footer API | FooterWidget | Locus adds: DCS score, operating mode, active faction, memory stats, sidecar status. |
| 7.7 | **Streaming tool output** | ✅ KEEP-PI | Pi | — | Real-time. |
| 7.8 | **Diagnostics UI** | 🔄 AUGMENT | Pi + Hermes `hermes doctor` | — | `locus doctor` checks: sidecar, Neo4j, Telegram, vault, Memory Tri-Stack health, coding harness availability. |
| 7.9 | **Provider attribution** | ✅ KEEP-PI | Pi `provider-attribution.ts` | — | Shows which provider/model is active. |

---

## §8. CLI

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 8.1 | **39 CLI flags** | ✅ KEEP-PI | Pi | — | All inherited. |
| 8.2 | **Run modes** | ✅ KEEP-PI | Pi | — | Interactive, Print, RPC, JSON. |
| 8.3 | **Batch mode** | ✅ KEEP-PI | Pi `--print` | — | One-shot. |
| 8.4 | **RPC / daemon mode** | ✅ KEEP-PI | Pi `--mode rpc` | — | JSON protocol over stdin/stdout. Used by Telegram bridge. |
| 8.5 | **Self-update** | 🔄 AUGMENT | Pi `pi update` | — | `locus update` updates both Pi core and Locus augmentation. |
| 8.6 | **Doctor / diagnostics** | 🆕 LOCUS-NEW | Hermes + OpenHuman + LOCUS_BRAIN_MODULE_PROMPT.md #103 | — | `locus doctor` — full health report: PG row counts, Neo4j node/edge counts, pgvector sizes, vault file count, sidecar status, coding harness availability. |
| 8.7 | **Config management** | 🔄 AUGMENT | Pi `config.ts` | — | `locus config` manages Locus-specific settings. |
| 8.8 | **Gateway lifecycle** | 🆕 LOCUS-NEW | Hermes gateway | — | `locus gateway run/start/stop/restart/status/install/uninstall`. |
| 8.9 | **Setup wizard** | 🆕 LOCUS-NEW | Locus | — | `locus setup` — guided first-run configuration (Telegram, Neo4j, vault, timezone, harnesses). |
| 8.10 | **Locus-specific CLI commands** | 🆕 LOCUS-NEW | Locus-unique | — | `locus life`, `locus memory`, `locus vault`, `locus brain`, `locus research`, `locus delegate`. |
| 8.11 | **Self-maintenance** | 🆕 LOCUS-NEW | Ideas.md #9 | — | Auto-update deps on schedule, diagnostic report on breakage, P1 fix task creation. |

---

## §9. Extensions / Plugins / Skills

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 9.1 | **Extension system** | ✅ KEEP-PI | Pi 25+ lifecycle events | — | Locus extensions load alongside Pi extensions. |
| 9.2 | **Skills system** | ✅ KEEP-PI | Pi SKILL.md discovery | — | Locus bundles skills in its `skills/` directory. |
| 9.3 | **Skills marketplace** | 🔄 AUGMENT | Pi packages + Hermes 4 indexes | — | `locus install` pulls from Pi gallery + Hermes skill indexes. |
| 9.4 | **ACP protocol** | 🆕 LOCUS-NEW | Hermes full ACP adapter | — | Steal Hermes' ACP for inter-agent communication. |
| 9.5 | **Prompt templates** | ✅ KEEP-PI | Pi `prompt-templates.ts` | — | Locus bundles its own templates. |
| 9.6 | **Register custom tools** | ✅ KEEP-PI | Pi `pi.registerTool()` | — | Locus registers ~14 custom tools. |
| 9.7 | **Register custom commands** | ✅ KEEP-PI | Pi `pi.registerCommand()` | — | Locus registers `/locus-*` commands. |
| 9.8 | **Context file loading** | 🔄 AUGMENT | Pi AGENTS.md + Locus SOUL.md | — | SOUL.md: personality, communication rules, "wants" engine output. |
| 9.9 | **Plugin LLM** | 🆕 LOCUS-NEW | Hermes `plugin_llm.py` | — | Secondary LLM for plugin/extension tasks. |
| 9.10 | **Dynamic MCP tool calling** | 🆕 LOCUS-NEW | locus_features #113 | — | Create, compile, register new MCP servers on-the-fly. |
| 9.11 | **Standard skills library** | 🆕 LOCUS-NEW | locus_features #117 | — | Pre-packaged core utilities and automation blueprints. |

---

## §10. Learning & Self-Improvement

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 10.1 | **Post-session learning** | 🔀 MULTI-PROVIDER | Hermes curator · OpenHuman hooks · Locus reflector | LearningProvider | **Options**: (a) Hermes curator, (b) OpenHuman 4-hook system, (c) Locus reflector, (d) Custom. ALL stackable. |
| 10.2 | **Cross-session recall** | 🔀 MULTI-PROVIDER | Memory Tri-Stack (default) | SearchProvider | Powered by Layer 3 (PageIndex) of the Tri-Stack. |
| 10.3 | **User profile building** | 🔀 MULTI-PROVIDER | Hermes Honcho · OpenHuman ambient · Locus design | UserModelProvider | Single-row PG table. Never hard-overwritten — rolling average updates. From LOCUS_MASTER_DOCUMENT.md §9. |
| 10.4 | **Tool usage tracking** | 🆕 LOCUS-NEW | OpenHuman `ToolTrackerHook` | — | Track tool name, args, success/fail, duration. |
| 10.5 | **Personal Reward Model** | 🆕 LOCUS-NEW | Locus-original · LOCUS_MASTER_DOCUMENT.md | RewardModel | sklearn LogisticRegression. 👍/👎 feedback. Weekly retrain Sunday 04:00. ≥0.6 threshold gates Inner Loop outputs. First meaningful training after ~200-500 labeled examples. |
| 10.6 | **Hebbian learning rules** | 🆕 LOCUS-NEW | Locus-original | — | Neo4j edge weights with biological decay, STDP reinforcement. |
| 10.7 | **Multi-horizon pattern detection** | 🆕 LOCUS-NEW | Locus-original + LOCUS_BRAIN_MODULE_PROMPT.md §5 | PatternEngine | 5 horizons (H1:6h → H5:all-time). Confidence-based promotion: >0.75 AND count >2 → PERSISTENT → auto-updates user_identity. |
| 10.8 | **Self-evolving Architect Bot** | 🆕 LOCUS-NEW | Locus-original + LOCUS_MASTER_DOCUMENT.md | — | Scans reward signals, generates patches, risk-gated deploy. LOW risk auto-deploy, HIGH risk → Telegram approval. |
| 10.9 | **QLoRA Pipeline (Quarterly)** | 🆕 LOCUS-NEW | Locus-original + LOCUS_MASTER_DOCUMENT.md §11 | — | Phase 3. 500+ reward_signals → vast.ai H100 → Unsloth QLoRA on DeepSeek distill → LoRA adapter → Ollama. "Hydro-dipping model weights in user." |
| 10.10 | **Thinking pattern capture** | 🆕 LOCUS-NEW | Ideas.md #124 + locus_features #76 | — | DeepSeek scans AI chat vault for recurring problem-solving approaches. Creates ConceptNode in Neo4j. |
| 10.11 | **Stability detection** | 🆕 LOCUS-NEW | OpenHuman stability detector (30min) | — | Detect when user's behavioral state stabilizes. |

---

## §11. Subagents / Delegation

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 11.1 | **Subagent spawning** | ✅ KEEP-PI | Pi built-in subagent tool | — | Built-in. |
| 11.2 | **Subagent archetypes** | 🔀 MULTI-PROVIDER | OpenHuman 15 · Locus 4 factions | SubagentArchetype | **Options**: OpenHuman's 15, Locus' 4 faction agents, custom. |
| 11.3 | **Depth limiting** | 🆕 LOCUS-NEW | OpenHuman MAX_SPAWN_DEPTH=3 | — | Steal OpenHuman's pattern. |
| 11.4 | **RPC-based subagents** | ✅ KEEP-PI | Pi RPC mode | — | Built-in. |
| 11.5 | **Coding agent** | 🔄 AUGMENT | Pi → Locus delegation | HarnessProvider | Pi's built-in coding agent augmented with Locus' harness delegation. Locus selects the best external coding harness instead of doing it itself. |
| 11.6 | **ACP client for subagents** | 🆕 LOCUS-NEW | Hermes `copilot_acp_client.py` | — | Steal Hermes' ACP client. |
| 11.7 | **Single-provider invokable council** | 🆕 LOCUS-NEW | locus_features #122 | — | Debate and review code/design decisions via spawned LLM advisory board. |

---

## §12. Scheduling & Cron

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 12.1 | **Cron / scheduled tasks** | 🔀 MULTI-PROVIDER | Hermes NL cron · OpenHuman scheduler_gate · Locus APScheduler | SchedulerProvider | **Options**: Hermes NL cron, OpenHuman scheduler_gate, node-cron, APScheduler (sidecar), custom. |
| 12.2 | **Task sources** | 🆕 LOCUS-NEW | OpenHuman `task_sources` | — | Steal patterns from both. |
| 12.3 | **Inner Loop (proactive)** | 🆕 LOCUS-NEW | Locus-original + LOCUS_MASTER_DOCUMENT.md §9 | BrainProvider | Every 90min (07:00-00:00). Deep pass 03:00. Sunday synthesis. |
| 12.4 | **Structured check-ins** | 🆕 LOCUS-NEW | Locus-original + LOCUS_SYSTEM_v1.md §6 | — | 07:30/13:00/18:00/22:00 IST → Telegram inline keyboards for E, M, S, ST, T. |
| 12.5 | **The Scheduling Algorithm** | 🆕 LOCUS-NEW | LOCUS_BRAIN_MODULE_PROMPT.md §6 + LOCUS_SYSTEM_v1.md §7 | — | 7-step algorithm: Lock non-negotiables → DCS mode filter → lag bonus → exhaustion risk → sort TWS → faction balance → time block assignment. |
| 12.6 | **Emergency rescheduling** | 🆕 LOCUS-NEW | LOCUS_BRAIN_MODULE_PROMPT.md §6 | — | `POST /brain/reschedule` accepts `{reason, lost_hours}` and recomputes. |
| 12.7 | **Review cadence** | 🆕 LOCUS-NEW | LOCUS_SYSTEM_v1.md §10 | — | Daily 22:00 (3-sentence), Sunday 20:00 (weekly narrative), Monthly, Quarterly. |

---

## §13. Security & Sandboxing

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 13.1 | **Project trust** | ✅ KEEP-PI | Pi `trust-manager.ts` | — | Built-in. |
| 13.2 | **Shell blocklist** | 🔄 AUGMENT | Pi + OpenHuman + Locus | — | Layer: Pi safety + OpenHuman command classification + Locus BLOCKED_PATTERNS. |
| 13.3 | **File safety** | 🆕 LOCUS-NEW | Hermes + OpenHuman | — | Steal patterns from both. |
| 13.4 | **Sandbox backends** | 🔀 MULTI-PROVIDER | OpenHuman 4 backends | SandboxProvider | **Options**: bubblewrap, docker, firejail, landlock, none. |
| 13.5 | **Autonomy tiers** | 🆕 LOCUS-NEW | OpenHuman readonly/supervised/full | — | Steal OpenHuman's tier system. |
| 13.6 | **Approval gate** | 🆕 LOCUS-NEW | OpenHuman 10-min TTL | — | Steal pattern. |
| 13.7 | **Data redaction** | 🆕 LOCUS-NEW | Hermes `redact.py` | — | Steal pattern. |
| 13.8 | **Prompt injection protection** | 🆕 LOCUS-NEW | OpenHuman + locus_features #71 | — | Layer 1: Regex blocklist (sudo, curl, rm, eval). Layer 2: DeepSeek semantic check (~20 tokens). |
| 13.9 | **Think token scrubbing** | 🆕 LOCUS-NEW | Hermes `think_scrubber.py` | — | Steal pattern. |
| 13.10 | **VM security** | 🆕 LOCUS-NEW | locus_features #69 | — | SSH key-only, fail2ban, UFW. Monthly audit cron → Telegram. |

---

## §14. Voice

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 14.1 | **STT (Speech-to-Text)** | 🔀 MULTI-PROVIDER | Locus + OpenHuman | STTProvider | **Options**: Groq Whisper (default, fastest), Whisper local/whisper-cpp, Azure, OpenAI, custom. |
| 14.2 | **TTS (Text-to-Speech)** | 🔀 MULTI-PROVIDER | Locus + OpenHuman | TTSProvider | **Options**: Edge TTS (default, free), ElevenLabs, OpenAI, Piper, Kokoro (Apache 2.0, 82M params, CPU), custom. |
| 14.3 | **Voice call interface** | 🆕 LOCUS-NEW | Locus-original + Ideas.md #89/#127 | — | Audio → STT → full pipeline → TTS → vault transcript. Debriefing/brainstorming. |
| 14.4 | **Dictation** | 🆕 LOCUS-NEW | OpenHuman + Locus | — | Steal patterns from both. |
| 14.5 | **Audio transcription pipeline** | 🆕 LOCUS-NEW | LOCUS_MASTER_DOCUMENT.md §9 | — | Whisper-large-v3-turbo via Groq. Auto-detect Hinglish. Context chaining between chunks. |
| 14.6 | **Kokoro audiobooks** | 🆕 LOCUS-NEW | LOCUS_MASTER_DOCUMENT.md §15 | — | Auto-generate audiobooks from vault books library. Phase 3. |

---

## §15. Web Search

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 15.1 | **Web search (8 providers)** | ✅ KEEP-PI | Pi `web_search` | — | OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini + full content fetch. |

---

## §16. Browser Automation

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 16.1 | **Browser automation** | 🔀 MULTI-PROVIDER | OpenHuman + Locus Playwright | BrowserProvider | **Options**: Playwright (default), OpenHuman screen_intelligence, Browserbase, custom. |
| 16.2 | **Screenshot / vision** | 🆕 LOCUS-NEW | OpenHuman + Locus | — | Steal OpenHuman's screen intelligence. |

---

## §17. Channels / Gateway / Messaging

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 17.1 | **Telegram** | 🆕 LOCUS-NEW | Hermes + Locus PTB | ChannelProvider | **Primary Locus interface.** Auth, inline keyboards (check-ins!), voice messages, file attachments. python-telegram-bot v21. |
| 17.2 | **Discord** | 🆕 LOCUS-NEW | Hermes adapter | ChannelProvider | Steal Hermes' adapter. |
| 17.3 | **Slack** | 🆕 LOCUS-NEW | Hermes adapter | ChannelProvider | Steal Hermes' adapter. |
| 17.4 | **WhatsApp** | 🆕 LOCUS-NEW | Hermes adapter | ChannelProvider | Steal Hermes' pattern. |
| 17.5 | **Signal** | 🆕 LOCUS-NEW | Hermes `apps/shared` | ChannelProvider | Steal Hermes' pattern. |
| 17.6 | **Additional channels** | 🆕 LOCUS-NEW | Locus | ChannelProvider | IRC, Matrix, Mattermost, Teams, etc. Each a swappable adapter. |
| 17.7 | **CLI / Terminal** | ✅ KEEP-PI | Pi TUI | — | Primary desktop interface. |
| 17.8 | **Platform registry** | 🆕 LOCUS-NEW | Hermes + OpenHuman | — | Registry of active channel bridges. |

---

## §18. MCP (Model Context Protocol)

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 18.1 | **MCP client** | 🆕 LOCUS-NEW | OpenHuman HTTP + stdio client | — | Steal OpenHuman's dual-transport MCP client. |
| 18.2 | **MCP server** | 🆕 LOCUS-NEW | OpenHuman + LOCUS_MASTER_DOCUMENT.md §9 | — | Expose entire backend as single remote MCP server. 12 tools: store_thought, log_task, retrieve_context, query_patterns, get_current_state, get_schedule, log_mood, defer_task, search_vault, get_goal_stack, get_faction_health. |
| 18.3 | **MCP registry** | 🆕 LOCUS-NEW | OpenHuman | — | Dynamic install + 60s reconnect. |
| 18.4 | **Obsidian MCP** | 🆕 LOCUS-NEW | locus_features #84 | — | vault_read, vault_write (append-only), vault_search, vault_tag, vault_stats. |
| 18.5 | **Dynamic MCP creation** | 🆕 LOCUS-NEW | locus_features #113 | — | Create + compile + register new MCP servers on-the-fly. |

---

## §19. Export & Artifacts

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 19.1 | **HTML/JSON/MD export** | ✅ KEEP-PI | Pi export system | — | Built-in. |
| 19.2 | **Trajectory recording** | 🆕 LOCUS-NEW | Hermes `trajectory.py` | — | Steal Hermes' trajectory recording for batch evaluation. |
| 19.3 | **Daily AI Chat Archiver** | 🆕 LOCUS-NEW | Locus-original + LOCUS_MASTER_DOCUMENT.md §9 | — | 23:45 → Playwright scrapes ChatGPT (3 accounts), Claude, Gemini → tagged .md → vault → git commit. |

---

## §20. Computer Use

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 20.1 | **Native desktop control** | 🆕 LOCUS-NEW | OpenHuman `desktop_companion` | — | Steal OpenHuman's pattern. |
| 20.2 | **Screen capture** | 🆕 LOCUS-NEW | OpenHuman `screen_intelligence` | — | Steal pattern. |

---

## §21. Integrations

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 21.1 | **Google Calendar** | 🆕 LOCUS-NEW | Locus manual OAuth + locus_features #61 | IntegrationProvider | 50-line manual OAuth. google-api-python-client. Read events as Scheduler constraints. Write faction-colored blocks. Two-way via Calendar Bridge. |
| 21.2 | **Gmail** | 🆕 LOCUS-NEW | Locus manual OAuth + locus_features #64 | IntegrationProvider | Same OAuth. Classify inbox → task/event/info/ignore. |
| 21.3 | **Webhooks** | 🆕 LOCUS-NEW | OpenHuman + Locus | — | Steal from both. |
| 21.4 | **Calendly** | 🆕 LOCUS-NEW | Ideas.md #14 | — | Link with Locus scheduling. |
| 21.5 | **NotebookLM** | 🆕 LOCUS-NEW | Ideas.md #52 + locus_features #111 | — | teng-lin/notebooklm-py for research/news digests. |
| 21.6 | **Social integrations** | 🆕 LOCUS-NEW | locus_features #123 | IntegrationProvider | WhatsApp, Instagram, Google Photos. Borrow OpenHuman account-linking patterns. |

---

## §22. Configuration

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 22.1 | **Config format** | 🔄 AUGMENT | Pi `settings.json` | — | Locus settings nested under `"locus": {}`. |
| 22.2 | **Config migration** | ✅ KEEP-PI | Pi `migrations.ts` | — | Built-in. |
| 22.3 | **Environment variables** | 🔄 AUGMENT | Pi `env-api-keys.ts` | — | Add `LOCUS_*` env vars. |
| 22.4 | **Multiple profiles** | 🆕 LOCUS-NEW | locus_features #129 | — | Multi-profile system with memory isolation. |

---

## §23. CI/CD & Testing

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 23.1 | **Unit tests** | ✅ KEEP-PI | Pi Vitest | — | Locus extensions tested with Vitest. |
| 23.2 | **CI pipeline** | ✅ KEEP-PI | Pi GitHub Actions | — | Standard CI. |
| 23.3 | **Docker** | 🆕 LOCUS-NEW | Hermes + OpenHuman + LOCUS_MASTER_DOCUMENT.md §7 | — | PostgreSQL 16 + pgvector, Neo4j 5.x, Redis 7.x (optional). **THREE containers, not five** (collapsed Qdrant). |
| 23.4 | **Database diagnostic script** | 🆕 LOCUS-NEW | LOCUS_BRAIN_MODULE_PROMPT.md + locus_features #103 | — | PG rows, Neo4j nodes/edges, pgvector sizes, vault files, Redis keys. Run before every dev session. |

---

## §24. Utilities

All Pi utilities inherited via ✅ KEEP-PI: clipboard, git, image handling, syntax highlighting, frontmatter, file watcher, etc.

---

## §25. Life OS — Behavioral Metrics *(Locus-Unique)*

> **Sources**: LOCUS_SYSTEM_v1.md (The System Bible), LOCUS_MASTER_DOCUMENT.md §6, Prompt.txt, My Initial idea.txt

ALL features → 🆕 LOCUS-NEW (Locus-original). All formulas deterministic (no AI) in Python sidecar.

| # | Feature | Formula / Logic | Source |
|---|---------|----------------|--------|
| 25.1 | **Four Factions Framework** | Health/Stability, Leverage/Money, Craft/Skills, Expression/Exploration. Hierarchy for crisis only. | System Bible §1 |
| 25.2 | **Daily Capacity Score (DCS)** | `DCS = ((E+M+S)/3) × (1 − ST/20)`. GENERATED ALWAYS AS column on `daily_checkins`. | System Bible §4 |
| 25.3 | **Five Operating Modes** | SURVIVAL (<4), RECOVERY (4-5), NORMAL (5-7), DEEP WORK (7-8), PEAK (>8). Python enum. | System Bible §5 |
| 25.4 | **Task Weight Score (TWS)** | `TWS = (P×0.4)+(U×0.4)+(D×0.2)`. GENERATED column. Lag bonus applied at scheduling time. | System Bible §3 |
| 25.5 | **Three-Layer Goal Stack** | Outcomes (WHY, max 7) → Projects (WHAT, max 3 active/faction) → Tasks (HOW). | System Bible §2 |
| 25.6 | **Action Gap Tracking** | `AG = declared_priority − (actual_hrs / target_hrs × 10)`. AG >5 → system alert. | System Bible §3 |
| 25.7 | **Deferral Detection (3/5/8+)** | 3× → FLAG, 5× → Telegram alert, 8+ → escalate in weekly review. | System Bible §9 |
| 25.8 | **Lag Score + TWS Lag Bonus** | `LS = target_hours − actual_hours`. LS>3h → TWS+2, LS>6h → TWS+4, ahead → TWS−1. | System Bible §3 |
| 25.9 | **Emergency Task Injection** | New task TWS > highest → replace lowest non-locked. If U=10 → clear ALL discretionary. | System Bible §11 |
| 25.10 | **Exhaustion Predictor** | `avg_D(5d) > 7 AND avg_DCS(5d) < 5 → exhaustion_risk → reduce load 30%`. | Brain Module §5.5 |
| 25.11 | **Weekly Faction Rebalance** | Sunday cron computes lag scores. Starving factions get auto TWS bonus. | System Bible §14 |
| 25.12 | **7-Step Scheduling Algorithm** | Lock non-negotiables → DCS filter → lag bonus → exhaustion → sort TWS → faction balance → time block. | Brain Module §6 |
| 25.13 | **Review Cadence System** | Daily 22:00 (3-sentence), Sunday 20:00 (weekly), Monthly, Quarterly. | System Bible §10 |
| 25.14 | **Goal Stack Enforcement** | Dead node detection (60 days), active project cap (3/faction), stalled project flag. | Brain Module §8 |
| 25.15 | **Cross-Faction Efficiency** | Three-birds-one-stone: tasks serving multiple factions get TWS+1 per extra faction. | My Initial idea.txt |
| 25.16 | **4-Level Emergency Protocol** | From LOCUS_SYSTEM_v1.md §11: immediate → DCS re-check → cascading deferrals → full shutdown. | System Bible §11 |

---

## §26. Proactive Reasoning / Brain Engine *(Locus-Unique)*

> **Sources**: LOCUS_BRAIN_MODULE_PROMPT.md (9 sub-systems), LOCUS_MASTER_DOCUMENT.md §8-9

ALL features → 🆕 LOCUS-NEW (Locus-original). Python sidecar.

| # | Feature | Modularity | Source |
|---|---------|------------|--------|
| 26.1 | **Inner Loop (Proactive Thinker)** | BrainProvider | MASTER_DOC §9: "You are NOT talking to Shivam. You are thinking about Shivam." Every 90min. Reward Model gate. |
| 26.2 | **State Engine + Inferred Cause Chain** | BrainProvider | BRAIN_MODULE §4: psychological_state, operational_state, contextual_flags, behavioral_alerts, inferred_cause_chain. Event-driven via PG LISTEN/NOTIFY. |
| 26.3 | **Multi-Horizon Pattern Engine** | PatternEngine | BRAIN_MODULE §5: H1(6h), H2(24h), H3(7d), H4(30d), H5(all-time). Promotes at confidence >0.75 + count >2. |
| 26.4 | **Context Forge** | ContextAssembler | BRAIN_MODULE: 6-layer, 800-token, anti-hallucination. |
| 26.5 | **Query Router / Intent Classifier** | IntentClassifier | MASTER_DOC §9: 8 intents, ~50 tokens, confidence <0.7 → query ALL sources. |
| 26.6 | **Personality + "Wants" Engine** | BrainProvider | MASTER_DOC §9: WantNodes in Neo4j. Operational goals from purpose + performance gaps. |
| 26.7 | **Weekly Full Vault Synthesis** | BrainProvider | MASTER_DOC: Sunday 02:00 IST. Personality drift report + faction narrative + top observations. |
| 26.8 | **Cause Chain Engine** | BrainProvider | MASTER_DOC §9: Specific, cited causal explanation of current state. Cross-references everything. |

---

## §27. Vault & Knowledge Intelligence *(Locus-Unique)*

> **Sources**: locus_features.md #30/#42/#43, LOCUS_BRAIN_MODULE_PROMPT.md §1-3, Ideas.md

ALL features → 🆕 LOCUS-NEW (Locus-original).

| # | Feature | Modularity | Notes |
|---|---------|------------|-------|
| 27.1 | **PageIndex (vectorless retrieval)** | RetrievalProvider | Layer 3 of Memory Tri-Stack. Whole-note embedding for <800w notes. |
| 27.2 | **Nightly Vault Ingestion Pipeline** | VaultProvider | APScheduler 23:30 IST. git diff → MD5 compare → new/changed files → embed/chunk → entity extraction → Neo4j + pgvector. |
| 27.3 | **LOCUS_SHORTHAND (4× compression)** | CompressionProvider | `{e:N,t:HHMM,f:FACTION}`. Fed into Headroom CCR. |
| 27.4 | **3-Level Tag Hierarchy** | VaultProvider | faction/domain/specific. ~3,800 unique tags. PG registry enforced on ingestion. |
| 27.5 | **Rough Note Parser / Idea Tracker** | — | Telegram /idea → `captures` table → DeepSeek suggests faction mapping → Promote/Research/Archive. |
| 27.6 | **Link Dump / Resource Logger** | — | Telegram /link → `captures` table → optional auto-summary. |
| 27.7 | **Excalidraw MCP Skill** | — | Phase 3. Autonomous Excalidraw diagrams in Obsidian. |
| 27.8 | **Obsidian Dashboard.md** | — | Central dashboard with Dataview. Panels: Today's Schedule, Faction Health, Active Patterns, Goal Stack, Hebbian Pathways, Brain Observations. |
| 27.9 | **Vault Processing Pipeline** | — | Raw export → parser → if <800w PageIndex, else spaCy chunk → entity extraction → Neo4j + pgvector. PDFs: MinerU. |
| 27.10 | **Local-first storage** | — | Vault markdown = source of truth. PG + Neo4j = volatile indices built from vault. |

---

## §28. File Crawlers & Proactive Information Retrieval *(NEW)*

> **Requirement**: "We will need to code file crawlers that will find out/retrieve the right info for the bot to work with"

| # | Feature | Verdict | Notes |
|---|---------|---------|-------|
| 28.1 | **The Collector (Vault Crawler)** | 🆕 LOCUS-NEW | BRAIN_MODULE §1: Nightly 02:00 IST. MD5 hash-based incremental crawl. Sources: vault .md files, PG events, Google Calendar. Per-file try/except. |
| 28.2 | **The Chunker** | 🆕 LOCUS-NEW | BRAIN_MODULE §2: Raw markdown → factual propositions → Qdrant/pgvector vectors. spaCy sentence boundaries → Groq factual classifier → group max 5 chunks. |
| 28.3 | **The Reader** | 🆕 LOCUS-NEW | BRAIN_MODULE §3: On-demand file read. Always from disk, never cached. 8000-word limit + truncation flag. |
| 28.4 | **The Retriever (Tri-Mode)** | 🆕 LOCUS-NEW | BRAIN_MODULE §4: Mode A (pgvector semantic), Mode B (PG structured SQL), Mode C (Neo4j graph Cypher). Auto-selected by Query Classifier. |
| 28.5 | **AI Chat Archiver Crawler** | 🆕 LOCUS-NEW | MASTER_DOC: 23:45 IST. Playwright persistent contexts. ChatGPT (3 accounts), Claude, Gemini → tagged .md → vault → trigger re-index. |
| 28.6 | **Event Writer** | 🆕 LOCUS-NEW | BRAIN_MODULE: Single write path for all behavioral events. PG NOTIFY after INSERT → triggers State Engine. |
| 28.7 | **Google Calendar Crawler** | 🆕 LOCUS-NEW | MASTER_DOC: Read upcoming events as scheduling constraints. |
| 28.8 | **Telegram Chat Logger Crawler** | 🆕 LOCUS-NEW | locus_features #82: Middleware intercepts ALL messages pre-routing. Nightly backup 23:55 → vault .md. |
| 28.9 | **Social Media Crawler** | 🆕 LOCUS-NEW | Ideas.md #60/#185: End-of-day retrieval of ALL AI chats from ALL accounts. |
| 28.10 | **Email Crawler** | 🆕 LOCUS-NEW | locus_features #64: Gmail API read headers + snippets → classify → captures table. |

**Crawler Architecture:**

```
INTERFACE CrawlerProvider:
  name: string
  schedule: CronExpression | "on-demand"
  
  crawl() → CrawlResult[]
  crawl_incremental(since: datetime) → CrawlResult[]
  health_check() → HealthStatus

ALGORITHM proactive_info_retrieval:
  1. SCHEDULED CRAWLERS run on cron:
     02:00  → Vault Collector (all vault .md files)
     23:30  → Nightly Vault Diff (new/changed files only)
     23:45  → AI Chat Archiver (ChatGPT/Claude/Gemini)
     23:55  → Telegram Chat Logger backup
     */6h   → Google Calendar sync
     */1h   → Email inbox scan (if enabled)
  
  2. ON-DEMAND CRAWLERS triggered by agent:
     Reader → specific file on disk
     Retriever → query against Memory Tri-Stack
     Web Searcher → external information
  
  3. EVERY CRAWLER writes to behavioral_events → triggers State Engine
  4. ALL crawled data flows into Memory Tri-Stack (Layer 1: storage → Layer 2: compress → Layer 3: index)
```

---

## §29. Research & AutoResearch *(NEW)*

> **Requirement**: "We will incorporate https://github.com/karpathy/autoresearch and make it invokeable"

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 29.1 | **AutoResearch integration** | 🆕 LOCUS-NEW | karpathy/autoresearch | ResearchProvider | **Invokeable via `locus research <topic>`** or `locus_research` tool. Karpathy's autoresearch pipeline: query → search → gather papers → synthesize. Adapted for Locus: results stored in vault + Neo4j. |
| 29.2 | **Research → Vault pipeline** | 🆕 LOCUS-NEW | Locus-original | — | AutoResearch output → tagged .md in `/vault/04-Resources/research/` → git commit → trigger re-index → Memory Tri-Stack. |
| 29.3 | **Scheduled research digest** | 🆕 LOCUS-NEW | Ideas.md #52 | — | Optional daily research/news digest on user-configured topics. |
| 29.4 | **NotebookLM integration** | 🆕 LOCUS-NEW | locus_features #111 | — | teng-lin/notebooklm-py for synthesized research briefs. |
| 29.5 | **Web Searcher sub-system** | 🆕 LOCUS-NEW | BRAIN_MODULE §7 | — | Activated when vault has no answer AND query is external. Always surfaces source URL. |

---

## §30. Coding Harness Delegation *(NEW)*

> **Principle**: "Locus shouldn't have its own harness to code something. It should understand the user and their requirements and based on that, prompt the best coding harness."

| # | Feature | Verdict | Source(s) | Modularity | Notes |
|---|---------|---------|-----------|------------|-------|
| 30.1 | **Harness selection engine** | 🆕 LOCUS-NEW | Locus-original | HarnessProvider | Understands user, requirements, deadline, complexity → selects best pre-installed harness. |
| 30.2 | **Pre-installed harnesses** | 🆕 LOCUS-NEW | Locus-original | — | Antigravity, Claude Code, OpenCode, Pi Agent, Aider pre-installed OOTB. |
| 30.3 | **Harness prompt generation** | 🆕 LOCUS-NEW | Locus-original | — | Locus generates the optimal prompt/context for the selected harness. Includes user profile, project context, coding style preferences. |
| 30.4 | **Progress monitoring** | 🆕 LOCUS-NEW | Locus-original | — | Monitor delegated coding task. Report progress to user. |
| 30.5 | **Harness performance learning** | 🆕 LOCUS-NEW | Locus-original | — | Track which harness performs best for which task types. Feed into harness selection. |
| 30.6 | **Custom harness registration** | 🆕 LOCUS-NEW | Locus-original | HarnessProvider | `locus install harness <name>` — register user's own coding harness. |
| 30.7 | **Inter-harness communication** | 🆕 LOCUS-NEW | locus_features #114 | — | Auto-detect local agent dirs, read session data, cross-harness delegation. |

**Harness Provider Interface:**

```
INTERFACE HarnessProvider:
  name: string
  capabilities: string[]       # ["python", "typescript", "full-stack", "debugging"]
  speed: "fast" | "medium" | "thorough"
  
  is_available() → bool
  delegate(task: CodingTask) → DelegationResult
  check_progress(task_id: string) → Progress
  cancel(task_id: string) → void

ALGORITHM harness_selection(task: CodingTask):
  1. ANALYZE task: language, complexity, file count, deadline urgency
  2. FILTER available harnesses by capabilities
  3. RANK by:
     - Historical performance for this task type (from learning data)
     - Speed requirement (deadline proximity)
     - Complexity match (simple → OpenCode, complex → Antigravity)
     - User preference (if set)
  4. SELECT top-ranked harness
  5. GENERATE context-rich prompt for selected harness
  6. DELEGATE and MONITOR
```

---

## §31. Interface Philosophy & Infrastructure *(Locus-Unique)*

| # | Feature | Verdict | Notes |
|---|---------|---------|-------|
| 31.1 | **Dual-interface (TUI + Telegram)** | 🆕 LOCUS-NEW | TUI for desktop, Telegram for mobile. Unified sessions. |
| 31.2 | **4 Daily Structured Check-ins** | 🆕 LOCUS-NEW | 07:30/13:00/18:00/22:00 IST. Telegram inline keyboards for E, M, S, ST, T. |
| 31.3 | **Voice Call Interface** | 🆕 LOCUS-NEW | STT → pipeline → TTS → transcript. For brainstorming/debriefing. |
| 31.4 | **DeepSeek V4 Flash default** | ✅ KEEP-PI config | ~$0.012/day. |
| 31.5 | **Zero-cost constraint** | ✅ KEEP-PI | ~$6-8/year total. |
| 31.6 | **Minimum AI in harness** | ✅ KEEP-PI | LLM for reasoning only. Deterministic logic wherever possible. |
| 31.7 | **Obsidian-centric interactions** | 🆕 LOCUS-NEW | locus_features #110. Interactive check-ins, dashboard buttons, command scripts. |
| 31.8 | **PWA → Obsidian Dashboard** | 🆕 LOCUS-NEW | MASTER_DOC §13. PWA deprecated. Obsidian Dashboard replaces it. |
| 31.9 | **Progress visualization** | 🆕 LOCUS-NEW | Ideas.md #27. Graphs: sleep, mood, goals, faction time. Obsidian Charts plugin. |
| 31.10 | **Avatar / RPG tracker** | 🆕 LOCUS-NEW | Ideas.md #114. Phase 3. AI-generated avatar with stats. |
| 31.11 | **Content Engine** | 🆕 LOCUS-NEW | MASTER_DOC §9. Trigger-based drafts for LinkedIn/Instagram from milestones. |

---

## §32. SOUL.md & Personality *(Locus-Unique)*

| # | Feature | Verdict | Source(s) | Notes |
|---|---------|---------|-----------|-------|
| 32.1 | **SOUL.md personality file** | 🆕 LOCUS-NEW | MASTER_DOC §9 | Defines Locus personality. Read into every LLM call as 80-token preamble. |
| 32.2 | **Communication rules** | 🆕 LOCUS-NEW | MASTER_DOC | Never: "Great question!", "Absolutely!", unsolicited praise. Always: direct, blunt, cite data, push back. |
| 32.3 | **Anti-hallucination guard** | 🆕 LOCUS-NEW | BRAIN_MODULE §9 | Validate response against context. If proper noun not in context → flag. If file/task/date → verify existence. |
| 32.4 | **Mode-aware tone** | 🆕 LOCUS-NEW | BRAIN_MODULE §9 | SURVIVAL/RECOVERY mode → gentle tone, don't push tasks. DEEP/PEAK → push hard. |

---

## §33. Miscellaneous

| # | Feature | Verdict | Source(s) | Notes |
|---|---------|---------|-----------|-------|
| 33.1 | **Error classifier** | 🆕 LOCUS-NEW | Hermes | Steal Hermes' pattern. |
| 33.2 | **Auxiliary LLM client** | 🆕 LOCUS-NEW | Hermes | Secondary LLM for background tasks. |
| 33.3 | **Health checks** | 🆕 LOCUS-NEW | Hermes + OpenHuman | Steal from both. |
| 33.4 | **Notifications** | 🆕 LOCUS-NEW | OpenHuman | Steal pattern. |
| 33.5 | **Code graph analysis** | 🆕 LOCUS-NEW | OpenHuman `codegraph` + locus_features #116 (Graphify) | For harness delegation context. |
| 33.6 | **Subconscious background** | 🆕 LOCUS-NEW | OpenHuman + Locus | Merge patterns. |
| 33.7 | **Workflows** | 🆕 LOCUS-NEW | OpenHuman | Steal pattern. |
| 33.8 | **GitMCP repo parsing** | 🆕 LOCUS-NEW | locus_features #115 | Clone + query remote repos to extract implementation blocks. |
| 33.9 | **Idea → PRD → Architecture pipeline** | 🆕 LOCUS-NEW | MASTER_DOC §15 | Vague ideas → enhanced PRDs → architecture stacks → daily tasks. |

---

# Part II — Feature → Source Codebase Mapping

> **STATUS: AWAITING USER INPUT**
>
> This section will be populated after the user provides their specific feature selection list.
> For each selected feature, the `/understand-anything` skill will be used to:
>
> 1. Identify all relevant files in the source codebase
> 2. Document the purpose of each file
> 3. Map how files work in congruence with each other

---

# Part III — Atomic Logic Stripping

> **STATUS: AWAITING USER INPUT**
>
> This section will be populated after Part II.
> For each feature: pseudocode/algorithm extracted from source files,
> how the logic adapts to Locus' architecture, integration points.

---

# Part IV — Modularity Contract Specifications

## All Provider Interfaces

| Interface | Purpose | Default Provider | Available Alternatives |
|-----------|---------|-----------------|----------------------|
| **MemoryProvider** | Store/query memories | Memory Tri-Stack (Neo4j + Headroom + PageIndex) | mem0, Supermemory, Honcho, Mastra, Cognee, custom |
| **CompressionProvider** | Token compression | Headroom CCR | LOCUS_SHORTHAND, simple summarization, custom |
| **RetrievalProvider** | Document retrieval | PageIndex (vectorless) | Hermes FTS5, pgvector semantic, BM25, custom |
| **UserModelProvider** | Build/query user profile | Locus rolling-average | Hermes Honcho, OpenHuman ambient, custom |
| **BrainProvider** | Proactive reasoning | Locus Brain Engine | Custom |
| **PatternEngine** | Multi-horizon patterns | Locus 5-horizon | Custom |
| **ContextAssembler** | Multi-source context | Locus Context Forge (6-layer, 800t) | Custom layers, custom assembler |
| **IntentClassifier** | Query intent | Locus 8-type classifier | Custom |
| **RewardModel** | Gate proactive outputs | Locus sklearn LogReg | Custom |
| **LifeOSProvider** | Behavioral metrics | Locus Life OS | Custom |
| **SchedulerProvider** | Cron / scheduled tasks | APScheduler (sidecar) | Hermes NL cron, OpenHuman scheduler_gate, custom |
| **ChannelProvider** | Messaging channel bridge | Telegram (primary) | Discord, Slack, WhatsApp, Signal, +8 more, custom |
| **STTProvider** | Speech-to-Text | Groq Whisper | Whisper local, Azure, OpenAI, custom |
| **TTSProvider** | Text-to-Speech | Edge TTS | ElevenLabs, OpenAI, Piper, Kokoro, custom |
| **SearchProvider** | Full-text/semantic search | PageIndex | Hermes FTS5, OpenHuman memory_search, custom |
| **EmbeddingProvider** | Vector embeddings | pgvector (BAAI/bge-small-en-v1.5, 384-dim) | custom |
| **EntityExtractor** | Entity extraction | spaCy → GLiNER → LLM | OpenHuman memory_entities, custom |
| **CompactionProvider** | Session compression | Pi compaction | Hermes compression, Headroom CCR, custom |
| **SandboxProvider** | Shell sandboxing | Pi trust model | bubblewrap, docker, firejail, landlock, custom |
| **BrowserProvider** | Browser automation | Playwright | OpenHuman screen_intelligence, Browserbase, custom |
| **VaultProvider** | Knowledge vault ops | Obsidian (local) | Custom |
| **LearningProvider** | Post-session learning | Locus reflector | Hermes curator, OpenHuman 4-hook, custom |
| **PostTurnProvider** | Post-turn processing | Hermes background_review | OpenHuman hooks, custom |
| **SubagentArchetype** | Subagent templates | Locus 4 factions | OpenHuman 15 archetypes, custom |
| **HarnessProvider** | Coding delegation | Antigravity (default) | Claude Code, OpenCode, Pi, Aider, custom |
| **ResearchProvider** | Research pipeline | AutoResearch (karpathy) | Custom |
| **CrawlerProvider** | File/data crawling | Locus Collector | Custom crawlers |
| **FooterWidget** | TUI footer content | Locus status widget | Custom |

**Universal Provider Pattern:**

```
EVERY provider follows this lifecycle:

1. REGISTRATION:
   provider_registry.register("name", ProviderClass)

2. CONFIGURATION (locus settings):
   locus:
     [subsystem]:
       provider: "name"
       enabled: true
       options:
         key: value

3. INITIALIZATION → 4. RUNTIME → 5. SHUTDOWN → 6. HEALTH CHECK
```

---

# Appendix A — Provider Registry

```
locus/providers/
├── memory/
│   ├── interface.ts           # MemoryProvider interface
│   ├── tri-stack/             # DEFAULT: Neo4j + Headroom + PageIndex
│   │   ├── neo4j-agent-memory.ts
│   │   ├── headroom-ccr.ts
│   │   └── pageindex.ts
│   ├── mem0.ts
│   ├── supermemory.ts
│   ├── honcho.ts, mastra.ts, cognee.ts
│   └── index.ts
├── brain/
│   ├── interface.ts
│   ├── locus-brain-engine.ts  # 9 sub-systems from BRAIN_MODULE_PROMPT
│   └── index.ts
├── channels/ (telegram, discord, slack, whatsapp, ...)
├── voice/ (stt, tts providers)
├── learning/ (reflector, curator, hooks)
├── harness/                   # NEW: Coding delegation
│   ├── interface.ts
│   ├── antigravity.ts
│   ├── claude-code.ts
│   ├── opencode.ts
│   ├── pi-agent.ts
│   ├── aider.ts
│   └── index.ts
├── research/                  # NEW: Research pipeline
│   ├── interface.ts
│   ├── autoresearch.ts
│   └── index.ts
├── crawlers/                  # NEW: File crawlers
│   ├── interface.ts
│   ├── vault-collector.ts
│   ├── ai-chat-archiver.ts
│   ├── telegram-logger.ts
│   ├── calendar-sync.ts
│   ├── email-crawler.ts
│   └── index.ts
└── [...]
```

---

# Appendix B — Config Schema

```json
{
  "locus": {
    "enabled": true,
    
    "memory": {
      "provider": "memory-tri-stack",
      "enabled": true,
      "tri_stack": {
        "layer1_memory": {
          "provider": "neo4j-agent-memory",
          "uri": "bolt://localhost:7687",
          "user": "neo4j",
          "password": "..."
        },
        "layer2_compression": {
          "provider": "headroom-ccr",
          "enabled": true
        },
        "layer3_retrieval": {
          "provider": "pageindex",
          "embedding_model": "BAAI/bge-small-en-v1.5",
          "embedding_dim": 384,
          "page_threshold_words": 800
        }
      },
      "secondary_providers": []
    },
    
    "brain": {
      "provider": "locus-brain-engine",
      "enabled": true,
      "inner_loop": {
        "enabled": true,
        "interval_minutes": 90,
        "active_window": { "start": "07:00", "end": "00:00" },
        "deep_pass_time": "03:00",
        "reward_threshold": 0.6
      },
      "context_forge": {
        "enabled": true,
        "total_budget_tokens": 800,
        "layers": {
          "identity": { "enabled": true, "budget": 80 },
          "temporal": { "enabled": true, "budget": 60 },
          "events": { "enabled": true, "budget": 180 },
          "graph": { "enabled": true, "budget": 150 },
          "retrieval": { "enabled": true, "budget": 200 },
          "web": { "enabled": true, "budget": 100 }
        }
      },
      "state_engine": { "enabled": true, "snapshot_interval_hours": 6 },
      "pattern_engine": { "enabled": true, "interval_hours": 6 }
    },
    
    "life_os": {
      "enabled": true,
      "timezone": "Asia/Kolkata",
      "factions": ["Health", "Leverage", "Craft", "Expression"],
      "faction_targets_weekly": [17.5, 17.5, 21.0, 14.0],
      "checkin_times": ["07:30", "13:00", "18:00", "22:00"],
      "review_cadence": {
        "daily": { "time": "22:00", "duration_min": 7 },
        "weekly": { "day": "Sunday", "time": "20:00", "duration_min": 30 },
        "monthly": { "duration_min": 60 },
        "quarterly": { "duration_min": 120 }
      }
    },
    
    "channels": {
      "telegram": { "enabled": true, "token": "...", "allowed_users": [] },
      "discord": { "enabled": false },
      "slack": { "enabled": false }
    },
    
    "voice": {
      "stt": { "provider": "groq-whisper", "enabled": true },
      "tts": { "provider": "edge-tts", "enabled": true }
    },
    
    "vault": {
      "provider": "obsidian",
      "enabled": true,
      "path": "...",
      "sync": "git",
      "nightly_ingestion": { "enabled": true, "time": "23:30" },
      "weekly_synthesis": { "enabled": true, "day": "Sunday", "time": "02:00" },
      "ai_chat_archiver": { "enabled": true, "time": "23:45" }
    },
    
    "learning": {
      "providers": ["locus-reflector"],
      "user_modeling": { "provider": "locus-rolling-average" },
      "reward_model": { "enabled": true, "retrain_schedule": "weekly" }
    },
    
    "harness": {
      "default": "antigravity",
      "installed": ["antigravity", "claude-code", "opencode", "pi", "aider"],
      "auto_select": true,
      "performance_tracking": true
    },
    
    "research": {
      "provider": "autoresearch",
      "enabled": true,
      "auto_digest": { "enabled": false, "topics": [], "schedule": "daily" }
    },
    
    "crawlers": {
      "vault_collector": { "enabled": true, "time": "02:00" },
      "ai_chat_archiver": { "enabled": true, "time": "23:45" },
      "telegram_logger": { "enabled": true, "backup_time": "23:55" },
      "calendar_sync": { "enabled": true, "interval_hours": 6 },
      "email_crawler": { "enabled": false }
    },
    
    "sidecar": {
      "host": "localhost",
      "port": 8420,
      "auto_start": true
    }
  }
}
```

---

# Appendix C — Coding Harness Registry

| Harness | CLI | Strengths | When Locus selects it |
|---------|-----|-----------|----------------------|
| **Antigravity** | `antigravity` | GSD workflow, multi-file, deep project understanding | Complex architecture, multi-file refactoring |
| **Claude Code** | `claude-code` | Reasoning-heavy, agentic loops | Debugging, logic-intensive, complex algorithms |
| **OpenCode** | `opencode` | Lightweight, fast, simple | Quick fixes, small scripts, one-file changes |
| **Pi Agent** | `pi` (inherited) | Extensible, 30+ providers | General coding, Pi extension development |
| **Aider** | `aider` | Git-aware, diff-based, pair programming | Incremental changes, code review, collaborative |
| **Custom** | user-defined | User's own tools | Registered via `locus install harness <name>` |

---

# Appendix D — The Memory Tri-Stack

**Neo4j Agent Memory** (github.com/neo4j-labs/agent-memory):
- POLE+O entity model (Person, Object, Location, Event, Observation)
- 3-tier memory: sensory → short-term → long-term
- `adopt_existing_graph()` layers on Locus's existing Neo4j
- Automatic entity extraction + relationship linking

**Headroom** (github.com/headroomlabs-ai/headroom):
- CCR: Cache-Compress-Retrieve pipeline
- 60-95% token reduction with zero information loss
- Compresses retrieved context before injection into LLM
- Pairs with LOCUS_SHORTHAND for behavioral event compression

**PageIndex** (github.com/VectifyAI/PageIndex):
- Whole-note embedding for well-structured docs (200-800 words)
- Preserves full context (no lossy chunking for short docs)
- Long docs (>2000 words): sentence-boundary chunks via spaCy
- BM25 + structural signals for precision retrieval
- Collapses Qdrant into PostgreSQL pgvector

**Combined flow:**
```
INPUT (query or crawled data)
    │
    ▼
PageIndex RETRIEVES relevant whole notes / chunks
    │
    ▼
Headroom COMPRESSES retrieved content (60-95% reduction)
    │
    ▼
Neo4j Agent Memory LINKS entities, relationships, and weights
    │
    ▼
Context Forge ASSEMBLES 800-token budget from all sources
    │
    ▼
OUTPUT → LLM prompt with grounded, compressed, structured context
```

---

## Summary Counts

| Verdict | Count | Meaning |
|---------|-------|---------|
| ✅ KEEP-PI | ~55 | Inherited from Pi. Zero effort. |
| 🔄 AUGMENT | ~18 | Pi base + Locus additions. |
| 🆕 LOCUS-NEW | ~110 | New Locus features (steal logic from codebases + Locus-original). |
| 🔀 MULTI-PROVIDER | ~20 | Multiple swappable provider options. |
| ⚪ SKIP | ~3 | Deliberately excluded. |

**28 provider interfaces** covering every major subsystem.
**7+ memory providers**, **4+ STT providers**, **4+ TTS providers**, **13+ channel providers**, **6+ coding harnesses**, **10+ crawlers**.

> **What changed from v3 → v4:**
> - Added **Memory Tri-Stack** (Neo4j Agent Memory + Headroom + PageIndex) as default memory architecture
> - Added **§28: File Crawlers & Proactive Information Retrieval** — 10 crawlers for proactive data gathering
> - Added **§29: Research & AutoResearch** — Karpathy's autoresearch as invokeable research pipeline
> - Added **§30: Coding Harness Delegation** — Locus doesn't code, it delegates to best harness
> - Added **§32: SOUL.md & Personality** — anti-hallucination, mode-aware tone, communication rules
> - Integrated ALL systems from Ideas and System directory (15 documents, 883-line master doc, 625-line brain module, 985-line system bible)
> - Updated all source references to match system design documents
> - **3 new Appendices**: Coding Harness Registry, Memory Tri-Stack spec, updated Config Schema
> - **28 provider interfaces** (up from 25)
> - Feature count: **~206 total** (up from ~178)
