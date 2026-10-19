# ATOMIC SELECTIONS — Locus as a Pi Agent Augmentation

> **Date**: July 16th, 2026
> **Paradigm**: Locus **AUGMENTS** Pi Agent's codebase — a forked, extended runtime with its own `locus` CLI
> **Sources**: COMBINED_ATOMIC_FEATURES.md (July 7th) · Pi Agent (`5_Locus/pi/`) · Hermes (`5_Locus/hermes-agent/`) · OpenHuman (`5_Locus/openhuman/`)
> **Philosophy**: Laziness-first · Steal logic, never rebuild · Everything modular · Maximum user choice

---

## Table of Contents

- [Part 0 — The Augmentation Paradigm](#part-0--the-augmentation-paradigm)
- [Part I — Augmented Feature Matrix (§1-§29)](#part-i--augmented-feature-matrix-129)
- [Part II — Feature → Source Codebase Mapping](#part-ii--feature--source-codebase-mapping)
- [Part III — Atomic Logic Stripping](#part-iii--atomic-logic-stripping)
- [Part IV — Modularity Contract Specifications](#part-iv--modularity-contract-specifications)
- [Appendix A — Provider Registry](#appendix-a--provider-registry)
- [Appendix B — Config Schema](#appendix-b--config-schema)

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
└──────────────────────────┴──────────────────────────────────┘
```

**Install scopes:**

- `pi install X` → installs globally, available to both `pi` and `locus`I want the user to be able to run pi agent and locus sepreately, even though locus will be built on top of pi agent's infrastructure.

If user wishes to install an extensino or package or anything for pi and locus (globally) they can use pi install whatever but if they wish to *install packages or extensions or mcps for Locus ALONE, they must use locus install whatever. Locus will have copied all cli commands of pi agent like locus install or locus help etc... but with different usecases and scopes. 



Plus, just because something is a part of: 

🟡	LOCUS-EXT	Build as a Locus Pi extension (TypeScript, uses ExtensionAPI).

🟠	LOCUS-SKILL	Build as a Locus skill (SKILL.md + optional scripts).

🟤	LOCUS-SIDECAR	Heavy logic in Python, called by Locus extensions via pi.exec() or HTTP.

🔴	LOCUS-THEME	Custom theme/prompt template in the package.



doesnt mean we will not obey our coding philosophy, we still need to extract the best from the existing codebases of Openhuman, Pi and Hermes Agent! remember this is our coding philosophy and this is how we will be doing things:



Locus is a personal intelligence FRAMEWORK. Which comes pre-installed with a lot of features but makes adding to or replacing ANY PART of its functionality super simple because of its modular architecture.



That represents the way that Locus also needs to be coded. In a modular fashion, LITERALLY EVERYTHING should be modular, meaning people can choose to turn some settings off, swap them for something else too. 



The coding philosophy for creating is:

- Laziness first, I will provide you with a few things we will certainly use instead of recreating from scratch, for eaxmple for Agent Memory we are currently using Neo4j Agent Memory which is a pre-built infrastructure

- If exists in any of the other codebases (or the provided things), then STEAL IT'S LOGIC AND IMPLEMENTATION STRATEGY and implement it for Locus. There is a way to do this too which is described in the following pointer.

- Never directly refer to any codebase, directly use the /understand-anything query skill that is already installed for Antigravity to query what you want to know in detail. 



That is going to be the coding philosophy. The following is what we are going to do next:



- I will give you a long list of features that I will select from "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os\.keysndocs\Documentation\Implementation Reports\June 28th\full_feature_matrix.md" plus some more from another file that I will mention and I will also tell you what I want you to use specifically for some features.

- For all the features that I point out from "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os\.keysndocs\Documentation\Implementation Reports\June 28th\full_feature_matrix.md" will be related to some of the other codebases, that are present in "C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus" so you will then need to use the /understand-anything skill to accurately find all the relevant files attached to the feature I want you to build refering to that codebase

- List out in detail (preferably in a clean table) for which feature, which codebase we will be refering from (if it is an already provided resource like Neo4j Agent Memory then mention that/those), which all files are linked to that particular feature and the detailed purpose of each file and how they work in congruation with the other files.

- Perform ⁠atomic feature wise logic stripping from all files. Strip the logic from all the files (respective to the feature (and if it is a provided resource then find a way to integrate it with Locus, by directly cloning it.)) and how they work together with other files.

- Then write in detail how the logic for each feature adapts to Locus' architecture (ignoring all the other older architecture docs completely) and usecase.

- After all this processing is done, you are supposed to output a very precisely detailed and atomic markdown file with all the data that we generated above. None should have code directly baked into it (only pseudocode, algorithms and/or the logic we made and determined).



So, you still need to edit [Atomic%20Selections%20from%20Antigravity.md](file;file:///c%3A/Users/soni8/Desktop/everything/University%202.0/Project%28s%29/5_Locus/locus-os/.keysndocs/Documentation/Implementation%20Reports/July%2016th/Atomic%20Selections%20from%20Antigravity.md)  in such a way that it is an AUGMENTATION and refinement over [COMBINED_ATOMIC_FEATURES.md](file;file:///c%3A/Users/soni8/Desktop/everything/University%202.0/Project%28s%29/5_Locus/locus-os/.keysndocs/Documentation/Implementation%20Reports/July%207th/COMBINED_ATOMIC_FEATURES.md) but with atomic selections for what to and what not to keep, the goal is to give the user as many options as possible so I would like to be able to fit as many memory management and "brain" systems from all codebases if possible for the user to choose from, there should be so much customization option that the user can hook up their own system as well.



Remember, AUGMENT over the file and refine it to fit our new strategy of making a package (also I feel to do that, we will need to literall augment the pi agent codebase, rather than approach it as building a package over Pi Agent, given my initial requirement in this prompt)

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
  "neo4j-agent-memory" → Neo4jAgentMemoryProvider   (default)
  "mem0"               → Mem0Provider
  "supermemory"        → SupermemoryProvider
  "honcho"             → HonchoProvider
  "mastra"             → MastraProvider
  "cognee"             → CogneeProvider
  "custom"             → user-provided adapter via config

CONFIG locus.memory:
  provider: "neo4j-agent-memory"   # or any registered provider
  enabled: true                     # toggle entire subsystem
  options: { ... }                  # provider-specific config
```

This pattern applies to: **Memory, Brain/Reasoning, Learning, Voice, Channels, Search, Context Assembly, Scheduling, User Modeling** — every single subsystem.

Users can:

- **Swap** any provider for another
- **Disable** any subsystem entirely
- **Hook in** their own custom provider via a simple adapter interface
- **Stack** multiple providers (e.g., Neo4j + mem0 for memory)

## 0.4 Coding Philosophy

1. **Laziness-first**: If something already exists (Neo4j Agent Memory, Pi's providers, etc.), USE IT. Clone it. Don't rebuild.
2. **Steal logic**: For every feature we want, find the BEST implementation across Pi/Hermes/OpenHuman, understand its logic via `/understand-anything`, and adapt it for Locus.
3. **Never directly reference**: Don't copy-paste files. Understand the LOGIC and STRATEGY, then implement fresh for Locus' modular architecture.
4. **Maximum options**: For every subsystem, provide as many swappable providers as possible. The user should feel they can customize EVERYTHING.

## 0.5 Available Codebases

| Codebase               | Path                      | Language           | Key Strengths                                                                                                                                       |
| ---------------------- | ------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pi Agent**     | `5_Locus/pi/`           | TypeScript/Node.js | Agent loop, 30+ providers, TUI, extensions, packages, sessions, 75+ examples                                                                        |
| **Hermes Agent** | `5_Locus/hermes-agent/` | Python             | Gateway, channels (Telegram/Discord/Slack/WhatsApp), background review, curator, memory manager, usage tracking, ACP protocol, cron scheduling      |
| **OpenHuman**    | `5_Locus/openhuman/`    | Rust + TypeScript  | Memory graph, embeddings, subagent archetypes (15!), sandboxing (4 backends), MCP client/server, approval gates, post-turn hooks, desktop companion |
| **Locus OS**     | `5_Locus/locus-os/`     | Python             | Life OS metrics, Brain Engine, vault intelligence, Telegram interface, voice pipeline, Neo4j memory, Context Forge                                  |

---

# Part I — Augmented Feature Matrix (§1-§29)

## Classification Legend

| Verdict                    | Meaning                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------- |
| ✅**KEEP-PI**        | Inherit directly from Pi's codebase. No changes needed.                                 |
| 🔄**AUGMENT**        | Pi provides the base; Locus adds functionality on top. Specify what's added.            |
| 🆕**LOCUS-NEW**      | Locus-unique feature. Specify source codebase to steal logic from, or mark as original. |
| 🔀**MULTI-PROVIDER** | Feature where Locus offers MULTIPLE swappable providers. List all options.              |
| ⚪**SKIP**           | Not needed or deliberately excluded.                                                    |

---

## §1. Agent Core / Runtime

| #    | Feature                                 | Verdict           | Source(s)                                                                       | Modularity       | Notes                                                                                                                                                                                         |
| ---- | --------------------------------------- | ----------------- | ------------------------------------------------------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1  | **Main agent loop**               | ✅ KEEP-PI        | Pi`agent-loop.ts`                                                             | —               | Pi's two-entry agent loop (tooled + simple) is production-grade.                                                                                                                              |
| 1.2  | **Turn context management**       | 🔄 AUGMENT        | Pi`agent-harness.ts` + Hermes `turn_context.py`                             | —               | Keep Pi's harness state machine. Add Locus lifecycle hooks for memory injection and context enrichment. Steal Hermes' per-turn state tracking pattern.                                        |
| 1.3  | **Turn retry / error recovery**   | 🔄 AUGMENT        | Pi agent loop + OpenHuman self-healing                                          | MemoryProvider   | Pi has basic retry (3x, exponential backoff). Augment with OpenHuman's self-healing pattern: ToolMaker polyfill (auto-generate missing tools), circuit breakers for failing providers.        |
| 1.4  | **System prompt builder**         | 🔄 AUGMENT        | Pi`system-prompt.ts` + Hermes `prompt_builder.py`                           | PromptAssembler  | Pi assembles from templates + skills. Locus augments to inject: SOUL.md personality, Context Forge output, user profile, DCS/mode state. Steal Hermes' dynamic prompt builder pattern.        |
| 1.5  | **Prompt caching**                | ✅ KEEP-PI        | Pi`openai-prompt-cache.ts`                                                    | —               | Built-in for OpenAI. Anthropic cache via provider config.                                                                                                                                     |
| 1.6  | **Iteration budget / limits**     | 🔄 AUGMENT        | Pi + Hermes`iteration_budget.py`                                              | —               | Pi has grace-turn after budget. Steal Hermes' configurable iteration budget with per-session overrides.                                                                                       |
| 1.7  | **Background review / post-turn** | 🔀 MULTI-PROVIDER | Hermes`background_review.py` · OpenHuman post-turn hooks · Locus Inner Loop | PostTurnProvider | **Options**: (a) Hermes curator → insights → memory nudge, (b) OpenHuman 4-hook system (Archivist, Reflection, ToolTracker, UserProfile), (c) Locus proactive Inner Loop, (d) Custom. |
| 1.8  | **Stream diagnostics**            | ✅ KEEP-PI        | Pi event stream utilities                                                       | —               | Built-in.                                                                                                                                                                                     |
| 1.9  | **Rate limit tracking**           | 🆕 LOCUS-NEW      | Hermes`rate_limit_tracker.py`                                                 | —               | Steal Hermes' pattern. Track rate limit headers from LLM responses. Surface in TUI footer / Telegram status.                                                                                  |
| 1.10 | **Usage / cost tracking**         | 🆕 LOCUS-NEW      | Hermes`usage_pricing.py` + `credits_tracker.py`                             | CostTracker      | Steal Hermes' pricing table and accumulation logic. Display in footer widget.                                                                                                                 |
| 1.11 | **Title generation**              | 🆕 LOCUS-NEW      | Hermes`title_generator.py`                                                    | —               | Auto-generate session titles. Steal Hermes' implementation.                                                                                                                                   |
| 1.12 | **Onboarding flow**               | 🔄 AUGMENT        | Pi project trust + Locus setup                                                  | —               | Keep Pi's project trust. Add`locus setup` wizard for first-run config (Telegram token, Neo4j URI, DeepSeek key, vault path, timezone).                                                      |
| 1.13 | **Agent initialization**          | 🔄 AUGMENT        | Pi`agent-harness.ts`                                                          | —               | Locus augments Pi's init to also initialize: sidecar connection, memory provider, channel bridges.                                                                                            |

---

## §2. LLM Providers

| #   | Feature                         | Verdict           | Source(s)                       | Modularity     | Notes                                                                                                                                                                                                        |
| --- | ------------------------------- | ----------------- | ------------------------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2.1 | **30+ Providers**         | ✅ KEEP-PI        | Pi`providers/`                | —             | Anthropic, OpenAI, Google, DeepSeek, Mistral, AWS, Azure, Cloudflare, + 22 more.                                                                                                                             |
| 2.2 | **OAuth flows**           | ✅ KEEP-PI        | Pi`oauth/`                    | —             | Device code + PKCE.                                                                                                                                                                                          |
| 2.3 | **Custom / local models** | ✅ KEEP-PI        | Pi`models.json`               | —             | Ollama, LM Studio, vLLM, any OpenAI-compatible.                                                                                                                                                              |
| 2.4 | **Provider registry**     | ✅ KEEP-PI        | Pi`api-registry.ts`           | —             | Auto-registration.                                                                                                                                                                                           |
| 2.5 | **Model selection**       | ✅ KEEP-PI        | Pi`/model`, Ctrl+P            | —             | Model cycling.                                                                                                                                                                                               |
| 2.6 | **Streaming (SSE)**       | ✅ KEEP-PI        | Pi`stream.ts`                 | —             | Built-in.                                                                                                                                                                                                    |
| 2.7 | **Intelligent routing**   | 🔀 MULTI-PROVIDER | OpenHuman`IntelligentRouting` | RouterProvider | **Options**: (a) Single-provider (Locus default — DeepSeek V4 Flash), (b) OpenHuman's intelligent routing (local+cloud fallback), (c) Custom routing logic. Toggleable via `locus.routing.enabled`. |
| 2.8 | **Refusal detection**     | 🆕 LOCUS-NEW      | OpenHuman Aho-Corasick DFA      | —             | Steal OpenHuman's DFA-based refusal scanner. Runs post-LLM-call, triggers retry with rephrased prompt.                                                                                                       |
| 2.9 | **Image generation**      | ✅ KEEP-PI        | Pi`images.ts`                 | —             | Built-in image provider registry.                                                                                                                                                                            |

**Default model config**: DeepSeek V4 Flash (~$0.012/day). User can change via `locus config set model <name>`.

---

## §3. Tools / Tool Execution

| #    | Feature                              | Verdict      | Source(s)                                                        | Modularity   | Notes                                                                                                  |
| ---- | ------------------------------------ | ------------ | ---------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------ |
| 3.1  | **File read/write/edit**       | ✅ KEEP-PI   | Pi`read.ts`, `write.ts`, `edit.ts`                         | —           | Built-in.                                                                                              |
| 3.2  | **Shell / bash**               | ✅ KEEP-PI   | Pi`bash.ts`                                                    | —           | Built-in with output capture.                                                                          |
| 3.3  | **Grep / search**              | ✅ KEEP-PI   | Pi`grep.ts`                                                    | —           | Ripgrep-backed.                                                                                        |
| 3.4  | **List / find**                | ✅ KEEP-PI   | Pi`ls.ts`, `find.ts`                                         | —           | Built-in.                                                                                              |
| 3.5  | **Web search**                 | ✅ KEEP-PI   | Pi`web_search`                                                 | —           | 8 providers (more than old Locus).                                                                     |
| 3.6  | **Web fetch**                  | ✅ KEEP-PI   | Pi`fetch_content`                                              | —           | URL→markdown, YouTube transcripts, GitHub repos.                                                      |
| 3.7  | **Git tools**                  | 🔄 AUGMENT   | Pi`git.ts` + Locus `git_ops.py`                              | —           | Pi has basic git. Augment with Locus'`git_status`, `git_diff`, `git_commit` as registered tools. |
| 3.8  | **Tool call validation**       | 🔄 AUGMENT   | Pi`tool-definition-wrapper.ts` + Hermes `tool_guardrails.py` | —           | Keep Pi's wrapper. Steal Hermes' guardrails pattern for additional safety checks.                      |
| 3.9  | **Tool result classification** | 🆕 LOCUS-NEW | Hermes`tool_result_classification.py`                          | —           | Classify tool results as success/failure/partial. Steal Hermes' implementation.                        |
| 3.10 | **Tool output accumulator**    | ✅ KEEP-PI   | Pi`output-accumulator.ts`                                      | —           | Built-in truncation.                                                                                   |
| 3.11 | **Tool timeout / budget**      | 🆕 LOCUS-NEW | OpenHuman`tool_timeout`                                        | —           | Per-tool timeout enforcement. Steal OpenHuman's pattern.                                               |
| 3.12 | **Custom Locus tools**         | 🆕 LOCUS-NEW | Locus-unique                                                     | ToolProvider | Register via`pi.registerTool()`. See §3 custom tools list below.                                    |

**Custom Locus Tools (registered by augmentation):**

| Tool                       | Description                     | Sidecar | Swappable         |
| -------------------------- | ------------------------------- | ------- | ----------------- |
| `locus_memory_query`     | Query active memory provider(s) | Yes     | MemoryProvider    |
| `locus_vault_search`     | Search Obsidian vault           | Yes     | VaultProvider     |
| `locus_checkin`          | Capture check-in data           | Yes     | —                |
| `locus_schedule`         | View/create scheduled tasks     | Yes     | SchedulerProvider |
| `locus_life_status`      | DCS, factions, operating mode   | Yes     | LifeOSProvider    |
| `locus_brain_think`      | Trigger Inner Loop reasoning    | Yes     | BrainProvider     |
| `locus_voice_transcribe` | Transcribe audio                | Yes     | VoiceProvider     |
| `locus_user_profile`     | Query/update user profile       | Yes     | UserModelProvider |

---

## §4. Memory & Persistence

| #    | Feature                                 | Verdict           | Source(s)                                                    | Modularity          | Notes                                                                                                                                                                                |
| ---- | --------------------------------------- | ----------------- | ------------------------------------------------------------ | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 4.1  | **Session storage**               | ✅ KEEP-PI        | Pi JSONL sessions                                            | —                  | Tree-based JSONL, fork, resume.                                                                                                                                                      |
| 4.2  | **Graph memory**                  | 🔀 MULTI-PROVIDER | OpenHuman`memory_graph` · Locus Neo4j                     | MemoryProvider      | **Default**: Neo4j Agent Memory (POLE+O). **Options**: OpenHuman's `memory_graph`, mem0, Supermemory, Honcho, Mastra, Cognee, custom.                                  |
| 4.3  | **Vector embeddings**             | 🔀 MULTI-PROVIDER | OpenHuman`embeddings` · Locus PageIndex                   | EmbeddingProvider   | **Options**: pgvector, Locus PageIndex (vectorless), OpenHuman embeddings module, custom.                                                                                      |
| 4.4  | **Full-text search**              | 🔀 MULTI-PROVIDER | Hermes FTS5 · OpenHuman`memory_search`                    | SearchProvider      | **Options**: Hermes FTS5, OpenHuman memory_search, Locus PageIndex, custom.                                                                                                    |
| 4.5  | **Memory tree / cascade**         | 🆕 LOCUS-NEW      | OpenHuman bucket-seal cascade                                | —                  | Steal OpenHuman's bucket-seal cascade for hierarchical memory organization.                                                                                                          |
| 4.6  | **Entity extraction**             | 🔀 MULTI-PROVIDER | OpenHuman`memory_entities` · Locus design                 | EntityExtractor     | **Options**: spaCy → GLiNER → LLM pipeline, OpenHuman's `memory_entities`, DeepSeek entity extraction, custom.                                                             |
| 4.7  | **Memory sync**                   | 🆕 LOCUS-NEW      | OpenHuman`memory_sync`                                     | —                  | Steal OpenHuman's memory sync for cross-session consistency.                                                                                                                         |
| 4.8  | **Memory queue**                  | 🆕 LOCUS-NEW      | OpenHuman`memory_queue`                                    | —                  | Async memory write queue. Steal OpenHuman's pattern.                                                                                                                                 |
| 4.9  | **Memory diff**                   | 🆕 LOCUS-NEW      | OpenHuman`memory_diff`                                     | —                  | Track memory state changes. Steal OpenHuman's pattern.                                                                                                                               |
| 4.10 | **Holographic HRR**               | 🆕 LOCUS-NEW      | Locus-original                                               | —                  | SHA-256 deterministic vectors, bind/unbind/bundle. Locus-unique biologically-inspired memory encoding.                                                                               |
| 4.11 | **Hebbian pathway weighting**     | 🆕 LOCUS-NEW      | Locus-original                                               | —                  | Neo4j edge weights: +0.1 traversal, ×1.3/×0.7 feedback, ×0.95 weekly decay.                                                                                                       |
| 4.12 | **STDP reinforcement**            | 🆕 LOCUS-NEW      | Locus-original                                               | —                  | Response latency < 2min = ×1.5 reinforcement.                                                                                                                                       |
| 4.13 | **Spaced repetition**             | 🆕 LOCUS-NEW      | Locus-original                                               | —                  | Nodes near decay + active outcomes → Inner Loop surfaces them.                                                                                                                      |
| 4.14 | **Project-specific memory decay** | 🆕 LOCUS-NEW      | Locus-original                                               | —                  | `SET r.weight = r.weight * 0.5` on project completion.                                                                                                                             |
| 4.15 | **User modeling store**           | 🔀 MULTI-PROVIDER | Hermes Honcho · OpenHuman ambient profiling · Locus design | UserModelProvider   | **Options**: Hermes' Honcho dialectic modeling, OpenHuman's ambient profile facets + PROFILE.md injection + stability detector (30min), Locus rolling-average profile, custom. |
| 4.16 | **Memory orchestrator**           | 🔄 AUGMENT        | Hermes`memory_manager.py` · OpenHuman `memory_store`    | —                  | Coordinates all active memory providers. Steal patterns from both.                                                                                                                   |
| 4.17 | **Headroom CCR compression**      | 🆕 LOCUS-NEW      | Locus-original                                               | CompressionProvider | Cache-Compress-Retrieve pipeline. 60-95% token reduction.**Options**: Headroom (default), simple summarization, custom.                                                        |
| 4.18 | **Approval store**                | 🆕 LOCUS-NEW      | OpenHuman approval gate + Locus`approval_store.py`         | —                  | Steal OpenHuman's 10-min TTL approval gate pattern.                                                                                                                                  |

**Memory Provider Interface:**

```
INTERFACE MemoryProvider:
  name: string
  
  // Core operations
  store(content: string, metadata: dict) → id: string
  query(query: string, limit: int, filters?: dict) → Memory[]
  delete(id: string) → bool
  
  // Entity operations (optional)
  extract_entities(text: string) → Entity[]
  link_entities(entity_a: string, entity_b: string, relation: string) → void
  
  // Weight operations (optional, for graph-based providers)
  update_weight(node_id: string, delta: float) → void
  decay_weights(factor: float) → int  // returns count affected
  
  // Lifecycle
  initialize(config: dict) → void
  health_check() → HealthStatus
  shutdown() → void

AVAILABLE PROVIDERS:
  ┌────────────────────────┬──────────────────────────────────┐
  │ Provider               │ What It Brings                   │
  ├────────────────────────┼──────────────────────────────────┤
  │ neo4j-agent-memory     │ POLE+O graph model, entity       │
  │ (default)              │ linking, relationship traversal  │
  ├────────────────────────┼──────────────────────────────────┤
  │ mem0                   │ Simple memory API, managed       │
  │                        │ service option                   │
  ├────────────────────────┼──────────────────────────────────┤
  │ supermemory            │ AI-native memory layer           │
  ├────────────────────────┼──────────────────────────────────┤
  │ honcho                 │ Dialectic modeling, user state   │
  ├────────────────────────┼──────────────────────────────────┤
  │ mastra                 │ Agent memory with workflows      │
  ├────────────────────────┼──────────────────────────────────┤
  │ cognee                 │ Knowledge graph from text        │
  ├────────────────────────┼──────────────────────────────────┤
  │ custom                 │ User implements MemoryProvider    │
  │                        │ interface, registers via config  │
  └────────────────────────┴──────────────────────────────────┘
```

---

## §5. Sessions

| #   | Feature                            | Verdict           | Source(s)                                                                        | Modularity         | Notes                                                                                                                                                     |
| --- | ---------------------------------- | ----------------- | -------------------------------------------------------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5.1 | **Session format**           | ✅ KEEP-PI        | Pi JSONL v3                                                                      | —                 | 9 entry types, tree-based.                                                                                                                                |
| 5.2 | **Session branching / fork** | ✅ KEEP-PI        | Pi`--fork`                                                                     | —                 | Built-in.                                                                                                                                                 |
| 5.3 | **Session resume**           | ✅ KEEP-PI        | Pi`--resume` / `--continue`                                                  | —                 | Built-in.                                                                                                                                                 |
| 5.4 | **Session naming**           | ✅ KEEP-PI        | Pi`--name`                                                                     | —                 | Built-in.                                                                                                                                                 |
| 5.5 | **Session picker UI**        | ✅ KEEP-PI        | Pi`session-picker.ts`                                                          | —                 | Interactive picker.                                                                                                                                       |
| 5.6 | **Session compression**      | 🔀 MULTI-PROVIDER | Pi compaction · Hermes`conversation_compression.py` · OpenHuman microcompact | CompactionProvider | **Options**: Pi's compaction engine (default), Hermes' conversation compression, OpenHuman's microcompact + summarizer, Locus Headroom CCR, custom. |
| 5.7 | **Session export**           | ✅ KEEP-PI        | Pi HTML/JSON/MD                                                                  | —                 | Built-in.                                                                                                                                                 |
| 5.8 | **Telegram session bridge**  | 🆕 LOCUS-NEW      | Locus-unique                                                                     | ChannelProvider    | Maps Telegram chats to Pi sessions.                                                                                                                       |

---

## §6. Context Management

| #   | Feature                                    | Verdict      | Source(s)                                   | Modularity       | Notes                                                                                                |
| --- | ------------------------------------------ | ------------ | ------------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------- |
| 6.1 | **Context window management**        | 🔄 AUGMENT   | Pi compaction + Hermes`context_engine.py` | —               | Keep Pi's compaction. Steal Hermes' context engine for more intelligent truncation decisions.        |
| 6.2 | **Context references**               | 🆕 LOCUS-NEW | Hermes`context_references.py`             | —               | Track which context was actually used. Steal Hermes' implementation.                                 |
| 6.3 | **Coding-specific context**          | 🆕 LOCUS-NEW | Hermes`coding_context.py`                 | —               | Inject code-aware context. Steal Hermes' implementation.                                             |
| 6.4 | **Token overflow handling**          | ✅ KEEP-PI   | Pi`overflow.ts`                           | —               | Built-in.                                                                                            |
| 6.5 | **Context Forge**                    | 🆕 LOCUS-NEW | Locus-original                              | ContextAssembler | 800-token, 6-layer multi-source context assembly. Modular: each layer is a`ContextLayer` provider. |
| 6.6 | **Query Router / Intent Classifier** | 🆕 LOCUS-NEW | Locus-original                              | IntentClassifier | 8 intent types → source routing matrix. Determines which memory/context sources to query.           |

**Context Forge — Modular Layer Architecture:**

```
INTERFACE ContextLayer:
  name: string
  budget_tokens: int
  priority: int  // lower = higher priority
  
  fetch(query: string, budget: int) → string
  compress(content: string, target_tokens: int) → string

DEFAULT LAYERS (all independently toggleable):
  identity_layer(80t)    → SOUL.md personality extract
  temporal_layer(60t)    → current time, day, recent events
  events_layer(180t)     → recent action log
  graph_layer(150t)      → Neo4j/memory_provider query
  retrieval_layer(200t)  → PageIndex / embeddings query
  web_layer(100t)        → web context (if query requires)

ALGORITHM context_forge(query, total_budget=800):
  layers = get_enabled_layers()
  layers.sort(by=priority)
  assembled = ""
  remaining = total_budget
  
  FOR layer IN layers:
    IF remaining <= 0: BREAK
    content = layer.fetch(query, min(layer.budget, remaining))
    IF tokens(content) > layer.budget:
      content = layer.compress(content, layer.budget)
    assembled += content
    remaining -= tokens(content)
  
  RETURN assembled
```

---

## §7. TUI / Terminal Interface

| #   | Feature                              | Verdict    | Source(s)                     | Modularity   | Notes                                                                                              |
| --- | ------------------------------------ | ---------- | ----------------------------- | ------------ | -------------------------------------------------------------------------------------------------- |
| 7.1 | **Full TUI framework**         | ✅ KEEP-PI | Pi React/Ink                  | —           | Full editor, message history, tool rendering.                                                      |
| 7.2 | **Multiline editing**          | ✅ KEEP-PI | Pi                            | —           | Built-in.                                                                                          |
| 7.3 | **Keyboard shortcuts**         | ✅ KEEP-PI | Pi 15+ keybindings            | —           | Configurable.                                                                                      |
| 7.4 | **Themes**                     | 🔄 AUGMENT | Pi theme system               | —           | Inherit Pi's system. Add Locus branded themes (locus-dark, locus-light).                           |
| 7.5 | **Slash command autocomplete** | ✅ KEEP-PI | Pi`slash-commands.ts`       | —           | Locus commands auto-registered.                                                                    |
| 7.6 | **Status bar / footer**        | 🔄 AUGMENT | Pi footer API                 | FooterWidget | Locus adds: DCS score, operating mode, active faction, memory stats, sidecar status.               |
| 7.7 | **Streaming tool output**      | ✅ KEEP-PI | Pi                            | —           | Real-time.                                                                                         |
| 7.8 | **Diagnostics UI**             | 🔄 AUGMENT | Pi + Hermes`hermes doctor`  | —           | Add`locus doctor` command. Checks: sidecar health, Neo4j connection, Telegram bot, vault access. |
| 7.9 | **Provider attribution**       | ✅ KEEP-PI | Pi`provider-attribution.ts` | —           | Shows which provider/model is active.                                                              |

---

## §8. CLI

| #    | Feature                               | Verdict      | Source(s)                                       | Modularity | Notes                                                                                                          |
| ---- | ------------------------------------- | ------------ | ----------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------- |
| 8.1  | **39 CLI flags**                | ✅ KEEP-PI   | Pi                                              | —         | All inherited.                                                                                                 |
| 8.2  | **Run modes**                   | ✅ KEEP-PI   | Pi                                              | —         | Interactive, Print, RPC, JSON.                                                                                 |
| 8.3  | **Batch mode**                  | ✅ KEEP-PI   | Pi`--print`                                   | —         | One-shot.                                                                                                      |
| 8.4  | **RPC / daemon mode**           | ✅ KEEP-PI   | Pi`--mode rpc`                                | —         | JSON protocol over stdin/stdout. Used by Telegram bridge.                                                      |
| 8.5  | **Self-update**                 | 🔄 AUGMENT   | Pi`pi update`                                 | —         | `locus update` updates both Pi core and Locus augmentation.                                                  |
| 8.6  | **Doctor / diagnostics**        | 🆕 LOCUS-NEW | Hermes`hermes doctor` · OpenHuman `doctor` | —         | `locus doctor` — checks all subsystems. Steal patterns from both.                                           |
| 8.7  | **Config management**           | 🔄 AUGMENT   | Pi`config.ts`                                 | —         | `locus config` manages Locus-specific settings. Nested under `locus.*` in Pi's settings.json.              |
| 8.8  | **Gateway lifecycle**           | 🆕 LOCUS-NEW | Hermes gateway + Locus gateway                  | —         | `locus gateway run/start/stop/restart/status/install/uninstall`. Steal Hermes' gateway lifecycle management. |
| 8.9  | **Setup wizard**                | 🆕 LOCUS-NEW | Locus                                           | —         | `locus setup` — guided first-run configuration.                                                             |
| 8.10 | **Locus-specific CLI commands** | 🆕 LOCUS-NEW | Locus-unique                                    | —         | `locus life`, `locus memory`, `locus vault`, `locus brain` — direct CLI access to Locus subsystems.   |

---

## §9. Extensions / Plugins / Skills

| #   | Feature                            | Verdict      | Source(s)                                  | Modularity | Notes                                                                                                        |
| --- | ---------------------------------- | ------------ | ------------------------------------------ | ---------- | ------------------------------------------------------------------------------------------------------------ |
| 9.1 | **Extension system**         | ✅ KEEP-PI   | Pi 25+ lifecycle events                    | —         | Locus extensions load alongside Pi extensions.                                                               |
| 9.2 | **Skills system**            | ✅ KEEP-PI   | Pi SKILL.md discovery                      | —         | Locus bundles skills in its`skills/` directory.                                                            |
| 9.3 | **Skills marketplace**       | 🔄 AUGMENT   | Pi packages + Hermes 4 marketplace indexes | —         | `locus install` can pull from Pi's gallery AND Hermes' skill indexes (Anthropic, Claude, LobeHub, OpenAI). |
| 9.4 | **ACP protocol**             | 🆕 LOCUS-NEW | Hermes full ACP adapter                    | —         | Steal Hermes' ACP implementation for inter-agent communication.                                              |
| 9.5 | **Prompt templates**         | ✅ KEEP-PI   | Pi`prompt-templates.ts`                  | —         | Locus bundles its own templates.                                                                             |
| 9.6 | **Register custom tools**    | ✅ KEEP-PI   | Pi`pi.registerTool()`                    | —         | Locus registers ~8 custom tools.                                                                             |
| 9.7 | **Register custom commands** | ✅ KEEP-PI   | Pi`pi.registerCommand()`                 | —         | Locus registers`/locus-*` commands.                                                                        |
| 9.8 | **Context file loading**     | 🔄 AUGMENT   | Pi AGENTS.md + Locus SOUL.md               | —         | Keep Pi's AGENTS.md. Add SOUL.md as Locus personality context file.                                          |
| 9.9 | **Plugin LLM**               | 🆕 LOCUS-NEW | Hermes`plugin_llm.py`                    | —         | Secondary LLM for plugin/extension tasks. Steal Hermes' pattern.                                             |

---

## §10. Learning & Self-Improvement

| #     | Feature                                   | Verdict           | Source(s)                                                    | Modularity        | Notes                                                                                                                                                                                                  |
| ----- | ----------------------------------------- | ----------------- | ------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 10.1  | **Post-session learning**           | 🔀 MULTI-PROVIDER | Hermes curator · OpenHuman hooks · Locus reflector         | LearningProvider  | **Options**: (a) Hermes curator → insights → memory nudge, (b) OpenHuman 4-hook system (Archivist, Reflection, ToolTracker, UserProfile), (c) Locus reflector, (d) Custom. ALL can be stacked. |
| 10.2  | **Cross-session recall**            | 🔀 MULTI-PROVIDER | Hermes FTS5 · OpenHuman`memory_search` · Locus PageIndex | SearchProvider    | Multiple providers stackable.                                                                                                                                                                          |
| 10.3  | **User profile building**           | 🔀 MULTI-PROVIDER | Hermes Honcho · OpenHuman ambient profiling · Locus design | UserModelProvider | **Options**: (a) Hermes Honcho dialectic modeling, (b) OpenHuman ambient profiling + PROFILE.md + stability detector, (c) Locus rolling-average profile, (d) Custom.                             |
| 10.4  | **Tool usage tracking**             | 🆕 LOCUS-NEW      | OpenHuman`ToolTrackerHook` + Locus `tool_tracker.py`     | —                | Track tool name, args, success/fail, duration. Used by learning providers.                                                                                                                             |
| 10.5  | **Personal Reward Model**           | 🆕 LOCUS-NEW      | Locus-original                                               | RewardModel       | sklearn LogisticRegression. 👍/👎 feedback. Weekly retrain. ≥0.6 threshold gates Inner Loop outputs.                                                                                                  |
| 10.6  | **Hebbian learning rules**          | 🆕 LOCUS-NEW      | Locus-original                                               | —                | Neo4j edge weights with biological decay, STDP reinforcement.                                                                                                                                          |
| 10.7  | **Multi-horizon pattern detection** | 🆕 LOCUS-NEW      | Locus-original                                               | PatternEngine     | 5 horizons (H1:6h → H5:all-time). Confidence-based promotion between horizons.                                                                                                                        |
| 10.8  | **Self-evolving Architect Bot**     | 🆕 LOCUS-NEW      | Locus-original                                               | —                | Scans reward signals, generates patches, risk-gated deploy.                                                                                                                                            |
| 10.9  | **Agent experience tracking**       | 🆕 LOCUS-NEW      | OpenHuman`agent_experience`                                | —                | Steal OpenHuman's agent experience module.                                                                                                                                                             |
| 10.10 | **Stability detection**             | 🆕 LOCUS-NEW      | OpenHuman stability detector (30min)                         | —                | Detect when user's behavioral state stabilizes. Steal OpenHuman's pattern.                                                                                                                             |

---

## §11. Subagents / Delegation

| #    | Feature                            | Verdict           | Source(s)                                   | Modularity        | Notes                                                                                                                                                                            |
| ---- | ---------------------------------- | ----------------- | ------------------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 11.1 | **Subagent spawning**        | ✅ KEEP-PI        | Pi built-in subagent tool                   | —                | Built-in.                                                                                                                                                                        |
| 11.2 | **Subagent archetypes**      | 🔀 MULTI-PROVIDER | OpenHuman 15 archetypes · Locus 4 factions | SubagentArchetype | **Options**: OpenHuman's 15 (orchestrator, planner, researcher, critic, etc.), Locus' 4 faction agents (Planner, Curator, Analyst, Builder), custom archetypes via config. |
| 11.3 | **Depth limiting**           | 🆕 LOCUS-NEW      | OpenHuman MAX_SPAWN_DEPTH=3                 | —                | Steal OpenHuman's pattern.                                                                                                                                                       |
| 11.4 | **RPC-based subagents**      | ✅ KEEP-PI        | Pi RPC mode                                 | —                | Built-in.                                                                                                                                                                        |
| 11.5 | **Coding agent**             | ✅ KEEP-PI        | Pi full coding agent                        | —                | Built-in.                                                                                                                                                                        |
| 11.6 | **ACP client for subagents** | 🆕 LOCUS-NEW      | Hermes`copilot_acp_client.py`             | —                | Steal Hermes' ACP client for inter-agent comms.                                                                                                                                  |

---

## §12. Scheduling & Cron

| #    | Feature                            | Verdict           | Source(s)                                                                            | Modularity        | Notes                                                                                                                   |
| ---- | ---------------------------------- | ----------------- | ------------------------------------------------------------------------------------ | ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 12.1 | **Cron / scheduled tasks**   | 🔀 MULTI-PROVIDER | Hermes NL cron · OpenHuman`cron` + `scheduler_gate` · Locus `cron_runner.py` | SchedulerProvider | **Options**: Hermes' natural language cron, OpenHuman's scheduler_gate, node-cron, APScheduler (sidecar), custom. |
| 12.2 | **Task sources**             | 🆕 LOCUS-NEW      | OpenHuman`task_sources` · Locus `scheduler/task_sources.py`                     | —                | Steal patterns from both.                                                                                               |
| 12.3 | **Inner Loop (proactive)**   | 🆕 LOCUS-NEW      | Locus-original                                                                       | BrainProvider     | Every 90min (07:00-00:00), unprompted reasoning, Reward Model gate.                                                     |
| 12.4 | **Structured check-ins**     | 🆕 LOCUS-NEW      | Locus-original                                                                       | —                | 07:30/13:00/18:00/22:00 IST → Telegram inline keyboards.                                                               |
| 12.5 | **Heartbeat / notification** | 🆕 LOCUS-NEW      | OpenHuman`heartbeat` · Locus `heartbeat/notification.py`                        | —                | Steal patterns from both.                                                                                               |

---

## §13. Security & Sandboxing

| #     | Feature                               | Verdict           | Source(s)                                                           | Modularity      | Notes                                                                                                            |
| ----- | ------------------------------------- | ----------------- | ------------------------------------------------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------- |
| 13.1  | **Project trust**               | ✅ KEEP-PI        | Pi`trust-manager.ts`                                              | —              | Built-in.                                                                                                        |
| 13.2  | **Shell blocklist**             | 🔄 AUGMENT        | Pi + OpenHuman policy engine + Locus`shell_exec.py`               | —              | Layer Locus' BLOCKED_PATTERNS on top of Pi's safety. Steal OpenHuman's command classification for richer policy. |
| 13.3  | **File safety**                 | 🆕 LOCUS-NEW      | Hermes`file_safety.py` · OpenHuman `file_state` + `cwd_jail` | —              | Steal patterns from both.                                                                                        |
| 13.4  | **Sandbox backends**            | 🔀 MULTI-PROVIDER | OpenHuman 4 backends                                                | SandboxProvider | **Options**: bubblewrap, docker, firejail, landlock, none. Steal OpenHuman's 4-backend system.             |
| 13.5  | **Autonomy tiers**              | 🆕 LOCUS-NEW      | OpenHuman readonly/supervised/full                                  | —              | Steal OpenHuman's tier system.                                                                                   |
| 13.6  | **Approval gate**               | 🆕 LOCUS-NEW      | OpenHuman 10-min TTL + Hermes ACP                                   | —              | Steal both patterns.                                                                                             |
| 13.7  | **Data redaction**              | 🆕 LOCUS-NEW      | Hermes`redact.py`                                                 | —              | Steal Hermes' pattern.                                                                                           |
| 13.8  | **Prompt injection protection** | 🆕 LOCUS-NEW      | OpenHuman`prompt_injection`                                       | —              | Steal OpenHuman's module.                                                                                        |
| 13.9  | **Think token scrubbing**       | 🆕 LOCUS-NEW      | Hermes`think_scrubber.py`                                         | —              | Steal Hermes' pattern.                                                                                           |
| 13.10 | **Message sanitization**        | 🆕 LOCUS-NEW      | Hermes`message_sanitization.py`                                   | —              | Steal Hermes' pattern.                                                                                           |

---

## §14. Voice

| #    | Feature                        | Verdict           | Source(s)                                        | Modularity  | Notes                                                                                                                |
| ---- | ------------------------------ | ----------------- | ------------------------------------------------ | ----------- | -------------------------------------------------------------------------------------------------------------------- |
| 14.1 | **STT (Speech-to-Text)** | 🔀 MULTI-PROVIDER | Locus 4 backends · OpenHuman voice inference    | STTProvider | **Options**: Groq Whisper (default, fastest), Whisper local, Azure, OpenAI, OpenHuman voice inference, custom. |
| 14.2 | **TTS (Text-to-Speech)** | 🔀 MULTI-PROVIDER | Locus 4 backends · OpenHuman voice inference    | TTSProvider | **Options**: Edge TTS (default, free), ElevenLabs, OpenAI, Piper, Kokoro, OpenHuman voice inference, custom.   |
| 14.3 | **Voice call interface** | 🆕 LOCUS-NEW      | Locus-original                                   | —          | Audio → STT → pipeline → TTS → vault transcript.                                                                 |
| 14.4 | **Dictation**            | 🆕 LOCUS-NEW      | OpenHuman`dictation` · Locus `dictation.py` | —          | Steal patterns from both.                                                                                            |

---

## §15. Web Search

| #    | Feature                            | Verdict    | Source(s)        | Modularity | Notes                                                                                                               |
| ---- | ---------------------------------- | ---------- | ---------------- | ---------- | ------------------------------------------------------------------------------------------------------------------- |
| 15.1 | **Web search (8 providers)** | ✅ KEEP-PI | Pi`web_search` | —         | OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini + full content fetch. Superset of old Locus (5 providers). |

---

## §16. Browser Automation

| #    | Feature                       | Verdict           | Source(s)                                               | Modularity      | Notes                                                                                        |
| ---- | ----------------------------- | ----------------- | ------------------------------------------------------- | --------------- | -------------------------------------------------------------------------------------------- |
| 16.1 | **Browser automation**  | 🔀 MULTI-PROVIDER | OpenHuman`screen_intelligence` · Locus Playwright    | BrowserProvider | **Options**: Playwright (default), OpenHuman screen_intelligence, Browserbase, custom. |
| 16.2 | **Screenshot / vision** | 🆕 LOCUS-NEW      | OpenHuman`screen_intelligence` · Locus `vision.py` | —              | Steal OpenHuman's screen intelligence pattern.                                               |

---

## §17. Channels / Gateway / Messaging

| #     | Feature                                                                                        | Verdict      | Source(s)                                                         | Modularity      | Notes                                                                              |
| ----- | ---------------------------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------- | --------------- | ---------------------------------------------------------------------------------- |
| 17.1  | **Telegram**                                                                             | 🆕 LOCUS-NEW | Hermes gateway adapter · Locus PTB                               | ChannelProvider | Primary Locus interface. Auth, inline keyboards, voice messages, file attachments. |
| 17.2  | **Discord**                                                                              | 🆕 LOCUS-NEW | Hermes gateway adapter · Locus channel module                    | ChannelProvider | Steal Hermes' adapter pattern.                                                     |
| 17.3  | **Slack**                                                                                | 🆕 LOCUS-NEW | Hermes gateway adapter · Locus channel module                    | ChannelProvider | Steal Hermes' adapter pattern.                                                     |
| 17.4  | **WhatsApp**                                                                             | 🆕 LOCUS-NEW | Hermes`whatsapp_identity.py` · Locus channel module            | ChannelProvider | Steal Hermes' pattern.                                                             |
| 17.5  | **Signal**                                                                               | 🆕 LOCUS-NEW | Hermes`apps/shared` · Locus channel module                     | ChannelProvider | Steal Hermes' pattern.                                                             |
| 17.6  | **IRC / Matrix / Mattermost / Teams / Lark / DingTalk / Google Chat / Email / iMessage** | 🆕 LOCUS-NEW | Locus channel modules                                             | ChannelProvider | Each is a swappable ChannelProvider adapter. Enable/disable via config.            |
| 17.7  | **CLI / Terminal**                                                                       | ✅ KEEP-PI   | Pi TUI                                                            | —              | Primary desktop interface.                                                         |
| 17.8  | **Platform registry**                                                                    | 🆕 LOCUS-NEW | Hermes`platform_registry.py` · OpenHuman `channels` · Locus | —              | Registry of active channel bridges. Steal patterns from both.                      |
| 17.9  | **Cross-platform message mirroring**                                                     | 🆕 LOCUS-NEW | Hermes`mirror.py`                                               | —              | Steal Hermes' mirror pattern.                                                      |
| 17.10 | **Graceful restart**                                                                     | 🆕 LOCUS-NEW | Hermes`restart.py`                                              | —              | Steal Hermes' pattern.                                                             |
| 17.11 | **Shutdown forensics**                                                                   | 🆕 LOCUS-NEW | Hermes`shutdown_forensics.py`                                   | —              | Steal Hermes' pattern.                                                             |

---

## §18. MCP (Model Context Protocol)

| #    | Feature                | Verdict      | Source(s)                               | Modularity | Notes                                          |
| ---- | ---------------------- | ------------ | --------------------------------------- | ---------- | ---------------------------------------------- |
| 18.1 | **MCP client**   | 🆕 LOCUS-NEW | OpenHuman HTTP + stdio client           | —         | Steal OpenHuman's dual-transport MCP client.   |
| 18.2 | **MCP server**   | 🆕 LOCUS-NEW | OpenHuman Axum HTTP + SSE               | —         | Steal OpenHuman's MCP server implementation.   |
| 18.3 | **MCP registry** | 🆕 LOCUS-NEW | OpenHuman dynamic install + Smithery.ai | —         | Steal OpenHuman's registry with 60s reconnect. |
| 18.4 | **MCP audit**    | 🆕 LOCUS-NEW | OpenHuman`mcp_audit`                  | —         | Steal OpenHuman's audit module.                |
| 18.5 | **Obsidian MCP** | 🆕 LOCUS-NEW | Locus-original                          | —         | vault_read/write/search/tag/stats.             |

---

## §19. Export & Artifacts

| #    | Feature                          | Verdict      | Source(s)                            | Modularity | Notes                                                    |
| ---- | -------------------------------- | ------------ | ------------------------------------ | ---------- | -------------------------------------------------------- |
| 19.1 | **HTML/JSON/MD export**    | ✅ KEEP-PI   | Pi export system                     | —         | Built-in.                                                |
| 19.2 | **Trajectory recording**   | 🆕 LOCUS-NEW | Hermes`trajectory.py` (1321 lines) | —         | Steal Hermes' trajectory recording for batch evaluation. |
| 19.3 | **Daily AI Chat Archiver** | 🆕 LOCUS-NEW | Locus-original                       | —         | 23:45 → export session → .md → vault → git commit.   |

---

## §20. Computer Use

| #    | Feature                          | Verdict      | Source(s)                                                           | Modularity | Notes                      |
| ---- | -------------------------------- | ------------ | ------------------------------------------------------------------- | ---------- | -------------------------- |
| 20.1 | **Native desktop control** | 🆕 LOCUS-NEW | OpenHuman`desktop_companion` + `overlay` · Locus `native.py` | —         | Steal OpenHuman's pattern. |
| 20.2 | **Screen capture**         | 🆕 LOCUS-NEW | OpenHuman`screen_intelligence` · Locus `capture.py`            | —         | Steal OpenHuman's pattern. |
| 20.3 | **VNC remote control**     | 🆕 LOCUS-NEW | Locus`vnc.py`                                                     | —         | Low priority.              |

---

## §21. Integrations

| #    | Feature                   | Verdict      | Source(s)                                      | Modularity          | Notes                        |
| ---- | ------------------------- | ------------ | ---------------------------------------------- | ------------------- | ---------------------------- |
| 21.1 | **Google Calendar** | 🆕 LOCUS-NEW | Locus manual OAuth                             | IntegrationProvider | 50-line manual OAuth.        |
| 21.2 | **Gmail**           | 🆕 LOCUS-NEW | Locus manual OAuth                             | IntegrationProvider | Same OAuth flow.             |
| 21.3 | **Webhooks**        | 🆕 LOCUS-NEW | OpenHuman`webhooks` · Locus `webhooks.py` | —                  | Steal from both.             |
| 21.4 | **Composio**        | ⚪ SKIP      | —                                             | —                  | Replaced by manual OAuth.    |
| 21.5 | **Web3 / wallet**   | ⚪ SKIP      | —                                             | —                  | Not needed for Life OS.      |
| 21.6 | **Billing**         | ⚪ SKIP      | —                                             | —                  | Not needed for personal use. |

---

## §22. Configuration

| #    | Feature                         | Verdict    | Source(s)             | Modularity | Notes                                       |
| ---- | ------------------------------- | ---------- | --------------------- | ---------- | ------------------------------------------- |
| 22.1 | **Config format**         | 🔄 AUGMENT | Pi`settings.json`   | —         | Locus settings nested under`"locus": {}`. |
| 22.2 | **Config migration**      | ✅ KEEP-PI | Pi`migrations.ts`   | —         | Built-in.                                   |
| 22.3 | **Environment variables** | 🔄 AUGMENT | Pi`env-api-keys.ts` | —         | Add`LOCUS_*` env vars.                    |

---

## §23. CI/CD & Testing

| #    | Feature                           | Verdict      | Source(s)                                       | Modularity | Notes                                       |
| ---- | --------------------------------- | ------------ | ----------------------------------------------- | ---------- | ------------------------------------------- |
| 23.1 | **Unit tests**              | ✅ KEEP-PI   | Pi Vitest                                       | —         | Locus extensions tested with Vitest.        |
| 23.2 | **CI pipeline**             | ✅ KEEP-PI   | Pi GitHub Actions                               | —         | Standard CI.                                |
| 23.3 | **Linting + Type checking** | ✅ KEEP-PI   | Pi ESLint + TypeScript                          | —         | Built-in.                                   |
| 23.4 | **Docker**                  | 🆕 LOCUS-NEW | Hermes Docker builds · OpenHuman Docker builds | —         | Steal Docker patterns from both.            |
| 23.5 | **Batch trajectory runner** | 🆕 LOCUS-NEW | Hermes`trajectory.py`                         | —         | Steal Hermes' pattern for batch evaluation. |

---

## §24. Utilities

All Pi utilities (clipboard, git, image handling, syntax highlighting, frontmatter, file watcher, etc.) inherited via ✅ KEEP-PI.

---

## §25. Life OS — Behavioral Metrics *(Locus-Unique)*

ALL features → 🆕 LOCUS-NEW (Locus-original). All formulas in Python sidecar. See Part IV for modularity contracts.

| #     | Feature                     | Modularity     |
| ----- | --------------------------- | -------------- |
| 25.1  | Four Factions Framework     | LifeOSProvider |
| 25.2  | Daily Capacity Score (DCS)  | LifeOSProvider |
| 25.3  | Five Operating Modes        | LifeOSProvider |
| 25.4  | Task Weight Score (TWS)     | LifeOSProvider |
| 25.5  | Three-Layer Goal Stack      | LifeOSProvider |
| 25.6  | Action Gap Tracking         | LifeOSProvider |
| 25.7  | Deferral Detection (3/5/8+) | LifeOSProvider |
| 25.8  | Lag Score + TWS Lag Bonus   | LifeOSProvider |
| 25.9  | Emergency Task Injection    | LifeOSProvider |
| 25.10 | Exhaustion Predictor        | LifeOSProvider |
| 25.11 | Weekly Faction Rebalance    | LifeOSProvider |
| 25.12 | 6-Step Scheduling Algorithm | LifeOSProvider |
| 25.13 | Review Cadence System       | LifeOSProvider |
| 25.14 | Goal Stack Enforcement      | LifeOSProvider |
| 25.15 | Cross-Faction Efficiency    | LifeOSProvider |
| 25.16 | 4-Level Emergency Protocol  | LifeOSProvider |

---

## §26. Proactive Reasoning / Brain Engine *(Locus-Unique)*

ALL features → 🆕 LOCUS-NEW (Locus-original). Python sidecar. See Part IV.

| #    | Feature                             | Modularity       |
| ---- | ----------------------------------- | ---------------- |
| 26.1 | Inner Loop (Proactive Thinker)      | BrainProvider    |
| 26.2 | State Engine + Inferred Cause Chain | BrainProvider    |
| 26.3 | Multi-Horizon Pattern Engine        | PatternEngine    |
| 26.4 | Context Forge                       | ContextAssembler |
| 26.5 | Query Router / Intent Classifier    | IntentClassifier |
| 26.6 | Personality + "Wants" Engine        | BrainProvider    |
| 26.7 | Weekly Full Vault Synthesis         | BrainProvider    |

---

## §27. Vault & Knowledge Intelligence *(Locus-Unique)*

ALL features → 🆕 LOCUS-NEW (Locus-original). See Part IV.

| #    | Feature                           | Modularity          |
| ---- | --------------------------------- | ------------------- |
| 27.1 | PageIndex (vectorless retrieval)  | RetrievalProvider   |
| 27.2 | Nightly Vault Ingestion Pipeline  | VaultProvider       |
| 27.3 | LOCUS_SHORTHAND (4× compression) | CompressionProvider |
| 27.4 | 3-Level Tag Hierarchy             | VaultProvider       |
| 27.5 | Rough Note Parser / Idea Tracker  | —                  |
| 27.6 | Link Dump / Resource Logger       | —                  |
| 27.7 | Excalidraw MCP Skill              | —                  |

---

## §28. Interface Philosophy & Infrastructure *(Locus-Unique)*

| #    | Feature                         | Verdict           | Notes                                                   |
| ---- | ------------------------------- | ----------------- | ------------------------------------------------------- |
| 28.1 | Dual-interface (TUI + Telegram) | 🆕 LOCUS-NEW      | TUI for desktop, Telegram for mobile. Unified sessions. |
| 28.2 | 4 Daily Structured Check-ins    | 🆕 LOCUS-NEW      | Morning/Afternoon/Evening/Night.                        |
| 28.3 | Voice Call Interface            | 🆕 LOCUS-NEW      | STT → pipeline → TTS → transcript.                   |
| 28.4 | DeepSeek V4 Flash default       | ✅ KEEP-PI config | Set via`locus config`.                                |
| 28.5 | Zero-cost constraint            | ✅ KEEP-PI        | ~$0.012/day.                                            |
| 28.6 | Minimum AI in harness           | ✅ KEEP-PI        | LLM for reasoning only.                                 |

---

## §29. Miscellaneous

| #    | Feature                 | Verdict      | Source(s)                                              | Notes                               |
| ---- | ----------------------- | ------------ | ------------------------------------------------------ | ----------------------------------- |
| 29.1 | Error classifier        | 🆕 LOCUS-NEW | Hermes`error_classifier.py`                          | Steal Hermes' pattern.              |
| 29.2 | Auxiliary LLM client    | 🆕 LOCUS-NEW | Hermes`auxiliary_client.py`                          | Secondary LLM for background tasks. |
| 29.3 | Health checks           | 🆕 LOCUS-NEW | Hermes`gateway/status.py` · OpenHuman `health`    | Steal from both.                    |
| 29.4 | Notifications           | 🆕 LOCUS-NEW | OpenHuman`notifications` · Locus                    | Steal OpenHuman's pattern.          |
| 29.5 | Connectivity checks     | 🆕 LOCUS-NEW | OpenHuman`connectivity`                              | Steal OpenHuman's module.           |
| 29.6 | Code graph analysis     | 🆕 LOCUS-NEW | OpenHuman`codegraph`                                 | Steal OpenHuman's module.           |
| 29.7 | Subconscious background | 🆕 LOCUS-NEW | OpenHuman`subconscious` · Locus `subconscious.py` | Merge patterns.                     |
| 29.8 | Workflows               | 🆕 LOCUS-NEW | OpenHuman`workflows`                                 | Steal OpenHuman's module.           |

---

# Part II — Feature → Source Codebase Mapping

To implement Locus as a modular, provider-based framework, the core logic is extracted and adapted from five primary codebases and external packages:

| Feature / Module | Source Codebase | Linked Files / Packages | Purpose | Inter-file Congruence & Data Flow |
| :--- | :--- | :--- | :--- | :--- |
| **Graph-Native Memory** | `neo4j-labs/agent-memory` | `client.py`, `long_term.py`, `short_term.py`, `reasoning.py` | Graph database interaction, entity extraction (GLiNER/GLiREL), POLE+O node traversal | Ingestion writes nodes to Neo4j; Retrieval translates high-level keywords to Cypher queries and pulls connected entity subgraphs. |
| **Token Compression** | `headroomlabs-ai/headroom` | `compress.py`, `proxy.py`, `mcp.py`, `ccr.py` | Cache-Compress-Retrieve (CCR) pipeline, ContentRouter (detect JSON/code/prose) | Intercepts prompts going to LLM; caches original context locally, returns compressed text, and exposes `headroom_retrieve` tool. |
| **Vectorless RAG** | `VectifyAI/PageIndex` | `tree_index.py`, `reasoning_rag.py` | Hierarchical document trees, reasoning-based tree navigation using LLM | Discards chunk-based search; maps Obsidian documents into semantic trees. LLMs navigate nodes sequentially to locate exact pages. |
| **Alternative Memory** | `hermes-agent` / `mem0` / `supermemory` / `honcho` | `plugins/memory/mem0/__init__.py`, `plugins/memory/supermemory/__init__.py`, `plugins/memory/honcho/__init__.py` | Adapters for third-party semantic memory, dialectic user state tracking | Providers implement the `MemoryProvider` ABC; loaded dynamically via Locus Registry on agent startup. |
| **Autonomous Research** | `karpathy/autoresearch` | `train.py`, `prepare.py`, `program.md` | Sandboxed overnight LLM research loops, validation bits-per-byte (bpb) tracking | Evaluates hyperparameter/model changes on Nanochat training loops. Triggered as an invokeable tool. |
| **File Crawlers** | `openhuman` / `locus-os` | `brain/collector.py`, `brain/chunker.py`, `gateway/bot.py` | Vault file monitoring (MD5 hashing), incremental indexing, Telegram message ingestion | VaultCrawler processes local Obsidian files; ChatArchiver processes AI chat markdown files; TelegramCrawler logs live bot chat logs. |
| **Coding Harnesses** | `pi` / `locus-os` | `packages/coding-agent/src/core/agent-session.ts`, `core/coding/` | Command translation, workspace preparation, prompting external tools, diff parsing | Locus analyzes tasks, constructs workspace bundles, prompts harnesses (Antigravity, Claude Code, Aider), and ingests code outputs. |
| **Model Context Protocol**| `openhuman` | `src/openhuman/mcp_client/`, `mcp_server/`, `mcp_registry/` | Dual stdio/HTTP transport protocol, dynamic MCP tool loading | Bridges external AI editors (Cursor, ChatGPT) to Locus's internal tools (checkins, DCS metrics, database queries). |

---

# Part III — Atomic Logic Stripping & Pseudocode

Here we strip down the exact execution logic of each key Locus feature into pure algorithmic schemas and specify how they adapt to Locus's modular registry architecture.

### 1. Memory retrieval: PageIndex + pgvector + Neo4j (Memory Combo)

#### Extracted Logic (Pseudocode)
```
FUNCTION query_memory_combo(user_query, session_context, limit=10):
    # Step 1: Perform Intent Classification
    intent = intent_classifier.classify(user_query)
    
    # Step 2: Set up parallel execution tasks
    tasks = []
    
    # Task A: Graph Memory Traversal (Neo4j Agent Memory)
    IF "graph" in intent.sources_required:
        tasks.append(neo4j_provider.query(
            query=user_query, 
            schema="POLE+O", 
            depth=2
        ))
        
    # Task B: Vectorless Document Search (PageIndex)
    IF "pageindex" in intent.sources_required:
        tasks.append(pageindex_provider.retrieve(
            query=user_query, 
            hierarchy_level="page"
        ))
        
    # Task C: Dense Vector Search (pgvector)
    IF "pgvector" in intent.sources_required:
        tasks.append(pgvector_provider.query(
            query=user_query, 
            limit=limit
        ))
        
    # Step 3: Await all parallel queries
    results = AWAIT parallel_execute(tasks)
    
    # Step 4: Reconcile and merge contexts based on Hebbian weights
    merged_context = reconcile_and_sort_contexts(results)
    
    # Step 5: Compress token footprint using Headroom CCR
    compressed_prompt = headroom_provider.compress(
        content=merged_context,
        target_tokens=800
    )
    
    RETURN compressed_prompt
```

#### Adaptation to Locus Architecture
- **Component**: `locus/providers/memory/` and `locus/providers/retrieval/`
- **Adapts via**: The `MemoryProvider` and `RetrievalProvider` interfaces. The `neo4j-agent-memory` client operates as a background microservice, feeding entities to PostgreSQL's `pgvector` tables. PageIndex builds document-tree indexes on top of local Obsidian vault paths. Headroom wraps the prompt builder internally, keeping the token footprint strictly under 800 tokens.

---

### 2. Proactive Agent Loop & File Crawlers

#### Extracted Logic (Pseudocode)
```
# Standard 90-minute Cron Task (Proactive Inner Loop)
CRON_TASK proactive_reasoning_pass():
    # Step 1: Calculate active window (07:00 - 00:00 IST)
    IF NOT current_time_within_window("07:00", "00:00"):
        RETURN
        
    # Step 2: Fetch current DCS, Operating Mode, and Faction status
    state = state_engine.get_current_state()
    
    # Step 3: Run incremental crawl of vault
    crawled_docs = vault_crawler.crawl_changed_files()
    IF crawled_docs:
        pageindex_provider.reindex(crawled_docs)
        pgvector_provider.reindex(crawled_docs)
        
    # Step 4: Run pattern engine over the five horizons (6h -> all-time)
    behavioral_patterns = pattern_engine.detect_patterns(horizon="24h")
    
    # Step 5: Formulate thought (Proactive reasoning loop)
    thought_prompt = construct_proactive_prompt(state, behavioral_patterns)
    inferred_cause = generator.think(thought_prompt)
    
    # Step 6: Evaluate generated thought using the Personal Reward Model
    reward_score = reward_model.score_thought(inferred_cause)
    
    # Step 7: Push message if it exceeds confidence threshold
    IF reward_score >= 0.6:
        channel_provider.send_message(
            recipient="user", 
            message=inferred_cause,
            interactive_keyboard=["Acknowledge", "Modify Plan", "Ignore"]
        )
```

#### Adaptation to Locus Architecture
- **Component**: `locus/providers/brain/` and `locus/providers/crawler/`
- **Adapts via**: The `BrainProvider` and `CrawlerProvider` interfaces. The `VaultCrawler` reads markdown files incrementally (comparing MD5 hashes saved in PG). The `PatternEngine` processes database entries to compile logs, which are then passed to the `BrainProvider` to generate insights. The reward model (an offline scikit-learn classifier) runs dynamically inside the runtime sidecar.

---

### 3. Coding Harness Delegation

#### Extracted Logic (Pseudocode)
```
FUNCTION delegate_coding_task(user_request, codebase_path):
    # Step 1: Analyze context and dependencies
    target_files = codebase_crawler.identify_relevant_files(user_request)
    brief = context_forge.generate_task_brief(user_request, target_files)
    
    # Step 2: Query active Harness Providers for time/confidence estimates
    estimates = []
    FOR harness IN harness_registry.get_active_harnesses():
        estimates.append({
            "harness": harness.name,
            "estimate": harness.estimate_task(brief)
        })
        
    # Step 3: Select the best harness based on confidence and capabilities
    selected_harness = select_best_harness(estimates)
    
    # Step 4: Prepare prompt instruction set formatted for that specific harness
    harness_prompt = compile_harness_instructions(brief, selected_harness)
    
    # Step 5: Execute and monitor harness process (async shell wrapper)
    task_execution = selected_harness.execute(harness_prompt, path=codebase_path)
    
    WHILE task_execution.is_running():
        status = task_execution.get_status()
        emit_progress_event(status)
        sleep(10)
        
    # Step 6: Parse results (Git diff & files modified)
    changes = task_execution.get_results()
    
    # Step 7: Post result to user for approval
    approval_store.queue_approval(
        task_id=task_execution.id,
        changes=changes,
        TTL=600 # 10-minute expiry
    )
    
    RETURN task_execution.id
```

#### Adaptation to Locus Architecture
- **Component**: `locus/providers/harness/`
- **Adapts via**: The `HarnessProvider` interface. Harness adapters wrap CLI invocations (e.g., executing `claude --dangerously-skip-permissions` or using Antigravity workspace buffers via RPC API). The delegation runs asynchronously to prevent blocking the reactive Telegram loop.

---

### 4. karpathy/autoresearch Integration

#### Extracted Logic (Pseudocode)
```
FUNCTION trigger_autonomous_research(research_goal, config_options):
    # Step 1: Initialize local workspace sandboxed directory
    sandbox_dir = sandbox_provider.create_workspace(name="autoresearch_sandbox")
    
    # Step 2: Clone Nanochat baseline and populate prepare.py and train.py
    sandbox_dir.write_file("prepare.py", get_resource_template("prepare.py"))
    sandbox_dir.write_file("train.py", get_resource_template("train.py"))
    
    # Step 3: Construct program.md instructions from user goal
    program_instructions = generate_program_markdown(research_goal)
    sandbox_dir.write_file("program.md", program_instructions)
    
    # Step 4: Run initial setup (prepare tokenizer, download dataset)
    sandbox_provider.execute(command="uv run prepare.py", cwd=sandbox_dir)
    
    # Step 5: Start autonomous iterative research loop
    best_val_bpb = float('inf')
    iteration = 0
    
    WHILE iteration < config_options.max_iterations:
        # Agent edits train.py based on program.md context
        agent_edit_prompt = construct_agent_edit_prompt(sandbox_dir.read_file("train.py"), program_instructions)
        new_train_code = generator.generate_code_modification(agent_edit_prompt)
        sandbox_dir.write_file("train.py", new_train_code)
        
        # Execute 5-minute training budget run
        run_result = sandbox_provider.execute_with_timeout(
            command="uv run train.py", 
            cwd=sandbox_dir, 
            timeout_seconds=300
        )
        
        # Parse metrics output (val_bpb)
        val_bpb = parse_validation_metrics(run_result.stdout)
        
        # Keep or Discard branch decisions
        IF val_bpb < best_val_bpb:
            best_val_bpb = val_bpb
            sandbox_dir.commit_changes(message=f"Iteration {iteration}: val_bpb improved to {val_bpb}")
            log_reasoning_trace(iteration, "keep", val_bpb)
        ELSE:
            sandbox_dir.revert_changes()
            log_reasoning_trace(iteration, "discard", val_bpb)
            
        iteration += 1
        
    # Step 6: Ingest results into long-term fact graph
    neo4j_provider.store_fact(
        subject="autoresearch_results",
        relation="achieved_bpb",
        obj=str(best_val_bpb)
    )
    
    RETURN best_val_bpb
```

#### Adaptation to Locus Architecture
- **Component**: `locus/providers/research/`
- **Adapts via**: The `ResearchProvider` interface. The implementation spawns `karpathy/autoresearch` runs inside the sandboxed environment defined by the `SandboxProvider`. This is configured as a background task managed by Locus's task scheduler (APScheduler sidecar).
# Part IV — Modularity Contract Specifications

## All Provider Interfaces

| Interface                     | Purpose                                 | Default Provider              | Available Alternatives                                          |
| ----------------------------- | --------------------------------------- | ----------------------------- | --------------------------------------------------------------- |
| **MemoryProvider**      | Store/query/manage memories             | Neo4j Agent Memory            | mem0, Supermemory, Honcho, Mastra, Cognee, custom               |
| **UserModelProvider**   | Build/query user profile                | Locus rolling-average         | Hermes Honcho, OpenHuman ambient profiling, custom              |
| **BrainProvider**       | Proactive reasoning, Inner Loop         | Locus Brain Engine            | Custom                                                          |
| **PatternEngine**       | Multi-horizon pattern detection         | Locus 5-horizon engine        | Custom                                                          |
| **ContextAssembler**    | Multi-source context assembly           | Locus Context Forge (6-layer) | Custom layers, custom assembler                                 |
| **IntentClassifier**    | Query intent classification             | Locus 8-type classifier       | Custom                                                          |
| **RewardModel**         | Gate proactive outputs                  | Locus sklearn LogReg          | Custom                                                          |
| **LifeOSProvider**      | Behavioral metrics (DCS, TWS, factions) | Locus Life OS                 | Custom                                                          |
| **SchedulerProvider**   | Cron / scheduled tasks                  | node-cron + APScheduler       | Hermes NL cron, OpenHuman scheduler_gate, custom                |
| **ChannelProvider**     | Messaging channel bridge                | Telegram (primary)            | Discord, Slack, WhatsApp, Signal, IRC, Matrix, + 8 more, custom |
| **STTProvider**         | Speech-to-Text                          | Groq Whisper                  | Whisper local, Azure, OpenAI, custom                            |
| **TTSProvider**         | Text-to-Speech                          | Edge TTS                      | ElevenLabs, OpenAI, Piper, Kokoro, custom                       |
| **SearchProvider**      | Full-text/semantic search               | PageIndex                     | Hermes FTS5, OpenHuman memory_search, custom                    |
| **EmbeddingProvider**   | Vector embeddings                       | pgvector                      | OpenHuman embeddings, custom                                    |
| **EntityExtractor**     | Entity extraction from text             | spaCy → GLiNER → LLM        | OpenHuman memory_entities, custom                               |
| **CompactionProvider**  | Session compression                     | Pi compaction engine          | Hermes compression, Headroom CCR, custom                        |
| **CompressionProvider** | Token compression                       | Headroom CCR                  | Simple summarization, LOCUS_SHORTHAND, custom                   |
| **SandboxProvider**     | Shell execution sandboxing              | Pi trust model                | bubblewrap, docker, firejail, landlock, custom                  |
| **BrowserProvider**     | Browser automation                      | Playwright                    | OpenHuman screen_intelligence, Browserbase, custom              |
| **VaultProvider**       | Knowledge vault operations              | Obsidian (local)              | Custom                                                          |
| **RetrievalProvider**   | Document retrieval                      | PageIndex (vectorless)        | Vector search, BM25, custom                                     |
| **LearningProvider**    | Post-session learning                   | Locus reflector               | Hermes curator, OpenHuman 4-hook system, custom                 |
| **PostTurnProvider**    | Post-turn processing                    | Hermes background_review      | OpenHuman hooks, custom                                         |
| **SubagentArchetype**   | Subagent behavior templates             | Locus 4 factions              | OpenHuman 15 archetypes, custom                                 |
| **FooterWidget**        | TUI footer content                      | Locus status widget           | Custom                                                          |

**Universal Provider Pattern:**

```
EVERY provider follows this lifecycle:

1. REGISTRATION:
   provider_registry.register("name", ProviderClass)

2. CONFIGURATION (locus settings):
   locus:
     [subsystem]:
       provider: "name"       # which provider to use
       enabled: true           # toggle on/off
       options:                # provider-specific config
         key: value

3. INITIALIZATION:
   ON locus_start:
     config = settings.get("locus.[subsystem]")
     IF NOT config.enabled: SKIP
     provider = registry.get(config.provider)
     provider.initialize(config.options)

4. RUNTIME:
     provider.method(args)

5. SHUTDOWN:
     provider.shutdown()

6. HEALTH CHECK:
     provider.health_check() → { status, latency, error? }
```

---

# Appendix A — Provider Registry

```
REGISTRY STRUCTURE:

locus/providers/
├── memory/
│   ├── interface.ts           # MemoryProvider interface
│   ├── neo4j-agent-memory.ts  # Default provider
│   ├── mem0.ts
│   ├── supermemory.ts
│   ├── honcho.ts
│   ├── mastra.ts
│   ├── cognee.ts
│   └── index.ts              # Registry + factory
├── brain/
│   ├── interface.ts           # BrainProvider interface
│   ├── locus-brain-engine.ts  # Default (calls Python sidecar)
│   └── index.ts
├── channels/
│   ├── interface.ts           # ChannelProvider interface
│   ├── telegram.ts            # Primary
│   ├── discord.ts
│   ├── slack.ts
│   ├── whatsapp.ts
│   └── ...
├── voice/
│   ├── stt-interface.ts
│   ├── tts-interface.ts
│   ├── groq-whisper.ts
│   ├── edge-tts.ts
│   └── ...
├── learning/
│   ├── interface.ts
│   ├── locus-reflector.ts
│   ├── hermes-curator.ts
│   ├── openhuman-hooks.ts
│   └── ...
└── [...]
```

---

# Appendix B — Config Schema

```
// In Pi's settings.json under "locus" key

{
  "locus": {
    "enabled": true,
  
    "memory": {
      "provider": "neo4j-agent-memory",
      "enabled": true,
      "options": {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "..."
      },
      "secondary_providers": ["pageindex"],  // stackable
      "compression": {
        "provider": "headroom-ccr",
        "enabled": true
      }
    },
  
    "brain": {
      "provider": "locus-brain-engine",
      "enabled": true,
      "inner_loop": {
        "enabled": true,
        "interval_minutes": 90,
        "active_window": { "start": "07:00", "end": "00:00" },
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
      }
    },
  
    "life_os": {
      "enabled": true,
      "timezone": "Asia/Kolkata",
      "factions": ["Health", "Leverage", "Craft", "Expression"],
      "checkin_times": ["07:30", "13:00", "18:00", "22:00"],
      "review_cadence": {
        "daily": { "duration_min": 7 },
        "weekly": { "duration_min": 30, "day": "Sunday" },
        "monthly": { "duration_min": 60 },
        "quarterly": { "duration_min": 120 }
      }
    },
  
    "channels": {
      "telegram": {
        "enabled": true,
        "token": "...",
        "allowed_users": [123456789]
      },
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
      "path": "C:/Users/.../ObsidianVault",
      "nightly_ingestion": { "enabled": true, "time": "23:45" },
      "weekly_synthesis": { "enabled": true, "day": "Sunday", "time": "02:00" }
    },
  
    "learning": {
      "providers": ["locus-reflector"],
      "user_modeling": { "provider": "locus-rolling-average" },
      "reward_model": { "enabled": true, "retrain_schedule": "weekly" }
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

## Summary Counts

| Verdict           | Count | Meaning                                          |
| ----------------- | ----- | ------------------------------------------------ |
| ✅ KEEP-PI        | ~60   | Inherited from Pi. Zero effort.                  |
| 🔄 AUGMENT        | ~18   | Pi base + Locus additions.                       |
| 🆕 LOCUS-NEW      | ~75   | New Locus features (steal logic from codebases). |
| 🔀 MULTI-PROVIDER | ~20   | Multiple swappable provider options.             |
| ⚪ SKIP           | ~5    | Deliberately excluded.                           |

**25 provider interfaces** covering every major subsystem.
**7+ memory providers**, **4+ STT providers**, **4+ TTS providers**, **13+ channel providers**, **4+ sandbox backends**, **3+ learning systems**, **3+ compression engines**.

> **Next Step**: User provides specific feature list → populate Part II (file mapping via `/understand-anything`) → populate Part III (atomic logic stripping).
