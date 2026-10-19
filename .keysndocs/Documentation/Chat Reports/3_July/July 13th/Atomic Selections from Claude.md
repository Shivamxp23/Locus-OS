# Atomic Selections — Feature Source Mapping for Locus Framework

> **Generated**: July 13th, 2025  
> **Purpose**: Map each atomic feature to source codebase files for implementation strategy  
> **Coding Philosophy**: Laziness first, steal logic from existing implementations

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented in Locus |
| 🔧 | Partially implemented or basic version |
| 📐 | Designed/architected but not implemented |
| ⬜ | Not present, to be cloned/adapted |
| ❌ | Rejected by Locus design |

---

## Section 1. Agent Core / Runtime

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Main Agent Loop | Pi (✅) + Hermes (✅) | Locus: `core/agent.py`, `core/tool_registry.py`; Pi: `packages/agent/src/agent-loop.ts`; Hermes: `agent/agent_init.py` | Hook into ToolRegistry dispatch pattern | Two-entry loop: receive -> context build -> LLM call -> tool parse -> tool exec -> response. Pi adds retry with exponential backoff. |
| Turn Context Management | Pi (✅ Harness) + Hermes (✅ turn_context.py) | Locus: `core/context/*`; Hermes: `agent/turn_context.py` | Implement full turn_context pattern with snapshots | Per-turn state: input/output tokens, tool results accumulator, compaction trigger. |
| Turn Retry / Error Recovery | Hermes (✅ turn_retry_state.py) | Hermes: `agent/turn_retry_state.py` | Clone retry state pattern | Retry on transient errors. 3 attempts, 2s base delay, exponential backoff. |
| System Prompt Builder | Pi (✅) + Hermes (✅) | Locus: `SETTINGS.md`, planned `core/system_prompt.py`; Pi: `packages/agent/src/harness/system-prompt.ts` | Dynamic assembly with skills injection | Dynamic assembly: template_base + skills_injection + context_layers. Pi progressive disclosure. |
| Prompt Caching | Pi (✅ openai-prompt-cache.ts) | Implement via httpx caching wrapper | Add prompt caching to LLM calls | Cache by prompt hash, 24hr TTL. Pi: cache hit detection. Hermes: integrates with context engine. |
| Background Review / Post-turn | Hermes (✅) + OpenHuman (✅) + Locus (📐 Inner Loop) | Locus: `core/heartbeat/subconscious.py`; Hermes: `agent/background_review.py` | Integrate into Inner Loop scheduler | After turn: Archivist archives, Reflection summarizes, ToolTracker logs usage. |

---

## Section 2. LLM Providers

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Provider Count | Locus (❌ single-provider) | Use DeepSeek V4 Flash only | Keep single-provider constraint | OpenAI-compatible via httpx. Single model: ~$0.012/day, ~$4/year. |
| OpenAI-compatible | Pi (✅) + Hermes (✅) | Locus: `core/llm_provider.py`; Pi: `packages/ai/src/providers/*` | Adapt with httpx wrapper | Unified adapter pattern with headers, auth, timeout, retry. Pi: 30+ providers. |
| Anthropic | Pi (✅) + Hermes (✅) | Extend provider registry | Add to Locus providers | Messages API with tool use. Streaming + reasoning support. |
| Provider Registry | Pi (✅) + Hermes (✅) | Locus: `core/provider_registry.py`; Pi: `packages/ai/src/models.ts` | Extend resolve_provider() | Auto-register with metadata: context window, cost, capabilities. |

---

## Section 3. Tools / Tool Execution

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| File Read/Write/Edit | Locus (✅) + Pi (✅) | Locus: `core/coding/file_ops.py`; Pi: `read.ts`, `write.ts`, `edit.ts` | Refactor to consistent interfaces | File tools with pagination (2000 lines), truncation, binary handling. |
| Shell / Bash Execution | Locus (✅ run_shell) + OpenHuman (✅) | Locus: `core/coding/shell_exec.py`; OpenHuman: `shell_exec.py` | Keep blocklist sandbox | Shell with timeout, stdout/stderr capture. Locus: BLOCKED_PATTERNS list. |
| Tool Call Validation | Hermes (✅) + Pi (✅) | Hermes: `agent/tool_guardrails.py` | Clone guardrails pattern | Validate tool params, check safety, enforce policies. |
| XML Tool Dispatch | OpenHuman (✅) | OpenHuman: `agent/xml_dispatcher.py` | Implement in core | XML-style tool calls for structured responses. |

---

## Section 4. Memory & Persistence

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Primary Storage | Locus (✅ SQLite WAL) | `core/memory_manager.py` | Extend for full persistence | SQLite WAL mode with SQLAlchemy. Pi: JSONL tree format alternative. |
| Graph Memory | Neo4j Agent Memory + Locus (✅ Neo4j) | `core/holographic/store.py`; Neo4j Agent Memory: github.com/neo4j-labs/agent-memory | Clone neo4j-labs agent-memory | Nodes: Entity, Concept, Session. Relationships: RELATED_TO, FOLLOWS, CONTAINS. |
| Vector Embeddings | PageIndex + Locus (✅ pgvector) | `core/vault/page_index.py` planned | Integrate PageIndex strategy | pgvector extension. PageIndex: whole-note embedding (200-800 words), sentence-chunking. |
| Memory Orchestrator | Locus (✅) + Hermes (✅) | `core/memory_manager.py`; Hermes: `agent/memory_manager.py` | Unified orchestrator pattern | Coordinate graph, vector, relational stores. Update context on memory changes. |
| Entity Extraction | Locus (📐) + OpenHuman (📐) | Planned: via DeepSeek entities | Extract entities -> graph nodes | NER + relevance scoring. Neo4j node creation with relationship inference. |
| Holographic HRR | Locus (✅) | `core/holographic/*` | Combine with Neo4j | SHA-256 deterministic vectors. bind/unbind/bundle operations. |
| Hebbian Pathway Weighting | Locus (📐) | Neo4j edge weights | Implement in edge properties | Edge weights: +0.1 traversal, x1.3/x0.7 feedback, x0.95 weekly decay. |
| User Modeling Store | Locus (📐) + Hermes (✅ Honcho) | Planned: `core/learning/user_profile.py` | Single-row PG with rolling averages | Ambient profile: behavioral tendencies, peak windows, stressors, communication style. |

---

## Section 5. Sessions

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Session Format | Locus (✅ SQLite) + Pi (✅ JSONL tree) | `core/session_manager.py`; Pi: `packages/agent/src/harness/session/` | Keep SQLite, add tree support | SQLite with UUID sessions. Pi tree: v3 (9 entry types), in-place branching. |
| Session Compression | Pi (✅) + Hermes (✅) + Locus (🔧 basic) | Locus: `core/context/compactor.py`; Hermes: `conversation_compression.py` | Extend compactor | Auto-trigger: contextTokens > limit. Keep 20k recent tokens. LLM summary -> CompactionEntry. |
| Session Resume / Branch | Pi (✅) | Pi: `--resume`, `--fork`, `--continue` | Add session picker | Interactive picker with search/sort. Tree navigation with branch summaries. |

---

## Section 6. Context Management

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Context Window Management | Pi (✅) + Hermes (✅) + Locus (🔧 token_counter.py) | Locus: `core/context/token_counter.py`; Hermes: `context_engine.py` | Implement full context engine | Multi-layer: system -> skills -> context -> memory -> history. Overflow handling. |
| Context Forge | Locus (📐) | Planned: 800-token 6-layer assembler | Implement as context assembly | Layers: identity(80) + temporal(60) + events(180) + graph(150) + vector(200) + web(100). |
| Query Router / Intent Classifier | Locus (📐) | Planned: 8 intent types | Implement intent classifier | Classify: query, task, chat, command, research, memory, schedule, reflection. Route to backend. |

---

## Section 7. TUI / Terminal Interface

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Full TUI Framework | ❌ Rejected | N/A | Use Telegram as primary | No TUI by design. Telegram inline keyboards replace controls. |
| Telegram-native Headless | Locus (✅) | `core/channels/telegram.py` | Primary interface | PTB framework, auth flow, inline keyboards for check-ins. |

---

## Section 8. CLI

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| CLI Flags Count | Locus (✅ 18 commands) | `locus_cli/*` | Extend command set | Current: config, gateway, setup, memory. Planned: full parity. |
| Run Modes | Pi (✅) | Extend `locus` CLI | CLI and Gateway modes | Locus: `locus` (CLI), `locus gateway` (daemon). |
| Setup Wizard | All have ✅ | `locus setup` + `locus setup gateway` | CLI + Telegram setup | Pi: project trust prompt. Locus: 2-phase setup. |
| Config Management | Locus (✅ 28 sections) | `SETTINGS.md` | Use SETTINGS.md format | ~70 schema files (OpenHuman), 28 sections (Locus). |

---

## Section 9. Extensions / Plugins / Skills

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Extension System | Pi (✅) + Hermes (ACP) | Planned: `plugins/` directory | Implement extension loader | TypeScript modules, discovered in project/plugins/. |
| Skills System | Pi (✅ SKILL.md) | Planned: `skills/` | SKILL.md discovery | YAML frontmatter: description, argument-hint. Progressive disclosure. |
| ACP Protocol | Hermes (✅) | Optional: `core/acp_client.py` | Optional integration | Hermes implements server, session, auth, approval, provenance, tools. |
| Prompt Templates | Pi (✅) | Planned: `prompts/` | Add template expansion | Markdown with YAML. 5 bundled: cl, is, pr, sa, wr. |

---

## Section 10. Learning & Self-Improvement

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Post-session Learning | Hermes (✅) + Locus (🔧) | `core/learning/reflector.py`; Hermes: `background_review.py` | Enhance reflector | Curator -> insights -> memory nudge. Archive, summarize, update profile. |
| User Profile Building | Locus (📐) + Hermes (✅ Honcho) | Planned: `core/learning/user_profile.py` | Ambient profile with facets | Rolling averages: tendencies, peak hours, stressors, communication style. |
| Tool Usage Tracking | Locus (✅) | `core/learning/tool_tracker.py` | Track calls, durations | ToolTrackerHook pattern. Log: name, timestamp, duration, success. |
| Personal Reward Model | Locus (📐) | Planned: sklearn LogisticRegression | Train on feedback | Features: response quality, completion, intervention. Weekly retrain. |

---

## Section 11. Subagents / Delegation

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Subagent Spawning | Pi (✅) + Locus (🔧) | `core/delegation/subagent.py`; Pi: `subagent/` | Extend delegation | Pi subagent tool with isolation. 4 faction sub-agents planned. |
| Subagent Archetypes | OpenHuman (✅ 15) + Locus (📐 4 factions) | Planned archetypes | Clone OpenHuman patterns | OpenHuman: orchestrator, planner, researcher, critic. Locus: Craft, Health, Expression, Leverage. |

---

## Section 12. Scheduling & Cron

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| Cron / Scheduled Tasks | Locus (✅) + Hermes (✅) | `core/cron_runner.py`; Hermes: `cron` module | Natural language scheduling | Hermes: natural lang -> cron. Locus: APScheduler every 90min (Inner Loop). |
| Inner Loop (Proactive) | Locus (📐) | `core/heartbeat/subconscious.py` | APScheduler every 90min | Fires without user input. Reward model gate. Checks tasks, schedule, memory. |

---

## Section 27. Vault & Knowledge Intelligence (Locus-only)

| Feature | Source for Locus | Key Files | Integration Strategy | Logic Summary |
|---------|-----------------|-----------|---------------------|---------------|
| PageIndex + Direct Retrieval | Locus (📐) + PageIndex | `core/vault/page_index.py` planned | Integrate PageIndex | Whole-note embedding (200-800 words). Sentence-chunking for long chats. |
| Nightly Vault Ingestion | Locus (📐) + autoresearch | `core/scheduler/vault_ingestion.py` planned | Multi-account Playwright | Scrape ChatGPT, Claude, Gemini, Perplexity. Embed -> store -> link. |
| 3-Level Tag Hierarchy | Locus (📐) | `core/vault/tag_registry.py` planned | PG tag registry | Structure: faction/tag/subtag. Dataview queries in Obsidian. |
| Rough Note Parser | Locus (📐) | `core/commands/idea.py` | /idea -> expand -> archive | Parse rough notes, classify, suggest research, archive/discard. |

---

## Section 32-35. Life OS & Brain Engine (Locus-only)

These features are **unique to Locus** and do not require cloning, but benefit from Pi/Hermes/OpenHuman patterns:

| Feature | Source for Patterns | Integration Strategy | Logic Summary |
|---------|-------------------|---------------------|---------------|
| Four Factions Framework | Internal design | Health/Leverage/Craft/Expression | Each: outcomes -> projects -> tasks. |
| Daily Capacity Score | Internal design | DCS formula: ((E+M+S)/3) x (1-ST/20) | Energy, Motivation, Stress -> 5 modes. |
| Task Weight Score | Internal design | TWS: (P x 0.4) + (U x 0.4) + (D x 0.2) | Priority x Urgency x Difficulty sorting. |
| State Engine | Internal design + Hermes | Psychological + operational state | Combine user state + operational metrics -> causal explanations. |
| Context Forge | Internal design | 800-token 6-layer assembler | identity -> temporal -> events -> graph -> vector -> web. |

---

## Key Architecture Notes for Locus

1. **Lazy First Implementation**: Start with Neo4j Agent Memory, PageIndex, Headroom before custom builds.

2. **Modular Swap Pattern**: Every module exposes interface that can be swapped. Example:
   - LlmProvider interface: DeepSeek now, any provider later
   - MemoryBackend interface: Neo4j + pgvector now, mem0/honcho/supermemory later

3. **Harness Integration Pattern**: Locus delegates coding tasks to best harness by analyzing requirements.

4. **Memory Stack Priority**:
   1. User query -> Query Router
   2. Intent -> Route to backend
   3. Graph memory (Neo4j): entity/concept retrieval
   4. Vector memory (pgvector): semantic search
   5. Relational (SQLite): structured queries
   6. Web search (fallback)

5. **Context Assembly (800-token)**:
   - identity(80) + temporal(60) + events(180) + graph(150) + vector(200) + web(100) = 670 + overhead

---

*Generated by Atomic Selection Analysis — Phase 1 of Locus modular implementation planning.*