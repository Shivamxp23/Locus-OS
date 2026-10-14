# COMBINED ATOMIC FEATURES — Pi · Hermes · OpenHuman · Locus OS

> **Assembled**: July 7th, 2025
> **Sources**: Merged losslessly from July 4th reports
> **Contains**: Full feature matrix + Pi atomic spec + Hermes atomic spec + OpenHuman atomic spec

---

## Table of Contents

1. [Full Feature Matrix](#1-full-feature-matrix)
   - [1. Agent Core / Runtime](#1-agent-core--runtime)
   - [2. LLM Providers](#2-llm-providers)
   - [3. Tools / Tool Execution](#3-tools--tool-execution)
   - [4. Memory &amp; Persistence](#4-memory--persistence)
   - [5. Sessions](#5-sessions)
   - [6. Context Management](#6-context-management)
   - [7. TUI / Terminal Interface](#7-tui--terminal-interface)
   - [8. CLI](#8-cli)
   - [9. Extensions / Plugins / Skills](#9-extensions--plugins--skills)
   - [10. Learning &amp; Self-Improvement](#10-learning--self-improvement)
   - [11. Subagents / Delegation](#11-subagents--delegation)
   - [12. Scheduling &amp; Cron](#12-scheduling--cron)
   - [13. Security &amp; Sandboxing](#13-security--sandboxing)
   - [14. Voice](#14-voice)
   - [15. Web Search](#15-web-search)
   - [16. Browser Automation](#16-browser-automation)
   - [17. Channels / Gateway / Messaging](#17-channels--gateway--messaging)
   - [18. MCP (Model Context Protocol)](#18-mcp-model-context-protocol)
   - [19. Export &amp; Artifacts](#19-export--artifacts)
   - [20. Computer Use](#20-computer-use)
   - [21. Integrations](#21-integrations)
   - [22. Configuration](#22-configuration)
   - [23. CI/CD &amp; Testing](#23-cicd--testing)
   - [24. Utilities](#24-utilities)
   - [25. Life OS — Behavioral Metrics](#25-life-os--behavioral-metrics)
   - [26. Proactive Reasoning / Brain Engine](#26-proactive-reasoning--brain-engine)
   - [27. Vault &amp; Knowledge Intelligence](#27-vault--knowledge-intelligence)
   - [28. Interface Philosophy &amp; Infrastructure Decisions](#28-interface-philosophy--infrastructure-decisions)
   - [29. Miscellaneous / Uncategorized](#29-miscellaneous--uncategorized)
   - [Summary Counts](#summary-counts)
2. [Pi Agent — Complete Atomic Feature Specification](#2-pi-agent--complete-atomic-feature-specification)
3. [Hermes Agent — Complete Atomic Feature Specification](#3-hermes-agent--complete-atomic-feature-specification)
4. [OpenHuman — Complete Atomic Feature Specification](#4-openhuman--complete-atomic-feature-specification)

---

# 1. Full Feature Matrix

> *Source: `full_feature_matrix.md` (July 4th)*

> **Legend**
>
> - ✅ = Implemented in code
> - 📐 = Designed / documented, not yet in code
> - 🔧 = Partial / basic implementation
> - ⬜ = Not present
> - ❌ = Deliberately rejected by design

---

## 1. Agent Core / Runtime

| Feature                                 | Pi                                     | Hermes                                                                 | OpenHuman                                              | Locus                                         |
| --------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------- |
| **Main agent loop**               | ✅ Two-entry (tooled + simple)         | ✅ Conversation loop + background review                               | ✅ Unified turn engine, 5 seams, 3 dispatchers         | ✅ ToolRegistry + LlmProvider                 |
| **Turn context management**       | ✅ Harness state machine               | ✅`turn_context.py` per-turn state                                   | ✅ Fork/memory/sandbox/worktree contexts               | 🔧 Basic request/response                     |
| **Turn retry / error recovery**   | ✅ Retry in agent loop                 | ✅`turn_retry_state.py`                                              | ✅ Self-healing (ToolMaker polyfill, circuit breakers) | ⬜                                            |
| **System prompt builder**         | ✅ Dynamic assembly + skills injection | ✅`system_prompt.py` + `prompt_builder.py`                         | ✅ Built into turn engine                              | 🔧 Static system prompt                       |
| **Prompt caching**                | ✅`openai-prompt-cache.ts`           | ✅`prompt_caching.py`                                                | ⬜                                                     | ⬜                                            |
| **Iteration budget / limits**     | ⬜                                     | ✅`iteration_budget.py`                                              | ✅`token_budget`                                     | ⬜                                            |
| **Background review / post-turn** | ⬜                                     | ✅`background_review.py`                                             | ✅ Post-turn hooks (4 types)                           | 📐 Inner Loop (not post-turn, proactive)      |
| **Stream diagnostics**            | ✅ Event stream utilities              | ✅`stream_diag.py`                                                   | ⬜                                                     | ⬜                                            |
| **Rate limit tracking**           | ⬜                                     | ✅`rate_limit_tracker.py`                                            | ✅ Health probes (30s TTL)                             | ⬜                                            |
| **Usage / cost tracking**         | ⬜                                     | ✅`usage_pricing.py` + `credits_tracker.py` + `account_usage.py` | ✅`cost`, `tokenjuice` modules                     | ⬜                                            |
| **Title generation**              | ⬜                                     | ✅`title_generator.py`                                               | ⬜                                                     | ⬜                                            |
| **Onboarding flow**               | ✅ Project trust prompt                | ✅`onboarding.py`                                                    | ⬜                                                     | ✅ CLI setup wizard + 📐 in-chat setup wizard |
| **Agent initialization**          | ✅`agent-harness.ts`                 | ✅`agent_init.py`                                                    | ✅`app_state`, `startup`                           | ✅`core/agent.py`                           |

---

## 2. LLM Providers

| Feature                                     | Pi                                     | Hermes                                                                                       | OpenHuman                                       | Locus                                   |
| ------------------------------------------- | -------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------- | --------------------------------------- |
| **Provider count**                    | ✅ 10+ APIs, 36+ models                | ✅ 15+ providers                                                                             | ✅ 5 provider types                             | ✅ 1 (DeepSeek V4 Flash — intentional) |
| **OpenAI / OpenAI-compatible**        | ✅ Responses + Completions + Codex     | ✅ Generic adapter                                                                           | ✅`OpenAiCompatible` (BYOK)                   | ✅ via httpx                            |
| **Anthropic**                         | ✅`anthropic.ts`                     | ✅`anthropic_adapter.py`                                                                   | ✅`ClaudeAgentSdk` (subprocess)               | ⬜                                      |
| **Google Gemini**                     | ✅`google.ts` + `google-vertex.ts` | ✅`gemini_native_adapter.py` + `gemini_cloudcode_adapter.py` + `google_code_assist.py` | ⬜                                              | ⬜                                      |
| **AWS Bedrock**                       | ✅`amazon-bedrock.ts`                | ✅`bedrock_adapter.py`                                                                     | ⬜                                              | ⬜                                      |
| **Azure OpenAI**                      | ✅`azure-openai-responses.ts`        | ✅`azure_identity_adapter.py`                                                              | ⬜                                              | ⬜                                      |
| **Cloudflare**                        | ✅`cloudflare.ts`                    | ⬜                                                                                           | ⬜                                              | ⬜                                      |
| **Mistral**                           | ✅`mistral.ts`                       | ⬜                                                                                           | ⬜                                              | ⬜                                      |
| **Moonshot / Kimi**                   | ⬜                                     | ✅`moonshot_schema.py`                                                                     | ⬜                                              | ⬜                                      |
| **LM Studio (local)**                 | ⬜                                     | ✅`lmstudio_reasoning.py`                                                                  | ⬜                                              | ⬜                                      |
| **GitHub Copilot**                    | ✅`github-copilot-headers.ts`        | ⬜                                                                                           | ⬜                                              | ⬜                                      |
| **Intelligent routing (auto-select)** | ⬜                                     | ⬜                                                                                           | ✅`IntelligentRouting` (local+cloud fallback) | ❌ Single-provider by design            |
| **Refusal detection**                 | ⬜                                     | ⬜                                                                                           | ✅ Aho-Corasick DFA                             | ⬜                                      |
| **Provider registry**                 | ✅`api-registry.ts` + auto-register  | ✅`model_metadata.py`                                                                      | ✅`RouterProvider` (hint-based)               | 🔧`resolve_provider()`                |
| **OAuth (device code, PKCE)**         | ✅`oauth.ts`                         | ⬜                                                                                           | ⬜                                              | ⬜                                      |
| **Model list/discovery**              | ✅`--list-models` flag               | ✅`model_metadata.py`                                                                      | ⬜                                              | ⬜                                      |
| **Image generation providers**        | ✅`images.ts` + registry             | ⬜                                                                                           | ⬜                                              | ⬜                                      |
| **Mock / test provider**              | ✅`faux.ts`                          | ⬜                                                                                           | ⬜                                              | ⬜                                      |
| **Streaming (SSE)**                   | ✅`stream.ts` + event stream         | ✅`stream_consumer.py` + `stream_dispatch.py`                                            | ⬜                                              | ⬜                                      |

---

## 3. Tools / Tool Execution

| Feature                              | Pi                               | Hermes                              | OpenHuman                       | Locus                               |
| ------------------------------------ | -------------------------------- | ----------------------------------- | ------------------------------- | ----------------------------------- |
| **File read**                  | ✅`read.ts`                    | ✅ (built-in)                       | ✅ (native dispatcher)          | ✅`read`                          |
| **File write / create**        | ✅`write.ts`                   | ✅ (built-in)                       | ✅ (native dispatcher)          | ✅`write`                         |
| **File edit (precise)**        | ✅`edit.ts` + `edit-diff.ts` | ✅ (built-in)                       | ✅ (native dispatcher)          | ✅`edit` + `edit_file`          |
| **Shell / bash execution**     | ✅`bash.ts`                    | ✅ (built-in)                       | ✅ (sandboxed, 4 backends)      | ✅`run_shell` (blocklist sandbox) |
| **Grep / search files**        | ✅`grep.ts`                    | ✅ (built-in)                       | ✅ (native)                     | ⬜ (uses web_search)                |
| **List directory**             | ✅`ls.ts`                      | ✅ (built-in)                       | ✅ (native)                     | ✅`list_directory`                |
| **Find files**                 | ✅`find.ts`                    | ✅ (built-in)                       | ✅ (native)                     | ⬜                                  |
| **Web search**                 | ⬜                               | ✅ (via plugins)                    | ✅ (web search tools)           | ✅`web_search` (5 providers)      |
| **Web fetch / scrape**         | ⬜                               | ✅ (via plugins)                    | ✅ (web tools)                  | ✅`web_fetch`                     |
| **Git status**                 | ⬜                               | ✅ (built-in)                       | ⬜                              | ✅`git_status`                    |
| **Git diff**                   | ⬜                               | ✅ (built-in)                       | ⬜                              | ✅`git_diff`                      |
| **Git commit**                 | ⬜                               | ✅ (built-in)                       | ⬜                              | ✅`git_commit`                    |
| **System info**                | ⬜                               | ⬜                                  | ⬜                              | ✅`system_info`                   |
| **Tool call validation**       | ✅`tool-definition-wrapper.ts` | ✅`tool_guardrails.py`            | ✅`tool_filter`               | 🔧 Basic validation                 |
| **Tool result classification** | ⬜                               | ✅`tool_result_classification.py` | ⬜                              | ⬜                                  |
| **Tool output accumulator**    | ✅`output-accumulator.ts`      | ⬜                                  | ✅ 16 KiB tool result budget    | ⬜                                  |
| **File mutation queue**        | ✅`file-mutation-queue.ts`     | ⬜                                  | ⬜                              | ⬜                                  |
| **Tool timeout / budget**      | ⬜                               | ⬜                                  | ✅`tool_timeout`              | ⬜                                  |
| **XML tool dispatch**          | ⬜                               | ⬜                                  | ✅`<tool_call>` XmlDispatcher | ⬜                                  |
| **Compact tool dispatch**      | ⬜                               | ⬜                                  | ✅ PFormat dispatcher           | ⬜                                  |

---

## 4. Memory & Persistence

| Feature                                            | Pi                       | Hermes                       | OpenHuman                                      | Locus                                                                             |
| -------------------------------------------------- | ------------------------ | ---------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------- |
| **Primary storage**                          | ✅ JSONL (append-only)   | ✅ SQLite (FTS5)             | ✅ SQLite + JSONL                              | ✅ SQLite (WAL)                                                                   |
| **In-memory backend**                        | ✅`memory-storage.ts`  | ⬜                           | ⬜                                             | ⬜                                                                                |
| **Graph memory**                             | ⬜                       | ⬜                           | ✅`memory_graph`                             | ✅ Neo4j                                                                          |
| **Vector embeddings**                        | ⬜                       | ⬜                           | ✅`embeddings` module                        | ✅ pgvector (📐 PageIndex)                                                        |
| **Full-text search**                         | ⬜                       | ✅ FTS5 session search       | ✅`memory_search`                            | ⬜                                                                                |
| **Memory tree / cascade**                    | ⬜                       | ⬜                           | ✅ Bucket-seal cascade                         | ⬜                                                                                |
| **Entity extraction**                        | ⬜                       | ⬜                           | ✅`memory_entities`                          | 📐 DeepSeek entity extraction → Neo4j                                            |
| **Memory sync**                              | ⬜                       | ⬜                           | ✅`memory_sync`                              | ⬜                                                                                |
| **Memory queue**                             | ⬜                       | ⬜                           | ✅`memory_queue`                             | ⬜                                                                                |
| **Memory diff**                              | ⬜                       | ⬜                           | ✅`memory_diff`                              | ⬜                                                                                |
| **Holographic HRR**                          | ⬜                       | ⬜                           | ⬜                                             | ✅ SHA-256 deterministic vectors, bind/unbind/bundle                              |
| **Hebbian pathway weighting**                | ⬜                       | ⬜                           | ⬜                                             | 📐 Neo4j edge weights (+0.1 traversal, ×1.3/×0.7 feedback, ×0.95 weekly decay) |
| **STDP (Spike-Timing Dependent Plasticity)** | ⬜                       | ⬜                           | ⬜                                             | 📐 Response latency < 2min = ×1.5 reinforcement                                  |
| **Spaced repetition reinforcement**          | ⬜                       | ⬜                           | ⬜                                             | 📐 Nodes near decay + active outcomes → Inner Loop surfaces                      |
| **Project-specific memory decay**            | ⬜                       | ⬜                           | ⬜                                             | 📐 Cypher:`SET r.weight = r.weight * 0.5` on completion                         |
| **User modeling store**                      | ⬜                       | ✅ Honcho dialectic modeling | ✅ Ambient profile facets + stability detector | 📐 User Identity Profile (PG single-row, rolling-average)                         |
| **Memory orchestrator**                      | ⬜                       | ✅`memory_manager.py`      | ✅`memory_store`                             | ✅`memory_manager.py`                                                           |
| **Approval store**                           | ⬜                       | ⬜                           | ✅ Approval gate (10-min TTL)                  | ✅`approval_store.py`                                                           |
| **Session manager**                          | ✅`session-manager.ts` | ✅`gateway/session.py`     | ✅`session_db`                               | ✅`session_manager.py`                                                          |

---

## 5. Sessions

| Feature                            | Pi                                          | Hermes                            | OpenHuman                    | Locus                                          |
| ---------------------------------- | ------------------------------------------- | --------------------------------- | ---------------------------- | ---------------------------------------------- |
| **Session format**           | ✅ Tree-based JSONL (v3, 9 entry types)     | ✅ SQLite sessions                | ✅ JSONL + bucket-seal       | ✅ SQLite (conversations, sessions, documents) |
| **Session branching / fork** | ✅`--fork` flag                           | ⬜                                | ⬜                           | ⬜                                             |
| **Session resume**           | ✅`--resume` / `--continue`             | ✅ Session history                | ⬜                           | ⬜                                             |
| **Session naming**           | ✅`--name` flag                           | ✅`title_generator.py`          | ⬜                           | ⬜                                             |
| **Session picker UI**        | ✅`session-picker.ts`                     | ⬜                                | ⬜                           | ⬜                                             |
| **Session compression**      | ✅ Compaction engine + branch summarization | ✅`conversation_compression.py` | ✅ Microcompact + summarizer | 🔧`compression.py` (basic)                   |
| **Session export**           | ✅ HTML, JSON, MD                           | ✅ Trajectory recording           | ⬜                           | ⬜                                             |
| **No-session mode**          | ✅`--no-session` flag                     | ⬜                                | ⬜                           | ⬜                                             |
| **Custom session directory** | ✅`--session-dir` flag                    | ⬜                                | ⬜                           | ⬜                                             |

---

## 6. Context Management

| Feature                                         | Pi                   | Hermes                                              | OpenHuman                       | Locus                                                                                                             |
| ----------------------------------------------- | -------------------- | --------------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Context window management**             | ✅ Compaction engine | ✅`context_engine.py` + `context_compressor.py` | ✅ Guard (0.90/0.95 thresholds) | 🔧`token_counter.py` only                                                                                       |
| **Context references**                    | ⬜                   | ✅`context_references.py`                         | ⬜                              | ⬜                                                                                                                |
| **Coding-specific context**               | ⬜                   | ✅`coding_context.py`                             | ⬜                              | ⬜                                                                                                                |
| **Manual compression feedback**           | ⬜                   | ✅`manual_compression_feedback.py`                | ⬜                              | ⬜                                                                                                                |
| **Token overflow handling**               | ✅`overflow.ts`    | ✅ (via context compressor)                         | ✅ 16 KiB tool result cap       | 🔧 Basic compactor                                                                                                |
| **Context Forge (multi-source assembly)** | ⬜                   | ⬜                                                  | ⬜                              | 📐 800-token, 6-layer: identity(80t) + temporal(60t) + PG events(180t) + Neo4j(150t) + pgvector(200t) + web(100t) |
| **Query Router / Intent Classifier**      | ⬜                   | ⬜                                                  | ⬜                              | 📐 8 intent types, source routing matrix                                                                          |

---

## 7. TUI / Terminal Interface

| Feature                                | Pi                               | Hermes                    | OpenHuman                         | Locus                                     |
| -------------------------------------- | -------------------------------- | ------------------------- | --------------------------------- | ----------------------------------------- |
| **Full TUI framework**           | ✅ React/Ink component library   | ✅`cli.py` (650K)       | ✅ Tauri desktop + web (React/TS) | ❌ Deliberately rejected                  |
| **Multiline editing**            | ✅ Full editor                   | ✅ Full editor            | ✅`text_input` module           | ❌                                        |
| **Keyboard shortcuts**           | ✅ 15+ configurable keybindings  | ✅ 13+ handlers           | ✅ Keyboard layer                 | ❌                                        |
| **Themes (dark/light/custom)**   | ✅ Theme system                  | ⬜                        | ✅ Dashboard themes               | ❌                                        |
| **Slash command autocomplete**   | ✅`slash-commands.ts`          | ✅ Built into TUI         | ✅`autocomplete` module         | ⬜ (Telegram /commands instead)           |
| **Streaming tool output**        | ✅ Real-time streaming           | ✅ Streaming TUI          | ⬜                                | 🔧`streaming_tui.py` (basic)            |
| **Voice recording in TUI**       | ⬜                               | ✅ Ctrl+R voice recording | ⬜                                | ❌                                        |
| **Paste support**                | ✅ System clipboard              | ✅ Ctrl+V / Alt+V         | ⬜                                | ❌                                        |
| **Editor integration ($EDITOR)** | ⬜                               | ✅ Open-in-editor         | ⬜                                | ❌                                        |
| **Session picker**               | ✅ Interactive session selection | ⬜                        | ⬜                                | ❌                                        |
| **Status bar / footer**          | ✅`footer-data-provider.ts`    | ✅`runtime_footer.py`   | ✅ Dashboard                      | ❌                                        |
| **Provider attribution display** | ✅`provider-attribution.ts`    | ⬜                        | ⬜                                | ❌                                        |
| **Diagnostics UI**               | ✅`diagnostics.ts`             | ✅`hermes doctor`       | ⬜                                | ⬜                                        |
| **Curses fallback TUI**          | ⬜                               | ⬜                        | ⬜                                | 🔧`curses_ui.py` exists but not primary |

---

## 8. CLI

| Feature                         | Pi                                                  | Hermes                              | OpenHuman                 | Locus                                                               |
| ------------------------------- | --------------------------------------------------- | ----------------------------------- | ------------------------- | ------------------------------------------------------------------- |
| **CLI flags count**       | ✅ 39 flags                                         | ✅ 13+ keyboard handlers            | ✅ JSON-RPC + CLI         | ✅ 18 CLI commands                                                  |
| **Run modes**             | ✅ Interactive, Print, RPC, JSON                    | ✅ CLI, Gateway                     | ✅ Desktop, Web, CLI, MCP | ✅ CLI, Gateway                                                     |
| **Batch mode (one-shot)** | ✅`--print` flag                                  | ⬜                                  | ⬜                        | ⬜                                                                  |
| **RPC / daemon mode**     | ✅ JSON-RPC protocol                                | ⬜                                  | ✅ JSON-RPC               | ⬜                                                                  |
| **Self-update**           | ✅`version-check.ts` + `windows-self-update.ts` | ✅`hermes update`                 | ✅`update` module       | ⬜                                                                  |
| **Doctor / diagnostics**  | ⬜                                                  | ✅`hermes doctor`                 | ✅`doctor` module       | ⬜                                                                  |
| **Config management**     | ✅`config.ts` + migrations                        | ✅`cli-config.yaml`               | ✅ ~70 schema files       | ✅`locus config show/set/path/env-path/check/migrate`             |
| **Gateway lifecycle**     | ⬜                                                  | ✅`hermes gateway run/start/stop` | ⬜                        | ✅`locus gateway run/start/stop/restart/status/install/uninstall` |
| **Setup wizard**          | ✅ Project trust prompt                             | ✅`onboarding.py`                 | ⬜                        | ✅`locus setup` + `locus setup gateway`                         |

---

## 9. Extensions / Plugins / Skills

| Feature                            | Pi                                               | Hermes                                                                   | OpenHuman                                | Locus                 |
| ---------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------ | ---------------------------------------- | --------------------- |
| **Extension system**         | ✅ Loader, runner, wrapper, 25+ lifecycle events | ⬜ (uses ACP + skills instead)                                           | ⬜ (uses MCP registry)                   | ⬜                    |
| **Skills system**            | ✅ SKILL.md frontmatter discovery                | ✅ Skill bundles, commands, preprocessing, 15 categories                 | ✅`skill_registry` + `skill_runtime` | ⬜                    |
| **Skills marketplace**       | ⬜                                               | ✅ 4 marketplace indexes (Anthropic, Claude, LobeHub, OpenAI)            | ✅ Smithery.ai dynamic install           | ⬜                    |
| **Prompt templates**         | ✅`prompt-templates.ts`                        | ⬜                                                                       | ⬜                                       | ⬜                    |
| **ACP protocol**             | ⬜                                               | ✅ Full ACP adapter (server, session, auth, approval, provenance, tools) | ⬜                                       | ⬜                    |
| **Plugin LLM**               | ⬜                                               | ✅`plugin_llm.py`                                                      | ⬜                                       | ⬜                    |
| **Register custom tools**    | ✅ Via extensions                                | ✅ Via skills                                                            | ✅ Via MCP registry                      | ⬜                    |
| **Register custom commands** | ✅ Via extensions                                | ✅ Via skill commands                                                    | ⬜                                       | ✅ Telegram /commands |
| **Context file loading**     | ✅ AGENTS.md, CLAUDE.md auto-discovery           | ⬜                                                                       | ⬜                                       | ✅ SOUL.md            |

---

## 10. Learning & Self-Improvement

| Feature                                   | Pi | Hermes                                       | OpenHuman                                                            | Locus                                                                                          |
| ----------------------------------------- | -- | -------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Post-session learning**           | ⬜ | ✅ Curator → insights → memory nudge       | ✅ Post-turn hooks (Archivist, Reflection, ToolTracker, UserProfile) | 🔧`reflector.py` (basic LLM reflection)                                                      |
| **Cross-session search / recall**   | ⬜ | ✅ FTS5 full-text search + LLM summarization | ✅`memory_search`                                                  | ⬜                                                                                             |
| **User profile building**           | ⬜ | ✅ Honcho dialectic modeling                 | ✅ Ambient profile facets + PROFILE.md injection                     | 📐 User Identity Profile (behavioral tendencies, peak windows, stressors, communication style) |
| **Stability detection**             | ⬜ | ⬜                                           | ✅ Stability detector (30min)                                        | ⬜                                                                                             |
| **Tool usage tracking**             | ⬜ | ⬜                                           | ✅`ToolTrackerHook`                                                | ✅`tool_tracker.py`                                                                          |
| **Personal Reward Model**           | ⬜ | ⬜                                           | ⬜                                                                   | 📐 sklearn LogisticRegression (👍/👎 feedback, weekly retrain, ≥0.6 threshold)                |
| **Hebbian learning rules**          | ⬜ | ⬜                                           | ⬜                                                                   | 📐 Neo4j edge weights with biological decay, STDP reinforcement                                |
| **Multi-horizon pattern detection** | ⬜ | ⬜                                           | ⬜                                                                   | 📐 5 horizons (H1: 6h, H2: 24h, H3: 7d, H4: 30d, H5: all-time)                                 |
| **Self-evolving Architect Bot**     | ⬜ | ⬜                                           | ⬜                                                                   | 📐 Scans reward signals, generates patches, risk-gated deploy                                  |
| **Agent experience tracking**       | ⬜ | ⬜                                           | ✅`agent_experience` module                                        | ⬜                                                                                             |

---

## 11. Subagents / Delegation

| Feature                            | Pi                           | Hermes                                         | OpenHuman                                                        | Locus                                                        |
| ---------------------------------- | ---------------------------- | ---------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------ |
| **Subagent spawning**        | ✅ Built-in subagent tool    | ✅`agent_init.py` + `process_bootstrap.py` | ✅ 3-tier hierarchy                                              | 🔧`delegation/subagent.py`                                 |
| **Subagent archetypes**      | ⬜                           | ⬜                                             | ✅ 15 built-in (orchestrator, planner, researcher, critic, etc.) | 📐 4 faction sub-agents (Planner, Curator, Analyst, Builder) |
| **Depth limiting**           | ⬜                           | ⬜                                             | ✅ MAX_SPAWN_DEPTH=3                                             | ⬜                                                           |
| **RPC-based subagents**      | ✅ RPC mode                  | ✅`codex_runtime.py` (RPC)                   | ⬜                                                               | ⬜                                                           |
| **Coding agent**             | ✅ Full coding agent package | ⬜                                             | ✅`code_executor` archetype                                    | 🔧`delegation/coding_agent.py`                             |
| **ACP client for subagents** | ⬜                           | ✅`copilot_acp_client.py`                    | ⬜                                                               | ⬜                                                           |

---

## 12. Scheduling & Cron

| Feature                                      | Pi | Hermes                                           | OpenHuman                               | Locus                                                               |
| -------------------------------------------- | -- | ------------------------------------------------ | --------------------------------------- | ------------------------------------------------------------------- |
| **Cron / scheduled tasks**             | ⬜ | ✅ Natural language cron scheduling              | ✅`cron` + `scheduler_gate` modules | ✅`cron_runner.py`                                                |
| **Task sources**                       | ⬜ | ⬜                                               | ✅`task_sources` module               | ✅`scheduler/task_sources.py`                                     |
| **Scheduled automations**              | ⬜ | ✅ Daily reports, nightly backups, weekly audits | ✅ Via cron module                      | 📐 Nightly vault ingestion, weekly synthesis, daily check-ins       |
| **Inner Loop (proactive, unprompted)** | ⬜ | ⬜                                               | ⬜                                      | 📐 APScheduler every 90min (07:00–00:00), fires without user input |
| **Structured check-in reminders**      | ⬜ | ⬜                                               | ⬜                                      | 📐 07:30/13:00/18:00/22:00 IST → Telegram inline keyboards         |
| **Heartbeat / notification**           | ⬜ | ⬜                                               | ✅`heartbeat` module                  | ✅`heartbeat/notification.py` + `subconscious.py`               |

---

## 13. Security & Sandboxing

| Feature                               | Pi                       | Hermes                        | OpenHuman                                     | Locus                                |
| ------------------------------------- | ------------------------ | ----------------------------- | --------------------------------------------- | ------------------------------------ |
| **Project trust management**    | ✅`trust-manager.ts`   | ⬜                            | ⬜                                            | ⬜                                   |
| **Shell command blocklist**     | ⬜                       | ⬜                            | ✅ Policy engine (command classification)     | ✅`shell_exec.py` BLOCKED_PATTERNS |
| **File safety checks**          | ⬜                       | ✅`file_safety.py`          | ✅`file_state`, `cwd_jail`                | ⬜                                   |
| **Sandbox backends**            | ⬜                       | ⬜                            | ✅ 4 (bubblewrap, docker, firejail, landlock) | ⬜                                   |
| **Autonomy tiers**              | ⬜                       | ⬜                            | ✅ readonly / supervised / full               | ⬜                                   |
| **Approval gate**               | ⬜                       | ✅ ACP edit approval          | ✅ 10-min TTL approval gate                   | ✅`approval_store.py`              |
| **Data redaction**              | ⬜                       | ✅`redact.py`               | ⬜                                            | ⬜                                   |
| **Prompt injection protection** | ⬜                       | ⬜                            | ✅`prompt_injection` module                 | ⬜                                   |
| **Think token scrubbing**       | ⬜                       | ✅`think_scrubber.py`       | ⬜                                            | ⬜                                   |
| **Message sanitization**        | ⬜                       | ✅`message_sanitization.py` | ⬜                                            | ⬜                                   |
| **Secret prompt encryption**    | ⬜                       | ⬜                            | ⬜                                            | ✅`secret_prompt.py`               |
| **Proxy support**               | ✅`node-http-proxy.ts` | ⬜                            | ✅`proxy` config                            | ✅`proxy.py`                       |
| **Encryption / keyring**        | ⬜                       | ⬜                            | ✅`encryption`, `keyring` modules         | ⬜                                   |
| **TLS**                         | ⬜                       | ⬜                            | ✅`tls` module                              | ⬜                                   |

---

## 14. Voice

| Feature                          | Pi | Hermes           | OpenHuman                 | Locus                                                                  |
| -------------------------------- | -- | ---------------- | ------------------------- | ---------------------------------------------------------------------- |
| **STT (Speech-to-Text)**   | ⬜ | ✅ Via plugins   | ✅ Voice inference module | ✅ 4 backends (Whisper local, Azure, Groq, OpenAI)                     |
| **TTS (Text-to-Speech)**   | ⬜ | ✅ Via plugins   | ✅ Voice inference module | ✅ 4 backends (Edge TTS, ElevenLabs, OpenAI, Piper)                    |
| **Voice recording in-app** | ⬜ | ✅ Ctrl+R in TUI | ⬜                        | ⬜                                                                     |
| **Voice call interface**   | ⬜ | ⬜               | ⬜                        | 📐 Audio → Groq Whisper → pipeline → Kokoro TTS → vault transcript |
| **Dictation**              | ⬜ | ⬜               | ✅`dictation` module    | ✅`dictation.py`                                                     |

---

## 15. Web Search

| Feature                         | Pi | Hermes         | OpenHuman           | Locus          |
| ------------------------------- | -- | -------------- | ------------------- | -------------- |
| **Search provider count** | ⬜ | ✅ Via plugins | ✅`search` module | ✅ 5 providers |
| **Brave Search**          | ⬜ | ⬜             | ⬜                  | ✅             |
| **Exa**                   | ⬜ | ⬜             | ⬜                  | ✅             |
| **Firecrawl**             | ⬜ | ⬜             | ⬜                  | ✅             |
| **SearXNG**               | ⬜ | ⬜             | ⬜                  | ✅             |
| **Tavily**                | ⬜ | ⬜             | ⬜                  | ✅             |

---

## 16. Browser Automation

| Feature                            | Pi | Hermes              | OpenHuman                        | Locus                                                         |
| ---------------------------------- | -- | ------------------- | -------------------------------- | ------------------------------------------------------------- |
| **Browser automation**       | ⬜ | ✅ Browser provider | ✅`screen_intelligence` module | ✅ Playwright (`browserbase.py`, `playwright_backend.py`) |
| **Screenshot**               | ⬜ | ⬜                  | ✅ Screen intelligence           | ✅`screenshot.py`                                           |
| **Vision / screen analysis** | ⬜ | ⬜                  | ✅ Screen intelligence + overlay | ✅`vision.py`                                               |

---

## 17. Channels / Gateway / Messaging

| Feature                                    | Pi                   | Hermes                      | OpenHuman             | Locus                                              |
| ------------------------------------------ | -------------------- | --------------------------- | --------------------- | -------------------------------------------------- |
| **Telegram**                         | ⬜                   | ✅ Via gateway adapter      | ⬜                    | ✅ Primary interface (PTB, auth, inline keyboards) |
| **Discord**                          | ⬜                   | ✅ Via gateway adapter      | ⬜                    | ✅ Channel module                                  |
| **Slack**                            | ⬜                   | ✅ Via gateway adapter      | ⬜                    | ✅ Channel module                                  |
| **WhatsApp**                         | ⬜                   | ✅`whatsapp_identity.py`  | ⬜                    | ✅ Channel module                                  |
| **Signal**                           | ⬜                   | ✅ Via`apps/shared`       | ⬜                    | ✅ Channel module                                  |
| **IRC**                              | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **Matrix**                           | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **Mattermost**                       | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **Teams**                            | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **Lark**                             | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **DingTalk**                         | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **Google Chat**                      | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **Email**                            | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **iMessage**                         | ⬜                   | ⬜                          | ⬜                    | ✅ Channel module                                  |
| **CLI / Terminal**                   | ✅ Primary interface | ✅`cli.py`                | ✅ CLI mode           | ✅ Basic CLI                                       |
| **Desktop app**                      | ⬜                   | ✅ Electron (38+ modules)   | ✅ Tauri v2 desktop   | ❌ Deliberately rejected                           |
| **Web interface**                    | ⬜                   | ⬜                          | ✅ React/TS web app   | ⬜                                                 |
| **Platform registry**                | ⬜                   | ✅`platform_registry.py`  | ✅`channels` module | ✅ Platform registry                               |
| **Cross-platform message mirroring** | ⬜                   | ✅`mirror.py`             | ⬜                    | ⬜                                                 |
| **Channel-specific display config**  | ⬜                   | ✅`display_config.py`     | ⬜                    | ⬜                                                 |
| **Device pairing**                   | ⬜                   | ✅`pairing.py`            | ✅`devices` module  | ⬜                                                 |
| **Sticker / media cache**            | ⬜                   | ✅`sticker_cache.py`      | ⬜                    | ⬜                                                 |
| **Graceful restart**                 | ⬜                   | ✅`restart.py`            | ⬜                    | ⬜                                                 |
| **Shutdown forensics**               | ⬜                   | ✅`shutdown_forensics.py` | ⬜                    | ⬜                                                 |
| **Kanban watchers**                  | ⬜                   | ✅`kanban_watchers.py`    | ⬜                    | ⬜                                                 |
| **Memory monitor**                   | ⬜                   | ✅`memory_monitor.py`     | ⬜                    | ⬜                                                 |
| **Gateway hooks**                    | ⬜                   | ✅`hooks.py`              | ⬜                    | ⬜                                                 |
| **Slash access control**             | ⬜                   | ✅`slash_access.py`       | ⬜                    | ⬜                                                 |

---

## 18. MCP (Model Context Protocol)

| Feature                | Pi                      | Hermes           | OpenHuman                                      | Locus                                                      |
| ---------------------- | ----------------------- | ---------------- | ---------------------------------------------- | ---------------------------------------------------------- |
| **MCP client**   | ⬜ (extensions instead) | ⬜ (ACP instead) | ✅ HTTP + stdio, protocol 2024–2025           | ✅`mcp_client.py`                                        |
| **MCP server**   | ⬜                      | ⬜               | ✅ Axum HTTP + SSE                             | ⬜                                                         |
| **MCP registry** | ⬜                      | ⬜               | ✅ Dynamic install, Smithery.ai, 60s reconnect | ⬜                                                         |
| **MCP audit**    | ⬜                      | ⬜               | ✅`mcp_audit`                                | ⬜                                                         |
| **Obsidian MCP** | ⬜                      | ⬜               | ⬜                                             | 📐 vault_read/write/search/tag/stats (localhost, .md only) |

---

## 19. Export & Artifacts

| Feature                           | Pi                      | Hermes                           | OpenHuman | Locus                                                |
| --------------------------------- | ----------------------- | -------------------------------- | --------- | ---------------------------------------------------- |
| **HTML session export**     | ✅`export-html/`      | ⬜                               | ⬜        | ⬜                                                   |
| **JSON session export**     | ✅ Via`--export json` | ⬜                               | ⬜        | ⬜                                                   |
| **Markdown session export** | ✅ Via`--export md`   | ⬜                               | ⬜        | ⬜                                                   |
| **Trajectory recording**    | ⬜                      | ✅`trajectory.py` (1321 lines) | ⬜        | ⬜                                                   |
| **ANSI → HTML conversion** | ✅`ansi-to-html.ts`   | ⬜                               | ⬜        | ⬜                                                   |
| **Daily AI Chat Archiver**  | ⬜                      | ⬜                               | ⬜        | 📐 Nightly 23:45 Telegram → vault .md → git commit |

---

## 20. Computer Use

| Feature                                | Pi | Hermes | OpenHuman                             | Locus            |
| -------------------------------------- | -- | ------ | ------------------------------------- | ---------------- |
| **Native desktop control**       | ⬜ | ⬜     | ✅`desktop_companion` + `overlay` | ✅`native.py`  |
| **VNC remote control**           | ⬜ | ⬜     | ⬜                                    | ✅`vnc.py`     |
| **Screen capture**               | ⬜ | ⬜     | ✅`screen_intelligence`             | ✅`capture.py` |
| **Screen intelligence / vision** | ⬜ | ⬜     | ✅`screen_intelligence`             | ✅`vision.py`  |

---

## 21. Integrations

| Feature                      | Pi | Hermes | OpenHuman                                      | Locus                                              |
| ---------------------------- | -- | ------ | ---------------------------------------------- | -------------------------------------------------- |
| **Composio**           | ⬜ | ⬜     | ✅`integrations` module                      | ✅`composio.py` (📐 replacing with manual OAuth) |
| **Polymarket**         | ⬜ | ⬜     | ⬜                                             | ✅`polymarket.py`                                |
| **Webhooks**           | ⬜ | ⬜     | ✅`webhooks` module                          | ✅`webhooks.py`                                  |
| **Google Calendar**    | ⬜ | ⬜     | ⬜                                             | 📐 Manual OAuth integration                        |
| **Gmail**              | ⬜ | ⬜     | ⬜                                             | 📐 Manual OAuth integration                        |
| **Calendly**           | ⬜ | ⬜     | ⬜                                             | 📐 Via setup wizard                                |
| **Web3 / wallet**      | ⬜ | ⬜     | ✅`wallet`, `web3`, `x402` modules       | ⬜                                                 |
| **Billing**            | ⬜ | ⬜     | ✅`billing` module                           | ⬜                                                 |
| **Meet / video calls** | ⬜ | ⬜     | ✅`meet`, `meet_agent`, `agent_meetings` | ⬜                                                 |
| **Team collaboration** | ⬜ | ⬜     | ✅`team`, `people` modules                 | ⬜                                                 |
| **Referral system**    | ⬜ | ⬜     | ✅`referral` module                          | ⬜                                                 |

---

## 22. Configuration

| Feature                                   | Pi                    | Hermes                | OpenHuman                               | Locus                              |
| ----------------------------------------- | --------------------- | --------------------- | --------------------------------------- | ---------------------------------- |
| **Config format**                   | ✅ YAML/JSON          | ✅`cli-config.yaml` | ✅ ~70 JSON schema files                | ✅ SETTINGS.md (56KB, 28 sections) |
| **Config migration**                | ✅`migrations.ts`   | ⬜                    | ✅`migration`, `migrations` modules | ✅`locus config migrate`         |
| **Environment variable management** | ✅`env-api-keys.ts` | ⬜                    | ⬜                                      | ✅`locus config env-path`        |
| **Config section count**            | ~10                   | ~5                    | ~70 schema files                        | 28 sections                        |

---

## 23. CI/CD & Testing

| Feature                           | Pi                | Hermes                                                    | OpenHuman                                    | Locus |
| --------------------------------- | ----------------- | --------------------------------------------------------- | -------------------------------------------- | ----- |
| **Unit tests**              | ✅ Vitest         | ✅ pytest                                                 | ✅ cargo test                                | ⬜    |
| **CI pipeline**             | ✅ GitHub Actions | ✅ Full CI (lint, test, typecheck, docker, nix, security) | ✅ Full CI (build, test, deploy, e2e, smoke) | ⬜    |
| **Linting**                 | ✅ ESLint         | ✅ Ruff/flake8                                            | ✅ clippy                                    | ⬜    |
| **Type checking**           | ✅ TypeScript     | ✅ mypy                                                   | ✅ Rust compiler                             | ⬜    |
| **Docker**                  | ⬜                | ✅ Docker builds                                          | ✅ Docker builds                             | ⬜    |
| **Nix**                     | ⬜                | ✅ Nix flake                                              | ⬜                                           | ⬜    |
| **Batch trajectory runner** | ⬜                | ✅`trajectory.py` (1321 lines)                          | ⬜                                           | ⬜    |

---

## 24. Utilities

| Feature                              | Pi                                           | Hermes              | OpenHuman          | Locus                              |
| ------------------------------------ | -------------------------------------------- | ------------------- | ------------------ | ---------------------------------- |
| **Clipboard**                  | ✅`clipboard.ts` + native + image          | ⬜                  | ⬜                 | ⬜                                 |
| **Git integration**            | ✅`git.ts`                                 | ✅ (built-in tools) | ⬜                 | ✅`git_ops.py`                   |
| **Image handling**             | ✅ Resize, convert, EXIF orientation, Photon | ⬜                  | ✅`image` module | ⬜                                 |
| **Syntax highlighting**        | ✅`syntax-highlight.ts` + highlight.js     | ⬜                  | ⬜                 | ⬜                                 |
| **MIME detection**             | ✅`mime.ts`                                | ⬜                  | ⬜                 | ⬜                                 |
| **Open browser**               | ✅`open-browser.ts`                        | ⬜                  | ⬜                 | ⬜                                 |
| **ANSI escape handling**       | ✅`ansi.ts`                                | ⬜                  | ⬜                 | ⬜                                 |
| **Shell integration**          | ✅`shell.ts`                               | ⬜                  | ⬜                 | ⬜                                 |
| **Frontmatter parser**         | ✅`frontmatter.ts`                         | ⬜                  | ⬜                 | ⬜                                 |
| **File system watcher**        | ✅`fs-watch.ts`                            | ⬜                  | ⬜                 | ⬜                                 |
| **Unicode sanitization**       | ✅`sanitize-unicode.ts`                    | ⬜                  | ⬜                 | ⬜                                 |
| **JSON safe parsing**          | ✅`json-parse.ts`                          | ⬜                  | ⬜                 | ⬜                                 |
| **Schema validation**          | ✅ TypeBox helpers                           | ⬜                  | ⬜                 | ⬜                                 |
| **Colors / output formatting** | ⬜                                           | ⬜                  | ⬜                 | ✅`colors.py`, `cli_output.py` |
| **Slash commands handler**     | ⬜                                           | ⬜                  | ⬜                 | ✅`slash_commands.py`            |
| **SSH deployment**             | ⬜                                           | ⬜                  | ⬜                 | ✅`deployment` module            |

---

## 25. Life OS — Behavioral Metrics *(Locus-only domain)*

| Feature                               | Pi | Hermes | OpenHuman | Locus                                                                          |
| ------------------------------------- | -- | ------ | --------- | ------------------------------------------------------------------------------ |
| **Four Factions Framework**     | ⬜ | ⬜     | ⬜        | 📐 Health/Leverage/Craft/Expression with weekly hour targets                   |
| **Daily Capacity Score (DCS)**  | ⬜ | ⬜     | ⬜        | 📐`((E+M+S)/3) × (1−ST/20)` → 5 operating modes                           |
| **Five Operating Modes**        | ⬜ | ⬜     | ⬜        | 📐 SURVIVAL / RECOVERY / NORMAL / DEEP_WORK / PEAK                             |
| **Task Weight Score (TWS)**     | ⬜ | ⬜     | ⬜        | 📐`(P×0.4)+(U×0.4)+(D×0.2)` sorting key                                   |
| **Three-Layer Goal Stack**      | ⬜ | ⬜     | ⬜        | 📐 Outcomes (max 7) → Projects (max 3/faction) → Tasks                       |
| **Action Gap Tracking**         | ⬜ | ⬜     | ⬜        | 📐 declared_priority − actual performance metric                              |
| **Deferral Detection (3/5/8+)** | ⬜ | ⬜     | ⬜        | 📐 Progressive alerts: flag → Telegram → Inner Loop                          |
| **Lag Score + TWS Lag Bonus**   | ⬜ | ⬜     | ⬜        | 📐 Lagging faction TWS +2/+4, ahead faction −1                                |
| **Emergency Task Injection**    | ⬜ | ⬜     | ⬜        | 📐 TWS comparison,`is_locked` protection                                     |
| **Exhaustion Predictor**        | ⬜ | ⬜     | ⬜        | 📐 5-day difficulty vs DCS average → load reduction                           |
| **Weekly Faction Rebalance**    | ⬜ | ⬜     | ⬜        | 📐 Starving faction gets priority boost                                        |
| **Cross-Faction Efficiency**    | ⬜ | ⬜     | ⬜        | 📐 Multi-faction tasks get TWS +1/extra faction                                |
| **Review Cadence System**       | ⬜ | ⬜     | ⬜        | 📐 Daily(7min)/Weekly(30-45min)/Monthly(60min)/Quarterly(2-3hrs)               |
| **Goal Stack Enforcement**      | ⬜ | ⬜     | ⬜        | 📐 Dead node detection (60d), stall detection (CR<20% @ 30d)                   |
| **6-Step Scheduling Algorithm** | ⬜ | ⬜     | ⬜        | 📐 Non-negotiables → DCS filter → lag bonus → TWS sort → balance → assign |
| **4-Level Emergency Protocol**  | ⬜ | ⬜     | ⬜        | 📐 Disruption classification, 2-week recovery rule                             |

---

## 26. Proactive Reasoning / Brain Engine *(Locus-only domain)*

| Feature                                       | Pi | Hermes | OpenHuman | Locus                                                                    |
| --------------------------------------------- | -- | ------ | --------- | ------------------------------------------------------------------------ |
| **Inner Loop (Proactive Thinker)**      | ⬜ | ⬜     | ⬜        | 📐 Every 90min, unprompted reasoning, Reward Model gate                  |
| **State Engine + Inferred Cause Chain** | ⬜ | ⬜     | ⬜        | 📐 Psychological + operational state + causal explanation                |
| **Multi-Horizon Pattern Engine**        | ⬜ | ⬜     | ⬜        | 📐 H1(6h)–H5(all-time), confidence-based promotion                      |
| **Context Forge**                       | ⬜ | ⬜     | ⬜        | 📐 800-token 6-layer assembler (identity/temporal/PG/Neo4j/pgvector/web) |
| **Query Router / Intent Classifier**    | ⬜ | ⬜     | ⬜        | 📐 8 intent types, source routing matrix                                 |
| **Inferred Cause Chain Engine**         | ⬜ | ⬜     | ⬜        | 📐 Cross-reference state+patterns+history → causal explanation          |
| **Personality + "Wants" Engine**        | ⬜ | ⬜     | ⬜        | 📐 SOUL.md rules + WantNodes in Neo4j                                    |
| **Weekly Full Vault Synthesis**         | ⬜ | ⬜     | ⬜        | 📐 Sunday 02:00, personality drift + faction narrative                   |

---

## 27. Vault & Knowledge Intelligence *(Locus-only domain)*

| Feature                                    | Pi | Hermes | OpenHuman | Locus                                                                           |
| ------------------------------------------ | -- | ------ | --------- | ------------------------------------------------------------------------------- |
| **PageIndex (whole-note embedding)** | ⬜ | ⬜     | ⬜        | 📐 200-800 word notes embedded whole, long chats chunked at sentence boundaries |
| **Nightly Vault Ingestion Pipeline** | ⬜ | ⬜     | ⬜        | 📐 Multi-account Playwright scraping (ChatGPT×3, Claude, Gemini, Perplexity)   |
| **LOCUS_SHORTHAND**                  | ⬜ | ⬜     | ⬜        | 📐 ~4× token compression, dedicated encode/decode                              |
| **Obsidian as Primary Dashboard**    | ⬜ | ⬜     | ⬜        | 📐 8 panels via Dataview/Charts, replaces PWA                                   |
| **3-Level Tag Hierarchy**            | ⬜ | ⬜     | ⬜        | 📐 faction/domain/specific, PG tag registry                                     |
| **Rough Note Parser / Idea Tracker** | ⬜ | ⬜     | ⬜        | 📐 /idea → expand → promote/research/archive                                  |
| **Link Dump / Resource Logger**      | ⬜ | ⬜     | ⬜        | 📐 /link → captures table → vault note                                        |
| **Excalidraw MCP Skill**             | ⬜ | ⬜     | ⬜        | 📐 Autonomous diagram generation via MCP                                        |

---

## 28. Interface Philosophy & Infrastructure Decisions *(Locus-only domain)*

| Feature                                     | Pi | Hermes | OpenHuman | Locus                                                               |
| ------------------------------------------- | -- | ------ | --------- | ------------------------------------------------------------------- |
| **Telegram-native headless**          | ⬜ | ⬜     | ⬜        | ✅ Primary interface is Telegram, no GUI/TUI                        |
| **4 Daily Structured Check-ins**      | ⬜ | ⬜     | ⬜        | 📐 Morning/Afternoon/Evening/Night via inline keyboards             |
| **Voice Call Interface**              | ⬜ | ⬜     | ⬜        | 📐 Groq Whisper → pipeline → Kokoro TTS → vault transcript       |
| **Obsidian Dashboard replaces PWA**   | ⬜ | ⬜     | ⬜        | 📐 PWA explicitly removed from architecture                         |
| **Git for vault sync**                | ⬜ | ⬜     | ⬜        | 📐 Directory partitioning (backend vs user writes)                  |
| **Manual Google OAuth**               | ⬜ | ⬜     | ⬜        | 📐 50 lines, replacing Composio                                     |
| **pgvector replaces Qdrant+ChromaDB** | ⬜ | ⬜     | ⬜        | 📐 <50K vectors, one fewer container                                |
| **Redis optional**                    | ⬜ | ⬜     | ⬜        | 📐 PG + in-memory dict at single-user scale                         |
| **DeepSeek V4 Flash only**            | ⬜ | ⬜     | ⬜        | ✅ ~$0.012/day, ~$4/year — architectural decision                  |
| **Zero-cost 1st-class constraint**    | ⬜ | ⬜     | ⬜        | ✅ $5 credit → ~416 days                                           |
| **Minimum AI in harness**             | ⬜ | ⬜     | ⬜        | ✅ LLM only for reasoning/generation, deterministic logic elsewhere |

---

## 29. Miscellaneous / Uncategorized

| Feature                              | Pi                                           | Hermes                           | OpenHuman                                 | Locus                                 |
| ------------------------------------ | -------------------------------------------- | -------------------------------- | ----------------------------------------- | ------------------------------------- |
| **Telemetry**                  | ✅`telemetry.ts`                           | ⬜                               | ✅`observability` config                | ⬜                                    |
| **Experimental features flag** | ✅`experimental.ts`                        | ⬜                               | ⬜                                        | ⬜                                    |
| **Auth storage**               | ✅`auth-storage.ts` + `auth-guidance.ts` | ✅`authz_mixin.py`             | ✅`keyring`                             | ⬜                                    |
| **Resource loader**            | ✅`resource-loader.ts`                     | ⬜                               | ⬜                                        | ⬜                                    |
| **Error classifier**           | ⬜                                           | ✅`error_classifier.py`        | ⬜                                        | ⬜                                    |
| **Auxiliary LLM client**       | ⬜                                           | ✅`auxiliary_client.py`        | ✅`model_council`                       | ⬜                                    |
| **Model council / committee**  | ⬜                                           | ⬜                               | ✅`council_registry`, `model_council` | ⬜                                    |
| **Accessibility**              | ⬜                                           | ⬜                               | ✅`accessibility` module                | ⬜                                    |
| **Connectivity checks**        | ⬜                                           | ⬜                               | ✅`connectivity` module                 | ⬜                                    |
| **Code graph analysis**        | ⬜                                           | ⬜                               | ✅`codegraph` module                    | ⬜                                    |
| **Runtime JS/Python**          | ⬜                                           | ⬜                               | ✅`runtime_node`, `runtime_python`    | ⬜                                    |
| **About app**                  | ⬜                                           | ⬜                               | ✅`about_app` module                    | ⬜                                    |
| **Workflows**                  | ⬜                                           | ⬜                               | ✅`workflows` module                    | ⬜                                    |
| **Health checks**              | ⬜                                           | ✅`gateway/status.py`          | ✅`health` module                       | ⬜                                    |
| **Notifications**              | ⬜                                           | ⬜                               | ✅`notifications` module                | ✅`heartbeat/notification.py`       |
| **Socket/WebSocket**           | ⬜                                           | ✅`gateway/stream_consumer.py` | ✅`socket` module                       | ⬜                                    |
| **Redirect links**             | ⬜                                           | ⬜                               | ✅`redirect_links` module               | ⬜                                    |
| **Provider surfaces**          | ⬜                                           | ⬜                               | ✅`provider_surfaces` module            | ⬜                                    |
| **Service orchestration**      | ⬜                                           | ⬜                               | ✅`service` module                      | ⬜                                    |
| **Workspace management**       | ⬜                                           | ⬜                               | ✅`workspace` module                    | ⬜                                    |
| **Agent tool policy**          | ⬜                                           | ⬜                               | ✅`agent_tool_policy` module            | ⬜                                    |
| **Test support**               | ⬜                                           | ⬜                               | ✅`test_support` module                 | ⬜                                    |
| **Subconscious background**    | ⬜                                           | ⬜                               | ✅`subconscious` module                 | ✅`subconscious.py` + 📐 Inner Loop |

---

## Summary Counts

| Category             | Pi | Hermes | OpenHuman | Locus (✅+🔧) | Locus (📐 designed) |
| -------------------- | -- | ------ | --------- | ------------- | ------------------- |
| Agent Core           | 9  | 16     | 8         | 4             | 1                   |
| LLM Providers        | 15 | 12     | 5         | 2             | 0                   |
| Tools                | 11 | 11     | 13        | 10            | 0                   |
| Memory               | 4  | 5      | 10        | 5             | 5                   |
| Sessions             | 8  | 3      | 2         | 1             | 0                   |
| Context              | 2  | 4      | 3         | 1             | 2                   |
| TUI                  | 12 | 12     | 5         | 1             | 0                   |
| CLI                  | 6  | 5      | 4         | 5             | 0                   |
| Extensions/Skills    | 5  | 6      | 3         | 1             | 0                   |
| Learning             | 0  | 3      | 5         | 2             | 3                   |
| Subagents            | 3  | 3      | 3         | 1             | 1                   |
| Scheduling           | 0  | 2      | 3         | 2             | 3                   |
| Security             | 2  | 4      | 8         | 3             | 0                   |
| Voice                | 0  | 2      | 2         | 3             | 1                   |
| Search               | 0  | 1      | 1         | 5             | 0                   |
| Browser              | 0  | 1      | 2         | 3             | 0                   |
| Channels             | 2  | 15     | 5         | 16            | 0                   |
| MCP                  | 0  | 0      | 4         | 1             | 1                   |
| Export               | 4  | 1      | 0         | 0             | 1                   |
| Computer Use         | 0  | 0      | 2         | 4             | 0                   |
| Life OS Metrics      | 0  | 0      | 0         | 0             | 16                  |
| Brain Engine         | 0  | 0      | 0         | 0             | 8                   |
| Vault Intelligence   | 0  | 0      | 0         | 0             | 8                   |
| Interface Philosophy | 0  | 0      | 0         | 4             | 7                   |

**Totals**:

- **Pi**: ~83 implemented features
- **Hermes**: ~106 implemented features
- **OpenHuman**: ~87 implemented features
- **Locus (code)**: ~73 implemented features
- **Locus (design)**: ~57 additional designed features → **130 total when built**

---

---

# 2. Pi Agent — Complete Atomic Feature Specification

> *Source: `PI_ATOMIC_FEATURES.md` (July 4th) — v2, corrected*

Source-of-truth dump for comprehension, clone, and reimplementation.
Covers: core runtime, tools, extensions, skills, providers, models, TUI, sessions, CLI, SDK, compaction, keybindings, themes, packages, settings, and more.

---

## 1. CORE RUNTIME & ARCHITECTURE

### Tech Stack

- **TypeScript monorepo** — Node.js runtime, npm workspaces
- **4 packages**: `pi-coding-agent` (CLI + SDK), `pi-agent-core` (agent runtime), `pi-ai` (LLM API), `pi-tui` (terminal UI)
- Lazy imports for cold-start optimization
- Diff-based terminal rendering with full Unicode support
- Supply-chain: exact version pins, shrinkwrap, `--ignore-scripts`, npm audit

### Agent Loop (`packages/agent/`)

- `AIAgent` core agent class with tool-calling loop
- `agent-loop.ts` — main conversation loop with iteration budget
- Streaming and non-streaming response paths
- Tool-call dispatch via function name matching
- Token tracking per turn (input/output/cache)
- Grace-turn after budget exhaustion
- Automatic agent-level retry on transient errors (max 3 retries, 2s base delay, exponential backoff)
- Provider-level retry config (timeout, maxRetries, maxRetryDelayMs)

### Agent Harness (`packages/agent/src/harness/`)

- `agent-harness.ts` — AgentHarness wrapping AIAgent with session, skills, compaction
- `system-prompt.ts` — system prompt assembly from templates + skills + context
- `skills.ts` — skill discovery, loading, progressive disclosure (Agent Skills standard)
- `prompt-templates.ts` — prompt template expansion
- `messages.ts` — session message types
- `env/nodejs.ts` — Node.js environment adapter
- `session/` — JSONL repo, memory repo, UUID generation
- `compaction/` — auto-compaction and branch summarization
- `utils/` — shell output capture, truncation helpers

---

## 2. CLI & EXECUTION MODES

### Interactive Mode (default)

- Full TUI with editor, message history, tool rendering
- Four visual areas: startup header, messages, editor, footer
- File reference: `@` fuzzy-search, Tab path completion, Shift+Enter multi-line
- Image paste: Ctrl+V (Alt+V on Windows), drag into terminal
- Shell: `!command` sends to model, `!!command` silent
- External editor: Ctrl+G opens `$VISUAL` or `$EDITOR`
- Message queue: Enter=steer, Alt+Enter=follow-up, Escape=abort, Alt+Up=restore

### Print Mode (`-p`, `--print`)

- Non-interactive: send prompt, print response, exit
- Reads piped stdin: `cat README.md | pi -p "Summarize"`

### JSON Event Stream Mode (`--mode json`)

- All session events as JSON lines to stdout
- Events: agent_start/end, turn_start/end, message_start/update/end, tool_execution_start/update/end
- queue_update, compaction_start/end, auto_retry_start/end

### RPC Mode (`--mode rpc`)

- JSON protocol over stdin/stdout (strict JSONL, LF-only)
- Commands: prompt, cancel, set-model, set-thinking, fork, compact, session-info, etc.
- `streamingBehavior`: queue, steer, queueHead, block
- Optional `id` for request/response correlation

### CLI Subcommands

- `pi install <source> [-l]` — install package (npm/git/path), `-l` for project-local
- `pi remove`/`uninstall <source> [-l]` — remove
- `pi update [source|self|pi]` — update pi + packages + reconcile pinned git refs
- `pi update --extensions` — packages only
- `pi update --self` — pi only (platform-specific)
- `pi update --self --force` — reinstall even if current
- `pi list` — list installed packages
- `pi config` — enable/disable package resources

---

## 3. PROVIDER & MODEL SYSTEM

### Provider Architecture (`packages/ai/src/providers/`)

- Multi-provider unified API over OpenAI-compatible interface
- 30+ providers implemented: `anthropic.ts`, `openai-completions.ts`, `openai-responses.ts`, `openai-codex-responses.ts`, `google.ts`, `google-vertex.ts`, `cloudflare.ts`, `azure-openai-responses.ts`, `mistral.ts`, `amazon-bedrock.ts`, `faux.ts`, `openai-prompt-cache.ts`, etc.
- `simple-options.ts` — simplified config for custom providers
- `transform-messages.ts` — format conversion between provider APIs
- `register-builtins.ts` — built-in provider registration
- Image providers: `openrouter.ts`, `register-builtins.ts`

### 3 OAuth Subscription Providers

- **ChatGPT Plus/Pro (Codex)** — OpenAI subscription, officially OSS-endorsed
- **Claude Pro/Max** — Anthropic subscription, extra usage billing
- **GitHub Copilot** — Enterprise Server domain support

### 28 API Key Providers

Anthropic, OpenAI, Google Gemini, Google Vertex AI, DeepSeek, NVIDIA NIM, Mistral, Groq, Cerebras, xAI, OpenRouter, Vercel AI Gateway, Together AI, Fireworks, Hugging Face, Cloudflare AI Gateway, Cloudflare Workers AI, Azure OpenAI Responses, Ant Ling, ZAI, ZAI Coding Plan (CN), OpenCode Zen, OpenCode Go, Kimi For Coding, MiniMax, MiniMax (CN), Xiaomi MiMo, Xiaomi MiMo Token Plan (CN/AMS/SGP)

### Custom Providers (`~/.pi/agent/models.json`)

- Ollama, vLLM, LM Studio, any OpenAI-compatible server
- `api`: `openai-completions`, `openai-responses`, `anthropic-messages`, `google-generative-language`
- `compat` flags: `supportsDeveloperRole`, `supportsReasoningEffort`
- Provider-level `baseUrl`, `apiKey`, `headers`, `query`
- Model-level `reasoning: true/false`
- Extension-based custom providers (Anthropic passthrough, GitLab Duo)

### OAuth System (`packages/ai/src/utils/oauth/`)

- `device-code.ts` — device code flow
- `pkce.ts` — PKCE authorization code flow
- `anthropic.ts`, `openai-codex.ts`, `oauth-page.ts`

### Model Selection & Thinking

- `/login`, `/logout`, `/model`, `/scoped-models`
- `--provider`, `--model`, `--thinking` CLI flags
- 6 thinking levels: off, minimal, low, medium, high, xhigh
- Custom token budgets per level (`thinkingBudgets` setting)
- `hideThinkingBlock`, `enabledModels` for Ctrl+P cycling
- Model registry: `models.ts`, `models.generated.ts`, `api-registry.ts`
- Image models: `image-models.ts`, `images-api-registry.ts`

---

## 4. BUILT-IN TOOLS (8)

### `read` — Read files with line numbers, image attachment support, pagination (2000 lines / 50KB cap)

### `bash` — Execute shell commands, stdout/stderr/exit code capture, timeout, temp file on truncation

### `edit` — Precise find-and-replace, multi-edit in one call, exact-text matching, non-overlapping enforcement

### `write` — Create/overwrite files, auto-creates parent directories

### `grep` — Ripgrep-backed search, context lines, output modes (content/files_with_matches/count)

### `find` / `ls` — Directory listing, recursive walk, pattern matching, max-depth

### `web_search` — 8 providers (OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini), multi-query, recency filter, domain filter, full content fetch

### `fetch_content` — URL→markdown, YouTube transcripts with frames, GitHub repos, local video frames, Gemini fallback

### `get_search_content` — Retrieve stored content from prior searches

Tools can be configured: `--tools` (allowlist), `--exclude-tools`, `--no-builtin-tools`, `--no-tools`

---

## 5. EXTENSIONS SYSTEM

### Extension Architecture

- TypeScript modules, auto-discovered: `~/.pi/agent/extensions/` (global), `.pi/extensions/` (project, trust-gated)
- CLI: `-e <source>` (path/npm/git), repeatable
- Hot-reload: `/reload`
- Dependencies via `package.json` in extension directory

### Extension API (`ExtensionAPI`)

- `pi.registerTool()` — custom LLM-callable tools
- `pi.registerCommand()` — slash commands
- `pi.on(event, handler)` — 15+ lifecycle events
- `pi.appendEntry()` — session persistence
- `pi.registerCustomModel()` — custom providers
- `pi.setCustomHeader()` / `pi.setCustomFooter()` — UI customization
- `pi.setToolRenderer()` / `pi.setMessageRenderer()` — custom rendering

### Lifecycle Events

- **Resource**: `resource_changed`
- **Session**: `session_start`, `session_end`
- **Agent**: `agent_start`, `agent_end`
- **Model**: `pre_llm_call`, `post_llm_call`
- **Tool**: `tool_call`, `tool_result` (can block/modify)
- **Compaction**: `pre_compact`, `post_compact`, `pre_branch_summary`, `post_branch_summary`
- **UI**: `project_trust`
- **Message**: `user_message`

### Custom UI Components

- Full TUI via `ctx.ui.custom(component)`
- Component interface: `render(width)`, `handleInput(data)`, `wantsKeyRelease`, `invalidate()`
- `Focusable` for IME: `CURSOR_MARKER` zero-width escape, `focused` propagation
- `ctx.ui.select()`, `ctx.ui.confirm()`, `ctx.ui.input()`, `ctx.ui.notify()`

### 75+ Example Extensions (shipped in `examples/extensions/`)

**Security/Permissions:** `confirm-destructive.ts`, `permission-gate.ts`, `protected-paths.ts`, `dirty-repo-guard.ts`, `project-trust.ts`

**Git Workflows:** `git-checkpoint.ts`, `git-merge-and-resolve.ts`, `auto-commit-on-exit.ts`

**Custom Providers:** `custom-provider-anthropic/`, `custom-provider-gitlab-duo/`

**Tool Extensions:** `tools.ts`, `dynamic-tools.ts`, `tool-override.ts`, `bash-spawn-hook.ts`, `inline-bash.ts`, `truncated-tool.ts`, `built-in-tool-renderer.ts`

**UI Customization:** `border-status-editor.ts`, `custom-footer.ts`, `custom-header.ts`, `titlebar-spinner.ts`, `working-indicator.ts`, `status-line.ts`, `model-status.ts`, `mac-system-theme.ts`, `hidden-thinking-label.ts`, `minimal-mode.ts`

**Input/Message:** `input-transform.ts`, `input-transform-streaming.ts`, `message-renderer.ts`, `send-user-message.ts`

**Games (yes, in terminal):** `snake.ts`, `space-invaders.ts`, `tic-tac-toe.ts`, `doom-overlay/` (DOOM in terminal overlay!)

**Sub-agents & Planning:** `subagent/`, `handoff.ts`, `plan-mode/`

**Compaction & Editors:** `custom-compaction.ts`, `trigger-compact.ts`, `rainbow-editor.ts`, `modal-editor.ts`

**Integration & Infrastructure:** `github-issue-autocomplete.ts`, `ssh.ts`, `gondolin/` (tools→micro-VM), `sandbox/`

**State Management:** `bookmark.ts`, `todo.ts`, `preset.ts`, `session-name.ts`

**Other:** `claude-rules.ts`, `event-bus.ts`, `file-trigger.ts`, `notify.ts`, `pirate.ts`, `prompt-customizer.ts`, `provider-payload.ts`, `qna.ts`, `question.ts`, `questionnaire.ts`, `reload-runtime.ts`, `shutdown-command.ts`, `structured-output.ts`, `summarize.ts`, `system-prompt-header.ts`, `timed-confirm.ts`, `widget-placement.ts`, `working-message-test.ts`, `overlay-test.ts`, `overlay-qa-tests.ts`, `hello.ts`, `commands.ts`, `dynamic-resources/`, `interactive-shell.ts`, `with-deps/`, `rpc-demo.ts`, `rpc-extension-ui.ts`

---

## 6. SKILLS SYSTEM

### Standards Compliance

- Implements [Agent Skills standard](https://agentskills.io/specification)
- **Cross-harness compatible** — can load skills from Claude Code, OpenAI Codex, etc.
- Progressive disclosure: only descriptions in context, full SKILL.md loaded on-demand
- Skills exposed as `/skill:name` commands with arguments

### Bundled Skills

- Pi ships with exactly **1** bundled skill: `.pi/skills/add-llm-provider.md` — guides agent on adding new LLM providers
- This is intentional minimalism — the extension system (75+ examples) is Pi's primary extension mechanism
- Skills are installed by users from the ecosystem or created by the agent itself

### Skill Locations

- Global: `~/.pi/agent/skills/`, `~/.agents/skills/`
- Project (trust-gated): `.pi/skills/`, `.agents/skills/`
- Packages: `skills/` dir or `pi.skills` in `package.json`
- Settings: `skills` array with glob patterns
- CLI: `--skill <path>` (repeatable)
- Cross-harness: load `~/.claude/skills`, `~/.codex/skills` via settings

### Discovery Rules

- Direct root `.md` files = individual skills (in `~/.pi/agent/skills/` and `.pi/skills/`)
- Directories with `SKILL.md` discovered recursively (all locations)
- `~/.agents/skills/` and `.agents/skills/`: root `.md` files ignored (dirs only)
- `--no-skills` disables discovery; explicit `--skill` paths still load

### No Bundled MCP

- Pi does **not** ship with a built-in MCP client or server
- MCP servers can be connected via extension or external tools
- The `pi-chat` companion repo handles Slack/chat automation separately

---

## 7. SESSIONS & PERSISTENCE

### Session Storage

- JSONL tree format in `~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl`
- Tree structure via `id`/`parentId` — in-place branching without new files
- Versioned: v1 (linear) → v2 (tree) → v3 (renamed custom role), auto-migrated
- Custom dir via `--session-dir`, `PI_CODING_AGENT_SESSION_DIR`, or `sessionDir` setting

### Session Commands

- `pi -c`/`--continue`, `pi -r`/`--resume`, `pi --no-session` (ephemeral)
- `pi --name`, `pi --session <path|id>`, `pi --fork <path|id>`
- `/resume` — interactive picker (search, sort, filter, rename, delete via `trash` CLI)
- `/tree` — navigate tree (↑↓, Ctrl+O filter, Shift+L label, branch summary on switch)
- `/fork`, `/clone`, `/new`, `/name`, `/session`
- `/export [file]` — HTML export with ANSI→HTML + tool rendering
- `/share` — private GitHub gist with shareable HTML link
- `badlogic/pi-share-hf` — publish to Hugging Face datasets

### Entry Types

`user`, `assistant`, `tool_call`, `tool_result`, `compaction`, `branch_summary`, `custom` (extensions), `model_change`, `thinking_change`, `label`

---

## 8. CONTEXT & COMPACTION

### Context Files

- `AGENTS.md` / `CLAUDE.md`: `~/.pi/agent/AGENTS.md`, parent dirs walking up to git root, cwd
- `--no-context-files` / `-nc` to disable
- `.pi/SYSTEM.md` / `~/.pi/agent/SYSTEM.md` — replace default system prompt
- `APPEND_SYSTEM.md` — append without replacing
- `--system-prompt`, `--append-system-prompt` CLI overrides

### Auto-Compaction

- Triggers: `contextTokens > contextWindow - reserveTokens` (default reserve: 16384)
- Process: find cut point (keepRecentTokens: 20000) → LLM summarize → append CompactionEntry → reload
- Iterative: passes previous summary as context
- Structured format: files read/modified/created, learned conventions, key decisions, tasks
- `/compact [instructions]` for manual trigger
- Extension hooks: `pre_compact`, `post_compact`

### Branch Summarization

- On `/tree` switch away from branch: no summary / default / custom instructions
- Preserves abandoned-branch context at new position
- Extension hooks: `pre_branch_summary`, `post_branch_summary`

### Overflow Handling

- Fallback compaction at hard limits
- Large results saved to temp files
- Output guard (`output-guard.ts`)

---

## 9. TUI — TERMINAL UI

### TUI Library (`packages/tui/`)

- Differential rendering — only changed lines redrawn
- Component system: `render(width)`, `handleInput(data)`, `invalidate()`
- `Focusable` IME support: `CURSOR_MARKER` APC escape, `focused` propagation
- Hardware cursor: `showHardwareCursor` / `PI_HARDWARE_CURSOR=1`
- Built-in components: `Input`, `Editor`, `Select`, `Container`, `Dialog`

### 30+ TUI Components (`modes/interactive/components/`)

- Message rendering: `assistant-message`, `armin` (thinking blocks), `user-message`, `custom-message`, `skill-invocation-message`
- Tool display: `tool-execution`, `bash-execution`, `diff` (syntax-highlighted)
- Compaction: `compaction-summary-message`, `branch-summary-message`
- Selectors: `model-selector`, `session-selector`, `theme-selector`, `thinking-selector`, `oauth-selector`, `extension-selector`, `config-selector`, `settings-selector`, `tree-selector`, `scoped-models-selector`, `show-images-selector`, `user-message-selector`, `trust-selector`
- UI: `footer` (cwd, session, tokens, cost, model), `bordered-loader`, `countdown-timer`, `keybinding-hints`, `login-dialog`, `first-time-setup`, `earendil-announcement`, `dynamic-border`, `visual-truncate`
- Editors: `extension-editor`, `custom-editor`

### Editor Features

- Syntax highlighting (highlight.js), file reference autocomplete (`@`), path autocomplete (Tab)
- Image paste, shell command dispatch (`!`/`!!`), external editor (Ctrl+G)
- Prompt template expansion (`/template`), slash command autocomplete
- Message queue, `editorPaddingX` setting (0-3)

---

## 10. KEYBINDINGS

### Fully Customizable

- `~/.pi/agent/keybindings.json` — namespaced IDs (`tui.editor.cursorUp`)
- Legacy auto-migration from pre-namespaced configs
- `/reload` to apply, `/hotkeys` to display
- Key format: `modifier+key` (ctrl, shift, alt combinable)
- All keyboard chars, function keys, special keys supported, multiple bindings per action

### Categories

- **Editor Cursor**: up/down/left/right, word jump, line start/end, page up/down, jump-to-char
- **Editor Deletion**: char/word forward/backward, to line start/end
- **Input**: submit (Enter), newline (Shift+Enter), tab/autocomplete
- **Navigation**: scroll, page, tree nav, fork, clone
- **UI**: settings, model, session picker
- **Extensions**: custom via `keyHint()` and injected `keybindings` manager

---

## 11. THEMES

- Built-in: `dark`, `light` — auto-detect terminal background on first run
- Custom: `~/.pi/agent/themes/*.json`, `.pi/themes/*.json` (trust-gated), packages, settings
- JSON format with `$schema`, `name`, `vars` (hex/ANSI/named colors)
- Color tokens: primary, secondary, background, foreground, borders, syntax, diffs
- Schema validation, `/settings` → theme selection, `--theme` CLI, `--no-themes`

---

## 12. PROMPT TEMPLATES

- Markdown files with YAML frontmatter, expanded via `/name` in editor
- Frontmatter: `description`, `argument-hint` (`<required>` / `[optional]`)
- Locations: `~/.pi/agent/prompts/`, `.pi/prompts/`, packages, settings
- CLI: `--prompt-template`, `--no-prompt-templates`
- **5 bundled templates**: `cl.md` (changelog), `is.md` (issues), `pr.md` (PR review), `sa.md` (summary), `wr.md` (work review)

---

## 13. PI PACKAGES

### Package System

- Bundle extensions, skills, prompts, themes for npm/git/path distribution
- `pi install <source> [-l]`, `pi remove`, `pi update`, `pi list`, `pi config`
- Sources: npm (`npm:@scope/pkg@1.2.3`), git (`git:github.com/user/repo@v1`), path, URL
- `-l` for project-local (`.pi/settings.json`), default user (`~/.pi/agent/settings.json`)
- `-e` for one-time use without install
- Auto-install missing project packages after trust
- Resource filtering: select specific skills/extensions, exclude by type

---

## 14. SETTINGS SYSTEM

### Architecture

- JSON: `~/.pi/agent/settings.json` (global), `.pi/settings.json` (project, trust-gated)
- Project overrides global — nested objects merged
- Edit directly or use `/settings`

### All Settings by Category

**Model & Thinking:** `defaultProvider`, `defaultModel`, `defaultThinkingLevel`, `hideThinkingBlock`, `thinkingBudgets`, `enabledModels`

**UI & Display:** `theme`, `quietStartup`, `collapseChangelog`, `doubleEscapeAction`, `treeFilterMode`, `editorPaddingX`, `autocompleteMaxVisible`, `showHardwareCursor`

**Trust:** `defaultProjectTrust` (ask/always/never)

**Compaction:** `compaction.enabled`, `compaction.reserveTokens` (16384), `compaction.keepRecentTokens` (20000)

**Branch Summary:** `branchSummary.reserveTokens` (16384), `branchSummary.skipPrompt`

**Retry:** `retry.enabled`, `retry.maxRetries` (3), `retry.baseDelayMs` (2000), `retry.provider.timeoutMs`, `retry.provider.maxRetries` (0), `retry.provider.maxRetryDelayMs` (60000)

**Message Delivery:** `steeringMode`, `followUpMode`, `transport` (auto/sse/websocket/websocket-cached), `httpIdleTimeoutMs` (300000), `websocketConnectTimeoutMs` (15000)

**Terminal & Images:** `terminal.showImages`, `terminal.imageWidthCells` (60), `terminal.clearOnShrink`, `images.autoResize`, `images.blockImages`

**Shell:** `shellPath`, `shellCommandPrefix`, `npmCommand`

**Sessions:** `sessionDir`

**Resources:** `packages`, `extensions`, `skills`, `prompts`, `themes`, `enableSkillCommands`

**Telemetry:** `enableInstallTelemetry` (true), `enableAnalytics` (false)

**Other:** `markdown.codeBlockIndent`, `warnings.anthropicExtraUsage`

---

## 15. SDK — PROGRAMMATIC API

### Core API

- `createAgentSession(options)` — main factory for `AgentSession`
- `SessionManager.inMemory()` / `SessionManager.file()` — persistence backends
- `AuthStorage.create()` — credential management
- `ModelRegistry.create(authStorage)` — provider/model registry
- `ResourceLoader` / `DefaultResourceLoader` — extensions, skills, prompts, themes, context
- Custom `ResourceLoader` for programmatic control

### AgentSession API

- `session.prompt(message, options?)`, `session.subscribe(callback)`, `session.cancel()`
- `session.setModel(model)`, `session.setThinking(level)`, `session.fork()`, `session.compact()`
- Events: message_update, tool_execution_start/end, compaction_start/end, etc.

### 13 SDK Examples

`01-minimal.ts` through `13-session-runtime.ts` covering: basic session, custom model, custom prompt, skills, tools, extensions, context files, prompt templates, auth, settings, sessions, full control, runtime integration

---

## 16. SECURITY & TRUST

### Project Trust

- Interactive prompt on startup for new projects with trust-gated inputs
- Trust saved in `~/.pi/agent/trust.json` (per-folder, inherited from parents)
- `/trust` to save, `--approve`/`-a` to override, `--no-approve`/`-na` to ignore
- Non-interactive: `defaultProjectTrust` fallback (ask/always/never)
- Before trust: only context files + user/global extensions + CLI `-e`
- After trust: project extensions, packages, settings loaded

### Supply-Chain Hardening

- Direct deps pinned to exact versions, `save-exact=true`, `min-release-age=2`
- `package-lock.json` is ground truth; pre-commit blocks accidental changes
- Published CLI includes `npm-shrinkwrap.json` for transitive pinning
- Release smoke tests: isolated npm/Bun installs outside repo
- `--ignore-scripts` on all install paths
- CI: `npm ci --ignore-scripts`, scheduled `npm audit --omit=dev`

### Containerization

- **OpenShell**: policy-controlled sandbox (NVIDIA)
- **Gondolin extension**: tools into local micro-VM while auth stays on host
- **Plain Docker**: full process in container
- No built-in permission system — relies on OS/containerization

---

## 17. SHELL, IMAGES & UTILITIES

### Shell Integration

- `!command` sends to model, `!!command` silent
- Non-interactive `bash -c`, optional timeout
- `shellCommandPrefix` for alias expansion, `shellPath` for custom shell
- `npmCommand` for npm wrappers (e.g., mise exec)

### Image System

- Paste: Ctrl+V / Alt+V, drag into terminal
- Resize: max 2000×2000 (`images.autoResize`), `images.blockImages` to disable
- Kitty/iTerm2 inline protocols (`terminal.showImages`, `terminal.imageWidthCells`)
- Pipeline: `image-convert.ts`, `image-resize.ts`, `image-resize-worker.ts`, `exif-orientation.ts`
- Photon WASM-based processing (`photon.ts`), MIME detection (`mime.ts`)
- Native + image clipboard (`clipboard-native.ts`, `clipboard-image.ts`)

### 30+ Utility Modules

- Core: `event-bus.ts`, `exec.ts`, `bash-executor.ts`, `http-dispatcher.ts`, `footer-data-provider.ts`, `provider-attribution.ts`, `diagnostics.ts`, `timings.ts`, `telemetry.ts`, `experimental.ts`, `defaults.ts`, `resource-loader.ts`, `package-manager.ts`, `project-trust.ts`, `trust-manager.ts`, `session-cwd.ts`, `config.ts`
- Frontend: `ansi.ts`, `syntax-highlight.ts`, `html.ts`, `git.ts`, `shell.ts`, `paths.ts`, `json.ts`, `mime.ts`, `sleep.ts`, `fs-watch.ts`, `frontmatter.ts`, `pi-user-agent.ts`, `open-browser.ts`, `child-process.ts`, `tools-manager.ts`, `deprecation.ts`

---

## 18. SLASH COMMANDS (FULL LIST)

### Session: `/resume`, `/new`, `/name`, `/session`, `/tree`, `/fork`, `/clone`, `/compact`, `/export`, `/share`

### Config: `/login`, `/logout`, `/model`, `/scoped-models`, `/settings`, `/trust`

### Info: `/reload`, `/hotkeys`, `/changelog`, `/quit`

### Skills: `/skill:<name>` + custom extension commands

---

## 19. CLI FLAGS (FULL REFERENCE)

### Mode: (default), `-p`/`--print`, `--mode json`, `--mode rpc`, `--export <in> [out]`

### Model: `--provider`, `--model`, `--api-key`, `--thinking`, `--models`, `--list-models`

### Session: `-c`/`--continue`, `-r`/`--resume`, `--session`, `--fork`, `--session-dir`, `--no-session`, `--name`/`-n`

### Tools: `--tools`/`-t`, `--exclude-tools`/`-xt`, `--no-builtin-tools`/`-nbt`, `--no-tools`/`-nt`

### Resources: `-e`/`--extension`, `--no-extensions`, `--skill`, `--no-skills`, `--prompt-template`, `--no-prompt-templates`, `--theme`, `--no-themes`, `--no-context-files`/`-nc`

### Other: `--system-prompt`, `--append-system-prompt`, `--verbose`, `-a`/`--approve`, `-na`/`--no-approve`, `-h`/`--help`, `-v`/`--version`

### File Args: `@file.md`, `@image.png`, multiple files

---

## 20. TELEMETRY & PLATFORM SUPPORT

### Telemetry

- `enableInstallTelemetry` (default: true) — anonymous version ping
- `PI_SKIP_VERSION_CHECK=1`, `PI_OFFLINE=1` to disable all startup network
- `enableAnalytics` (default: false, opt-in via `PI_EXPERIMENTAL=1`)

### Platforms

- Windows (full TUI, ConPTY, Windows Terminal, `windows-self-update.ts`)
- macOS (full TUI, system theme detection)
- Linux (full TUI, various terminals)
- Termux for Android, Tmux compatibility
- Kitty/iTerm2 image protocols, cursor/IME support

---

## 21. KEY PATHS & ENV VARS

### Paths

| Path                             | Purpose              |
| -------------------------------- | -------------------- |
| `~/.pi/agent/settings.json`    | Global settings      |
| `~/.pi/agent/auth.json`        | OAuth + API keys     |
| `~/.pi/agent/trust.json`       | Trust decisions      |
| `~/.pi/agent/keybindings.json` | Custom keybindings   |
| `~/.pi/agent/models.json`      | Custom providers     |
| `~/.pi/agent/sessions/`        | Sessions             |
| `~/.pi/agent/extensions/`      | Global extensions    |
| `~/.pi/agent/skills/`          | Global skills        |
| `~/.pi/agent/prompts/`         | Global templates     |
| `~/.pi/agent/themes/`          | Global themes        |
| `~/.pi/agent/AGENTS.md`        | Global context       |
| `~/.pi/agent/npm/`             | User packages        |
| `~/.agents/skills/`            | Cross-harness skills |
| `.pi/settings.json`            | Project settings     |
| `.pi/extensions/`              | Project extensions   |
| `.pi/skills/`                  | Project skills       |
| `.pi/prompts/`                 | Project templates    |
| `.pi/themes/`                  | Project themes       |
| `.pi/npm/`                     | Project packages     |

### Env Vars

`PI_SKIP_VERSION_CHECK`, `PI_OFFLINE`, `PI_CODING_AGENT_SESSION_DIR`, `PI_HARDWARE_CURSOR`, `PI_ALLOW_LOCKFILE_CHANGE`, `PI_EXPERIMENTAL`

---

## 22. DEVELOPMENT & TESTING

- TypeScript composite project references, `tsconfig.base.json`
- `npm run build`, `npm run check` (lint+format+typecheck+dep checks)
- `./test.sh` (skips LLM tests without API keys), `./pi-test.sh` (run from sources)
- Vitest for all packages, E2E tests with LLM-dependent suites
- CI: `ci.yml`, `build-binaries.yml`, `npm-audit.yml`, `pr-gate.yml`, `issue-gate.yml`, `approve-contributor.yml`

---

## 23. CORRECTED COMPARISON TABLE

| Feature                              | Hermes                              | OpenHuman                       | Pi                                  |
| ------------------------------------ | ----------------------------------- | ------------------------------- | ----------------------------------- |
| **Bundled Skills**             | **73** (17 categories)        | **1** (marketplace)       | **1** (`add-llm-provider`)  |
| **Optional Skills**            | **97** (10 categories)        | 0                               | 0 (user installs)                   |
| **Managed Integrations**       | 0                                   | **118+** (Composio)       | 0                                   |
| **Native MCP Client**          | ✅ (catalog/picker/circuit-breaker) | ✅ (stdio+HTTP, registry)       | ❌                                  |
| **Native MCP Server**          | ✅ (serve/add/remove/test)          | ✅ (stdio+HTTP+SSE)             | ❌                                  |
| **MCP OAuth 2.1 PKCE**         | ✅                                  | ❌                              | ❌                                  |
| **MCP Audit/Registry**         | ❌                                  | ✅ (audit+registry)             | ❌                                  |
| **Agent Skills Standard**      | ❌ (custom format)                  | ❌ (metadata-only now)          | ✅ (spec-compliant)                 |
| **Extension System**           | Plugins (20+ types)                 | None                            | Extensions (75+ examples)           |
| **Package Ecosystem**          | Skills hub                          | None                            | npm/git packages                    |
| **Memory System**              | 8 providers                         | Memory Tree + 16 domains        | None                                |
| **Voice/STT/TTS**              | ✅                                  | ✅                              | ❌                                  |
| **Desktop Mascot**             | ❌                                  | ✅ (Rive-animated)              | ❌                                  |
| **Messaging Gateway**          | 25 platforms                        | 17 platforms                    | None (pi-chat repo)                 |
| **Wallet/Web3**                | ❌                                  | ✅ (BTC/ETH/SOL/TRON)           | ❌                                  |
| **Subconscious/Background**    | ❌                                  | ✅ (subconscious + dreaming)    | ❌                                  |
| **Cron/Scheduling**            | ✅                                  | ✅                              | ❌                                  |
| **Browser/Computer Use**       | ✅ (CDP + macOS CUA)                | ✅ (CEF + mouse/kb)             | ❌                                  |
| **Model Providers**            | 30+                                 | Hint-routed (managed)           | **31** (3 OAuth + 28 API)     |
| **Custom Providers**           | Plugin-based                        | Config TOML                     | **JSON config** (Ollama/vLLM) |
| **SDK**                        | ❌                                  | ❌                              | ✅`AgentSession`                  |
| **Supply-Chain**               | ❌                                  | ❌                              | ✅ shrinkwrap + audit               |
| **Total Skills (bundled+opt)** | **170**                       | **1** (+118 integrations) | **1** (+ecosystem)            |

---

End of Pi atomic specification (v2, corrected).

---

---

# 3. Hermes Agent — Complete Atomic Feature Specification

> *Source: `Hermes Atomic Features List.txt` (July 4th) — Telegram chat dump, 12 chunks*

Source-of-truth dump for clone/reimplementation.
Covers: core runtime, tools, skills, plugins, providers, memory, gateway, TUI, MCP, ACP, cron, kanban, voice, observability, context engines, terminal backends, release features.

---

## 1. CORE RUNTIME & EXECUTION

### Agent Loop

- `AIAgent.run_conversation()` core loop with tool calling
- Iteration budget: `max_iterations` (default 90) + grace call
- Interrupt checks per iteration (`_interrupt_requested`)
- Budget tracking via `iteration_budget`
- Tool-call dispatch via `handle_function_call()`
- Grace-turn after budget exhaustion
- `AIAgent.chat()` simple interface — returns final response string
- OpenAI-format message roles: `system / user / assistant / tool`
- Reasoning content stored in `assistant_msg["reasoning"]`
- Streaming + non-streaming response paths
- Tool-call argument coercion to JSON Schema types
- Accept reasoning-only responses without retry
- Self-optimized GPT/Codex tool-use guidance (behavioral benchmarking of 5 failure modes)
- Thinking-only prefill continuation for structured reasoning

### Context & Memory

- Automatic context compression at token limit
- `/compress` manual trigger
- Context compaction failure recovery
- Save oversized tool results to file instead of destructive truncation
- Sandbox-aware tool result persistence
- Prior-history tool messages excluded from review summary (clean-context fork)
- Multi-modal image routing based on model vision capability (not provider defaults)
- `context.engine` pluggable context engines — only one active at a time
- Default: `compressor` (built-in ContextCompressor)
- Plugin-dir: `plugins/context_engine/<name>/`
- Prompt cache TTL configurable: `prompt_caching.cache_ttl` (5m default, 1h opt-in)

### Provider / Model Layer

- 30+ model providers via plugin architecture (see Section 8)
- Credential pool: rotate across multiple API keys; exhaustion-aware
- `hermes fallback` command for managing fallback providers
- Remote model catalog manifest (OpenRouter + Nous Portal pulled from remote)
- `/model` live mid-session model/provider switching
- Aggregator-aware resolution
- Automatic cross-provider fallback
- Inline button picker on Telegram/Discord
- Model pricing display for OpenRouter and Nous Portal
- Free-tier model gating + pricing display
- Non-agentic model warning
- `/fast` whitelist for OpenAI + Anthropic models
- Auxiliary client payment fallback: retry next provider on 402
- Auxiliary client resolves named custom providers and `main` alias
- Vision auto-detection: tries main provider first

### Profiles

- Multiple independent Hermes instances with isolated configs/sessions/skills/memory
- `hermes profile list / create / use / delete / show / alias / rename / export / import`
- Clone profiles: `--clone`, `--clone-all`, `--clone-from`
- Profile-scoped memory isolation
- Sticky default profile
- Profile-aware paths via `get_hermes_home()`
- Profile-aware service units (systemd)
- Worktree mode: `hermes -w` (isolated git worktree for parallel agents)

### Sessions & History

- SQLite + FTS5 session store (`state.db`)
- Session export to JSONL
- Session rename / delete / prune (--older-than N days)
- Session stats
- Session browsing with interactive picker
- JSONL transcripts + optional per-session JSON snapshots
- Subagent sessions linked to parent, hidden from list
- Thread sessions by default (multi-user thread support across gateway)
- Shared thread sessions across platforms
- `hermes sessions export`, `list`, `browse`, `rename`, `delete`, `prune`, `stats`
- `/resume [name]` resume named session
- `/branch`, `/fork`
- `/usage` token usage
- `/insights [days]` usage analytics

### Self-Improvement Loop

- Background review fork per turn
- Rubric-based skill review (class-first)
- Active-update bias (prefers skill just loaded)
- Handles `references/` / `templates/` sub-files
- Inherits parent's live runtime (provider, model, credentials)
- Scoped to memory + skills toolsets (no shell/web)
- Clean shutdown for memory providers
- Excludes prior-history tool messages from summary

### Autonomous Curator

- Runs as background agent via gateway cron ticker
- 7-day cycle default (configurable)
- Grades skill library; consolidates related skills; prunes dead ones
- Archived skills classified: consolidated vs pruned (model + heuristic)
- Per-run reports: `logs/curator/run.json` + `REPORT.md`
- `hermes curator status` ranks skills by usage
- Unified under `auxiliary.curator` config
- Defense-in-depth: never touches bundled/hub skills; max action is archive
- Pinned skills exempt from all auto-transitions + LLM review passes
- Backup tar.gz before every run
- Available verbs: status, run, pause, resume, pin, unpin, archive, restore, prune, backup, rollback
- Slash: `/curator <subcommand>`

---

## 2. CLI & TERMINAL UI

### HERMES CLI (`hermes`)

- `hermes` default to chat mode
- `hermes chat -q` single-query mode
- `hermes -z <prompt>` one-shot mode
- `hermes --yolo` skip dangerous command approval
- `--resume`, `--continue`, `--worktree`, `--skills`, `--profile`, `--pass-session-id`
- Skin engine: data-driven theming (banner colors, spinner faces/verbs/wings, tool prefix, response box)
- KawaiiSpinner animated faces during API calls; `┊` activity feed
- Rich banner/panels; prompt_toolkit input with autocomplete
- Ghost status-bar lines cleared on terminal resize
- CR/LF normalization in pasted text
- Native Windows image paste
- LaTeX rendering
- Mouse-wheel line scroll; `/mouse` toggle for ConPTY phantom mouse injection

### TUI (Ink/React terminal UI)

- `hermes --tui` Ink terminal UI
- TUI cold-start ~57% faster (lazy agent init, lazy imports, mtime-cached config, memoized tool defs)
- Entry: `ui-tui/src/entry.tsx`
- Python JSON-RPC backend: `tui_gateway/`
- Types: `gatewayTypes.ts`, `types/`
- Components, hooks, lib, theme
- Auto-resume last session (opt-in)
- Light-terminal auto-detection
- Session delete from `/resume` picker with `d`
- `/redraw` force full UI repaint

### CLI Subcommands (`hermes`)

- `config` — view config
- `config edit` — open config.yaml
- `config set KEY VAL`
- `config path`, `config env-path`, `config check`, `config migrate`
- `model` — interactive model/provider picker
- `model` `/model` mid-session switch
- `setup [section]` — interactive wizard (model|terminal|gateway|tools|agent)
- `doctor [--fix]` — dependency/config diagnostics
- `status [--all]` — component status
- `login [--provider]` — OAuth login
- `logout`
- `auth add / list / remove / reset` — credential pool
- `insights [--days]` — usage analytics
- `update`, `update --check`
- `completion bash|zsh`
- `acp` — ACP server for IDE integration
- `claw migrate` — migrate from OpenClaw
- `uninstall`
- `honcho setup/status` — Honcho memory integration
- `memory setup/status/off` — memory provider config
- `pairing list/approve/revoke` — DM authorization
- `plugins list/install/remove` — plugin management
- `tools` — interactive tool enable/disable (curses UI)
- `tools list / enable / disable`
- `skills list / search / install / inspect / config / check / update / uninstall / publish / browse / tap`
- `mcp serve / add / remove / list / test / configure`
- `gateway run / install / start / stop / restart / status / setup`
- `cron list / add / edit / pause / resume / run / status`
- `webhook subscribe / list / remove / test`
- `profile list / create / use / delete / show / alias / rename / export / import`
- `sessions list / export / rename / delete / prune / stats / browse`
- `logs [--follow] [--level] [--session]`

### Slash Commands (in-session)

- Session: `/new` `/reset` `/clear` `/retry` `/undo` `/title` `/compress` `/stop` `/rollback` `/snapshot` `/background` `/queue` `/steer` `/agents` `/tasks` `/resume` `/goal` `/redraw` `/branch` `/fork` `/fast` `/browser` `/history` `/save` `/copy` `/paste` `/image`
- Config: `/config` `/model` `/personality` `/reasoning` `/verbose` `/voice` `/yolo` `/busy` `/indicator` `/footer` `/skin` `/statusbar`
- Tools/Skills: `/tools` `/toolsets` `/skills` `/skill` `/reload-skills` `/reload` `/reload-mcp` `/cron` `/curator` `/kanban` `/plugins`
- Gateway: `/approve` `/deny` `/restart` `/sethome` `/update` `/topic` `/platforms` `/gateway`
- Info: `/help` `/commands` `/usage` `/insights` `/gquota` `/status` `/profile` `/debug`
- Exit: `/quit` `/exit` `/q`
- Special: `/background <prompt>` fire-and-forget in background
- `/queue <prompt>` queue for next turn
- `/steer <prompt>` inject after next tool call without interrupting
- `/goal [text|sub]` set standing goal across turns (`status`, `pause`, `resume`, `clear`)
- `/fast` priority/fast processing toggle
- `/voice [on|off|tts]`

---

## 3. TOOL SYSTEM

### Tool Architecture

- `tools/registry.py` central registry with auto-discovery
- `discover_builtin_tools()` imports `tools/*.py` with top-level `registry.register()` calls
- `ToolEntry` metadata: name, toolset, schema, handler, check_fn, requires_env, is_async, emoji, max_result_size_chars, dynamic_schema_overrides
- `check_fn` TTL cache (~30s)
- All handlers return JSON strings
- `get_hermes_home()` for paths (profile-safe)
- `path_security.py` for path sandboxing
- `tool_result_storage.py` for persistent result storage
- `tool_output_limits.py` for output truncation
- `tool_backend_helpers.py` for backend support
- `tirith_security.py` for website/shell blocklists
- `schema_sanitizer.py` for schema sanitization

### Built-in Tools (from `_HERMES_CORE_TOOLS`)

- `web_search` — web search
- `web_extract` — web content extraction
- `terminal` — shell commands + process management + background
- `process` — background process management (list/poll/log/wait/kill/write/close)
- `read_file` — read file with pagination
- `write_file` — write/overwrite files
- `patch` — targeted find-and-replace edits; V4A patch mode supported
- `search_files` — ripgrep-backed content/file search with context, output modes
- `vision_analyze` — image analysis (URL, file path, data URL)
- `image_generate` — AI image generation
- `text_to_speech` — text-to-speech with provider config
- `todo` — task list management (read/write/complete/cancel)
- `memory` — persistent memory read/write
- `session_search` — FTS5 full-text search over past sessions
- `clarify` — ask user clarifying questions (multi-choice / open-ended)
- `execute_code` — sandboxed Python execution with Hermes tools programmable
- `delegate_task` — subagent task delegation (single/batch)
- `cronjob` — scheduled task management
- `send_message` — cross-platform message sending
- `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_scroll`, `browser_back`, `browser_press`, `browser_get_images`, `browser_vision`, `browser_console` — browser automation
- `skills_list` — list installed skills
- `skill_view` — view skill content + linked files
- `skill_manage` — create/edit/patch/delete/write_file/remove_file skills
- Home Assistant: `ha_list_entities`, `ha_get_state`, `ha_list_services`, `ha_call_service`
- Kanban: `kanban_show`, `kanban_list`, `kanban_complete`, `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_create`, `kanban_link`, `kanban_unblock`
- `computer_use` — macOS computer use (gated on cua-driver)

### Special / Auxiliary Tools

- `browser_cdp` — CDP browser connection
- `browser_dialog` — browser dialog tool
- `computer_use_tool` — computer use wrapper
- `mixture_of_agents_tool` — MoA
- `x_search_tool` — X/Twitter search via xAI
- `yuanbao_tools` — Yuanbao integration tools
- `feishu_doc_tool` — Feishu doc tools
- `feishu_drive_tool` — Feishu drive tools
- `homeassistant_tool` — HA tools
- `discord_tool` — Discord tools
- `send_message_tool` — messaging
- `session_search_tool` — session history search
- `memory_tool` — memory interface
- `todo_tool` — todo interface
- `skill_manager_tool`, `skill_provenance`, `skill_usage`, `skills_ast_audit`, `skills_guard`, `skills_hub`, `skills_sync`, `skills_tool` — skill management subsystem
- `transcription_tools` — STT-provider tools
- `tts_tool` — TTS provider
- `cronjob_tools` — cron management tools
- `code_execution_tool` — Python execution
- `delegate_tool` — delegation
- `terminal_tool` — terminal backend
- `file_operations`, `file_tools`, `file_state` — file I/O
- `web_tools` — web search/extract
- `vision_tools` — vision
- `video_generation_tool` — video gen
- `image_generation_tool` — image gen
- `tts_tool` — text to speech provider tool
- `approval.py` — approval gating
- `interrupt.py` — interrupt handling
- `checkpoint_manager.py` — filesystem checkpoints
- `process_registry.py` — background process registry
- `credential_files` — cred-file helpers
- `credential_pool` / `credential_sources` / `credential_persistence` — credential management
- `mcp_tool` — MCP tool adapter
- `mcp_oauth.py`, `mcp_oauth_manager.py` — MCP OAuth flows
- `env_passthrough.py` — env passthrough for sandbox
- `slash_confirm.py` — slash confirm
- `debug_helpers.py` — debug helpers
- `patch_parser.py` — patch parsing
- `fuzzy_match.py` — fuzzy matching
- `url_safety.py` — URL safety checks
- `website_policy.py` — website policy
- `binary_extensions.py` — binary detection
- `path_security.py` — path security
- `tool_result_classification.py` — result classification
- `tool_output_limits.py` — output limits
- `lazy_deps.py` — lazy dependency imports
- `managed_tool_gateway.py` — gateway tool management
- `ansible_strip.py` — ANSI stripping
- `neutts_samples`, `neutts_synth.py` — NeuTTS lib
- `fal_common.py` — FAL shared
- `openrouter_client.py` — OpenRouter client
- `xai_http.py` — xAI HTTP helpers
- `microsoft_graph_auth.py`, `microsoft_graph_client.py` — MS Graph auth
- `lsp/client.py`, `lsp/manager.py`, `lsp/workspace.py`, `lsp/eventlog.py`, `lsp/cli.py`, `lsp/install.py`, `lsp/protocol.py`, `lsp/servers.py`, `lsp/reporter.py`, `lsp/range_shift.py` — LSP client

---

## 4. SKILL SYSTEM

### Skill Architecture

- Agent-created skills: saved as SKILL.md with YAML frontmatter
- Skills hub: search, install, inspect, update, unpublish, browse, tap
- Install from direct HTTP(S) URL
- `/reload-skills` slash command
- Preload on startup: `-s skill1,skill2`
- Per-platform enable/disable
- `hermes skills list` shows enabled/disabled status
- `hermes skills config` — per-platform enable
- `skill_manage` refuses writes on pinned skills
- `skill_manage` edits `external_dirs` skills in place
- Skill telemetry: `~/.hermes/skills/.usage.json`
- `use_count`, `view_count`, `patch_count`, `last_activity_at`, `state`, `pinned`
- Skill AST audit (`skills_ast_audit.py`)
- Skills guard (`skills_guard.py`)
- Skill sync (`skills_sync.py`)
- Automated skill generation during conversation loop (background review fork)
- References/templates sub-files in skill dirs
- `.archive/` excluded from index walk
- Curator manages skill lifecycle: grade, consolidate, prune, archive
- Bundled + hub skills protected from mutation

### Bundled Skills (from `skills/`)

- `autonomous-ai-agents` — spawning/orchestrating agents
- `creative` — ASCII art, diagrams, visual design, etc.
- `data-science` — Jupyter kernels, data analysis
- `diagramming` — Excalidraw diagrams (arch, flow, seq)
- `domain` — domain intelligence (subdomain discovery, SSL, WHOIS, DNS)
- `email` — terminal email (Himalaya)
- `gaming` — Minecraft modpacks, Pokemon player
- `gifs` — GIF search/download
- `github` — GitHub workflows (PRs, issues, auth, codebase inspection)
- `inference-sh` — inference.sh platform (150+ AI apps)
- `mcp` — MCP server building/testing/deploying
- `media` — YouTube transcripts, GIFs, Suno music, spectrograms, Spotify
- `mlops` — training, fine-tuning, inference, evaluation, model search
- `note-taking` — Obsidian vault integration (read, search, create, edit)
- `productivity` — docs, spreadsheets, presentations, Linear, Airtable, Notion, Google Workspace, OCR, PDF editing, Maps, Teams pipeline
- `research` — arXiv, blog/RSS monitoring, Polymarket, LLM Wiki, paper writing
- `smart-home` — Philips Hue lights
- `social-media` — X/Twitter via xurl CLI
- `apple` — macOS desktop integration (Finder, native apps, accessibility, screenshots)
- `yuanbao` — Tencent Yuanbao groups

### Optional Skills (from `optional-skills/`)

- **autonomous-ai-agents**: `blackbox`, `honcho`
- **blockchain**: `evm`, `hyperliquid`, `solana`
- **communication**: `one-three-one-rule`
- **creative**: `blender-mcp`, `concept-diagrams`, `hyperframes`, `kanban-video-orchestrator`, `meme-generation`
- **devops**: `cli`, `docker-management`, `pinggy-tunnel`, `watchers`
- **dogfood**: `adversarial-ux-test`
- **email**: `agentmail`
- **finance**: `3-statement-model`, `comps-analysis`, `dcf-model`, `excel-author`, `lbo-model`, `merger-model`, `pptx-author`, `stocks`
- **health**: `fitness-nutrition`, `neuroskill-bci`
- **mcp**: `fastmcp`, `mcporter`
- **migration**: `openclaw-migration`
- **security**: `1password`, `oss-forensics`, `sherlock`
- **software-development**: `rest-graphql-debug`
- **web-development**: `page-agent`

---

## 5. PLUGIN SYSTEM

### Plugin Architecture

- `plugins/` directory scanned at startup
- Plugin types: `backend` (auto-loaded), `standalone` (opt-in), `kind` field
- Registration API via `ctx`: `register_tool`, `register_hook`, `register_memory_provider`, `register_context_engine`, `register_cli_command`, `register_web_search_provider`, `register_image_gen_provider`, `register_video_gen_provider`
- Hook lifecycle: `pre_api_request`, `post_api_request`, `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`, `on_session_end`, `on_pre_compress`, `pre_gateway_dispatch`, `pre_approval_request`, `post_approval_response`
- Plugin discovery: subdirectory scans in `plugins/<category>/<name>/`
- `plugin.yaml` metadata: name, version, kind, description, hooks, provides_tools, pip_dependencies, external_dependencies, requires_env
- Page-scoped plugin slots for built-in dashboard pages
- Declarative plugin installation for NixOS module

### Bundled Plugins

**Context Engines:**

- `compressor` (default) — built-in ContextCompressor

**Memory Providers (`plugins/memory/`):**

- `honcho` — Honcho AI-native memory
- `mem0` — Mem0
- `hindsight` — long-term memory with knowledge graph
- `holographic` — local SQLite fact store, FTS5 search, trust scoring
- `byterover` — persistent knowledge tree with `brv` CLI
- `openviking` — session-managed memory
- `retaindb` — cloud memory API
- `supermemory` — semantic long-term memory
- `builtin` (default) — built-in Python memory

**Model Providers (`plugins/model-providers/`):**

- `openai-codex`, `openrouter`, `anthropic`, `gemini`, `deepseek`, `xai`, `nous`, `huggingface`
- `copilot`, `copilot-acp`, `bedrock`
- `minimax`, `minimax_cn`, `minimax_oauth`, `zai` (GLM)
- `kimi-coding`, `alibaba`, `alibaba-coding-plan`, `xiaomi` (MiMo), `kilocode`
- `gmi` (GMI Cloud), `stepfun`, `azure-foundry`, `qwen-oauth`, `ai-gateway`
- `opencode-zen`, `opencode-go`, `ollama-cloud`, `arcee`, `novita`, `nvidia`
- `custom`

**Image Gen Providers (`plugins/image_gen/`):**

- `openai`, `openai-codex`, `fal`, `xai`

**Video Gen Providers (`plugins/video_gen/`):**

- `fal`, `xai`

**Web Search Providers (`plugins/web/`):**

- `brave_free`, `ddgs` (DuckDuckGo), `exa`, `firecrawl`, `parallel`, `searxng`, `tavily`, `xai`

**Browser Providers (`plugins/browser/`):**

- `browser_use`, `browserbase`, `firecrawl`

**Platform Adapters (`plugins/platforms/`):**

- `discord`, `google_chat`, `irc`, `line`, `mattermost`, `ntfy`, `simplex`, `teams`

**Standalone Plugins:**

- `disk-cleanup` — auto-cleanup of ephemeral session files
  - Hooks: `post_tool_call`, `on_session_end`
  - Slash: `/disk-cleanup` status/dry-run/quick/deep/track/forget
- `google_meet` — join Meet calls, transcribe, speak, follow up
  - v1: transcribe-only (headless Chromium + live captions)
  - v2: realtime duplex audio (OpenAI Realtime + BlackHole/PulseAudio)
  - v3: remote node host (gateway on Linux, Chrome+signed-in profile on Mac)
  - Tools: `meet_join`, `meet_leave`, `meet_status`, `meet_transcript`, `meet_say`
  - Explicit-by-design: only joins `meet.google.com` URLs passed in
- `spotify` — Spotify integration
  - 7 tools: playback, devices, queue, search, playlists, albums, library
  - PKCE OAuth, `hermes auth spotify`
- `teams_pipeline` — Microsoft Teams meeting pipeline
  - Operator CLI flows
  - Graph-backed transcript-first meeting summaries
  - Durable runtime state
  - Subscriptions, jobs, meetings modules

**Observability:**

- `langfuse` — Langfuse observability
  - Hooks: `pre_api_request`, `post_api_request`, `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`

---

## 6. GATEWAY — MULTI-PLATFORM MESSAGING

### Supported Platforms (25)

1. Telegram
2. Discord
3. Slack
4. WhatsApp
5. Signal
6. Matrix
7. Email (IMAP/SMTP via Himalaya)
8. SMS
9. Mattermost
10. Home Assistant
11. DingTalk
12. Feishu / Lark
13. WeCom
14. BlueBubbles (iMessage on macOS)
15. Weixin (WeChat)
16. Yuanbao (Tencent 元bao)
17. IRC
18. Google Chat
19. Microsoft Teams (plugin)
20. NTFY
21. Simplex
22. Line
23. QQ Bot
24. Webhook
25. API Server (Open WebUI adapter)

### Gateway Core

- `gateway/run.py` + `gateway/session.py`
- `gateway/platforms/<name>/adapter.py` per platform
- `gateway/platforms/<name>/plugin.yaml` per platform
- `builtin_hooks/` extension point (none shipped yet)
- Runtime-metadata footer on final replies (`/footer`)
- Inactivity-based agent timeout (tracks tool activity, not wall-clock)
- Infinite timeout support + periodic notifications
- Duplicate message prevention + dedup
- Typing indicator paused during approval waits
- Caption exact-line match (not substring match)
- MEDIA: tag extraction/stripping from streamed gateway messages
- Profile-aware service units
- Thread-safe PairingStore with atomic writes
- Make-hygiene hard message limit configurable
- Opt-in runtime-metadata footer
- `pre_gateway_dispatch` hook
- `pre_approval_request` / `post_approval_response` hooks

### Platform-Specific Features

**Telegram:**

- Chat allowlists for groups and forums
- Emoji reactions for approval status
- Group topics skill binding for supergroup forums
- Fresh finals for stale preview streams
- Markdown tables rendered as row-group bullets
- Native multi-image sending
- Centralized audio routing + FLAC support + Telegram document fallback
- Command names sanitized
- Per-platform disabled skills respected

**Discord:**

- Opt-in toolsets
- ID injection + tool split
- Feishu wiring
- Coerce `limit` to int
- Channel ignored/no_thread_channels
- Skills registered as native slash commands
- `/approve`, `/deny`, `/queue`, `/background`, `/btw` native slash commands

**Slack:**

- Thread engagement (auto-respond in bot-started + mentioned threads)
- `strict_mention` config
- `channel_skill_bindings`
- Approval buttons + thread context preservation
- mrkdwn in edit_message

**Signal:**

- Native formatting (markdown → bodyRanges, reply quotes, reactions)
- Full MEDIA: tag delivery (send_image_file, send_voice, send_video)

**Matrix:**

- Tier 1 feature parity (reactions, read receipts, rich formatting, room management)
- `MATRIX_REQUIRE_MENTION`, `MATRIX_AUTO_THREAD`
- Encrypted media, auth recovery, cron E2EE, Synapse compat
- CJK input, E2EE, reconnect

**Feishu:**

- Interactive card approval buttons
- Reconnect + ACL fixes
- Native multi-image sending

**Mattermost:**

- File attachments (DOCUMENT type when post has files)
- Native multi-image sending

**Microsoft Teams (plugin):**

- Graph-backed transcript-first meeting summaries
- Operator CLI
- Subscriptions
- Jobs, meetings runtime

**Offline / No-gateway:**

- `send_message` tool checks if gateway running; falls back
- Webhook tool constrained to safe tools only

### DM Authorization / Pairing

- `hermes pairing list / approve / revoke`
- `/approve`, `/deny` in gateway
- `PairingStore` atomic writes
- Approval session key isolated per turn
- Active-session guard bypass for `/approve`, `/deny`, `/stop`, `/new`

---

## 7. VOICE & TRANSCRIPTION

### STT (Voice → Text)

- Provider auto-detection
  1. Local faster-whisper (free, no key: pip install faster-whisper)
  2. Groq Whisper (free tier: GROQ_API_KEY)
  3. OpenAI Whisper (paid: VOICE_TOOLS_OPENAI_KEY)
  4. Mistral Voxtral (MISTRAL_API_KEY)
- Config: `stt.enabled`, `stt.provider`, `stt.local.model`
- Local model options: tiny, base, small, medium, large-v3

---

## 8. MODEL PROVIDERS (COMPLETE INVENTORY)

### Native / Plugin Providers

- OpenRouter — API key — `OPENROUTER_API_KEY`
- Anthropic — API key — `ANTHROPIC_API_KEY`
- Nous Portal — OAuth — `hermes auth`
- OpenAI Codex — OAuth — `hermes auth`
- GitHub Copilot — Token / OAuth — `hermes model` → Copilot
- Google Gemini / AI Studio — API key — `GOOGLE_API_KEY` / `GEMINI_API_KEY`
- DeepSeek — API key — `DEEPSEEK_API_KEY`
- xAI / Grok — API key — `XAI_API_KEY`
- Hugging Face — Token — `HF_TOKEN`
- Z.AI / GLM — API key — `GLM_API_KEY`
- MiniMax — API key — `MINIMAX_API_KEY`
- MiniMax CN — API key — `MINIMAX_CN_API_KEY`
- MiniMax OAuth — OAuth (PKCE) — Browser flow
- Kimi / Moonshot — API key — `KIMI_API_KEY`
- Alibaba / DashScope — API key — `DASHSCOPE_API_KEY`
- Xiaomi MiMo — API key — `XIAOMI_API_KEY`
- Kilo Code — API key — `KILOCODE_API_KEY`
- Vercel AI Gateway — API key — `AI_GATEWAY_API_KEY`
- OpenCode Zen — API key — `OPENCODE_ZEN_API_KEY`
- OpenCode Go — API key — `OPENCODE_GO_API_KEY`
- Qwen OAuth — OAuth — `hermes login --provider qwen-oauth`
- GMI Cloud — API key — Plugin
- Azure AI Foundry — API key — Plugin
- LM Studio — Local — First-class provider
- Tencent Tokenhub — API key — Plugin
- Ollama Cloud — API key — Plugin
- Arcee — API key — Plugin
- Novita — API key — Plugin
- Nvidia — API key — Plugin
- Bedrock — AWS — Plugin
- Copilot ACP — External — `COPILOT_CLI_PATH` or Copilot CLI
- Custom endpoint — Config — `model.base_url` + `model.api_key`

---

## 9. MEMORY SYSTEM

- `builtin`, `honcho`, `mem0`, `hindsight`, `holographic`, `byterover`, `openviking`, `retaindb`, `supermemory`
- Memory hooks: `on_session_end`, `on_pre_compress`, shutdown on `/new` or `/resume`
- Profile-scoped memory isolation
- Thread gateway user_id → memory plugin for per-user scoping
- Secret redaction in memory operations

---

## 10. MCP (MODEL CONTEXT PROTOCOL)

- Native MCP client; `hermes mcp serve / add / remove / list / test / configure / reload`
- MCP OAuth 2.1 PKCE; OSV malware scanning; circuit breaker
- Dynamic tool discovery; 401 handling; schema prefix stripping for Anthropic
- Configurable in config.yaml; auto-discovery from config

### ACP (AGENT COMMUNICATION PROTOCOL)

- `hermes acp` ACP server mode
- ACP adapter modules: entry, server, session, auth, permissions, edit_approval, tools, events
- Transports: Hermes tools as MCP server, Copilot ACP client, Codex transport
- IDE support: VS Code, Zed, JetBrains

---

## 11. SCHEDULING & BACKGROUND

- CLI: `hermes cron list / add / edit / pause / resume / run / status`; slash `/cron`
- Schedules: duration, natural language, cron, ISO timestamp
- Per-job overrides: skills, model/provider, script, no_agent, context_from, workdir, profile, deliver, enabled_toolsets
- 3-minute hard interrupt; `.tick.lock`; skip_memory; header/footer framing
- Background processes: `terminal(background=True, notify_on_complete=True)`
- Webhooks: `hermes webhook subscribe / list / remove / test`; safe-tools-only execution

---

## 12. KANBAN — MULTI-AGENT WORK QUEUE

- SQLite durable board
- CLI verbs: init, create, list, show, assign, link, unlink, comment, complete, block, unblock, archive, tail, watch, stats, runs, log, dispatch, daemon, gc
- Worker tools: show, complete, block, heartbeat, comment, create, link
- Orchestrator tools: list, unblock
- Dispatcher in gateway; reclaims stale claims; atomic claims

---

## 13. DELEGATION (SUBAGENTS)

- `delegate_task` for single task or batch parallel tasks
- Roles: leaf, orchestrator; depth=1 by default
- Synchronous; isolated context + terminal per child
- Uses same provider pool + credentials as parent

---

## 14. SECURITY

- Approval modes: manual, smart, off; `redact_secrets` / `redact_pii`
- SSRF protection, cron path traversal hardening, cross-session isolation, DM pairing

---

## 15. RELEASE HISTORY v0.3 → v0.12

- **v0.12**: Autonomous Curator, self-improvement upgrade, LM Studio, Azure Foundry, MiniMax OAuth, Tencent Tokenhub, Google Meet, TTS provider registry, Vercel Sandbox, 57% cold-start cut
- **v0.8**: Background auto-notifications, live Model Switching, MCP OAuth 2.1 + OSV scanning, security hardening, shared thread sessions
- **v0.7**: ACP adapter, dashboard/plugins, gateway hooks
- **v0.6**: Self-improving skills background review fork
- **v0.4**: Achievement share cards
- **v0.3**: s6 container supervision, ACP backend

---

## 16. OBSERVABILITY

- Langfuse plugin with pre/post hooks
- Insights analytics, per-skill telemetry, account usage, rate limits

---

## 17. OBSIDIAN / EXCALIDRAW

- Note-taking skill: read, search, create, edit markdown notes in local vault
- Interacts with frontmatter, wikilinks, tags
- Excalidraw skill: hand-drawn style JSON diagrams; embed/render in notes

---

## 18. COMPUTER USE (CUA)

- `computer_use` tool for macOS
- Accessibility API, screenshot, mouse/keyboard simulation, Finder/native app interaction

---

## 19. SPECIAL CAPABILITIES

- Patch tool with V4A multi-file patch format
- LSP client workspace support and server discovery
- Task planning: `/goal`, `/queue`, `/steer`, `/background`
- Terminal checkpoints + `/rollback`
- Secret management: Bitwarden secret source, credential pool exhaustion-aware rotation

---

## 20. CODE PATHS / EXTENSION POINTS

- `tools/<toolname>.py`
- `toolsets.py`
- `hermes_cli/commands.py`
- `cli.py`
- `gateway/platforms/<name>/`
- `plugins/<category>/<name>/`
- `context.engine`, `memory.provider` in `config.yaml`

### Repo Layout

```
hermes-agent/
├── run_agent.py
├── model_tools.py
├── toolsets.py
├── cli.py
├── hermes_state.py
├── hermes_constants.py
├── agent/
├── hermes_cli/
├── tools/
├── gateway/
├── cron/
├── plugins/
├── optional-skills/
├── skills/
├── ui-tui/
├── acp_adapter/
├── scripts/
├── website/
└── tests/
```

---

## 21. CONFIG KEYS

- `model`, `agent`, `terminal`, `compression`, `display`, `stt/tts`, `memory`, `security/privacy`, `approvals`, `delegation`, `checkpoints`, `prompt_caching`, `context`, `auxiliary`, `curator`, `kanban`, `hooks`

---

## 22. ENV VARS

- Provider keys: `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `VOICE_TOOLS_OPENAI_KEY`, `MISTRAL_API_KEY`, `ELEVENLABS_API_KEY`, `MINIMAX_API_KEY`, `MINIMAX_CN_API_KEY`, `DEEPSEEK_API_KEY`, `XAI_API_KEY`, `HF_TOKEN`, `GLM_API_KEY`, `KIMI_API_KEY`, `DASHSCOPE_API_KEY`, `XIAOMI_API_KEY`, `KILOCODE_API_KEY`, `AI_GATEWAY_API_KEY`, `OPENCODE_ZEN_API_KEY`, `OPENCODE_GO_API_KEY`
- Memory/services: `OPENVIKING_ENDPOINT`, `RETAINDB_API_KEY`, `SUPERMEMORY_API_KEY`, `COPILOT_GITHUB_TOKEN`, `COPILOT_CLI_PATH`
- Runtime: `HERMES_HOME`, `HERMES_MEDIA_ALLOW_DIRS`, `HERMES_REDACT_SECRETS`, `HERMES_YOLO_MODE`, `HERMES_PORTAL_BASE_URL`, `HERMES_KANBAN_TASK`, `HERMES_KANBAN_BOARD`, `HASS_TOKEN`
- Generic fallbacks: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GEMINI_API_KEY`
- Platform tokens: Telegram bot token, Discord bot token, Slack bot token, etc.

---

## 23. KEY PATHS

- `~/.hermes/config.yaml`
- `~/.hermes/.env`
- `~/.hermes/state.db`
- `~/.hermes/sessions/`
- `~/.hermes/logs/`
- `~/.hermes/skills/`
- `~/.hermes/plugins/`
- `~/.hermes/memories/`
- `~/.hermes/auth.json`
- `~/.hermes/state-snapshots/`
- Profile dirs: `~/.hermes/profiles/<name>/`
- Source: `~/.hermes/hermes-agent/`

---

## 24. OBSIDIAN MCP / OBSIDIAN SKILL SCOPE

- No standalone obsidian-mcp server ships in this repo
- Obsidian integration is via the `note-taking` skill
- Excalidraw integration is via the `diagramming/excalidraw` skill

---

## 25. KNOWN GAPS

- No standalone obsidian-mcp server
- `page-agent` is optional web-dev skill only
- `blender-mcp`, `meme-generation` are optional creative skills

---

End of Hermes atomic specification.

---

---

# 4. OpenHuman — Complete Atomic Feature Specification

> *Source: `OPENHUMAN_ATOMIC_FEATURES.md` (July 4th) — v2, corrected*

Source-of-truth dump for comprehension, clone, and reimplementation.
Covers: core runtime, tools, skills, integrations, memory, UI, voice, scheduling, security, agents, wallet, providers, channels, MCP, desktop companion, and more.

---

## 1. CORE RUNTIME & EXECUTION

### Tech Stack

- Rust core (`src/`) — business logic, execution, domains, RPC, persistence, CLI
- React + Tauri v2 desktop app (`app/`) — UI, screens, navigation
- Core runs in-process as tokio task (no sidecar since PR #1061)
- Frontend ↔ core via `http://127.0.0.1:<port>/rpc` with per-launch hex bearer token
- `OPENHUMAN_CORE_TOKEN` env var for CLI/docker/cloud
- `OPENHUMAN_CORE_REUSE_EXISTING=1` for external core debugging

### Agent Loop / Chat Runtime

- `AIAgent` with tool-calling loop in Rust core
- Hint-based model routing: `hint:reasoning`, `hint:fast`, `hint:vision`, `hint:summarize`, `hint:code`
- Concrete model names bypass hints: `anthropic/claude-sonnet-4`
- Per-agent model pins for sub-agents (orchestrator vs leaf)
- Agent turn lifecycle: user input → tool calls → response → next turn
- Streaming response support
- Chat runtime provider chain in React: `Sentry.ErrorBoundary` → `Redux Provider` → `PersistGate` → `BootCheckGate` → `CoreStateProvider` → `SocketProvider` → `ChatRuntimeProvider` → `HashRouter` → `CommandProvider` → `ServiceBlockingGate` → `AppShell`
- Event bus (`src/core/event_bus/`): typed pub/sub + native request/response
  - Broadcast: `publish_global` / `subscribe_global` (fire-and-forget, many subscribers)
  - Native request/response: `register_native_global` / `request_native_global` (one-to-one, zero serialization)
  - Domain events: agent, memory, channel, cron, skill, tool, webhook, system

### Configuration

- Rust: TOML `Config` struct (`src/openhuman/config/schema/types.rs`) with env overrides
- Frontend: centralized `app/src/utils/config.ts` (never raw `import.meta.env`)
- `.env.example` for Rust core + Tauri shell + backend URL
- `app/.env.example` for `VITE_*` vars
- `config.update_autonomy_settings` RPC
- Profile-aware via `OPENHUMAN_WORKSPACE`

### Startup & Lifecycle

- `CoreProcessHandle` in `app/src-tauri/src/core_process.rs`
- `run_server_embedded_with_ready(rpc_token: Some(_))` for embedded core
- Boot gate checks: workspace exists, core healthy, auth valid
- Workspace auto-creation on first launch
- Core restart via IPC command `restart_core_process`
- Daemon health service (`daemonHealthService`)
- Shutdown cleanup for memory providers, connections, cron

---

## 2. TOOL SYSTEM

### Tool Architecture

- Tool registry (`src/openhuman/tool_registry/`)
- Domain-owned tools: each domain has `tools.rs`, re-exported via `src/openhuman/tools/mod.rs`
- Only cross-cutting families stay in `tools/impl/`
- Generated tool schemas (`tools/generated.rs`)
- Tool policy / user filter (`tools/policy.rs`, `tools/user_filter.rs`)
- Tool timeout management (`tool_timeout/`)
- `classify_command` → `CommandClass` (`Read`/`Write`/`Network`/`Install`/`Destructive`)
- `gate_decision(class, tier)` → `Allow`/`Prompt`/`Block`

### Coder Tools (`tools/impl/filesystem/`)

- `file_read` — read file with line numbers (like `cat -n`), image support
- `file_write` — write new file
- `edit_file` — targeted match-and-replace with strict uniqueness checks
- `apply_patch` — apply unified diff
- `glob_search` — find files by glob pattern
- `grep` — ripgrep-style content/file search with context, output modes
- `list_files` — walk directory tree
- `read_diff` — diff between two files or revisions
- `git_operations` — status, diff, log, blame, branch, commit
- `run_linter` — run project linter
- `run_tests` — run project test command
- `csv_export` — export query results as CSV

### System & Utility Tools (`tools/impl/system/`)

- `shell` — run shell command, bounded output, captured exit code
- `node_exec` — run Node.js snippet
- `npm_exec` — run npm/pnpm/yarn script
- `current_time` — get current time in any timezone with formatting
- `schedule` — one-shot "do this once at time T"
- `pushover` — send push notification to devices
- `insert_sql_record` — append row to agent's structured SQL store
- `lsp` — query language server (definitions, references, diagnostics)
- `workspace_state` — inspect current workspace (open files, recent edits, environment)
- `proxy_config` — read or change proxy configuration
- `tool_stats` — self-reflection: tools used in this session and how often

### Browser & Computer Control (`tools/impl/browser/`, `tools/impl/computer/`)

- Browser open URL in embedded CEF webview
- Browser screenshot current page
- Browser inspect image output and metadata
- Mouse: move, click, drag with human-like trajectories
- Keyboard: type text, send key chords
- Human-path cursor movement (not teleporting) — avoids naive bot detection

### Network Tools (`tools/impl/network/`)

- Web search via managed proxy (Parallel) — default no-API-key required
- Self-hosted SearXNG search (`searxng_search`) — opt-in, configurable
- Web scraper: pull clean text from URLs, HTML-to-Markdown
- `http_request` — generic HTTP calls

### Presentation Tools (`tools/impl/presentation/`)

- PowerPoint manipulation (`ppt-rs`)

### Integration Tools (`integrations/tools/`)

- `apify` — web scraping platform
- `google_places` — Google Places API
- `stock_prices` — stock/crypto price lookup
- `twilio` — SMS/voice via Twilio

### Coordination Tools (`agent_orchestration/tools.rs`)

- `todo_write` — maintain structured TODO list across long tasks
- `spawn_subagent` — fresh agent with own context window for subtask
- `spawn_worker_thread` — background work not blocking main conversation
- `delegate` — hand task to specialist archetype
- `archetype_delegation` — route to named archetype (coder, researcher, planner, etc.)
- `skill_delegation` — hand off to installed skill
- `ask_clarification` — pause and ask user precise question
- `plan_exit` — exit planning phase, start executing
- `check_onboarding_status` / `complete_onboarding` — gate behavior on onboarding state

### Memory Tools (`memory_tools/` / `memory/tools.rs`)

- `recall` — search Memory Tree by query (source-scoped, topic-scoped, global)
- `store` — write memory the agent decides is worth keeping
- `forget` — remove memory by ID
- Tree-aware retrieval: drill down topic, fetch global digest

### Cron Tools (`cron/`)

- `cron_add` — create scheduled job (cron expression + agent prompt)
- `cron_list` — list existing jobs and next-run times
- `cron_update` — edit job (schedule, prompt, enabled)
- `cron_remove` — delete job
- `cron_run` — run job once immediately
- `cron_runs` — inspect recent run history

### Voice Tools (`voice/`)

- Speech-to-text via hotkey (push-to-talk / toggle modes)
- Streaming transcription with voice-activity detection
- Hallucination filter (strips silence artefacts)
- Text-to-speech with configurable voice, natural prosody
- Live Google Meet agent: join, transcribe, speak back into call
- Mascot viseme lip-sync against TTS audio stream

### Image Tools (`image/`)

- Image analysis via vision models
- Screenshot capture
- Image processing pipeline

### Accessibility Tools (`accessibility/`)

- `ax_interact` — UI Automation (Windows via UIA, macOS via AXUIElement)
- Cross-platform accessibility APIs

### Screen Intelligence (`screen_intelligence/`)

- Screen capture engine (`capture.rs`, `capture_worker.rs`)
- Screen state monitoring
- Image processing pipeline (`image_processing.rs`, `processing_worker.rs`)
- Vision analysis (`vision.rs`)
- Screen input simulation (`input.rs`)
- Screen intelligence server (`server.rs`)
- Permission gating (`permissions.rs`)

---

## 3. SKILLS SYSTEM

### Skill Architecture

- User-installed skills via the **Skills tab** in the desktop app
- Each skill runs sandboxed with enforced resource limits
- Skills integrate with the Memory Tree as data sources
- Skills can fetch external data, run on a schedule, transform information, respond to events
- Skill registry (`skill_registry/`) — metadata, discovery, installation
- Skill runtime (`skill_runtime/`) — sandboxed execution (QuickJS JS engine removed; metadata-only now)
- Skills exposed as agent-delegatable capabilities
- **Skills are installed from a marketplace, not pre-bundled** — the app ships with a curated catalog

### Bundled Skills

- OpenHuman ships with only **1** built-in skill/template as a demo of the format
- The real skill ecosystem is user-installed from the marketplace

### Skills vs Integrations — Critical Distinction

- **Skills** = sandboxed functional modules (data fetchers, transformers, event responders)
- **Managed Integrations** = 118+ third-party services connected via one-click OAuth (Composio layer)
- Integrations are NOT skills — they're a separate, much richer system (see Section 4)
- Agent Coordination tools can `delegate` to both skills and integrations

---

## 4. INTEGRATIONS — 118+ MANAGED CONNECTORS

### Integration Architecture

- Backend-proxied access via OpenHuman's Composio connector layer
- One-click OAuth flow inside the desktop app
- Zero API keys needed in managed mode
- Direct Composio mode supported (bring your own Composio API key)
- Four exposure surfaces per integration: agent tool, memory source (auto-fetch), profile signal, trigger source

### Integration Catalog (118+ services across categories)

**Email & Calendar:** Gmail, Outlook, Google Calendar, Apple Calendar

**Docs & Storage:** Google Docs, Google Drive, Notion, Dropbox, Airtable

**Code & Dev:** GitHub, Linear, Jira, Figma

**Comms:** Slack, Discord, Microsoft Teams, Telegram, WhatsApp

**CRM & Sales:** Salesforce, HubSpot

**Commerce & Payments:** Stripe, Shopify

**Project Management:** Asana, Trello

**Social:** Twitter/X, Spotify, YouTube

**Finance:** Polymarket

### Integration Tools (`integrations/tools/`)

- `apify` — web scraping platform connector
- `google_places` — location search
- `stock_prices` — financial data
- `twilio` — messaging platform

### Auto-Fetch

- 20-minute loop walks active connections
- Pulls fresh data into Memory Tree
- No prompts or polling loops to write
- Configurable per-integration
- Each integration shows status: Not connected / Connected / Manage
- **Per-provider sync interval** (e.g., Gmail every 15 min by default)
- **Daily budget cap** per connection — bounds API usage
- **OAuth scope binding** — auto-fetch respects the scope you granted
- Revocation stops syncing at next tick; existing chunks remain local

### Messaging Channels (3 special integrations)

- **Telegram** — primary two-way channel, 80+ actions, encrypted credentials, group topics
- **Discord** — send/receive, skills as native slash commands
- **Web** — browser-based chat within desktop app

---

## 5. MEMORY SYSTEM

### Memory Tree Architecture

- Local-first knowledge base, deterministic bucket-sealed pipeline
- NOT a vector database — structured, queryable, summary-backed Markdown on device
- All data canonicalized into ≤3k-token Markdown chunks
- Stored in SQLite on user's machine
- Obsidian-compatible Markdown vault (`wiki/`)

### Pipeline Stages

1. **Canonicalize** — source adapters → normalized Markdown + provenance metadata
2. **Chunker** — deterministic IDs, ≤3k-token bounded segments
3. **Content Store** — atomic .md files on disk (body + tags)
4. **Store** — persistence (chunks, scores, summaries, jobs)
5. **Score** — signals + embeddings + entity extraction
6. **Trees** — source / topic / global summary trees
7. **Retrieval** — search / drill_down / topic / global / fetch

### Three Trees, Three Scopes

- **Source trees** — per-source rolling buffer (L0 → L1 → L2 cascading). One per Gmail label, Slack channel, uploaded doc
- **Topic trees** — per-entity summaries, materialized lazily by hotness (person, project, ticker, repo)
- **Global tree** — daily global digest across everything ingested

### Background Workers & Job Kinds

- `extract_chunk` — deep score + entity extraction, decides admitted/dropped
- `append_buffer` — adds admitted leaf to tree buffer, may trigger seal
- `seal` — compresses L0 into L1 summary, cascades up
- `topic_route` — routes leaf into per-entity topic trees, gated by hotness
- `digest_daily` — builds global daily digest node

### Memory Domains (16 sub-modules)

- `memory/` — core orchestration
- `memory_archivist/` — archival and consolidation
- `memory_conversations/` — conversation memory with cross-thread FTS5 search
- `memory_diff/` — change tracking
- `memory_entities/` — entity extraction and tracking
- `memory_graph/` — knowledge graph representation
- `memory_queue/` — durable job queue for follow-up work
- `memory_search/` — search infrastructure
- `memory_sources/` — source adapter registry
- `memory_store/` — SQLite persistence
- `memory_sync/` — sync across workspaces
- `memory_tools/` — agent-facing memory tools
- `memory_tree/` — tree structure and traversal

### Disk Layout

- `memory_tree/chunks.db` — chunks, scores, summaries, entity index, jobs, hotness
- `wiki/` — Markdown vault (Obsidian-compatible with wikilinks/frontmatter)
- Optional `agentmemory` backend for cross-agent memory sharing

---

## 6. SUBCONSCIOUS LOOP

### Background Agent Thread

- Periodic tick evaluation and execution system
- Loads user-defined and system tasks
- Reads workspace state and recent memory
- Decides actions: skip (noop), act (execute), escalate (deeper agent)
- Each tick independent — if running when next starts, old cancelled

### Task Types

- **System tasks** (seeded automatically, can be disabled):
  - Check connected skills for errors/disconnections
  - Review new memory updates for actionable items
  - Monitor system health (local model, memory, connections)
- **User tasks** (added manually from UI, toggle on/off, edit, delete):
  - "Check urgent emails" (read-only)
  - "Send daily summary to Slack" (write intent)
  - "Summarize Notion updates" (read-only)

### Decisions

- **Skip** — nothing relevant right now
- **Act** — execute task (write-intent tasks escalate for approval)
- **Escalate** — needs deeper reasoning, hand off to cloud agent

### Dreaming State

- Offline consolidation pass when user away
- Distills day's chunks into longer-horizon summaries
- Refreshes topic trees for heated entities
- Surfaces patterns across sources
- Mascot animates differently while dreaming
- Dreams folded into Memory Tree on wake

---

## 7. VOICE & MEETINGS

### Speech-to-Text

- Hotkey push-to-talk and toggle modes
- Cross-platform mic capture with voice-activity detection
- Streaming transcription via whisper-rs (local, Metal-accelerated on macOS)
- Hallucination filter: strips "Thanks for watching", silence artefacts
- Postprocess: punctuation, capitalisation, dictation cleanup
- Can replace active text input or send directly to agent

### Text-to-Speech

- Hosted TTS model with configurable voice
- Natural timing and prosody
- Viseme map for mascot lip-sync

### Live Google Meet Agent

- Joins Google Meet via embedded webview
- Streams audio to STT in real time
- Transcribes everyone in call
- Writes structured notes into Memory Tree
- Can speak back into meeting as outbound camera/mic stream
- Mascot face piped as camera feed
- Operates as real participant

### Audio Toolkit (`audio_toolkit/`)

- Audio capture, processing, and playback
- CPAL (`cpal` crate) for cross-platform audio
- Hound (`hound` crate) for WAV encoding

---

## 8. DESKTOP COMPANION (MASCOT)

### Mascot Features

- Animated desktop character (Rive animation: `tiny_mascot.riv`)
- Mood states: idle, thinking, listening, talking, surprised, dreaming
- Transitions based on agent activity
- Lip-sync via viseme map against TTS audio
- Conversation-level cue reactions (success, uncertainty, warning, failure)
- Memory-backed personality: remembers across sessions
- Background thinking via Subconscious Loop
- Dreaming animation during offline consolidation
- Native window management (`mascot_native_window` in tauri)
- Position and overlay control

### Desktop Companion Pipeline (`desktop_companion/`)

- Pipeline for processing agent output to mascot reactions (`pipeline.rs`)
- Session management for companion state (`session.rs`)
- Handoff between states (`handoff.rs`)
- Event bus integration (`bus.rs`)
- Pointing/gesture system (`pointing.rs`)

---

## 9. AGENT ORCHESTRATION & TEAMS

### Agent Teams (`agent_orchestration/agent_teams/`)

- Multi-agent coordination
- Orchestrator → leaf agent delegation
- Per-agent model pins (orchestrator gets strong model, leaf gets fast)
- Isolated context per sub-agent
- Team-level config in `config.toml`:
  - `[orchestrator]` — lead model
  - `[teams.research]` — lead_model + agent_model
  - `[teams.code]` — agent_model

### 14 Built-in Archetypes (`.claude/agents/`)

| Archetype                            | Role                |
| ------------------------------------ | ------------------- |
| `architectobot`                    | Architecture design |
| `build-agent`                      | Build/deployment    |
| `codecrusher`                      | Intensive coding    |
| `deploy-agent`                     | Deployment          |
| `designguru`                       | UI/UX design        |
| `dev-agent`                        | General development |
| `memory-keeper`                    | Memory management   |
| `mobile-agent`                     | Mobile development  |
| `pr-manager` / `pr-manager-lite` | PR management       |
| `pr-reviewer`                      | Code review         |
| `qualityqueen`                     | Quality assurance   |
| `taskmaster`                       | Task management     |
| `test-agent`                       | Testing             |
| `ship-and-babysit`                 | Release + monitor   |

### Command Center & Workflows

- `agent_orchestration/command_center/` — central dispatch
- `workflows/` — multi-step workflows
- `workflow_runs/` — execution tracking
- `worktree.rs` — git worktree management for parallel agent work
- `agent_registry/` — available agents registry
- `agent_experience/` — agent UX and interaction patterns

---

## 10. MODEL ROUTING & PROVIDERS

### Router Provider (`routing/`)

- `resolve(model)` → `(provider_index, model_name)`
- Hint prefixes: `hint:reasoning`, `hint:fast`, `hint:vision`, `hint:summarize`, `hint:code`
- Routes remappable at runtime
- Per-agent model pins (inline or config.toml)
- One subscription, many providers — backend brokers access

### Provider Architecture (`routing/provider.rs`)

- Multi-provider wrapping
- Factory pattern for provider creation
- Health checks
- Telemetry
- Quality assessment (`quality.rs` — refusal/empty-noise detection via aho-corasick DFA)

### Local AI (`local_ai/`)

- Ollama integration for on-device models
- Self-hosted model serving
- Embedding generation on-device
- Memory tree building on-device when Local AI enabled

### Model Council (`model_council/`)

- Multi-model deliberation
- Council registry for configured councils

---

## 11. SCHEDULING & CRON

### Cron System (`cron/`)

- Recurring jobs on cron schedules
- One-off reminders
- Arbitrary agent runs on schedule
- Run history tracking per job
- Each cron run is a normal agent invocation (uses any tool)
- Backend: `cron` crate for expression parsing

### Scheduler Gate (`scheduler_gate/`)

- Battery-aware scheduling (laptop throttling via `starship-battery`)
- System signal monitoring
- Background LLM work throttling

### Webhooks (`webhooks/`)

- Incoming webhook triggers
- Safe-tools-only execution for webhook-triggered runs

---

## 12. MESSAGING CHANNELS — 17 PLATFORMS

### Channel Providers (`channels/providers/`)

| Channel                   | Key Features                                                                                          |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Telegram**        | Primary channel, two-way, 80+ actions, encrypted credentials, group topics, emoji reactions           |
| **Discord**         | Send/receive, channel management, skills as native slash commands,`/approve`/`/deny`              |
| **Slack**           | Thread engagement, strict_mention, channel skill bindings, approval buttons, mrkdwn                   |
| **Signal**          | Native formatting (markdown→bodyRanges), reply quotes, reactions, full MEDIA tag delivery            |
| **Matrix**          | E2E encryption, reactions, read receipts, rich formatting, room management, Synapse compat, CJK input |
| **WhatsApp**        | WhatsApp Web via WhatsApp-Rust v0.5, SQLiteStore, group sender-key, LID-addressed contacts            |
| **Email**           | IMAP/SMTP (Himalaya-backed), Gmail native ingest path, Outlook support                                |
| **Mattermost**      | File attachments, multi-image sending                                                                 |
| **iMessage**        | Via BlueBubbles on macOS                                                                              |
| **Lark/Feishu**     | Interactive card approval buttons, reconnect, multi-image, ACL fixes                                  |
| **DingTalk**        | Messaging                                                                                             |
| **WeCom**           | Messaging                                                                                             |
| **IRC**             | IRC channel                                                                                           |
| **QQ**              | QQ bot                                                                                                |
| **Yuanbao**         | Tencent Yuanbao groups (COS HMAC-SHA1 signing)                                                        |
| **Microsoft Teams** | Graph-backed transcripts, operator CLI, meetings (plugin)                                             |
| **Web**             | Browser-based chat within desktop app, messages stay local                                            |

### Channel Architecture

- `channels/traits.rs` — channel trait interface
- `channels/context.rs` — channel-aware context
- `channels/proactive.rs` — proactive messaging
- `channels/routes.rs` — HTTP routes
- `channels/controllers/` — controller endpoints
- `channels/cli.rs` / `channels/commands.rs` — CLI + slash commands
- `channels/bus.rs` — event bus integration

### Backfill Binaries

- `slack-backfill` — bulk Slack history import
- `gmail-backfill-3d` — 3-day Gmail backfill

---

## 13. UI & FRONTEND

### Routing (`AppRoutes.tsx`, HashRouter)

- `/` — Welcome
- `/onboarding/*` — multi-step onboarding
- `/home` — main dashboard
- `/human` — human/agent interaction hub
- `/intelligence` — intelligence/insights
- `/skills` — skills management + integration connections
- `/chat` — chat interface
- `/channels` — messaging channels
- `/invites` — team invites
- `/notifications` — notification center
- `/rewards` — rewards/achievements
- `/settings/*` — settings pages

### State (Redux Toolkit)

- `accounts`, `channelConnections`, `chatRuntime`, `coreMode`, `deepLinkAuth`, `mascot`, `notification`, `providerSurface`, `socket`, `thread`

### Services (`app/src/services/`)

- `apiClient`, `socketService`, `coreRpcClient`, `coreCommandClient`, `chatService`, `analytics`, `notificationService`, `webviewAccountService`, `daemonHealthService`, domain `api/*` clients

### Tauri Shell (`app/src-tauri/`)

- `core_process`, `core_rpc`, `cdp`, `cef_preflight`/`cef_profile`, `dictation_hotkeys`, `file_logging`, `mascot_native_window`, `screen_capture`, `window_state`
- Per-platform channel scanners: `discord_scanner`, `slack_scanner`, `telegram_scanner`, `whatsapp_scanner`
- `meet_audio`, `meet_call`, `meet_video`, `fake_camera` — Google Meet
- `webview_accounts`, `webview_apis` — embedded webviews
- IPC commands: `greet`, `write_ai_config_file`, `ai_get_config`, `ai_refresh_config`, `core_rpc_relay`, `core_rpc_token`, `start_core_process`, `restart_core_process`

### Visual Design

- Ocean primary `#4A83DD`, sage/amber/coral semantics
- Typography: Inter + Cabinet Grotesk + JetBrains Mono
- 14+ language translations (ar, bn, de, es, fr, hi, id, it, ko, pl, pt, ru, zh-CN)
- i18n via `useT()` hook, CI enforces parity

---

## 14. SECURITY

### Autonomy & Permissions

- `[autonomy]` config block → `SecurityPolicy`
- Tiers: `readonly` / `supervised` / `full`
- `workspace_only` flag, `trusted_roots`, `allow_tool_install` gate
- Configurable via Settings → Agent access or `config.update_autonomy_settings`

### Path Security

- **`action_dir`** — agent's read/write root (default: `~/OpenHuman/projects`)
- **`workspace_dir`** — internal state (`~/.openhuman/users/<id>/workspace`), agent tools CANNOT write here
- `is_workspace_internal_path` fail-closed regardless of tier/trusted_roots
- `is_always_forbidden` — system/credential dirs unconditionally blocked

### Command Permission Model

- `classify_command` → `CommandClass` (Read/Write/Network/Install/Destructive)
- Unrecognized commands → `Write`
- `gate_decision(class, tier)` → Allow/Prompt/Block

### Approval Gate

- ON by default (opt out: `OPENHUMAN_APPROVAL_GATE=0`)
- Parks interactive chat turns only; background/cron allowed through
- Frontend: `ApprovalRequestCard`
- 10-min TTL → Auto-Deny

### Sandbox (`sandbox/`, `cwd_jail/`)

- Docker: remote/cron sandbox
- Local OS jail: Landlock (Linux), Seatbelt (macOS), AppContainer (Windows)
- Noop fallback
- `sandbox_mode = "sandboxed"` opt-in per agent

### Encryption & Keyring

- `encryption/` domain — local data encryption
- OS keyring integration (`keyring/`):
  - Apple Keychain (macOS), Windows Credential Manager, Linux Secret Service / kernel keyring
- `keyring_consent/` — permission flows for keyring access

### Privacy

- Core never calls third-party API directly (default managed mode)
- OAuth tokens never on disk in plaintext (managed mode)
- Agent only sees tool call results, not credentials
- Audio capture local, streaming STT through backend, no recording retained
- TTS audio streamed and discarded
- Memory Tree data stays on device
- `prompt_injection/` — prompt injection detection and mitigation

---

## 15. MCP (MODEL CONTEXT PROTOCOL) — FULL STACK

### MCP Client (`mcp_client/`)

- Native MCP client implementation
- `client.rs` — MCP client with transport management
- `client_helpers.rs` — helper utilities
- `registry.rs` — connected server registry
- `sanitize.rs` — tool output sanitization
- `setup_agent.rs` — agent configuration for MCP
- `stdio.rs` — stdio transport for local MCP servers
- Dynamic tool discovery from connected MCP servers
- Tool result proxying into agent tool registry
- Integration tests: `setup_agent_integration_test.rs`

### MCP Server (`mcp_server/`)

- OpenHuman exposes its tools as an MCP server for external clients
- `http.rs` — HTTP+SSE transport
- `stdio.rs` — stdio transport
- `protocol.rs` — JSON-RPC protocol implementation
- `resources.rs` — resource exposure
- `session.rs` — session management
- Tools subsystem: `tools/dispatch.rs`, `tools/params.rs`, `tools/specs.rs`, `tools/types.rs`
- `write_dispatch.rs` — write-capable tool dispatch
- SEARXNG search exposed to external MCP clients

### MCP Registry (`mcp_registry/`)

- Registry of connected MCP servers
- Server metadata, capabilities, and health status
- Dynamic registration and removal

### MCP Audit (`mcp_audit/`)

- Audit trail for MCP tool calls
- Security and compliance tracking
- Call provenance and result logging

### Test Stub

- `src/bin/test_mcp_stub.rs` — standalone MCP test server binary

---

## 16. WALLET & WEB3

### Wallet (`wallet/`)

- Multi-chain wallet signing
- BIP-39 mnemonic → seed (via `coins-bip39`)
- **Bitcoin**: P2WPKH PSBT build/sign/broadcast, HASH160, `secp256k1`
- **Ethereum/EVM**: via `ethers-core` + `ethers-signers`
- **Solana**: ed25519 transaction signing, ATA derivation, base58 addresses, `curve25519-dalek`
- **Tron**: base58check addresses, secp256k1 derivation
- ABI encoding/decoding (`abi.rs`)
- Chain configurations (`chains/`)
- RPC endpoint management (`rpc.rs`)
- Wallet execution engine (`execution.rs`)

### Web3 (`web3/`)

- DApp integration (`dapp/`)
- Token swaps (`swap/`)
- Cross-chain bridge (`bridge/`)
- Web3 client (`client.rs`)
- Web3 store (`store.rs`)

### x402 (`x402/`)

- HTTP 402 Payment Required protocol support
- Blockchain-based micropayments for API access

---

## 17. TEAM, BILLING & MONITORING

### Team Features (`team/`)

- Multi-user workspace support, team invitations (`/invites` route), role-based access

### People (`people/`)

- Contact/people management, entity tracking across conversations

### Billing (`billing/`)

- Subscription management, plan tiers, usage tracking

### Cost Tracking (`cost/`)

- Per-call token cost tracking, model pricing awareness, cost aggregation

### Health & Observability

- `health/` — system health endpoints
- `heartbeat/` — liveness checks
- `doctor/` — diagnostic tool
- `monitor/` — system monitoring
- Prometheus metrics export
- Sentry error tracking (with `before_send` filter)
- OpenTelemetry tracing and metrics (OTLP)
- Structured logging via `tracing` + `tracing-subscriber`

### Learning System (`learning/`)

- User profile building (`user_profile.rs`)
- Reflection loop (`reflection.rs`) — agent reviews past interactions
- Transcript ingest pipeline (`transcript_ingest/`)
- Tool usage tracking (`tool_tracker.rs`)
- LinkedIn enrichment (`linkedin_enrichment.rs`)
- Learning scheduler (`scheduler.rs`)
- Stability detection (`stability_detector.rs`)
- Profile.md renderer (`profile_md_renderer.rs`)
- Prompt section generation (`prompt_sections.rs`)
- Candidate extraction (`candidate.rs`)
- Entity extraction for learning (`extract/`)

### Codegraph (`codegraph/`)

- Codebase knowledge graph with full-text index (`index.rs`)
- Symbol/code search (`search.rs`)
- Graph store (`store.rs`)
- Codegraph tools for agent (`tools.rs`)

---

## 18. ADDITIONAL CAPABILITIES

### Context & Token Compression

- `context/` — context window management, automatic compression at token limit
- **TokenJuice** (`tokenjuice/`) — smart compression pipeline (classify → match rule → reduce)
- Three-layer rule overlay: Builtin, User (`~/.config/tokenjuice/rules/`), Project (`.tokenjuice/rules/`)
- Reduction strategies: truncate, dedup lines, fold whitespace, drop matching regexes, summarize sections
- HTML → Markdown with CJK/emoji grapheme preservation, multi-byte never stripped
- Up to 80% token/cost reduction — makes 6-month email ingest cost single-digit dollars

### Connectivity & Devices

- `devices/` — multi-device management, pairing, tunnel transport (E2E encrypted XChaCha20-Poly1305)
- **iOS Client** (experimental): React screens, PTT plugin, `LanHttpTransport`/`TunnelTransport`/`CloudHttpTransport`
- `connectivity/` — network state monitoring, connection fallback

### Deep Links

- `openhuman://` protocol registered on desktop
- macOS requires built `.app` bundle; Windows via `tauri-plugin-deep-link::register_all`

### Artifacts (`artifacts/`)

- Artifact store (`store.rs`), ops (`ops.rs`), schemas (`schemas.rs`), tools (`tools.rs`)

### Other Domains

- `todos/` — task management
- `text_input/` — text parsing/processing
- `threads/` — conversation thread management
- `session_db/` — session persistence, search, retrieval
- `overlay/` — desktop overlay management for mascot
- `accessibility/` — UIA (Windows) + AXUIElement (macOS)
- `provider_surfaces/` — provider management UI
- `autocomplete/` — command and query autocomplete
- `http_host/` — embedded HTTP server for RPC
- `tls/` — TLS config, rustls with platform-native certs
- `service/` — background service, systemd integration

---

## 19. INSTALL & DISTRIBUTION

### Package Paths

- **macOS**: Homebrew tap (`brew install openhuman`)
- **Linux**: Signed apt repo, AUR (`openhuman-bin`), `.deb`, `.AppImage`
- **Windows**: Signed `.msi` installer
- **Script install**: `curl | bash` (macOS/Linux), `irm | iex` (Windows)

### Builds

- Tauri v2 with vendored CEF (Chromium Embedded Framework)
- Cross-platform: Windows, macOS, Linux
- Cloud: Fly.io, DigitalOcean, Docker

---

## 20. CONFIG SUMMARY

### Key Paths

| Path                                   | Purpose                  |
| -------------------------------------- | ------------------------ |
| `~/.openhuman/`                      | Workspace root           |
| `~/.openhuman/memory_tree/chunks.db` | Memory chunks            |
| `~/.openhuman/wiki/`                 | Obsidian vault           |
| `~/OpenHuman/projects/`              | action_dir               |
| `~/.config/tokenjuice/rules/`        | TokenJuice rules         |
| `.tokenjuice/rules/`                 | Project TokenJuice rules |
| `config.toml`                        | Rust config              |
| `app/.env.local`                     | Vite env                 |

### Env Vars

- `OPENHUMAN_WORKSPACE`, `OPENHUMAN_ACTION_DIR`, `OPENHUMAN_CORE_TOKEN`, `OPENHUMAN_CORE_REUSE_EXISTING`, `OPENHUMAN_APPROVAL_GATE`, `OPENHUMAN_SEARXNG_*`, `GGML_NATIVE=OFF`

---

## 21. DOMAIN LAYOUT

### Rust Core (`src/openhuman/`) — 80+ domains

`about_app`, `accessibility`, `agent`, `agent_experience`, `agent_meetings`, `agent_memory`, `agent_orchestration`, `agent_registry`, `agent_tool_policy`, `app_state`, `approval`, `artifacts`, `audio_toolkit`, `autocomplete`, `billing`, `channels`, `codegraph`, `composio`, `config`, `connectivity`, `context`, `cost`, `council_registry`, `credentials`, `cron`, `cwd_jail`, `dashboard`, `desktop_companion`, `devices`, `doctor`, `embeddings`, `encryption`, `file_state`, `health`, `heartbeat`, `http_host`, `image`, `inference`, `integrations`, `javascript`, `keyring`, `keyring_consent`, `learning`, `mcp_audit`, `mcp_client`, `mcp_registry`, `mcp_server`, `meet`, `meet_agent`, `memory`, `memory_archivist`, `memory_conversations`, `memory_diff`, `memory_entities`, `memory_graph`, `memory_queue`, `memory_search`, `memory_sources`, `memory_store`, `memory_sync`, `memory_tools`, `memory_tree`, `migration`, `migrations`, `model_council`, `monitor`, `notifications`, `overlay`, `people`, `prompt_injection`, `provider_surfaces`, `redirect_links`, `referral`, `routing`, `runtime_node`, `runtime_python`, `sandbox`, `scheduler_gate`, `screen_intelligence`, `search`, `security`, `service`, `session_db`, `skill_registry`, `skill_runtime`, `socket`, `startup`, `subconscious`, `task_sources`, `team`, `test_support`, `text_input`, `threads`, `tls`, `todos`, `tokenjuice`, `tool_registry`, `tool_timeout`, `tools`, `update`, `voice`, `wallet`, `web3`, `webhooks`, `webview_accounts`, `webview_apis`, `webview_notifications`, `whatsapp_data`, `workflows`, `workspace`, `x402`

### Transport Layer (`src/core/`)

- `all`, `auth`, `cli`, `dispatch`, `event_bus/`, `jsonrpc`, `logging`, `observability`, `types`

---

## 22. COMPARISON TABLE (UPDATED)

| Feature                           | Hermes          | OpenHuman                   | Pi                                 |
| --------------------------------- | --------------- | --------------------------- | ---------------------------------- |
| Bundled Skills                    | **73**    | **1** (marketplace)   | **1** (`add-llm-provider`) |
| Optional Skills                   | **97**    | 0                           | 0 (user installs)                  |
| Managed Integrations              | 0               | **118+** via Composio | 0                                  |
| Native MCP Client                 | ✅              | ✅                          | ❌                                 |
| Native MCP Server                 | ✅              | ✅                          | ❌                                 |
| MCP OAuth/Catalog/Circuit Breaker | ✅              | ❌                          | ❌                                 |
| MCP Registry/Audit                | ❌              | ✅                          | ❌                                 |
| Agent Skills Standard             | ❌ (custom)     | ❌ (custom)                 | ✅                                 |
| Extension/Package System          | Plugins         | None                        | Extensions + Packages              |
| Memory System                     | 8 providers     | Memory Tree + 16 domains    | None                               |
| Voice/STT/TTS                     | ✅              | ✅                          | ❌                                 |
| Desktop Mascot                    | ❌              | ✅                          | ❌                                 |
| Messaging Gateway                 | 25 platforms    | 17 platforms                | None (separate pi-chat)            |
| Wallet/Web3                       | ❌              | ✅                          | ❌                                 |
| Subconscious Loop                 | ❌              | ✅                          | ❌                                 |
| Cron/Scheduling                   | ✅              | ✅                          | ❌                                 |
| Browser/Computer Use              | CDP + macOS CUA | CEF + mouse/kb              | None                               |
| SDK                               | None            | None                        | ✅`AgentSession`                 |
| Supply-chain Hardening            | No              | No                          | ✅ shrinkwrap + audit              |

---

End of OpenHuman atomic specification.

---

---

> **End of Combined Document**
>
> **Total Lines**: ~5,000+
> **Source Files**: 4 (full_feature_matrix.md + PI_ATOMIC_FEATURES.md + Hermes Atomic Features List.txt + OPENHUMAN_ATOMIC_FEATURES.md)
> **Combined On**: July 7th, 2025
> **Lossless**: Yes — all original content preserved verbatim with structural separators
