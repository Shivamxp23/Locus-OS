# ATOMIC SELECTIONS — Locus OS Modular Architecture

> **Date:** July 13th, 2026  
> **Purpose:** Final verdict on which codebase/external resource to adopt for every feature across all 37 domains  
> **Philosophy:** Laziness First — if it exists elsewhere, steal its logic and adapt for Locus. Never code from scratch what already works.  
> **Architecture Principle:** Everything is modular — swappable, disable-able, replaceable. Locus is a **Framework**, not a monolith.

---

## Coding Philosophy (as stated)

1. **Laziness First** — Pre-built infrastructure always preferred (e.g., Neo4j Agent Memory instead of custom graph memory)
2. **Steal Logic, Not Just Ideas** — If a feature exists in Pi/Hermes/OpenHuman/ext-resource, strip its atomic logic and implementation strategy for Locus
3. **Never Directly Refer** — Always use `/understand-anything` to query codebases for detail. This document contains the mapping of WHAT to adopt, not verbatim code.
4. **Modular Above All** — Every feature must be a pluggable module. Users turn off, swap, replace any component.

---

## Table of Contents

1. [Core Runtime & Architecture](#1-core-runtime--architecture)
2. [LLM Providers & Model System](#2-llm-providers--model-system)
3. [Tool System](#3-tool-system)
4. [Memory & Persistence](#4-memory--persistence)
5. [Sessions](#5-sessions)
6. [Context Management](#6-context-management)
7. [Profiles](#7-profiles)
8. [CLI & Terminal UI](#8-cli--terminal-ui)
9. [CLI Subcommands](#9-cli-subcommands)
10. [Slash Commands](#10-slash-commands)
11. [Extensions / Plugins / Skills](#11-extensions--plugins--skills)
12. [Learning & Self-Improvement](#12-learning--self-improvement)
13. [Agent Orchestration & Teams](#13-agent-orchestration--teams)
14. [Scheduling & Cron](#14-scheduling--cron)
15. [Subconscious & Background Intelligence](#15-subconscious--background-intelligence)
16. [Security & Sandboxing](#16-security--sandboxing)
17. [Voice & Meetings](#17-voice--meetings)
18. [Desktop Companion](#18-desktop-companion)
19. [Messaging Channels / Gateway](#19-messaging-channels--gateway)
20. [MCP (Model Context Protocol)](#20-mcp-model-context-protocol)
21. [Wallet & Web3](#21-wallet--web3)
22. [Team, Billing & Monitoring](#22-team-billing--monitoring)
23. [Health & Observability](#23-health--observability)
24. [i18n & Localization](#24-i18n--localization)
25. [Connectivity & Devices](#25-connectivity--devices)
26. [SDK](#26-sdk)
27. [Export & Artifacts](#27-export--artifacts)
28. [Integrations](#28-integrations)
29. [Install & Distribution](#29-install--distribution)
30. [CI/CD & Testing](#30-cicd--testing)
31. [Utilities](#31-utilities)
32. [Life OS — Behavioral Metrics](#32-life-os--behavioral-metrics-locus-only)
33. [Proactive Reasoning / Brain Engine](#33-proactive-reasoning--brain-engine-locus-only)
34. [Vault & Knowledge Intelligence](#34-vault--knowledge-intelligence-locus-only)
35. [Interface Philosophy & Infrastructure](#35-interface-philosophy--infrastructure)
36. [Obsidian & Note-Taking](#36-obsidian--note-taking)
37. [Key Paths](#37-key-paths)

---

## 1. Core Runtime & Architecture

### 1A. Tech Stack

| Feature | Adopt From | Rationale |
|---------|-----------|-----------|
| **Language / Runtime** | OpenHuman (Python) — but Hermes-style monolith structure | Locus is Python. Hermes' monolithic agent directory structure (`agent/`, `tools/`, `gateway/`, `cron/`, `plugins/`, `skills/`) is the cleanest Python agent layout across all codebases |
| **Package Structure** | Custom — Modular Plugin Architecture | No existing codebase has true modularity. Design: `locus_core/` (kernel), `locus_modules/` (pluggable features), `locus_providers/` (swappable backends) |
| **Transport Layer** | Hermes Gateway | HTTP + Telegram webhook + gateway system is battle-tested. Locus is Telegram-native headless, so Hermes' gateway architecture fits perfectly |
| **Lazy Imports / Cold-Start** | Hermes | 57% faster cold-start via lazy agent init, lazy imports, mtime-cached config, memoized tool defs |
| **Event Bus (typed pub/sub)** | OpenHuman | `src/core/event_bus/` — publish_global/subscribe_global (broadcast), register_native_global/request_native_global (one-to-one, zero serialization). Domain events for agent, memory, channel, cron, skill, tool, webhook, system |
| **Diff-based rendering** | Pi | Full Unicode support in terminal rendering |

### 1B. Agent Loop

| Feature | Adopt From | Key Files & Logic |
|---------|-----------|-------------------|
| **Main Agent Loop** | Hermes | `AIAgent.run_conversation()` — core loop with tool calling + `AIAgent.chat()` simple interface. Two-entry pattern (tooled + simple) is the cleanest. Adopt: agent loop with iteration budget, tool dispatch, interrupt checks. |
| **Turn Context Management** | Hermes | `turn_context.py` — per-turn state that tracks current conversation turn. Better than OpenHuman's multi-context complexity for Locus' needs |
| **Turn Retry / Error Recovery** | OpenHuman | Self-healing pattern: ToolMaker polyfill + circuit breakers. Hermes has `turn_retry_state.py` but OpenHuman's self-healing is more robust for unattended operation |
| **System Prompt Builder** | Hermes | `system_prompt.py` + `prompt_builder.py` — dynamic assembly from SOUL.md + faction context + temporal window. Pi's skills injection is worth layering on top |
| **Prompt Caching** | Hermes | `prompt_caching.py` — configurable TTL (5min default, 1hr opt-in). Reduces cost at near-zero engineering cost |
| **Iteration Budget / Limits** | Hermes | `iteration_budget.py` — max_iterations (default 90) + grace call. OpenHuman's `token_budget` is more token-accurate but Hermes' iteration-based is simpler and sufficient |
| **Reasoning Content** | Pi | 6 thinking levels (off/minimal/low/medium/high/xhigh) with custom token budgets per level. Locus should offer this as optional since DeepSeek supports reasoning |
| **Rate Limit Tracking** | Hermes | `rate_limit_tracker.py` — critical for single-provider DeepSeek setup. OpenHuman's 30s TTL health probes also worth adopting |
| **Usage / Cost Tracking** | Hermes | `usage_pricing.py` + `credits_tracker.py` + `account_usage.py` — most comprehensive cost tracking across all codebases |
| **Title Generation** | Hermes | `title_generator.py` — auto-name sessions. Low-cost quality-of-life feature |
| **Onboarding Flow** | Hermes | `onboarding.py` — interactive wizard (model → terminal → gateway → tools → agent). Locus already has `locus setup` + `locus setup gateway`, layer Hermes' structured interview on top |

### 1C. Configuration

| Feature | Adopt From | Logic Adaptation |
|---------|-----------|-----------------|
| **Config Format** | Hermes + Locus | Keep Locus' SETTINGS.md (56KB, 28 sections) as canonical. Add Hermes' `config.yaml` + `config set/get/path/env-path/check/migrate` CLI as the programmable interface. YAML for machine, SETTINGS.md for human |
| **Config Migration** | Pi | `migrations.ts` pattern — versioned, auto-migrated. Python equivalent needed |
| **CLI Config Management** | Hermes | `config` — view, `config edit` — open yaml, `config set KEY VAL`, `config path`, `config env-path`, `config check`, `config migrate` |
| **Environment Variables** | Hermes | 19+ provider keys + memory/services keys + runtime vars + platform tokens. Structured env var management through config system |
| **Profile-Aware Config** | Hermes | `get_hermes_home()`, profile-aware service units. Multiple profiles with isolated configs/sessions/skills/memory |

### 1D. Startup & Lifecycle

| Feature | Adopt From | Notes |
|---------|-----------|-------|
| **Agent Initialization** | Hermes | `agent_init.py` — clean initialization pattern |
| **Workspace Auto-Creation** | OpenHuman | On-first-launch workspace setup |
| **Core Restart** | Hermes | `/restart` slash command, clean shutdown for memory providers |
| **Self-Update** | Hermes | `hermes update [--check]` — check + pull + restart |
| **Doctor / Diagnostics** | Hermes | `hermes doctor [--fix]` — dependency/config diagnostics |
| **Status Command** | Hermes | `hermes status [--all]` — component health status |

### 1E. Prompt Caching

| Feature | Adopt From |
|---------|-----------|
| **Prompt Cache** | Hermes — `prompt_caching.py`, cache TTL configurable (5min default, 1hr opt-in) |

### 1F. Background Review & Post-Turn

| Feature | Adopt From | Logic |
|---------|-----------|-------|
| **Background Review** | Hermes + OpenHuman hybrid | Hermes: Background review fork per turn, rubric-based skill review. OpenHuman: Post-turn hooks (Archivist, Reflection, ToolTracker, UserProfile). Locus: combine — Hermes' review fork structure with OpenHuman's hook-type architecture |
| **Autonomous Curator** | Hermes | Background agent via gateway cron ticker, 7-day cycle. Grades skill library, consolidates, prunes dead ones. Archived skills classified. Defense-in-depth: never touches bundled/hub skills; max action is archive. |

---

## 2. LLM Providers & Model System

### Provider Architecture

| Feature | Adopt From | Rationale |
|---------|-----------|-----------|
| **Provider Abstraction** | Hermes | Plugin-based provider architecture. Even though Locus defaults to DeepSeek V4 Flash, the provider layer must be modular so users can swap. Hermes' 30+ provider plugin architecture is the most extensible |
| **Provider Registry** | Hermes | `model_metadata.py` — remote catalog manifest (OpenRouter + Nous Portal pulled from remote). Add DeepSeek as default provider |
| **Credential Pool** | Hermes | Rotate across multiple API keys; exhaustion-aware |
| **Automatic Cross-Provider Fallback** | Hermes | `hermes fallback` — retry next provider on 402. Auxiliary client payment fallback |
| **Live Mid-Session Model Switching** | Hermes | `/model` live mid-session model/provider switching. Aggregator-aware resolution. Inline button picker on Telegram |
| **Model Pricing Display** | Hermes | For OpenRouter and Nous Portal. Free-tier model gating |
| **`/fast` Mode** | Hermes | `/fast` whitelist for streaming-prioritized models |
| **Refusal Detection** | OpenHuman | Aho-Corasick DFA (`quality.rs`) — very efficient pattern matching for refusal detection |
| **Model List/Discovery** | Hermes | `model_metadata.py` + remote catalog |
| **Mock / Test Provider** | Pi | `faux.ts` — useful for testing without API costs |

### Decision: Locus Default Provider

> **DeepSeek V4 Flash** remains the default. All other provider infrastructure is optional and swappable. The provider module follows Hermes' plugin pattern: each provider is a self-contained module that registers with the provider registry.

---

## 3. Tool System

### 3A. Tool Architecture

| Feature | Adopt From | Key Files & Logic |
|---------|-----------|-------------------|
| **Tool Registry** | Hermes | `tools/registry.py` — central registry with auto-discovery. `discover_builtin_tools()` imports `tools/*.py`. `ToolEntry` metadata: name, toolset, schema, handler, check_fn, requires_env, is_async, emoji, max_result_size_chars. check_fn TTL cache (~30s). All handlers return JSON strings |
| **Tool Policy / User Filter** | OpenHuman | `tools/policy.rs`, `tools/user_filter.rs`. `classify_command` → `CommandClass` (Read/Write/Network/Install/Destructive). `gate_decision(class, tier)` → Allow/Prompt/Block. More granular than simple blocklist |
| **Tool Timeout / Budget** | OpenHuman | `tool_timeout/` |
| **Tool Result Classification** | Hermes | `tool_result_classification.py` |
| **Tool Output Limits** | Hermes | `tool_output_limits.py` — save oversized results to file instead of destructive truncation |
| **Path Security** | Hermes | `path_security.py` for path sandboxing. OpenHuman's `cwd_jail` + `is_workspace_internal_path` also worth layering |
| **Schema Sanitization** | Hermes | `schema_sanitizer.py` |
| **File Mutation Queue** | Pi | `file-mutation-queue.ts` — sequential file operations, prevents race conditions |
| **XML Tool Dispatch** | OpenHuman | `<tool_call>` XmlDispatcher — lower token overhead than JSON |
| **Compact Tool Dispatch** | OpenHuman | PFormat dispatcher — even more compact |

### 3B. File & Code Tools

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **File Read** | Pi | `read.ts` — pagination (2000 lines / 50KB cap), line numbers, image support. Best UX |
| **File Write** | Pi | `write.ts` — auto-creates parent directories |
| **File Edit** | Pi | `edit.ts` + `edit-diff.ts` — precise find-and-replace, multi-edit in one call, exact-text matching, non-overlapping enforcement |
| **Apply Patch** | Hermes | V4A multi-file patch format, `patch_parser.py` |
| **Shell/Bash** | OpenHuman | 4 sandboxed backends (bubblewrap, docker, firejail, landlock) + Hermes' PTY mode for interactive CLI tools. Locus: use Hermes' backend set with OpenHuman's sandboxing |
| **Grep/Search** | Pi | `grep.ts` — ripgrep-backed, context lines, output modes (content/files_with_matches/count) |
| **List Directory** | Pi | `ls.ts` — recursive walk, pattern matching, max-depth |
| **Find Files** | Pi | `find.ts` |
| **Git Operations** | OpenHuman | `git_operations` — status, diff, log, blame, branch, commit. Most complete git tool set |
| **Run Linter** | OpenHuman | `run_linter` — run project linter |
| **Run Tests** | OpenHuman | `run_tests` — run project test command |
| **LSP Query** | Hermes | `lsp/client.py`, `lsp/manager.py`, `lsp/workspace.py` — full LSP integration for definitions, references, diagnostics |
| **Sandboxed Python** | Hermes | `execute_code` — sandboxed Python execution with Hermes tools programmable |

### 3C. Web & Network Tools

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Web Search** | Locus (existing) + Pi enhancement | Locus already has 5 providers (Brave, Exa, Firecrawl, SearXNG, Tavily). Add Pi's multi-query capability, recency filter, domain filter, full content fetch |
| **Web Fetch/Scrape** | Pi | `fetch_content` — URL→markdown, YouTube transcripts with frames, GitHub repos, Gemini fallback. Most versatile |
| **Get Search Content** | Pi | `get_search_content` — retrieve stored content from prior searches |

### 3D. Vision & Image Tools

| Feature | Adopt From |
|---------|-----------|
| **Vision / Image Analysis** | Hermes — `vision_analyze` (URL, file path, data URL) |
| **Image Generation** | Hermes — `image_generate` with providers: openai, openai-codex, fal, xai |
| **Image Paste/Handling** | Pi — resize, convert, EXIF orientation, Photon WASM, MIME detection |

### 3E. Browser & Computer Control

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Browser Automation** | Hermes | CDP supervisor: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_scroll`, `browser_vision`, `browser_console`. Providers: Browserbase, Camofox local Firefox, Firecrawl, local Chromium auto-spawn. Dialog detection + response |
| **Computer Use** | Hermes | `computer_use` tool for macOS — Accessibility API, screenshot, mouse/keyboard simulation, Finder/native app interaction |
| **VNC Remote Control** | Locus (existing) | Keep `vnc.py` |
| **Screen Capture** | OpenHuman | `screen_intelligence/` — capture engine, state monitoring, image processing pipeline |

### 3F. Coordination & Delegation Tools

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Delegate / Subagent** | Hermes | `delegate_task` — single task or batch parallel. Roles: leaf, orchestrator; depth=1 by default. Synchronous; isolated context + terminal per child. Same provider pool + credentials as parent |
| **Todo / Task Management** | Hermes | `todo` — task list management (read/write/complete/cancel) |
| **Session Search** | Hermes | `session_search` — FTS5 full-text search over past sessions |

### 3G. Coding Harness Delegation Tool ⭐ NEW

> This is a **Locus-original** feature per user requirements.

**Purpose:** Locus does NOT have its own coding agent. Instead, it acts as an intelligent dispatcher that:
1. Understands the user's requirements, deadline, and project context
2. Selects the best pre-installed coding harness (Antigravity, Claude Code, OpenCode, Pi, etc.)
3. Prompts that harness with optimized context to code for the user
4. Returns results through Locus' interface

**Algorithm (Pseudocode):**
```
FUNCTION dispatch_coding_task(user_request, deadline, context):
    // Step 1: Classify task type
    task_profile = classify_coding_task(user_request)
    // {language, complexity, is_refactor, is_new_project, tokens_needed}
    
    // Step 2: Select best harness
    harness = SELECT FROM installed_harnesses
        WHERE capabilities CONTAINS task_profile.requirements
        ORDER BY suitability_score(task_profile) DESC
        LIMIT 1
    
    // Step 3: Build optimized prompt for harness
    harness_prompt = context_forge.assemble_coding_context(
        user_request=user_request,
        relevant_files=file_crawler.find_relevant(task_profile),
        coding_style=SOUL.md.coding_preferences,
        deadline=deadline
    )
    
    // Step 4: Dispatch to harness
    result = harness.execute(harness_prompt, timeout=timeout_from_deadline(deadline))
    
    // Step 5: Verify and return
    verify_result(result)  // basic sanity check
    RETURN result
```

**Harness Registry (pre-installed):**
- **Antigravity** — best for multi-agent orchestration, design-to-code
- **Claude Code** — best for complex reasoning, debugging, research-heavy tasks
- **OpenCode** — best for fast, iterative coding
- **Pi** — best for terminal-native, TypeScript-heavy projects
- **GitHub Copilot** — best for IDE-integrated refactoring

### 3H. File Crawlers ⭐ NEW

> Per user requirement: proactive file crawlers that find the right context for the agent to work with.

**Purpose:** Before any agent task, autonomously crawl the vault/project to find relevant files, context, and dependencies.

**Algorithm (Pseudocode):**
```
FUNCTION file_crawler.crawl(task_description, search_domains):
    relevant_files = []
    
    // Strategy 1: PageIndex tree search
    FOR domain IN search_domains:
        tree = pageindex.get_tree(domain)
        scored_nodes = llm_score_nodes(tree, task_description)
        relevant_files.extend(top_k(scored_nodes, k=5))
    
    // Strategy 2: Neo4j graph traversal
    entities = entity_extractor.extract(task_description)
    FOR entity IN entities:
        graph_files = neo4j.traverse(
            start_node=entity,
            relationship_types=['references', 'contains', 'related_to'],
            max_depth=3
        )
        relevant_files.extend(graph_files)
    
    // Strategy 3: Full-text grep fallback
    IF len(relevant_files) < min_files:
        keywords = extract_keywords(task_description)
        grep_results = ripgrep_search(keywords, search_domains)
        relevant_files.extend(grep_results)
    
    // Strategy 4: Semantic search (pgvector)
    IF pgvector_enabled:
        embedding = embed(task_description)
        semantic_results = pgvector.search(embedding, top_k=10)
        relevant_files.extend(semantic_results)
    
    // Deduplicate and rank
    RETURN rank_by_relevance(deduplicate(relevant_files))

FUNCTION file_crawler.find_relevant(task_profile):
    // Determines which domains/sources to search based on task type
    SWITCH task_profile.type:
        CASE 'code':
            RETURN crawl(task_profile.description, ['vault/code/', 'vault/projects/'])
        CASE 'research':
            RETURN crawl(task_profile.description, ['vault/04-Resources/', 'vault/02-Captures/'])
        CASE 'life_os':
            RETURN crawl(task_profile.description, ['vault/01-System/', 'vault/05-Journal/'])
        DEFAULT:
            RETURN crawl(task_profile.description, ['vault/'])
```

---

## 4. Memory & Persistence ⭐ CRITICAL

### 4A. Primary Storage

| Feature | Adopt From | Rationale |
|---------|-----------|-----------|
| **Primary Storage** | Locus (existing) | SQLite (WAL) — keep. But layer Hermes' FTS5 session search on top |
| **Graph Memory** | **neo4j-labs/agent-memory** (external) | Pre-built Neo4j Agent Memory infrastructure. Clone and integrate directly. Provides: entity extraction → graph nodes, relationship management, memory querying, temporal awareness. Don't reinvent Neo4j integration |
| **Vector Embeddings** | **VectifyAI/PageIndex** (external) + pgvector | PageIndex is vectorless tree-index (reasoning-based, not embedding-based). pgvector stays for semantic search as optional fallback. No vector DB containers |
| **Full-Text Search** | Hermes | FTS5 session search — layer on Locus' SQLite |

### 4B. Memory Stack Architecture ⭐ NEW

The user specified: **neo4j-labs/agent-memory + headroomlabs-ai/headroom + VectifyAI/PageIndex = Memory + Token Compression + Smart Retrieval**

```
┌─────────────────────────────────────────────────────────────┐
│                    MEMORY STACK                              │
│                                                              │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ Agent Memory     │  │ Headroom     │  │ PageIndex     │ │
│  │ (neo4j-labs)     │  │ (Token       │  │ (Smart        │ │
│  │                  │  │  Compression)│  │  Retrieval)   │ │
│  │ • Entity Graph   │  │ • Context    │  │ • Tree Index  │ │
│  │ • Relationship   │  │   Summarize  │  │ • LLM Search  │ │
│  │ • Temporal       │  │ • Token      │  │ • Section     │ │
│  │   Tracking       │  │   Budget     │  │   Locate      │ │
│  │ • Query API      │  │ • History    │  │ • Relevance   │ │
│  │                  │  │   Compress   │  │   Score       │ │
│  └────────┬─────────┘  └──────┬───────┘  └───────┬───────┘ │
│           │                   │                   │          │
│  ┌────────┴───────────────────┴───────────────────┴───────┐ │
│  │              Memory Orchestrator                       │ │
│  │  • Stores: Agent Memory writes → Neo4j                │ │
│  │  • Retrieves: PageIndex finds → pages                 │ │
│  │  • Compresses: Headroom token-controls → context      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 4C. Agent Memory (neo4j-labs/agent-memory) Integration

| Component | Logic |
|-----------|-------|
| **Clone & Integrate** | Clone `neo4j-labs/agent-memory` as a Locus memory provider module. This is pre-built infrastructure for agent memory in Neo4j |
| **Entity Extraction** | Use DeepSeek V4 Flash for entity extraction during ingestion. Agent Memory's schema maps entities → nodes, interactions → edges |
| **Graph Queries** | Agent Memory provides natural-language-to-Cypher translation. Locus wraps this with Context Forge's Neo4j layer |
| **Temporal Awareness** | Agent Memory tracks when memories were created/accessed/updated. Locus layers Hebbian weighting on top |

### 4D. Headroom (headroomlabs-ai/headroom) Integration

| Component | Logic |
|-----------|-------|
| **Token Compression** | Clone/integrate Headroom for context compression. It reduces context size before sending to LLM, saving tokens |
| **History Summarization** | Progressive summarization of conversation history — keep essential facts, discard filler |
| **Context Budget Management** | Enforce token budgets per-turn, per-session. Prevent context window overflow |

### 4E. PageIndex (VectifyAI/PageIndex) Integration

| Component | Logic |
|-----------|-------|
| **Tree Index Building** | Extract Markdown headers → hierarchical tree. Each note becomes a navigable structure |
| **LLM-Based Retrieval** | Instead of embeddings, LLM reasons over tree structures to find relevant sections. No vectors needed |
| **Page-Level Access** | `get_document_structure(note)` → tree. `get_page_content(pages="5-7")` → exact content. Agent gets precisely what it needs |
| **Fallback** | If LLM tree-search fails → raw grep over vault. Graceful degradation |

### 4F. Memory Retrieval Flow

```
USER QUERY
    │
    ▼
QUERY ROUTER (#57)
    │ Classifies intent into 1 of 8 types
    ▼
┌───────────────────────────────────────────────┐
│         MEMORY ORCHESTRATOR                    │
│                                                │
│  1. PageIndex: LLM → tree search → pages X-Y  │
│  2. Agent Memory: Neo4j → graph traversal     │
│  3. FTS5: SQLite → full-text session search   │
│  4. pgvector: semantic search (optional)      │
│                                                │
│  Results assembled by Context Forge → LLM     │
└───────────────────────────────────────────────┘
```

### 4G. Memory Providers (Other Options)

Per user requirement, Locus provides options:

| Provider | Source | When to Use |
|----------|--------|-------------|
| **Locus Default** (Agent Memory + Headroom + PageIndex) | Pre-installed | Standard use — graph + compression + smart retrieval |
| **Mem0** | Hermes integration | Cloud-hosted memory with API |
| **Supermemory** | Hermes integration | Semantic long-term memory |
| **Honcho** | Hermes integration | Dialectic user modeling |
| **Cognee** | External integration | Graph-based memory for codebases |
| **Mastra** | External integration | Workflow-based agent memory |
| **Personal Integrations** | Custom provider interface | Users can build their own memory backend |

### 4H. User Modeling & Approval

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **User Identity Profile** | OpenHuman + Locus design | Ambient profile facets + stability detector (30min). Learning system: `user_profile.rs`, `reflection.rs`, `transcript_ingest/`. Locus: PG single-row, rolling-average behavioral metrics |
| **Approval Store** | OpenHuman | 10-min TTL approval gate. `ApprovalRequestCard` |
| **Session Manager** | OpenHuman | `session_db` — persistence, search, retrieval |

### 4I. Neuroscience-Inspired Memory (Locus Native)

| Feature | Status | Logic |
|---------|--------|-------|
| **Holographic HRR** | ✅ Implemented | SHA-256 deterministic vectors, bind/unbind/bundle |
| **Hebbian Pathway Weighting** | 📐 | Neo4j edge weights: +0.1 traversal, ×1.3/×0.7 feedback, ×0.95 weekly decay |
| **STDP** | 📐 | Response latency <2min = ×1.5 reinforcement |
| **Spaced Repetition** | 📐 | Nodes near decay + active outcomes → Inner Loop surfaces |
| **Project Memory Decay** | 📐 | Cypher: `SET r.weight = r.weight * 0.5` on completion |

---

## 5. Sessions

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Session Format** | Hermes + Locus | Keep Locus' SQLite (conversations, sessions, documents). Layer Hermes' FTS5 session search |
| **Session Branching/Fork** | Pi | `--fork` flag, `/fork`, `/clone`. Tree structure via `id`/`parentId` — in-place branching |
| **Session Resume** | Hermes | `/resume [name]`, session history browsing |
| **Session Naming** | Hermes | `title_generator.py` — auto-name from first prompt |
| **Session Picker** | Pi | Interactive picker (search, sort, filter, rename, delete) — best UX |
| **Session Tree Navigation** | Pi | `/tree` — navigate tree (↑↓, Ctrl+O filter, Shift+L label, branch summary on switch) |
| **Session Compression** | Hermes | `/compress` manual trigger, automatic at token limit, compaction failure recovery. OpenHuman's Microcompact + summarizer for lighter compression |
| **Session Export** | Pi | HTML, JSON, MD. `/share` — private GitHub gist. Hugging Face datasets |
| **Session Stats** | Hermes | `/usage` token usage, `/insights [days]` usage analytics |
| **Session Prune/Delete** | Hermes | Prune older-than-N-days, TUI delete from picker |
| **Subagent Sessions** | Hermes | Linked to parent, hidden from list |
| **Thread Sessions** | Hermes | Multi-user thread support across gateway |

---

## 6. Context Management

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Context Window Management** | Hermes | `context_engine.py` + `context_compressor.py`. Pluggable context engines. Default: built-in ContextCompressor. Plugin-dir architecture means users can swap compression strategies |
| **Manual Compaction** | Hermes | `/compress` manual trigger |
| **Branch Summarization** | Pi | On `/tree` switch: no summary / default / custom instructions. Preserves abandoned-branch context |
| **Context References** | Hermes | `context_references.py` |
| **Coding-Specific Context** | Hermes | `coding_context.py` |
| **Token Overflow Handling** | Hermes + OpenHuman | Hermes: save oversized results to file. OpenHuman: 16 KiB cap + TokenJuice |
| **TokenJuice (Smart Compression)** | OpenHuman | Classify → match rule → reduce. Three-layer: Builtin, User, Project. Up to 80% token reduction. Strategies: truncate, dedup, fold whitespace, drop regexes, summarize |
| **Context Forge** | Locus (designed) | 800-token, 6-layer assembler: identity(80t) + temporal(60t) + PG events(180t) + Neo4j(150t) + PageIndex(200t) + web(100t) |
| **Query Router / Intent Classifier** | Locus (designed) | 8 intent types, source routing matrix |
| **Context File Loading** | Locus (existing) | SOUL.md — user identity and behavioral rules. Add Pi's AGENTS.md/CLAUDE.md auto-discovery for project context |

---

## 7. Profiles

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Multiple Profiles** | Hermes | `hermes profile list/create/use/delete/show/alias/rename/export/import`. Isolated configs/sessions/skills/memory. Sticky default. Profile-aware paths. Worktree mode for parallel agents |

---

## 8. CLI & Terminal UI

> **Locus Decision:** Locus is Telegram-native. No TUI/GUI. But for admin/CLI, adopt:

| Feature | Adopt From |
|---------|-----------|
| **CLI Flags** | Hermes — 13+ keyboard handlers, rich banner/panels, prompt_toolkit input with autocomplete |
| **Single-Query / Print Mode** | Hermes — `hermes chat -q` single-query, `hermes -z <prompt>` one-shot |
| **Run Modes** | Hermes — CLI, Gateway |
| **Curses Fallback** | Locus (existing) — `curses_ui.py` for basic terminal admin |

---

## 9. CLI Subcommands

| Feature | Adopt From | Key Commands |
|---------|-----------|--------------|
| **Config** | Hermes | `config`, `config edit`, `config set`, `config path`, `config env-path`, `config check`, `config migrate` |
| **Model** | Hermes | `model` — interactive picker |
| **Setup** | Hermes | `setup [section]` — interactive wizard |
| **Doctor/Diagnostics** | Hermes | `doctor [--fix]` |
| **Status** | Hermes | `status [--all]` |
| **Gateway** | Hermes | `gateway run/install/start/stop/restart/status/setup` |
| **Cron** | Hermes | `cron list/add/edit/pause/resume/run/status` |
| **Profile** | Hermes | `profile list/create/use/delete/show/alias/rename/export/import` |
| **Sessions** | Hermes | `sessions list/export/rename/delete/prune/stats/browse` |
| **Memory** | Hermes | `memory setup/status/off` — for memory provider config |
| **Skills** | Hermes | `skills list/search/install/inspect/config/check/update/uninstall` |
| **MCP** | Hermes | `mcp serve/add/remove/list/test/configure` |

---

## 10. Slash Commands

> Locus is Telegram-native, so slash commands are `/telegram_command` style.

| Category | Adopt From | Commands |
|----------|-----------|----------|
| **Session** | Hermes | `/new`, `/reset`, `/retry`, `/undo`, `/compress`, `/stop`, `/resume`, `/branch`, `/fork` |
| **Config** | Hermes | `/config`, `/model`, `/personality`, `/reasoning`, `/verbose` |
| **Tools/Skills** | Hermes | `/tools`, `/skills`, `/cron`, `/kanban` |
| **Info** | Hermes | `/help`, `/usage`, `/insights`, `/status`, `/profile` |
| **Life OS** | Locus (existing) | `/checkin`, `/goals`, `/schedule`, `/review`, `/emergency`, `/idea`, `/link` |

---

## 11. Extensions / Plugins / Skills

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Skills System** | Hermes | Skill bundles, commands, preprocessing, 15 categories. This is the most mature skills system. Pi's SKILL.md frontmatter discovery should be layered for compatibility |
| **Skills Marketplace** | Hermes | 4 marketplace indexes (Anthropic, Claude, LobeHub, OpenAI) — multi-source skill discovery |
| **ACP Protocol** | Hermes | Full ACP adapter (server, session, auth, approval, provenance, tools) — for inter-agent communication |
| **Plugin LLM** | Hermes | `plugin_llm.py` — allows plugins to make independent LLM calls |
| **Extension System** | Pi | Registration API (`registerTool()`, `registerCommand()`), lifecycle events (15+), custom UI. Best for deep extensibility |
| **Context File Loading** | Locus (existing) + Pi | SOUL.md (primary). Add AGENTS.md/CLAUDE.md auto-discovery for project-specific context |

---

## 12. Learning & Self-Improvement

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Post-Session Learning** | Hermes + OpenHuman | Hermes: Curator → insights → memory nudge. OpenHuman: Post-turn hooks (Archivist, Reflection, ToolTracker, UserProfile). Locus: combine both — Hermes' curator cycle with OpenHuman's hook architecture |
| **Cross-Session Search/Recall** | Hermes | FTS5 full-text search + LLM summarization |
| **User Profile Building** | OpenHuman + Hermes | OpenHuman: Ambient profile facets + stability detector. Hermes: Honcho dialectic modeling. Locus: behavioral tendencies, peak windows, stressors, communication style |
| **Stability Detection** | OpenHuman | 30-min stability detector |
| **Tool Usage Tracking** | Locus (existing) + OpenHuman | `tool_tracker.py` + OpenHuman's `ToolTrackerHook` |
| **Personal Reward Model** | Locus (designed) | sklearn LogisticRegression (👍/👎 feedback, weekly retrain, ≥0.6 threshold) |
| **Multi-Horizon Pattern Detection** | Locus (designed) | 5 horizons (H1: 6h, H2: 24h, H3: 7d, H4: 30d, H5: all-time) |
| **Self-Evolving Architect Bot** | Locus (designed) | Scans reward signals, generates patches, risk-gated deploy |
| **Agent Experience Tracking** | OpenHuman | `agent_experience` module |

---

## 13. Agent Orchestration & Teams

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Subagent Spawning** | Hermes | `agent_init.py` + `process_bootstrap.py` — clean process isolation. Same provider pool + credentials as parent |
| **Subagent Archetypes** | OpenHuman | 15 built-in (orchestrator, planner, researcher, critic, etc.). Locus: 4 faction sub-agents (Planner, Curator, Analyst, Builder) |
| **Depth Limiting** | OpenHuman | MAX_SPAWN_DEPTH=3 — prevents runaway agent trees |
| **RPC-Based Subagents** | Hermes | `codex_runtime.py` (RPC) — for remote execution |
| **Coding Agent (Harness Delegation)** | Locus (new) | See §3G — Locus delegates to external harnesses, no native coding agent |
| **ACP Client for Subagents** | Hermes | `copilot_acp_client.py` — standard protocol for subagent communication |

---

## 14. Scheduling & Cron

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Cron / Scheduled Tasks** | Hermes | Natural language cron scheduling. `cron list/add/edit/pause/resume/run/status` |
| **Task Sources** | OpenHuman | `task_sources` module — pluggable task discovery |
| **Scheduled Automations** | Hermes | Daily reports, nightly backups, weekly audits |
| **Inner Loop** | Locus (designed) | APScheduler every 90min (07:00–00:00), fires without user input |
| **Structured Check-ins** | Locus (designed) | 07:30/13:00/18:00/22:00 IST → Telegram inline keyboards |
| **Heartbeat / Notification** | Locus (existing) + OpenHuman | `heartbeat/notification.py` + `subconscious.py` + OpenHuman's `heartbeat` module |

---

## 15. Subconscious & Background Intelligence

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Subconscious Loop** | OpenHuman | Background intelligence that runs continuously: tool tracking, memory archiving, profile updating |

---

## 16. Security & Sandboxing

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Project Trust Management** | Pi | `trust-manager.ts` — trust levels per project directory |
| **Shell Command Blocklist** | OpenHuman + Locus | Policy engine (command classification) + Locus' BLOCKED_PATTERNS |
| **File Safety Checks** | Hermes | `file_safety.py` — prevent accidental destruction |
| **Sandbox Backends** | OpenHuman | 4 backends (bubblewrap, docker, firejail, landlock) |
| **Autonomy Tiers** | OpenHuman | readonly / supervised / full — user chooses per-project |
| **Approval Gate** | OpenHuman + Locus | 10-min TTL + Locus' `approval_store.py` |
| **Data Redaction** | Hermes | `redact.py` — redact sensitive data from logs/memory |
| **Prompt Injection Protection** | OpenHuman | `prompt_injection` module |
| **Think Token Scrubbing** | Hermes | `think_scrubber.py` |
| **Message Sanitization** | Hermes | `message_sanitization.py` |
| **Secret Prompt Encryption** | Locus (existing) | `secret_prompt.py` — keep system prompts encrypted |
| **Proxy Support** | Pi | `node-http-proxy.ts` pattern |
| **Encryption / Keyring** | OpenHuman | `encryption`, `keyring` modules |
| **TLS** | OpenHuman | `tls` module — rustls with platform-native certs |

---

## 17. Voice & Meetings

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **STT (Speech-to-Text)** | Locus (existing) | 4 backends (Whisper local, Azure, Groq, OpenAI) — keep |
| **TTS (Text-to-Speech)** | Locus (existing) | 4 backends (Edge TTS, ElevenLabs, OpenAI, Piper) — keep |
| **Voice Recording In-App** | Hermes | Ctrl+R voice recording |
| **Voice Call Interface** | Locus (designed) | Audio → Groq Whisper → pipeline → Kokoro TTS → vault transcript |
| **Dictation** | Locus (existing) + OpenHuman | `dictation.py` + OpenHuman's `dictation` module |
| **Google Meet Agent** | OpenHuman | Live meet agent: join, transcribe, speak back. Mascot face piped as camera feed |

---

## 18. Desktop Companion

| Feature | Adopt From | Notes |
|---------|-----------|-------|
| **Desktop App** | ❌ Rejected | Locus is Telegram-native. No desktop app. |
| **Desktop Overlay/Mascot** | ❌ Rejected | No visual avatar |

---

## 19. Messaging Channels / Gateway

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Gateway Architecture** | Hermes | `gateway/` — most mature multi-platform gateway. 25+ platforms, graceful restart, memory monitor, hooks, kanban watchers |
| **Telegram** | Locus (existing) | Primary interface — keep PTB, auth, inline keyboards |
| **All Other Channels** | Hermes | Discord, Slack, WhatsApp, Signal, IRC, Matrix, Mattermost, Teams, Lark, DingTalk, Google Chat, Email, iMessage — Hermes' channel adapter pattern |
| **Platform Registry** | Hermes | `platform_registry.py` — clean abstraction per platform |
| **Cross-Platform Message Mirroring** | Hermes | `mirror.py` |
| **Channel-Specific Display Config** | Hermes | `display_config.py` |
| **Device Pairing** | Hermes | `pairing.py` |
| **Sticker/Media Cache** | Hermes | `sticker_cache.py` |
| **Gateway Hooks** | Hermes | `hooks.py` |
| **Slash Access Control** | Hermes | `slash_access.py` |

---

## 20. MCP (Model Context Protocol)

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **MCP Client** | OpenHuman + Locus | HTTP + stdio, protocol 2024-2025. Locus' `mcp_client.py` exists |
| **MCP Server** | OpenHuman | Axum HTTP + SSE — expose Locus tools as MCP tools |
| **MCP Registry** | OpenHuman | Dynamic install, Smithery.ai, 60s reconnect |
| **MCP Audit** | OpenHuman | `mcp_audit` — security audit for MCP servers |
| **Obsidian MCP** | Locus (designed) | vault_read/write/search/tag/stats (localhost, .md only) |
| **Dynamic MCP Integration** | Locus (designed) | Auto-discover + connect MCPs for inter-harness communication, git repo parsing, graphify |

---

## 21. Wallet & Web3

| Feature | Decision |
|---------|----------|
| **Wallet / Web3 / x402** | ❌ Not for Locus. Personal intelligence framework, not financial. |

---

## 22. Team, Billing & Monitoring

| Feature | Decision |
|---------|----------|
| **Team / People** | ❌ Not for Locus. Single-user framework. |
| **Billing** | ❌ Not for Locus. Zero-cost architecture. |
| **Referral** | ❌ Not for Locus. |

---

## 23. Health & Observability

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Health Checks** | Hermes + OpenHuman | `gateway/status.py` + `health` module |
| **Logs** | Hermes | `logs [--follow] [--level] [--session]` |
| **Telemetry** | Pi (optional, off by default) | `telemetry.ts` — usage stats, never personal data |

---

## 24. i18n & Localization

| Feature | Decision |
|---------|----------|
| **i18n** | OpenHuman pattern if needed. Low priority for single-user framework |

---

## 25. Connectivity & Devices

| Feature | Adopt From | Notes |
|---------|-----------|-------|
| **Device Management** | ❌ | Single-user, single-device. Not needed. |
| **Connectivity Monitoring** | OpenHuman | `connectivity/` module — network state monitoring, connection fallback |

---

## 26. SDK

| Feature | Adopt From | Notes |
|---------|-----------|-------|
| **Agent SDK** | Pi | `AgentSession` — programmatic agent access. Low priority for Locus but useful for automation |

---

## 27. Export & Artifacts

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Session Export** | Pi | HTML, JSON, MD formats |
| **Trajectory Recording** | Hermes | `trajectory.py` (1321 lines) — record full agent trajectories for replay |
| **Daily AI Chat Archiver** | Locus (designed) | Nightly 23:45 Telegram → vault .md → git commit |

---

## 28. Integrations

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Composio** | Locus (existing) + OpenHuman | Keep `composio.py`. OpenHuman has 118+ managed integrations through Composio |
| **Polymarket** | Locus (existing) | Keep `polymarket.py` |
| **Webhooks** | Locus (existing) + OpenHuman | `webhooks.py` + `webhooks` module |
| **Google Calendar** | Locus (designed) | Manual OAuth — 50 lines, replacing Composio dependency |
| **Gmail** | Locus (designed) | Manual OAuth |
| **Calendly** | Locus (designed) | Via setup wizard |
| **Stock/Crypto Prices** | OpenHuman | Stock/crypto price lookup |
| **Twilio** | OpenHuman | SMS/voice via Twilio |

---

## 29. Install & Distribution

| Feature | Adopt From |
|---------|-----------|
| **Package Distribution** | Hermes — `pip install locus-os` |
| **Self-Update** | Hermes — `locus update [--check]` |
| **Homebrew / apt / AUR** | OpenHuman pattern |
| **Docker** | Hermes — Docker builds for server deployment |
| **Nix** | Hermes — Nix flake |

---

## 30. CI/CD & Testing

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Unit Tests** | Hermes | pytest — Python standard |
| **CI Pipeline** | Hermes | Full CI (lint, test, typecheck, docker, nix, security) |
| **Linting** | Hermes | Ruff/flake8 |
| **Type Checking** | Hermes | mypy |
| **Batch Trajectory Runner** | Hermes | `trajectory.py` — run trajectories in batch for testing |

---

## 31. Utilities

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Git Integration** | Locus (existing) | Keep `git_ops.py` |
| **Image Handling** | Pi | Resize, convert, EXIF orientation, Photon WASM, MIME detection |
| **Syntax Highlighting** | Pi | highlight.js in editor |
| **Clipboard** | Pi | System clipboard |
| **Frontmatter Parser** | Pi | YAML/TOML frontmatter extraction |
| **File System Watcher** | Pi | `fs-watch.ts` — watch for file changes |
| **Colors / Output Formatting** | Locus (existing) | Keep `colors.py`, `cli_output.py` |
| **SSH Deployment** | Locus (existing) | Keep `deployment` module |
| **Error Classifier** | Hermes | `error_classifier.py` |

---

## 32. Life OS — Behavioral Metrics (Locus-Only Domain)

> All features in this section are Locus-designed. No external adoption needed. These are the differentiating features.

| # | Feature | Gear Type | Logic Summary |
|---|---------|-----------|---------------|
| 1 | **Four Factions Framework** | [D] | Health/Leverage/Craft/Expression. Each is a process fighting for CPU time (attention). PG `factions` table, seed on first start |
| 2 | **Daily Capacity Score (DCS)** | [D] | `((E+M+S)/3) × (1−ST/20)`. Morning Telegram check-in metric. GENERATED ALWAYS AS column |
| 3 | **Five Operating Modes** | [D] | DCS→mode mapping: SURVIVAL/RECOVERY/NORMAL/DEEP_WORK/PEAK. Drives schedule weightage |
| 4 | **Task Weight Score (TWS)** | [D] | `(P×0.4)+(U×0.4)+(D×0.2)`. GENERATED ALWAYS AS. Lag bonus applied at scheduling |
| 5 | **Goal Stack (3-Layer)** | [D] | Outcomes(max7)→Projects(max3/faction)→Tasks. Parsed from Goals.md |
| 6 | **Faction Weekly Stats** | [D] | Sunday cron. SQL aggregation: CR, CS, MS, LS, AG per faction |
| 7 | **Behavioral Event Stream** | [D] | PG LISTEN/NOTIFY foundation. Every endpoint emits. Critical-path infrastructure |
| 8 | **Action Gap Tracking** | [D] | declared_priority − actual_performance. AG>5 → Telegram warning |
| 9 | **Deferral Detection** | [D] | 3/5/8+ rule. Flag→Telegram→Inner Loop escalation |
| 10 | **Dead Node Detection** | [D] | 60d untouched → status→dead_node. Telegram: [Recommit][Kill][Pause] |
| 11 | **Lag Score + TWS Bonus** | [D] | LS>6→TWS+4, LS>3→TWS+2. Ahead faction→TWS−1 |
| 12 | **Emergency Task Injection** | [H] | `/emergency` or AI-detected. TWS comparison, is_locked protection |
| 13 | **Exhaustion Predictor** | [H] | 5-day difficulty vs DCS avg. Auto-reduce load 30% |
| 14 | **Weekly Faction Rebalance** | [D] | Starving faction priority boost. Deterministic, no LLM |
| 15 | **Momentum Score** | [D] | AVG completion_rate over 3 weeks per faction |
| 16 | **Parallel Task Optimizer** | [H] | Topological sort → independent chains. Phase 2 |
| 17 | **Three-Birds Efficiency** | [H] | Cross-faction tasks get TWS+1/extra faction (max +3) |
| 18 | **Review Cadence** | [D+AI] | Daily(7min)/Weekly(30-45min)/Monthly(60min)/Quarterly(2-3hrs) |

---

## 33. Proactive Reasoning / Brain Engine (Locus-Only Domain)

| # | Feature | Gear Type | Logic Summary |
|---|---------|-----------|---------------|
| 56 | **Inner Loop (Proactive Thinker)** | [H] | Every 90min, unprompted. Reward Model gate (≥0.6 threshold). Fires without user input |
| 57 | **Query Router / Intent Classifier** | [H] | 8 intent types → source routing matrix. Routes queries to PageIndex/Neo4j/pgvector/FTS5/web |
| 58 | **Context Forge** | [H] | 800-token 6-layer assembler: identity(80t)+temporal(60t)+PG(180t)+Neo4j(150t)+PageIndex(200t)+web(100t) |
| 59 | **State Engine** | [D] | Single PG row `current_state`. Updated on check-in + significant events. Cached 30min |
| 60 | **Multi-Horizon Pattern Engine** | [H] | H1(6h)→H5(all-time). Confidence-based promotion. Cross-reference state+patterns+history |
| 61 | **Inferred Cause Chain** | [AI] | Plain-language causal explanations. Cross-references state+patterns+identity+calendar. Confidence scored |
| 62 | **Personality + Wants Engine** | [AI] | SOUL.md rules + WantNodes in Neo4j. Drives Inner Loop priorities |
| 28 | **Weekly Vault Synthesis** | [AI] | Sunday 02:00. Personality drift report + faction narrative + top 3 observations |

---

## 34. Vault & Knowledge Intelligence (Locus-Only Domain)

| # | Feature | Gear Type | Logic Summary |
|---|---------|-----------|---------------|
| 26 | **PageIndex + Smart Retrieval** | [H] | Vectorless tree index from Markdown headers. LLM reasons over tree. `get_page_content(pages="X-Y")`. Combined with Neo4j graph traversal at query time |
| 27 | **Nightly Vault Ingestion** | [H] | 23:30 IST. Scan vault, scrape external chats (ChatGPT×3, Claude, Gemini, Perplexity via Playwright), extract entities→Neo4j, update PageIndex trees |
| 65 | **LOCUS_SHORTHAND** | [D] | ~4× token compression. Custom encode/decode. Phase 2 |
| 36 | **Obsidian Dashboard** | [D] | 8 panels via Dataview/Charts. Backend pushes JSON→vault. Replaces PWA |
| 43 | **3-Level Tag Hierarchy** | [D] | faction/domain/specific. PG tag registry |
| 44 | **Rough Note Parser / Idea Tracker** | [H] | /idea → expand → promote/research/archive |
| 45 | **Link Dump / Resource Logger** | [D] | /link → captures table → vault note |
| 47 | **Excalidraw MCP Skill** | [AI] | Autonomous diagram generation via MCP |

---

## 35. Interface Philosophy & Infrastructure

| Feature | Status | Details |
|---------|--------|---------|
| **Telegram-Native Headless** | ✅ | Primary interface. No GUI, no TUI, no PWA |
| **4 Daily Structured Check-ins** | 📐 | Morning/Afternoon/Evening/Night inline keyboards |
| **Voice Call Interface** | 📐 | Groq Whisper→pipeline→Kokoro TTS→vault transcript |
| **Git for Vault Sync** | 📐 | Directory partitioning (backend vs user writes). GitHub private repo |
| **Manual Google OAuth** | 📐 | 50 lines, replacing Composio |
| **pgvector Replaces Qdrant+ChromaDB** | 📐 | <50K vectors, one fewer container |
| **Redis Optional** | 📐 | PG + in-memory dict at single-user scale |
| **DeepSeek V4 Flash Only** | ✅ | ~$0.012/day, ~$4/year |
| **Zero-Cost Constraint** | ✅ | $5 credit → ~416 days |
| **Minimum AI in Harness** | ✅ | LLM only for reasoning/generation. Deterministic logic elsewhere |

---

## 36. Obsidian & Note-Taking

| Feature | Adopt From | Key Logic |
|---------|-----------|-----------|
| **Obsidian Integration** | Hermes | Via `note-taking` skill: read, search, create, edit markdown notes. Frontmatter, wikilinks, tags |
| **Obsidian as Dashboard** | Locus (designed) | Primary dashboard replacing PWA |
| **Excalidraw** | Hermes | Via `diagramming/excalidraw` skill: hand-drawn JSON diagrams |

---

## 37. Key Paths

| Path | Purpose |
|------|---------|
| `~/.locus/config.yaml` | Main configuration |
| `~/.locus/.env` | Environment variables |
| `~/.locus/state.db` | SQLite state (WAL) |
| `~/.locus/sessions/` | Session storage |
| `~/.locus/logs/` | Logs |
| `~/.locus/skills/` | Installed skills |
| `~/.locus/modules/` | Pluggable modules |
| `~/.locus/providers/` | Swappable providers (memory, LLM, search) |
| `~/.locus/auth.json` | OAuth tokens |
| `~/.locus/vault/` | Obsidian vault (git-synced) |
| `~/.agents/skills/` | Cross-harness skills |

---

## Summary: Adoption Map

| Category | Primary Source | Secondary Source(s) | Locus Original |
|----------|---------------|---------------------|----------------|
| **Core Runtime** | Hermes | Pi (event bus) | Modular provider layer |
| **LLM Providers** | Hermes | OpenHuman (refusal detect) | Single-provider default |
| **Tools** | Hermes + OpenHuman | Pi (file tools) | Harness delegation, file crawlers |
| **Memory** | **neo4j-labs/agent-memory + Headroom + PageIndex** | Hermes (FTS5), OpenHuman (approval) | Hebbian learning, pageindex integration |
| **Sessions** | Hermes | Pi (tree/fork/export) | — |
| **Context** | Hermes + OpenHuman | Pi (overflow) | Context Forge, Query Router |
| **Profiles** | Hermes | — | — |
| **CLI/TUI** | Hermes | — | Telegram-native (no TUI) |
| **Skills/Plugins** | Hermes | Pi (extension API) | — |
| **Learning** | Hermes + OpenHuman | — | Reward Model, Pattern Engine |
| **Subagents** | Hermes + OpenHuman | — | Harness delegation |
| **Scheduling** | Hermes | OpenHuman | Inner Loop, Check-ins |
| **Security** | OpenHuman | Hermes + Pi | — |
| **Voice** | Locus existing | OpenHuman | Voice call interface |
| **Channels** | Hermes gateway | Locus existing (Telegram) | — |
| **MCP** | OpenHuman | Locus existing | Dynamic MCP, Obsidian MCP |
| **Life OS (32)** | — | — | All Locus designed |
| **Brain Engine (33)** | — | — | All Locus designed |
| **Vault Intel (34)** | PageIndex (ext) | Hermes (Obsidian skills) | Ingestion pipeline, shorthand |
| **Infrastructure (35)** | — | — | All Locus designed |

---

## Autoresearch Integration ⭐

Per user requirement: **karpathy/autoresearch** is invokeable from Locus.

**Purpose:** When a user asks a research question, Locus can invoke the autoresearch pipeline to perform deep, multi-step web research autonomously.

**Integration Logic:**
```
FUNCTION invoke_autoresearch(query, depth=3):
    // This triggers karpathy/autoresearch as a subprocess
    // Autoresearch does: search → read → synthesize → repeat
    
    // Step 1: Locus' Query Router classifies this as 'research' intent
    intent = query_router.classify(query)
    IF intent != 'deep_research':
        RETURN standard_web_search(query)
    
    // Step 2: Invoke autoresearch pipeline
    research_result = subprocess.run(
        'autoresearch',
        args=[query, f'--depth={depth}', f'--output=/vault/04-Resources/'],
        timeout=600  // 10 minutes
    )
    
    // Step 3: Ingest results into memory
    memory_orchestrator.ingest_file(research_result.output_path)
    
    // Step 4: Context Forge assembles research + memory context
    context = context_forge.assemble([
        'web',      // fresh research
        'pgvector', // related stored knowledge
        'neo4j'     // entity relationships
    ])
    
    // Step 5: Synthesize for user
    RETURN llm.generate(
        system="Synthesize research findings for the user",
        context=context,
        user_query=query
    )
```

**Autoresearch as a Module:** Autoresearch is a pluggable `locus_modules/research/` module. Users can:
- Enable/disable it
- Configure depth, timeouts, source preferences
- Swap it for another research backend (Perplexity Deep Research, etc.)

---

## Modular Architecture: The Provider Pattern

Every feature in Locus follows this pattern:

```python
# Abstract base class defines the interface
class MemoryProvider(ABC):
    @abstractmethod
    def store(self, key: str, value: dict) -> None: ...
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10) -> list[dict]: ...
    @abstractmethod
    def search(self, text: str) -> list[dict]: ...
    @abstractmethod
    def forget(self, key: str) -> None: ...

# Default implementation (Agent Memory + Headroom + PageIndex)
class LocusDefaultMemory(MemoryProvider):
    def __init__(self):
        self.graph = Neo4jAgentMemory()      # neo4j-labs/agent-memory
        self.compressor = HeadroomCompressor()  # headroomlabs-ai/headroom
        self.retriever = PageIndexRetriever()   # VectifyAI/PageIndex
    
    def retrieve(self, query, top_k=10):
        pages = self.retriever.search(query, top_k)
        graph_context = self.graph.traverse(query)
        compressed = self.compressor.compress(pages + graph_context)
        return compressed

# Swappable — user configures which provider to use
# config.yaml: memory.provider = "mem0" | "supermemory" | "honcho" | "custom"
```

This pattern applies to: **Memory, LLM, Search, Voice (STT/TTS), Browser, Context Compression, Scheduling, Skills, MCP.**

---

## Next Steps After This Document

1. For each feature marked with a codebase adoption, run `/understand-anything` on that codebase to get exact file paths and logic
2. For each feature marked `⭐ NEW` or `[H]`, create detailed implementation specs
3. For external resources (Agent Memory, Headroom, PageIndex, Autoresearch), clone and build integration adapters
4. Build the modular provider layer first — everything else plugs into it

---

> **End of Atomic Selections**
> 
> **Total Features Mapped:** 130+
> **Adoption Decision Coverage:** 37/37 sections
> **Locus-Original Features:** Sections 32-35 (Life OS + Brain + Vault + Infrastructure)
> **External Resources:** 4 (Agent Memory, Headroom, PageIndex, Autoresearch)
> **Codebase Adaptations:** Pi (file tools, sessions, extensions) · Hermes (agent core, tools, gateway, skills, profiles, config) · OpenHuman (security, MCP, learning, event bus)
