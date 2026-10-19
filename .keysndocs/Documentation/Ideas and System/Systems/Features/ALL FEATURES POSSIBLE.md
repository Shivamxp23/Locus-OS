# COMPLETE ATOMIC FEATURE MATRIX — Pi · Hermes · OpenHuman · Locus OS

> **Source files merged losslessly:**
>
> 1. `Hermes Atomic Features List.txt` (863 lines, 38 KB)
> 2. `OPENHUMAN_ATOMIC_FEATURES.md` (813 lines, 35 KB)
> 3. `PI_ATOMIC_FEATURES.md` (581 lines, 28 KB)
> 4. `full_feature_matrix.md` (566 lines, 35 KB)
>
> **Date:** July 8, 2026
> **Zero data loss — every feature from every source is included.**

> **Legend**
>
> - ✅ = Implemented in code
> - 📐 = Designed / documented, not yet in code
> - 🔧 = Partial / basic implementation
> - ⬜ = Not present
> - ❌ = Deliberately rejected by design

---

## 1. Core Runtime & Architecture

### 1A. Tech Stack

| Feature                                 | Pi                                                                                                                            | Hermes                                                                                                                                                                                                        | OpenHuman                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Locus                      |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| **Language / runtime**            | ✅ TypeScript monorepo, Node.js, npm workspaces                                                                               | ✅ Python —`run_agent.py`, `model_tools.py`, `toolsets.py`, `cli.py`, `hermes_state.py`, `hermes_constants.py`                                                                                   | ✅ Rust core (`src/`), React + Tauri v2 desktop (`app/`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ✅ Python                  |
| **Package structure**             | ✅ 4 packages:`pi-coding-agent` (CLI+SDK), `pi-agent-core` (agent runtime), `pi-ai` (LLM API), `pi-tui` (terminal UI) | ✅ Monolithic Python:`agent/`, `hermes_cli/`, `tools/`, `gateway/`, `cron/`, `plugins/`, `skills/`, `optional-skills/`, `ui-tui/`, `acp_adapter/`, `scripts/`, `website/`, `tests/` | ✅ 80+ Rust domains:`about_app`, `accessibility`, `agent`, `agent_experience`, `agent_meetings`, `agent_memory`, `agent_orchestration`, `agent_registry`, `agent_tool_policy`, `app_state`, `approval`, `artifacts`, `audio_toolkit`, `autocomplete`, `billing`, `channels`, `codegraph`, `composio`, `config`, `connectivity`, `context`, `cost`, `council_registry`, `credentials`, `cron`, `cwd_jail`, `dashboard`, `desktop_companion`, `devices`, `doctor`, `embeddings`, `encryption`, `file_state`, `health`, `heartbeat`, `http_host`, `image`, `inference`, `integrations`, `javascript`, `keyring`, `keyring_consent`, `learning`, `mcp_audit`, `mcp_client`, `mcp_registry`, `mcp_server`, `meet`, `meet_agent`, `memory`, `memory_archivist`, `memory_conversations`, `memory_diff`, `memory_entities`, `memory_graph`, `memory_queue`, `memory_search`, `memory_sources`, `memory_store`, `memory_sync`, `memory_tools`, `memory_tree`, `migration`, `migrations`, `model_council`, `monitor`, `notifications`, `overlay`, `people`, `prompt_injection`, `provider_surfaces`, `redirect_links`, `referral`, `routing`, `runtime_node`, `runtime_python`, `sandbox`, `scheduler_gate`, `screen_intelligence`, `search`, `security`, `service`, `session_db`, `skill_registry`, `skill_runtime`, `socket`, `startup`, `subconscious`, `task_sources`, `team`, `test_support`, `text_input`, `threads`, `tls`, `todos`, `tokenjuice`, `tool_registry`, `tool_timeout`, `tools`, `update`, `voice`, `wallet`, `web3`, `webhooks`, `webview_accounts`, `webview_apis`, `webview_notifications`, `whatsapp_data`, `workflows`, `workspace`, `x402` | ✅ Python monolith         |
| **Transport layer**               | ✅ stdin/stdout JSON-RPC, HTTP SSE, WebSocket                                                                                 | ✅ CLI direct, gateway HTTP, TUI JSON-RPC                                                                                                                                                                     | ✅`src/core/`: `all`, `auth`, `cli`, `dispatch`, `event_bus/`, `jsonrpc`, `logging`, `observability`, `types`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ✅ HTTP + Telegram webhook |
| **Lazy imports / cold-start**     | ✅ Lazy imports for cold-start optimization                                                                                   | ✅ TUI cold-start ~57% faster (lazy agent init, lazy imports, mtime-cached config, memoized tool defs)                                                                                                        | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | ⬜                         |
| **Diff-based terminal rendering** | ✅ Full Unicode support                                                                                                       | ⬜                                                                                                                                                                                                            | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | ⬜                         |
| **Supply-chain hardening**        | ✅ Exact version pins, shrinkwrap,`--ignore-scripts`, npm audit, `min-release-age=2`                                      | ⬜                                                                                                                                                                                                            | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | ⬜                         |
| **Core runs in-process**          | ⬜                                                                                                                            | ⬜                                                                                                                                                                                                            | ✅ tokio task (no sidecar since PR#1061)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ⬜                         |
| **Frontend ↔ core IPC**          | ✅ JSON-RPC stdin/stdout                                                                                                      | ⬜                                                                                                                                                                                                            | ✅`http://127.0.0.1:<port>/rpc` + per-launch hex bearer token, `OPENHUMAN_CORE_TOKEN` env var                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ⬜                         |
| **Event bus (typed pub/sub)**     | ✅`event-bus.ts`                                                                                                            | ⬜                                                                                                                                                                                                            | ✅`src/core/event_bus/`: `publish_global`/`subscribe_global` (broadcast), `register_native_global`/`request_native_global` (one-to-one, zero serialization). Domain events: agent, memory, channel, cron, skill, tool, webhook, system                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | ⬜                         |

### 1B. Agent Loop

| Feature                                    | Pi                                                                                                                                              | Hermes                                                                                                                    | OpenHuman                                                                                                                                                                                                                                                     | Locus                          |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| **Main agent loop**                  | ✅`agent-loop.ts` — two-entry (tooled + simple)                                                                                              | ✅`AIAgent.run_conversation()` core loop with tool calling + `AIAgent.chat()` simple interface                        | ✅`AIAgent` with tool-calling loop in Rust core. Unified turn engine, 5 seams, 3 dispatchers                                                                                                                                                                | ✅ ToolRegistry + LlmProvider  |
| **Turn context management**          | ✅ Harness state machine via`agent-harness.ts`                                                                                                | ✅`turn_context.py` per-turn state                                                                                      | ✅ Fork/memory/sandbox/worktree contexts                                                                                                                                                                                                                      | 🔧 Basic request/response      |
| **Turn retry / error recovery**      | ✅ Retry in agent loop — max 3 retries, 2s base delay, exponential backoff. Provider-level retry config (timeout, maxRetries, maxRetryDelayMs) | ✅`turn_retry_state.py`                                                                                                 | ✅ Self-healing (ToolMaker polyfill, circuit breakers)                                                                                                                                                                                                        | ⬜                             |
| **System prompt builder**            | ✅ Dynamic assembly + skills injection via`system-prompt.ts`, `prompt-templates.ts`                                                         | ✅`system_prompt.py` + `prompt_builder.py`                                                                            | ✅ Built into turn engine                                                                                                                                                                                                                                     | 🔧 Static system prompt        |
| **Streaming + non-streaming**        | ✅ Event stream utilities,`stream.ts`                                                                                                         | ✅ Streaming + non-streaming response paths,`stream_consumer.py` + `stream_dispatch.py`                               | ✅ Streaming response support                                                                                                                                                                                                                                 | 🔧`streaming_tui.py` (basic) |
| **Iteration budget / limits**        | ⬜                                                                                                                                              | ✅`max_iterations` (default 90) + grace call, `iteration_budget` module                                               | ✅`token_budget`                                                                                                                                                                                                                                            | ⬜                             |
| **Grace-turn after budget**          | ✅ Grace-turn after budget exhaustion                                                                                                           | ✅ Grace-turn after budget exhaustion                                                                                     | ⬜                                                                                                                                                                                                                                                            | ⬜                             |
| **Interrupt checks**                 | ⬜                                                                                                                                              | ✅ Per-iteration`_interrupt_requested` checks                                                                           | ⬜                                                                                                                                                                                                                                                            | ⬜                             |
| **Tool-call dispatch**               | ✅ Tool-call dispatch via function name matching                                                                                                | ✅`handle_function_call()` dispatch                                                                                     | ✅ Agent turn lifecycle: user input → tool calls → response → next turn                                                                                                                                                                                    | 🔧 Basic dispatch              |
| **Tool-call argument coercion**      | ⬜                                                                                                                                              | ✅ Tool-call argument coercion to JSON Schema types                                                                       | ⬜                                                                                                                                                                                                                                                            | ⬜                             |
| **Reasoning content**                | ✅ 6 thinking levels: off, minimal, low, medium, high, xhigh. Custom token budgets per level                                                    | ✅ Reasoning content stored in`assistant_msg["reasoning"]`. Thinking-only prefill continuation for structured reasoning | ⬜                                                                                                                                                                                                                                                            | ⬜                             |
| **Accept reasoning-only responses**  | ⬜                                                                                                                                              | ✅ Accept reasoning-only responses without retry                                                                          | ⬜                                                                                                                                                                                                                                                            | ⬜                             |
| **Self-optimized tool-use guidance** | ⬜                                                                                                                                              | ✅ Behavioral benchmarking of 5 failure modes (GPT/Codex)                                                                 | ⬜                                                                                                                                                                                                                                                            | ⬜                             |
| **OpenAI-format message roles**      | ✅                                                                                                                                              | ✅`system / user / assistant / tool`                                                                                    | ⬜                                                                                                                                                                                                                                                            | ⬜                             |
| **Multi-modal image routing**        | ⬜                                                                                                                                              | ✅ Based on model vision capability (not provider defaults)                                                               | ⬜                                                                                                                                                                                                                                                            | ⬜                             |
| **Token tracking per turn**          | ✅ Input/output/cache                                                                                                                           | ✅`usage_pricing.py` + `credits_tracker.py` + `account_usage.py`                                                    | ✅`cost`, `tokenjuice` modules                                                                                                                                                                                                                            | ⬜                             |
| **Hint-based model routing**         | ⬜                                                                                                                                              | ⬜                                                                                                                        | ✅`hint:reasoning`, `hint:fast`, `hint:vision`, `hint:summarize`, `hint:code`. Concrete model names bypass hints                                                                                                                                    | ⬜                             |
| **Per-agent model pins**             | ⬜                                                                                                                                              | ⬜                                                                                                                        | ✅ For sub-agents (orchestrator vs leaf)                                                                                                                                                                                                                      | ⬜                             |
| **Chat runtime provider chain**      | ⬜                                                                                                                                              | ⬜                                                                                                                        | ✅ React:`Sentry.ErrorBoundary` → `Redux Provider` → `PersistGate` → `BootCheckGate` → `CoreStateProvider` → `SocketProvider` → `ChatRuntimeProvider` → `HashRouter` → `CommandProvider` → `ServiceBlockingGate` → `AppShell` | ⬜                             |

### 1C. Configuration

| Feature                                   | Pi                                                                                                      | Hermes                                                                                                                                                                                                   | OpenHuman                                                                                                                                                                                                                                                                                  | Locus                                                   |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| **Config format**                   | ✅ JSON:`~/.pi/agent/settings.json` (global), `.pi/settings.json` (project, trust-gated). YAML/JSON | ✅`config.yaml`. Keys: model, agent, terminal, compression, display, stt/tts, memory, security/privacy, approvals, delegation, checkpoints, prompt_caching, context, auxiliary, curator, kanban, hooks | ✅ Rust TOML`Config` struct (`src/openhuman/config/schema/types.rs`) with env overrides. ~70 schema files. Frontend: `app/src/utils/config.ts` (never raw `import.meta.env`). `.env.example` for Rust core + Tauri shell + backend URL. `app/.env.example` for `VITE_*` vars | ✅ SETTINGS.md (56KB, 28 sections)                      |
| **Config migration**                | ✅`migrations.ts`                                                                                     | ✅`config migrate`                                                                                                                                                                                     | ✅`migration`, `migrations` modules                                                                                                                                                                                                                                                    | ✅`locus config migrate`                              |
| **Config management CLI**           | ✅`config.ts` + migrations                                                                            | ✅`config` — view, `config edit` — open config.yaml, `config set KEY VAL`, `config path`, `config env-path`, `config check`, `config migrate`                                            | ✅`config.update_autonomy_settings` RPC                                                                                                                                                                                                                                                  | ✅`locus config show/set/path/env-path/check/migrate` |
| **Environment variable management** | ✅`env-api-keys.ts`                                                                                   | ✅ 19+ provider keys + memory/services keys + runtime vars + platform tokens (see env vars section)                                                                                                      | ✅`OPENHUMAN_WORKSPACE`, `OPENHUMAN_ACTION_DIR`, `OPENHUMAN_CORE_TOKEN`, `OPENHUMAN_CORE_REUSE_EXISTING`, `OPENHUMAN_APPROVAL_GATE`, `OPENHUMAN_SEARXNG_*`, `GGML_NATIVE=OFF`                                                                                                | ✅`locus config env-path`                             |
| **Profile-aware config**            | ⬜                                                                                                      | ✅`get_hermes_home()`, profile-aware service units                                                                                                                                                     | ✅ Via`OPENHUMAN_WORKSPACE`                                                                                                                                                                                                                                                              | ⬜                                                      |
| **Settings UI**                     | ✅`/settings` editor                                                                                  | ⬜                                                                                                                                                                                                       | ✅ Settings → Agent access                                                                                                                                                                                                                                                                | ⬜                                                      |
| **Project overrides global**        | ✅ Nested objects merged                                                                                | ⬜                                                                                                                                                                                                       | ⬜                                                                                                                                                                                                                                                                                         | ⬜                                                      |

### 1D. Startup & Lifecycle

| Feature                           | Pi                                                                       | Hermes                                                       | OpenHuman                                                                                                                | Locus               |
| --------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ------------------- |
| **Onboarding flow**         | ✅ Project trust prompt, first-time-setup component                      | ✅`hermes setup [section]` — interactive wizard (model    | terminal                                                                                                                 | gateway             |
| **Agent initialization**    | ✅`agent-harness.ts` wrapping AIAgent with session, skills, compaction | ✅`agent_init.py`                                          | ✅`CoreProcessHandle` in `app/src-tauri/src/core_process.rs`. `run_server_embedded_with_ready(rpc_token: Some(_))` | ✅`core/agent.py` |
| **Workspace auto-creation** | ⬜                                                                       | ⬜                                                           | ✅ On first launch                                                                                                       | ⬜                  |
| **Core restart**            | ⬜                                                                       | ✅`/restart` slash command                                 | ✅ Via IPC command`restart_core_process`                                                                               | ⬜                  |
| **Daemon health service**   | ⬜                                                                       | ⬜                                                           | ✅`daemonHealthService`                                                                                                | ⬜                  |
| **Shutdown cleanup**        | ⬜                                                                       | ✅ Clean shutdown for memory providers                       | ✅ For memory providers, connections, cron                                                                               | ⬜                  |
| **Self-update**             | ✅`version-check.ts` + `windows-self-update.ts`                      | ✅`hermes update`, `hermes update --check`               | ✅`update` module                                                                                                      | ⬜                  |
| **Doctor / diagnostics**    | ✅`diagnostics.ts`                                                     | ✅`hermes doctor [--fix]` — dependency/config diagnostics | ✅`doctor` module                                                                                                      | ⬜                  |
| **Status command**          | ⬜                                                                       | ✅`hermes status [--all]` — component status              | ✅`health` module                                                                                                      | ⬜                  |

### 1E. Prompt Caching

| Feature                | Pi                           | Hermes                                                                                                | OpenHuman | Locus |
| ---------------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------- | --------- | ----- |
| **Prompt cache** | ✅`openai-prompt-cache.ts` | ✅`prompt_caching.py`, cache TTL configurable: `prompt_caching.cache_ttl` (5m default, 1h opt-in) | ⬜        | ⬜    |

### 1F. Background Review & Post-Turn

| Feature                                        | Pi | Hermes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | OpenHuman                                                                     | Locus                                    |
| ---------------------------------------------- | -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------- | ---------------------------------------- |
| **Background review / self-improvement** | ⬜ | ✅ Background review fork per turn. Rubric-based skill review (class-first). Active-update bias (prefers skill just loaded). Handles`references/` / `templates/` sub-files. Inherits parent's live runtime (provider, model, credentials). Scoped to memory + skills toolsets (no shell/web). Excludes prior-history tool messages from summary                                                                                                                                                                                                                | ✅ Post-turn hooks (4 types): Archivist, Reflection, ToolTracker, UserProfile | 📐 Inner Loop (not post-turn, proactive) |
| **Autonomous Curator**                   | ⬜ | ✅ Background agent via gateway cron ticker, 7-day cycle default. Grades skill library; consolidates related skills; prunes dead ones. Archived skills classified: consolidated vs pruned. Per-run reports:`logs/curator/run.json` + `REPORT.md`. `hermes curator status` ranks skills by usage. Defense-in-depth: never touches bundled/hub skills; max action is archive. Pinned skills exempt. Backup tar.gz before every run. Verbs: status, run, pause, resume, pin, unpin, archive, restore, prune, backup, rollback. Slash: `/curator <subcommand>` | ⬜                                                                            | ⬜                                       |

### 1G. Stream Diagnostics & Rate Limiting

| Feature                       | Pi                        | Hermes                      | OpenHuman                  | Locus |
| ----------------------------- | ------------------------- | --------------------------- | -------------------------- | ----- |
| **Stream diagnostics**  | ✅ Event stream utilities | ✅`stream_diag.py`        | ⬜                         | ⬜    |
| **Rate limit tracking** | ⬜                        | ✅`rate_limit_tracker.py` | ✅ Health probes (30s TTL) | ⬜    |
| **Title generation**    | ⬜                        | ✅`title_generator.py`    | ⬜                         | ⬜    |

---

## 2. LLM Providers & Model System

### 2A. Provider Architecture

| Feature                                     | Pi                                                               | Hermes                                                                                                                        | OpenHuman                                                                                                                      | Locus                                   |
| ------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| **Provider count**                    | ✅ 31 (3 OAuth + 28 API key)                                     | ✅ 30+ via plugin architecture                                                                                                | ✅ 5 provider types (hint-routed, managed)                                                                                     | ✅ 1 (AI model V4 Flash — intentional) |
| **Provider registry**                 | ✅`api-registry.ts` + `register-builtins.ts` + auto-register | ✅`model_metadata.py` + remote catalog manifest (OpenRouter + Nous Portal pulled from remote)                               | ✅`RouterProvider` (hint-based), `routing/provider.rs`: multi-provider wrapping, factory pattern, health checks, telemetry | 🔧`resolve_provider()`                |
| **Credential pool**                   | ⬜                                                               | ✅ Rotate across multiple API keys; exhaustion-aware                                                                          | ⬜                                                                                                                             | ⬜                                      |
| **Automatic cross-provider fallback** | ⬜                                                               | ✅ Automatic fallback +`hermes fallback` command. Auxiliary client payment fallback: retry next provider on 402             | ✅`IntelligentRouting` (local+cloud fallback)                                                                                | ❌ Single-provider by design            |
| **Live mid-session model switching**  | ✅`/model` slash command                                       | ✅`/model` live mid-session model/provider switching. Aggregator-aware resolution. Inline button picker on Telegram/Discord | ⬜                                                                                                                             | ⬜                                      |
| **Model pricing display**             | ⬜                                                               | ✅ For OpenRouter and Nous Portal. Free-tier model gating + pricing display                                                   | ⬜                                                                                                                             | ⬜                                      |
| **Non-agentic model warning**         | ⬜                                                               | ✅ Warning for non-agentic models                                                                                             | ⬜                                                                                                                             | ⬜                                      |
| **`/fast` mode**                    | ⬜                                                               | ✅`/fast` whitelist for OpenAI + Anthropic models                                                                           | ⬜                                                                                                                             | ⬜                                      |
| **Vision auto-detection**             | ⬜                                                               | ✅ Tries main provider first                                                                                                  | ⬜                                                                                                                             | ⬜                                      |
| **Refusal detection**                 | ⬜                                                               | ⬜                                                                                                                            | ✅ Aho-Corasick DFA (`quality.rs`)                                                                                           | ⬜                                      |
| **Model list/discovery**              | ✅`--list-models` flag                                         | ✅`model_metadata.py` + remote catalog                                                                                      | ⬜                                                                                                                             | ⬜                                      |
| **Mock / test provider**              | ✅`faux.ts`                                                    | ⬜                                                                                                                            | ⬜                                                                                                                             | ⬜                                      |

### 2B. OAuth Subscription Providers

| Feature                            | Pi                                                                                                                         | Hermes                                                      | OpenHuman | Locus |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | --------- | ----- |
| **ChatGPT Plus/Pro (Codex)** | ✅ OpenAI subscription, officially OSS-endorsed                                                                            | ✅ OpenAI Codex — OAuth —`hermes auth`                  | ⬜        | ⬜    |
| **Claude Pro/Max**           | ✅ Anthropic subscription, extra usage billing                                                                             | ⬜                                                          | ⬜        | ⬜    |
| **GitHub Copilot**           | ✅ Enterprise Server domain support                                                                                        | ✅ Token/OAuth —`hermes model → Copilot`                | ⬜        | ⬜    |
| **OAuth flows**              | ✅`device-code.ts` (device code flow), `pkce.ts` (PKCE authorization code flow), `anthropic.ts`, `openai-codex.ts` | ✅ OAuth —`hermes login [--provider]`, `hermes logout` | ⬜        | ⬜    |
| **Nous Portal**              | ⬜                                                                                                                         | ✅ OAuth —`hermes auth`                                  | ⬜        | ⬜    |
| **MiniMax OAuth**            | ⬜                                                                                                                         | ✅ OAuth (PKCE) — Browser flow                             | ⬜        | ⬜    |
| **Qwen OAuth**               | ⬜                                                                                                                         | ✅ OAuth —`hermes login --provider qwen-oauth`           | ⬜        | ⬜    |

### 2C. API Key Providers (Complete List)

| Provider                            | Pi                                                   | Hermes                                                                                                                                 | OpenHuman                         | Locus                 |
| ----------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | --------------------- |
| **Anthropic**                 | ✅`anthropic.ts`                                   | ✅`ANTHROPIC_API_KEY`                                                                                                                | ✅`ClaudeAgentSdk` (subprocess) | ⬜                    |
| **OpenAI**                    | ✅`openai-completions.ts`, `openai-responses.ts` | ✅ (via OpenRouter / generic adapter)                                                                                                  | ✅`OpenAiCompatible` (BYOK)     | ⬜                    |
| **Google Gemini / AI Studio** | ✅`google.ts`                                      | ✅`GOOGLE_API_KEY` / `GEMINI_API_KEY` + `gemini_native_adapter.py` + `gemini_cloudcode_adapter.py` + `google_code_assist.py` | ⬜                                | ⬜                    |
| **Google Vertex AI**          | ✅`google-vertex.ts`                               | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **AI model**                  | ✅                                                   | ✅`AI model_API_KEY`                                                                                                                 | ⬜                                | ✅ Primary (V4 Flash) |
| **xAI / Grok**                | ✅                                                   | ✅`XAI_API_KEY`                                                                                                                      | ⬜                                | ⬜                    |
| **OpenRouter**                | ✅`openrouter.ts` (image)                          | ✅`OPENROUTER_API_KEY` + `openrouter_client.py`                                                                                    | ⬜                                | ⬜                    |
| **Hugging Face**              | ✅                                                   | ✅`HF_TOKEN`                                                                                                                         | ⬜                                | ⬜                    |
| **Mistral**                   | ✅`mistral.ts`                                     | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **AWS Bedrock**               | ✅`amazon-bedrock.ts`                              | ✅ Plugin                                                                                                                              | ⬜                                | ⬜                    |
| **Azure OpenAI**              | ✅`azure-openai-responses.ts`                      | ✅`azure_identity_adapter.py` + Azure Foundry plugin                                                                                 | ⬜                                | ⬜                    |
| **Cloudflare**                | ✅`cloudflare.ts` (AI Gateway + Workers AI)        | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **NVIDIA NIM**                | ✅                                                   | ✅ Plugin                                                                                                                              | ⬜                                | ⬜                    |
| **Groq**                      | ✅                                                   | ✅`GROQ_API_KEY` (STT)                                                                                                               | ⬜                                | ⬜                    |
| **Cerebras**                  | ✅                                                   | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **Together AI**               | ✅                                                   | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **Fireworks**                 | ✅                                                   | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **Vercel AI Gateway**         | ✅                                                   | ✅`AI_GATEWAY_API_KEY`                                                                                                               | ⬜                                | ⬜                    |
| **Ant Ling**                  | ✅                                                   | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **Z.AI / GLM**                | ✅                                                   | ✅`GLM_API_KEY`                                                                                                                      | ⬜                                | ⬜                    |
| **ZAI Coding Plan (CN)**      | ✅                                                   | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **Kimi / Moonshot**           | ✅                                                   | ✅`KIMI_API_KEY` + `moonshot_schema.py`                                                                                            | ⬜                                | ⬜                    |
| **MiniMax**                   | ✅                                                   | ✅`MINIMAX_API_KEY`                                                                                                                  | ⬜                                | ⬜                    |
| **MiniMax (CN)**              | ✅                                                   | ✅`MINIMAX_CN_API_KEY`                                                                                                               | ⬜                                | ⬜                    |
| **Alibaba / DashScope**       | ⬜                                                   | ✅`DASHSCOPE_API_KEY` + `alibaba-coding-plan` plugin                                                                               | ⬜                                | ⬜                    |
| **Xiaomi MiMo**               | ✅ (including Token Plan CN/AMS/SGP)                 | ✅`XIAOMI_API_KEY`                                                                                                                   | ⬜                                | ⬜                    |
| **Kilo Code**                 | ⬜                                                   | ✅`KILOCODE_API_KEY`                                                                                                                 | ⬜                                | ⬜                    |
| **OpenCode Zen**              | ✅                                                   | ✅`OPENCODE_ZEN_API_KEY`                                                                                                             | ⬜                                | ⬜                    |
| **OpenCode Go**               | ✅                                                   | ✅`OPENCODE_GO_API_KEY`                                                                                                              | ⬜                                | ⬜                    |
| **Perplexity**                | ✅ (web_search)                                      | ⬜                                                                                                                                     | ⬜                                | ⬜                    |
| **GMI Cloud**                 | ⬜                                                   | ✅ Plugin                                                                                                                              | ⬜                                | ⬜                    |
| **StepFun**                   | ⬜                                                   | ✅ Plugin                                                                                                                              | ⬜                                | ⬜                    |
| **Tencent Tokenhub**          | ⬜                                                   | ✅ Plugin                                                                                                                              | ⬜                                | ⬜                    |
| **Ollama Cloud**              | ⬜                                                   | ✅ Plugin                                                                                                                              | ⬜                                | ⬜                    |
| **Arcee**                     | ⬜                                                   | ✅ Plugin                                                                                                                              | ⬜                                | ⬜                    |
| **Novita**                    | ⬜                                                   | ✅ Plugin                                                                                                                              | ⬜                                | ⬜                    |

### 2D. Custom / Local Providers

| Feature                                    | Pi                                                                                                                                                                                                                                                                                                                                                                              | Hermes                                                                              | OpenHuman                                                                                                                                                                   | Locus |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Custom endpoint**                  | ✅`~/.pi/agent/models.json` — Ollama, vLLM, LM Studio, any OpenAI-compatible. `api`: `openai-completions`, `openai-responses`, `anthropic-messages`, `google-generative-language`. `compat` flags: `supportsDeveloperRole`, `supportsReasoningEffort`. Provider-level `baseUrl`, `apiKey`, `headers`, `query`. Model-level `reasoning: true/false` | ✅ Plugin-based: Custom endpoint — Config —`model.base_url` + `model.api_key` | ✅ Config TOML                                                                                                                                                              | ⬜    |
| **LM Studio (local)**                | ✅ (via custom)                                                                                                                                                                                                                                                                                                                                                                 | ✅`lmstudio_reasoning.py` — First-class provider                                 | ⬜                                                                                                                                                                          | ⬜    |
| **Ollama (local)**                   | ✅ (via custom models.json)                                                                                                                                                                                                                                                                                                                                                     | ⬜                                                                                  | ✅`local_ai/` — Ollama integration for on-device models, self-hosted model serving, embedding generation on-device, memory tree building on-device when Local AI enabled | ⬜    |
| **Extension-based custom providers** | ✅ Anthropic passthrough, GitLab Duo via extensions                                                                                                                                                                                                                                                                                                                             | ⬜                                                                                  | ⬜                                                                                                                                                                          | ⬜    |
| **Model Council**                    | ⬜                                                                                                                                                                                                                                                                                                                                                                              | ⬜                                                                                  | ✅`model_council/` — multi-model deliberation, `council_registry` for configured councils                                                                              | ⬜    |

### 2E. Model Selection & Thinking

| Feature                        | Pi                                                                                                                               | Hermes                                                                                             | OpenHuman | Locus |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------- | ----- |
| **Model selection UI**   | ✅`/login`, `/logout`, `/model`, `/scoped-models`, Ctrl+P cycling via `enabledModels`                                  | ✅`/model` mid-session switch, `hermes model` interactive picker                               | ⬜        | ⬜    |
| **Thinking levels**      | ✅ 6 levels: off, minimal, low, medium, high, xhigh. Custom token budgets per level (`thinkingBudgets`). `hideThinkingBlock` | ⬜                                                                                                 | ⬜        | ⬜    |
| **CLI model flags**      | ✅`--provider`, `--model`, `--thinking`, `--models`, `--list-models`, `--api-key`                                    | ✅`--resume`, `--continue`, `--worktree`, `--skills`, `--profile`, `--pass-session-id` | ⬜        | ⬜    |
| **Model registry**       | ✅`models.ts`, `models.generated.ts`, `api-registry.ts`                                                                    | ✅ Remote model catalog manifest                                                                   | ⬜        | ⬜    |
| **Image model registry** | ✅`image-models.ts`, `images-api-registry.ts`                                                                                | ✅ Image gen providers:`openai`, `openai-codex`, `fal`, `xai`                              | ⬜        | ⬜    |
| **Video gen providers**  | ⬜                                                                                                                               | ✅`fal`, `xai`                                                                                 | ⬜        | ⬜    |

---

## 3. Tool System

### 3A. Tool Architecture

| Feature                              | Pi                                                                                     | Hermes                                                                                                                                                                                                                                                                                                                               | OpenHuman                                                                                                                                                                                                                        | Locus               |
| ------------------------------------ | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| **Tool registry**              | ✅`tool-definition-wrapper.ts`, `tools-manager.ts`                                 | ✅`tools/registry.py` central registry with auto-discovery. `discover_builtin_tools()` imports `tools/*.py`. `ToolEntry` metadata: name, toolset, schema, handler, check_fn, requires_env, is_async, emoji, max_result_size_chars, dynamic_schema_overrides. `check_fn` TTL cache (~30s). All handlers return JSON strings | ✅`src/openhuman/tool_registry/`. Domain-owned tools: each domain has `tools.rs`, re-exported via `src/openhuman/tools/mod.rs`. Cross-cutting families in `tools/impl/`. Generated tool schemas (`tools/generated.rs`) | ✅ ToolRegistry     |
| **Tool policy / user filter**  | ✅`--tools` (allowlist), `--exclude-tools`, `--no-builtin-tools`, `--no-tools` | ✅ Toolsets system (enable/disable)                                                                                                                                                                                                                                                                                                  | ✅`tools/policy.rs`, `tools/user_filter.rs`. `classify_command` → `CommandClass` (`Read`/`Write`/`Network`/`Install`/`Destructive`). `gate_decision(class, tier)` → `Allow`/`Prompt`/`Block`         | 🔧 Basic validation |
| **Tool timeout / budget**      | ⬜                                                                                     | ⬜                                                                                                                                                                                                                                                                                                                                   | ✅`tool_timeout/`                                                                                                                                                                                                              | ⬜                  |
| **Tool result classification** | ⬜                                                                                     | ✅`tool_result_classification.py`                                                                                                                                                                                                                                                                                                  | ⬜                                                                                                                                                                                                                               | ⬜                  |
| **Tool output limits**         | ✅`output-accumulator.ts`                                                            | ✅`tool_output_limits.py`                                                                                                                                                                                                                                                                                                          | ✅ 16 KiB tool result budget                                                                                                                                                                                                     | ⬜                  |
| **Tool result storage**        | ⬜                                                                                     | ✅`tool_result_storage.py` — save oversized tool results to file instead of destructive truncation                                                                                                                                                                                                                                | ⬜                                                                                                                                                                                                                               | ⬜                  |
| **Path security**              | ⬜                                                                                     | ✅`path_security.py` for path sandboxing                                                                                                                                                                                                                                                                                           | ✅`cwd_jail`, `is_workspace_internal_path` fail-closed, `is_always_forbidden`                                                                                                                                              | ⬜                  |
| **Schema sanitization**        | ⬜                                                                                     | ✅`schema_sanitizer.py`                                                                                                                                                                                                                                                                                                            | ⬜                                                                                                                                                                                                                               | ⬜                  |
| **File mutation queue**        | ✅`file-mutation-queue.ts`                                                           | ⬜                                                                                                                                                                                                                                                                                                                                   | ⬜                                                                                                                                                                                                                               | ⬜                  |
| **XML tool dispatch**          | ⬜                                                                                     | ⬜                                                                                                                                                                                                                                                                                                                                   | ✅`<tool_call>` XmlDispatcher                                                                                                                                                                                                  | ⬜                  |
| **Compact tool dispatch**      | ⬜                                                                                     | ⬜                                                                                                                                                                                                                                                                                                                                   | ✅ PFormat dispatcher                                                                                                                                                                                                            | ⬜                  |

### 3B. File & Code Tools

| Feature                                | Pi                                                                                                                                     | Hermes                                                                                                                                                                                                       | OpenHuman                                                                                                                           | Locus                                          |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| **File read**                    | ✅`read.ts` — line numbers, image support, pagination (2000 lines / 50KB cap)                                                       | ✅`read_file` — read file with pagination                                                                                                                                                                 | ✅`file_read` — read file with line numbers (like `cat -n`), image support                                                     | ✅`read`                                     |
| **File write / create**          | ✅`write.ts` — auto-creates parent directories                                                                                      | ✅`write_file` — write/overwrite files                                                                                                                                                                    | ✅`file_write` — write new file                                                                                                  | ✅`write`                                    |
| **File edit (precise)**          | ✅`edit.ts` + `edit-diff.ts` — precise find-and-replace, multi-edit in one call, exact-text matching, non-overlapping enforcement | ✅`patch` — targeted find-and-replace edits; V4A patch mode supported                                                                                                                                     | ✅`edit_file` — targeted match-and-replace with strict uniqueness checks                                                         | ✅`edit` + `edit_file`                     |
| **Apply patch**                  | ⬜                                                                                                                                     | ✅ V4A multi-file patch format,`patch_parser.py`                                                                                                                                                           | ✅`apply_patch` — apply unified diff                                                                                             | ⬜                                             |
| **Shell / bash execution**       | ✅`bash.ts` — stdout/stderr/exit code capture, timeout, temp file on truncation. `!command` sends to model, `!!command` silent  | ✅`terminal` — shell commands + process management + background. Local/docker/SSH/Modal/Daytona/Singularity/Vercel Sandbox backends. PTY mode for interactive CLI tools. Subprocess.run() timeouts        | ✅`shell` — run shell command, bounded output, captured exit code. 4 sandboxed backends (bubblewrap, docker, firejail, landlock) | ✅`run_shell` (blocklist sandbox)            |
| **Grep / search files**          | ✅`grep.ts` — ripgrep-backed, context lines, output modes (content/files_with_matches/count)                                        | ✅`search_files` — ripgrep-backed content/file search with context, output modes                                                                                                                          | ✅`grep` — ripgrep-style content/file search                                                                                     | ⬜ (uses web_search)                           |
| **List directory**               | ✅`ls.ts` — recursive walk, pattern matching, max-depth                                                                             | ✅ (built-in)                                                                                                                                                                                                | ✅`list_files` — walk directory tree                                                                                             | ✅`list_directory`                           |
| **Find files**                   | ✅`find.ts`                                                                                                                          | ✅ (built-in)                                                                                                                                                                                                | ✅`glob_search` — find files by glob pattern                                                                                     | ⬜                                             |
| **Read diff**                    | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`read_diff` — diff between two files or revisions                                                                              | ⬜                                             |
| **Git operations**               | ⬜                                                                                                                                     | ✅ (built-in)                                                                                                                                                                                                | ✅`git_operations` — status, diff, log, blame, branch, commit                                                                    | ✅`git_status`, `git_diff`, `git_commit` |
| **Run linter**                   | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`run_linter` — run project linter                                                                                              | ⬜                                             |
| **Run tests**                    | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`run_tests` — run project test command                                                                                         | ⬜                                             |
| **CSV export**                   | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`csv_export` — export query results as CSV                                                                                     | ⬜                                             |
| **Node/npm execution**           | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`node_exec`, `npm_exec`                                                                                                       | ⬜                                             |
| **System info**                  | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`current_time`, `workspace_state`                                                                                             | ✅`system_info`                              |
| **Insert SQL record**            | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`insert_sql_record` — append row to agent's structured SQL store                                                               | ⬜                                             |
| **LSP query**                    | ⬜                                                                                                                                     | ✅`lsp/client.py`, `lsp/manager.py`, `lsp/workspace.py`, `lsp/eventlog.py`, `lsp/cli.py`, `lsp/install.py`, `lsp/protocol.py`, `lsp/servers.py`, `lsp/reporter.py`, `lsp/range_shift.py` | ✅`lsp` — query language server (definitions, references, diagnostics)                                                           | ⬜                                             |
| **Proxy config**                 | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`proxy_config`                                                                                                                  | ⬜                                             |
| **Tool stats / self-reflection** | ⬜                                                                                                                                     | ⬜                                                                                                                                                                                                           | ✅`tool_stats`                                                                                                                    | ✅`tool_tracker.py`                          |
| **Sandboxed Python execution**   | ⬜                                                                                                                                     | ✅`execute_code` — sandboxed Python execution with Hermes tools programmable                                                                                                                              | ⬜                                                                                                                                  | ⬜                                             |

### 3C. Web & Network Tools

| Feature                          | Pi                                                                                                                                                         | Hermes                                                                                                                                               | OpenHuman                                                                                                                  | Locus                                                                  |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **Web search**             | ✅`web_search` — 8 providers (OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini), multi-query, recency filter, domain filter, full content fetch | ✅`web_search` via plugin providers: `brave_free`, `ddgs` (DuckDuckGo), `exa`, `firecrawl`, `parallel`, `searxng`, `tavily`, `xai` | ✅ Web search via managed proxy (Parallel) — default no-API-key required. Self-hosted SearXNG (`searxng_search`) opt-in | ✅`web_search` (5 providers: Brave, Exa, Firecrawl, SearXNG, Tavily) |
| **Web fetch / scrape**     | ✅`fetch_content` — URL→markdown, YouTube transcripts with frames, GitHub repos, local video frames, Gemini fallback                                   | ✅`web_extract` — web content extraction                                                                                                          | ✅ Web scraper: pull clean text from URLs, HTML-to-Markdown.`http_request` — generic HTTP calls                         | ✅`web_fetch`                                                        |
| **Get search content**     | ✅`get_search_content` — retrieve stored content from prior searches                                                                                    | ⬜                                                                                                                                                   | ⬜                                                                                                                         | ⬜                                                                     |
| **X/Twitter search**       | ⬜                                                                                                                                                         | ✅`x_search_tool` via xAI                                                                                                                          | ⬜                                                                                                                         | ⬜                                                                     |
| **Pushover notifications** | ⬜                                                                                                                                                         | ⬜                                                                                                                                                   | ✅`pushover` — send push notification to devices                                                                        | ⬜                                                                     |

### 3D. Vision & Image Tools

| Feature                           | Pi                                                                                                                                                                                                                      | Hermes                                                                                                 | OpenHuman                                                                            | Locus           |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | --------------- |
| **Vision / image analysis** | ⬜                                                                                                                                                                                                                      | ✅`vision_analyze` — image analysis (URL, file path, data URL)                                      | ✅ Image analysis via vision models + screenshot capture + image processing pipeline | ✅`vision.py` |
| **Image generation**        | ⬜                                                                                                                                                                                                                      | ✅`image_generate` — AI image generation. Providers: `openai`, `openai-codex`, `fal`, `xai` | ⬜                                                                                   | ⬜              |
| **Video generation**        | ⬜                                                                                                                                                                                                                      | ✅`video_generation_tool`. Providers: `fal`, `xai`                                               | ⬜                                                                                   | ⬜              |
| **Image paste/handling**    | ✅ Ctrl+V / Alt+V, drag into terminal. Resize: max 2000×2000. Kitty/iTerm2 inline protocols. Pipeline:`image-convert.ts`, `image-resize.ts`, `exif-orientation.ts`. Photon WASM-based processing. MIME detection | ⬜                                                                                                     | ⬜                                                                                   | ⬜              |

### 3E. Browser & Computer Control

| Feature                       | Pi | Hermes                                                                                                                                                                                                                                                                                                                                                                   | OpenHuman                                                                                                                                                                                                                                                                                                   | Locus                                                         |
| ----------------------------- | -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **Browser automation**  | ⬜ | ✅`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_scroll`, `browser_back`, `browser_press`, `browser_get_images`, `browser_vision`, `browser_console`. Providers: Browserbase, Camofox local Firefox, Firecrawl, local Chromium auto-spawn. CDP supervisor: dialog detection + response + cross-origin iframe eval | ✅ Browser open URL in embedded CEF webview, browser screenshot, browser inspect                                                                                                                                                                                                                            | ✅ Playwright (`browserbase.py`, `playwright_backend.py`) |
| **Computer use**        | ⬜ | ✅`computer_use` tool for macOS — Accessibility API, screenshot, mouse/keyboard simulation, Finder/native app interaction (gated on cua-driver)                                                                                                                                                                                                                       | ✅`screen_intelligence/`: capture engine, state monitoring, image processing pipeline, vision analysis, input simulation, server, permission gating. Mouse: move, click, drag with human-like trajectories. Keyboard: type text, send key chords. Human-path cursor movement (avoids naive bot detection) | ✅`native.py`                                               |
| **VNC remote control**  | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                                                       | ⬜                                                                                                                                                                                                                                                                                                          | ✅`vnc.py`                                                  |
| **Screen capture**      | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                                                       | ✅`screen_intelligence` — `capture.rs`, `capture_worker.rs`                                                                                                                                                                                                                                          | ✅`capture.py`, `screenshot.py`                           |
| **Accessibility tools** | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                                                       | ✅`ax_interact` — UI Automation: Windows via UIA, macOS via AXUIElement. Cross-platform accessibility APIs                                                                                                                                                                                               | ⬜                                                            |

### 3F. Coordination & Delegation Tools

| Feature                               | Pi                        | Hermes                                                                                                                                                                                                    | OpenHuman                                                                                                                                                                                                                 | Locus                        |
| ------------------------------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| **Delegate / subagent tool**    | ✅ Built-in subagent tool | ✅`delegate_task` — single task or batch parallel tasks. Roles: leaf, orchestrator; depth=1 by default. Synchronous; isolated context + terminal per child. Same provider pool + credentials as parent | ✅`spawn_subagent` (fresh agent), `spawn_worker_thread` (background), `delegate` (specialist archetype), `archetype_delegation` (named: coder, researcher, planner, etc.), `skill_delegation` (installed skill) | 🔧`delegation/subagent.py` |
| **Clarify / ask user**          | ⬜                        | ✅`clarify` — multi-choice / open-ended                                                                                                                                                                | ✅`ask_clarification` — pause and ask user precise question                                                                                                                                                            | ⬜                           |
| **Plan exit**                   | ⬜                        | ⬜                                                                                                                                                                                                        | ✅`plan_exit` — exit planning phase, start executing                                                                                                                                                                   | ⬜                           |
| **Todo / task management tool** | ⬜                        | ✅`todo` — task list management (read/write/complete/cancel)                                                                                                                                           | ✅`todo_write` — maintain structured TODO list across long tasks                                                                                                                                                       | ⬜                           |
| **Send message tool**           | ⬜                        | ✅`send_message` — cross-platform message sending. Checks if gateway running; falls back                                                                                                               | ⬜                                                                                                                                                                                                                        | ⬜                           |
| **Session search**              | ⬜                        | ✅`session_search` — FTS5 full-text search over past sessions                                                                                                                                          | ⬜                                                                                                                                                                                                                        | ⬜                           |

### 3G. Home Automation & Specialized Tools

| Feature                      | Pi | Hermes                                                                                                                                                                                                                                                                                                                         | OpenHuman                                                                                           | Locus               |
| ---------------------------- | -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- | ------------------- |
| **Home Assistant**     | ⬜ | ✅`ha_list_entities`, `ha_get_state`, `ha_list_services`, `ha_call_service` (gated on HA token)                                                                                                                                                                                                                        | ⬜                                                                                                  | ⬜                  |
| **Kanban board**       | ⬜ | ✅`kanban_show`, `kanban_list`, `kanban_complete`, `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_create`, `kanban_link`, `kanban_unblock`. SQLite durable board, dispatcher in gateway, auto-claims ready tasks, spawns assigned profiles, auto-blocks after failure_limit, tenant namespace | ⬜                                                                                                  | ⬜                  |
| **Mixture of Agents**  | ⬜ | ✅`mixture_of_agents_tool` (off by default)                                                                                                                                                                                                                                                                                  | ⬜                                                                                                  | ⬜                  |
| **Spotify**            | ⬜ | ✅ 7 tools: playback, devices, queue, search, playlists, albums, library. PKCE OAuth,`hermes auth spotify`                                                                                                                                                                                                                   | ⬜                                                                                                  | ⬜                  |
| **Discord tools**      | ⬜ | ✅`discord_tool` — Discord tools                                                                                                                                                                                                                                                                                            | ⬜                                                                                                  | ⬜                  |
| **Feishu doc/drive**   | ⬜ | ✅`feishu_doc_tool`, `feishu_drive_tool`                                                                                                                                                                                                                                                                                   | ⬜                                                                                                  | ⬜                  |
| **Yuanbao tools**      | ⬜ | ✅`yuanbao_tools` — Yuanbao integration                                                                                                                                                                                                                                                                                     | ⬜                                                                                                  | ⬜                  |
| **Microsoft Graph**    | ⬜ | ✅`microsoft_graph_auth.py`, `microsoft_graph_client.py`                                                                                                                                                                                                                                                                   | ⬜                                                                                                  | ⬜                  |
| **Google Meet**        | ⬜ | ✅`meet_join`, `meet_leave`, `meet_status`, `meet_transcript`, `meet_say`. v1: transcribe-only (headless Chromium + live captions). v2: realtime duplex audio (OpenAI Realtime + BlackHole/PulseAudio). v3: remote node host                                                                                         | ✅ Live Google Meet agent: join, transcribe, speak back into call. Mascot face piped as camera feed | ⬜                  |
| **Presentation tools** | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                             | ✅ PowerPoint manipulation (`ppt-rs`)                                                             | ⬜                  |
| **Apify**              | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                             | ✅ Web scraping platform connector                                                                  | ⬜                  |
| **Google Places**      | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                             | ✅ Location search                                                                                  | ⬜                  |
| **Stock prices**       | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                             | ✅ Stock/crypto price lookup                                                                        | ⬜                  |
| **Twilio**             | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                             | ✅ SMS/voice via Twilio                                                                             | ⬜                  |
| **Polymarket**         | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                             | ⬜                                                                                                  | ✅`polymarket.py` |

### 3H. Toolsets (Hermes-specific)

| Toolset                           | Description                             |
| --------------------------------- | --------------------------------------- |
| `web`                           | web_search, web_extract                 |
| `search`                        | web_search only                         |
| `x_search`                      | X/Twitter via xAI                       |
| `browser`                       | browser automation                      |
| `terminal`                      | shell/process                           |
| `file`                          | file operations                         |
| `code_execution`                | Python sandbox                          |
| `vision`                        | vision_analyze                          |
| `image_gen`                     | image generation                        |
| `video`                         | video generation                        |
| `tts`                           | text-to-speech                          |
| `skills`                        | skills browse/install/manage            |
| `memory`                        | memory interface                        |
| `session_search`                | history search                          |
| `delegation`                    | subagents                               |
| `cronjob`                       | cron                                    |
| `clarify`                       | clarifying questions                    |
| `messaging`                     | cross-platform messaging                |
| `todo`                          | task list                               |
| `kanban`                        | kanban board                            |
| `debugging`                     | introspection (off by default)          |
| `safe`                          | minimal low-risk                        |
| `spotify`                       | Spotify                                 |
| `homeassistant`                 | smart home                              |
| `discord` / `discord_admin`   | Discord tools                           |
| `feishu_doc` / `feishu_drive` | Feishu                                  |
| `yuanbao`                       | Yuanbao                                 |
| `rl`                            | reinforcement learning (off by default) |
| `moa`                           | mixture of agents (off by default)      |
| `computer_use`                  | macOS CUA                               |

---

## 4. Memory & Persistence

### 4A. Primary Storage

| Feature                     | Pi                      | Hermes                                     | OpenHuman                                                                                             | Locus                      |
| --------------------------- | ----------------------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------------- | -------------------------- |
| **Primary storage**   | ✅ JSONL (append-only)  | ✅ SQLite (FTS5) —`~/.hermes/state.db`  | ✅ SQLite + JSONL.`memory_tree/chunks.db` — chunks, scores, summaries, entity index, jobs, hotness | ✅ SQLite (WAL)            |
| **In-memory backend** | ✅`memory-storage.ts` | ⬜                                         | ⬜                                                                                                    | ⬜                         |
| **Graph memory**      | ⬜                      | ⬜                                         | ✅`memory_graph`                                                                                    | ✅ Neo4j                   |
| **Vector embeddings** | ⬜                      | ⬜                                         | ✅`embeddings` module — on-device when Local AI enabled                                            | ✅ pgvector (📐 PageIndex) |
| **Full-text search**  | ⬜                      | ✅ FTS5 session search + LLM summarization | ✅`memory_search` + `memory_conversations` (cross-thread FTS5)                                    | ⬜                         |

### 4B. Memory Tree (OpenHuman-specific)

| Feature                             | Pi | Hermes | OpenHuman                                                                                                                                                                                                                                                                        | Locus |
| ----------------------------------- | -- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Memory Tree architecture**  | ⬜ | ⬜     | ✅ Local-first knowledge base, deterministic bucket-sealed pipeline. NOT a vector database — structured, queryable, summary-backed Markdown on device. All data canonicalized into ≤3k-token Markdown chunks. Stored in SQLite. Obsidian-compatible Markdown vault (`wiki/`) | ⬜    |
| **Pipeline stages**           | ⬜ | ⬜     | ✅ 7 stages: Canonicalize → Chunker → Content Store → Store → Score → Trees → Retrieval                                                                                                                                                                                    | ⬜    |
| **Three trees, three scopes** | ⬜ | ⬜     | ✅**Source trees** (per-source rolling buffer L0→L1→L2), **Topic trees** (per-entity, materialized lazily by hotness), **Global tree** (daily global digest)                                                                                                 | ⬜    |
| **Background workers**        | ⬜ | ⬜     | ✅ Job kinds:`extract_chunk`, `append_buffer`, `seal`, `topic_route`, `digest_daily`                                                                                                                                                                                   | ⬜    |
| **Memory cascade**            | ⬜ | ⬜     | ✅ Bucket-seal cascade: L0 sealed into L1 summary, cascades up                                                                                                                                                                                                                   | ⬜    |

### 4C. Memory Domains & Sub-modules

| Feature                               | Pi | Hermes                                            | OpenHuman                                                                                                                                                                                   | Locus                                  |
| ------------------------------------- | -- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| **Memory orchestrator**         | ⬜ | ✅`memory_manager.py`                           | ✅`memory_store` — persistence                                                                                                                                                           | ✅`memory_manager.py`                |
| **Memory archivist**            | ⬜ | ⬜                                                | ✅`memory_archivist/` — archival and consolidation                                                                                                                                       | ⬜                                     |
| **Conversation memory**         | ⬜ | ⬜                                                | ✅`memory_conversations/` — cross-thread FTS5 search                                                                                                                                     | ⬜                                     |
| **Memory diff**                 | ⬜ | ⬜                                                | ✅`memory_diff/` — change tracking                                                                                                                                                       | ⬜                                     |
| **Entity extraction**           | ⬜ | ⬜                                                | ✅`memory_entities/` — entity extraction and tracking                                                                                                                                    | 📐 AI model entity extraction → Neo4j |
| **Memory queue**                | ⬜ | ⬜                                                | ✅`memory_queue/` — durable job queue for follow-up work                                                                                                                                 | ⬜                                     |
| **Memory sources**              | ⬜ | ⬜                                                | ✅`memory_sources/` — source adapter registry                                                                                                                                            | ⬜                                     |
| **Memory sync**                 | ⬜ | ⬜                                                | ✅`memory_sync/` — sync across workspaces                                                                                                                                                | ⬜                                     |
| **Memory tree**                 | ⬜ | ⬜                                                | ✅`memory_tree/` — tree structure and traversal                                                                                                                                          | ⬜                                     |
| **Memory tools (agent-facing)** | ⬜ | ✅`memory` tool — persistent memory read/write | ✅`memory_tools/`: `recall` (search by query, source-scoped, topic-scoped, global), `store` (write), `forget` (remove). Tree-aware retrieval: drill down topic, fetch global digest | ⬜                                     |

### 4D. Memory Providers (Hermes-specific)

| Provider              | Description                                         |
| --------------------- | --------------------------------------------------- |
| `builtin` (default) | Built-in Python memory                              |
| `honcho`            | Honcho AI-native memory + dialectic modeling        |
| `mem0`              | Mem0                                                |
| `hindsight`         | Long-term memory with knowledge graph               |
| `holographic`       | Local SQLite fact store, FTS5 search, trust scoring |
| `byterover`         | Persistent knowledge tree with`brv` CLI           |
| `openviking`        | Session-managed memory                              |
| `retaindb`          | Cloud memory API                                    |
| `supermemory`       | Semantic long-term memory                           |

### 4E. Neuroscience-Inspired Memory (Locus-specific)

| Feature                                   | Pi | Hermes | OpenHuman | Locus                                                                             |
| ----------------------------------------- | -- | ------ | --------- | --------------------------------------------------------------------------------- |
| **Holographic HRR**                 | ⬜ | ⬜     | ⬜        | ✅ SHA-256 deterministic vectors, bind/unbind/bundle                              |
| **Hebbian pathway weighting**       | ⬜ | ⬜     | ⬜        | 📐 Neo4j edge weights (+0.1 traversal, ×1.3/×0.7 feedback, ×0.95 weekly decay) |
| **STDP**                            | ⬜ | ⬜     | ⬜        | 📐 Response latency <2min = ×1.5 reinforcement                                   |
| **Spaced repetition reinforcement** | ⬜ | ⬜     | ⬜        | 📐 Nodes near decay + active outcomes → Inner Loop surfaces                      |
| **Project-specific memory decay**   | ⬜ | ⬜     | ⬜        | 📐 Cypher:`SET r.weight = r.weight * 0.5` on completion                         |

### 4F. User Modeling & Approval

| Feature                       | Pi                       | Hermes                                   | OpenHuman                                                                                                                                                                                                                                                                                                                | Locus                                                     |
| ----------------------------- | ------------------------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| **User modeling store** | ⬜                       | ✅ Honcho dialectic modeling             | ✅ Ambient profile facets + stability detector (30min). Learning system:`user_profile.rs`, `reflection.rs`, `transcript_ingest/`, `tool_tracker.rs`, `linkedin_enrichment.rs`, `scheduler.rs`, `stability_detector.rs`, `profile_md_renderer.rs`, `prompt_sections.rs`, `candidate.rs`, `extract/` | 📐 User Identity Profile (PG single-row, rolling-average) |
| **Approval store**      | ⬜                       | ⬜                                       | ✅ Approval gate (10-min TTL,`ApprovalRequestCard`)                                                                                                                                                                                                                                                                    | ✅`approval_store.py`                                   |
| **Session manager**     | ✅`session-manager.ts` | ✅`gateway/session.py`                 | ✅`session_db`                                                                                                                                                                                                                                                                                                         | ✅`session_manager.py`                                  |
| **Secret redaction**    | ⬜                       | ✅ Secret redaction in memory operations | ⬜                                                                                                                                                                                                                                                                                                                       | ⬜                                                        |

---

## 5. Sessions

| Feature                            | Pi                                                                                                                                                                                                                                      | Hermes                                                                                                    | OpenHuman                    | Locus                                          |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------------------------- | ---------------------------------------------- |
| **Session format**           | ✅ Tree-based JSONL (v3, 9 entry types:`user`, `assistant`, `tool_call`, `tool_result`, `compaction`, `branch_summary`, `custom`, `model_change`, `thinking_change`, `label`). Versioned: v1→v2→v3, auto-migrated | ✅ SQLite + FTS5 session store (`state.db`). JSONL transcripts + optional per-session JSON snapshots    | ✅ JSONL + bucket-seal       | ✅ SQLite (conversations, sessions, documents) |
| **Session branching / fork** | ✅`--fork` flag, `/fork`, `/clone`. Tree structure via `id`/`parentId` — in-place branching without new files                                                                                                                | ✅`/branch`, `/fork`                                                                                  | ⬜                           | ⬜                                             |
| **Session resume**           | ✅`-c`/`--continue`, `-r`/`--resume`, `--session <path                                                                                                                                                                          | id>`                                                                                                      | ✅`/resume [name]`         | ⬜                                             |
| **Session naming**           | ✅`--name` / `-n`, `/name`                                                                                                                                                                                                        | ✅ Session rename,`title_generator.py`                                                                  | ⬜                           | ⬜                                             |
| **Session picker UI**        | ✅`/resume` — interactive picker (search, sort, filter, rename, delete)                                                                                                                                                              | ✅ Session browsing with interactive picker                                                               | ⬜                           | ⬜                                             |
| **Session tree navigation**  | ✅`/tree` — navigate tree (↑↓, Ctrl+O filter, Shift+L label, branch summary on switch)                                                                                                                                             | ⬜                                                                                                        | ⬜                           | ⬜                                             |
| **Session compression**      | ✅ Compaction engine + branch summarization                                                                                                                                                                                             | ✅`/compress` manual trigger, automatic context compression at token limit, compaction failure recovery | ✅ Microcompact + summarizer | 🔧`compression.py` (basic)                   |
| **Session export**           | ✅`/export [file]` — HTML export with ANSI→HTML + tool rendering. `/share` — private GitHub gist. `badlogic/pi-share-hf` — Hugging Face datasets. JSON, MD formats                                                            | ✅ Session export to JSONL. Trajectory recording                                                          | ⬜                           | ⬜                                             |
| **Session stats**            | ⬜                                                                                                                                                                                                                                      | ✅ Session stats,`/usage` token usage, `/insights [days]` usage analytics                             | ⬜                           | ⬜                                             |
| **Session prune**            | ⬜                                                                                                                                                                                                                                      | ✅ Session prune (--older-than N days)                                                                    | ⬜                           | ⬜                                             |
| **Session delete**           | ✅ Delete via`trash` CLI from `/resume` picker                                                                                                                                                                                      | ✅ Session delete, TUI delete from picker with`d`                                                       | ⬜                           | ⬜                                             |
| **No-session mode**          | ✅`--no-session` flag                                                                                                                                                                                                                 | ⬜                                                                                                        | ⬜                           | ⬜                                             |
| **Custom session directory** | ✅`--session-dir`, `PI_CODING_AGENT_SESSION_DIR`, or `sessionDir` setting                                                                                                                                                         | ⬜                                                                                                        | ⬜                           | ⬜                                             |
| **Subagent sessions**        | ⬜                                                                                                                                                                                                                                      | ✅ Linked to parent, hidden from list                                                                     | ⬜                           | ⬜                                             |
| **Thread sessions**          | ⬜                                                                                                                                                                                                                                      | ✅ Multi-user thread support across gateway, shared thread sessions across platforms                      | ⬜                           | ⬜                                             |
| **Session path format**      | ✅`~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl`                                                                                                                                                                          | ✅`~/.hermes/sessions/`                                                                                 | ⬜                           | ⬜                                             |

---

## 6. Context Management

| Feature                                    | Pi                                                                                                                                                                                                                                                                                                                                        | Hermes                                                                                                                                                                                                            | OpenHuman                                                                                                                                                                                                                                                                                                                                              | Locus                                                                                                             |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| **Context window management**        | ✅ Compaction engine: triggers at`contextTokens > contextWindow - reserveTokens` (default reserve: 16384). Find cut point (keepRecentTokens: 20000) → LLM summarize → append CompactionEntry → reload. Iterative: passes previous summary. Structured format: files read/modified/created, learned conventions, key decisions, tasks | ✅`context_engine.py` + `context_compressor.py`. Pluggable context engines — only one active at a time. Default: `compressor` (built-in ContextCompressor). Plugin-dir: `plugins/context_engine/<name>/` | ✅ Guard (0.90/0.95 thresholds)                                                                                                                                                                                                                                                                                                                        | 🔧`token_counter.py` only                                                                                       |
| **Manual compaction**                | ✅`/compact [instructions]`                                                                                                                                                                                                                                                                                                             | ✅`/compress` manual trigger                                                                                                                                                                                    | ⬜                                                                                                                                                                                                                                                                                                                                                     | ⬜                                                                                                                |
| **Branch summarization**             | ✅ On`/tree` switch away: no summary / default / custom instructions. Preserves abandoned-branch context. Extension hooks: `pre_branch_summary`, `post_branch_summary`                                                                                                                                                              | ⬜                                                                                                                                                                                                                | ⬜                                                                                                                                                                                                                                                                                                                                                     | ⬜                                                                                                                |
| **Context references**               | ⬜                                                                                                                                                                                                                                                                                                                                        | ✅`context_references.py`                                                                                                                                                                                       | ⬜                                                                                                                                                                                                                                                                                                                                                     | ⬜                                                                                                                |
| **Coding-specific context**          | ⬜                                                                                                                                                                                                                                                                                                                                        | ✅`coding_context.py`                                                                                                                                                                                           | ⬜                                                                                                                                                                                                                                                                                                                                                     | ⬜                                                                                                                |
| **Manual compression feedback**      | ⬜                                                                                                                                                                                                                                                                                                                                        | ✅`manual_compression_feedback.py`                                                                                                                                                                              | ⬜                                                                                                                                                                                                                                                                                                                                                     | ⬜                                                                                                                |
| **Token overflow handling**          | ✅`overflow.ts` — fallback compaction at hard limits. Large results saved to temp files. Output guard (`output-guard.ts`)                                                                                                                                                                                                            | ✅ Save oversized tool results to file instead of destructive truncation. Sandbox-aware tool result persistence                                                                                                   | ✅ 16 KiB tool result cap                                                                                                                                                                                                                                                                                                                              | 🔧 Basic compactor                                                                                                |
| **TokenJuice (smart compression)**   | ⬜                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                                                                                | ✅`tokenjuice/` — classify → match rule → reduce. Three-layer rule overlay: Builtin, User (`~/.config/tokenjuice/rules/`), Project (`.tokenjuice/rules/`). Strategies: truncate, dedup lines, fold whitespace, drop matching regexes, summarize sections. HTML→Markdown with CJK/emoji grapheme preservation. Up to 80% token/cost reduction | ⬜                                                                                                                |
| **Context Forge**                    | ⬜                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                                                                                | ⬜                                                                                                                                                                                                                                                                                                                                                     | 📐 800-token, 6-layer: identity(80t) + temporal(60t) + PG events(180t) + Neo4j(150t) + pgvector(200t) + web(100t) |
| **Query Router / Intent Classifier** | ⬜                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                                                                                | ⬜                                                                                                                                                                                                                                                                                                                                                     | 📐 8 intent types, source routing matrix                                                                          |
| **Context file loading**             | ✅`AGENTS.md` / `CLAUDE.md`: `~/.pi/agent/AGENTS.md`, parent dirs walking up to git root, cwd. `.pi/SYSTEM.md` / `~/.pi/agent/SYSTEM.md` — replace default system prompt. `APPEND_SYSTEM.md`. `--system-prompt`, `--append-system-prompt`. `--no-context-files` / `-nc`                                              | ⬜                                                                                                                                                                                                                | ⬜                                                                                                                                                                                                                                                                                                                                                     | ✅ SOUL.md                                                                                                        |
| **Prior-history exclusion**          | ⬜                                                                                                                                                                                                                                                                                                                                        | ✅ Prior-history tool messages excluded from review summary (clean-context fork)                                                                                                                                  | ⬜                                                                                                                                                                                                                                                                                                                                                     | ⬜                                                                                                                |

---

## 7. Profiles (Hermes-specific)

| Feature                     | Pi | Hermes                                                                                                                                                                                                                                                                                                                                                                                                                                                            | OpenHuman | Locus |
| --------------------------- | -- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ----- |
| **Multiple profiles** | ⬜ | ✅ Multiple independent instances with isolated configs/sessions/skills/memory.`hermes profile list / create / use / delete / show / alias / rename / export / import`. Clone profiles: `--clone`, `--clone-all`, `--clone-from`. Profile-scoped memory isolation. Sticky default profile. Profile-aware paths via `get_hermes_home()`. Profile-aware service units (systemd). Worktree mode: `hermes -w` (isolated git worktree for parallel agents) | ⬜        | ⬜    |

---

## 8. CLI & Terminal UI

### 8A. CLI Modes & Flags

| Feature                             | Pi                                                                                                                                                                                                                  | Hermes                                                                  | OpenHuman                         | Locus                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------- | ------------------------------------------ |
| **Interactive mode**          | ✅ Full TUI with editor, message history, tool rendering. Four visual areas: startup header, messages, editor, footer                                                                                               | ✅`hermes` default to chat mode                                       | ✅ Tauri desktop + web (React/TS) | ❌ Deliberately rejected (Telegram-native) |
| **Single-query / print mode** | ✅`-p`/`--print` — non-interactive, reads piped stdin                                                                                                                                                          | ✅`hermes chat -q` single-query. `hermes -z <prompt>` one-shot mode | ⬜                                | ⬜                                         |
| **JSON event stream mode**    | ✅`--mode json` — all session events as JSON lines. Events: agent_start/end, turn_start/end, message_start/update/end, tool_execution_start/update/end, queue_update, compaction_start/end, auto_retry_start/end | ⬜                                                                      | ⬜                                | ⬜                                         |
| **RPC / daemon mode**         | ✅`--mode rpc` — JSON protocol over stdin/stdout (strict JSONL, LF-only). Commands: prompt, cancel, set-model, set-thinking, fork, compact, session-info. `streamingBehavior`: queue, steer, queueHead, block  | ⬜                                                                      | ✅ JSON-RPC                       | ⬜                                         |
| **Export mode**               | ✅`--export <in> [out]`                                                                                                                                                                                           | ⬜                                                                      | ⬜                                | ⬜                                         |
| **CLI flags count**           | ✅ 39 flags                                                                                                                                                                                                         | ✅ 13+ keyboard handlers                                                | ✅ JSON-RPC + CLI                 | ✅ 18 CLI commands                         |
| **YOLO mode**                 | ⬜                                                                                                                                                                                                                  | ✅`--yolo` skip dangerous command approval                            | ⬜                                | ⬜                                         |

### 8B. TUI Framework

| Feature                                 | Pi                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Hermes                                                                                                                                                                                                                   | OpenHuman               | Locus                                     |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------- | ----------------------------------------- |
| **TUI library**                   | ✅`packages/tui/` — differential rendering (only changed lines redrawn). Component system: `render(width)`, `handleInput(data)`, `invalidate()`. `Focusable` IME support: `CURSOR_MARKER` APC escape, `focused` propagation. Built-in components: `Input`, `Editor`, `Select`, `Container`, `Dialog`                                                                                                                                                                                                                                                                                     | ✅ Ink/React terminal UI (`hermes --tui`). Entry: `ui-tui/src/entry.tsx`. Python JSON-RPC backend: `tui_gateway/`. Types: `gatewayTypes.ts`, `types/`. Components, hooks, lib, theme. Auto-resume last session | ✅ Tauri v2 desktop app | ❌ Deliberately rejected                  |
| **30+ TUI components**            | ✅ Message rendering (`assistant-message`, `armin`, `user-message`, `custom-message`, `skill-invocation-message`), tool display (`tool-execution`, `bash-execution`, `diff`), compaction (`compaction-summary-message`, `branch-summary-message`), selectors (model, session, theme, thinking, oauth, extension, config, settings, tree, scoped-models, show-images, user-message, trust), UI (footer, bordered-loader, countdown-timer, keybinding-hints, login-dialog, first-time-setup, earendil-announcement, dynamic-border, visual-truncate), editors (extension-editor, custom-editor) | ✅ Rich banner/panels, prompt_toolkit input with autocomplete, KawaiiSpinner animated faces during API calls,`┊` activity feed                                                                                        | ⬜                      | ⬜                                        |
| **Hardware cursor**               | ✅`showHardwareCursor` / `PI_HARDWARE_CURSOR=1`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ⬜                                                                                                                                                                                                                       | ⬜                      | ⬜                                        |
| **Light-terminal auto-detection** | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ Auto-detection in TUI                                                                                                                                                                                                 | ⬜                      | ⬜                                        |
| **Skin engine**                   | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ Data-driven theming (banner colors, spinner faces/verbs/wings, tool prefix, response box)                                                                                                                             | ⬜                      | ⬜                                        |
| **Ghost status-bar**              | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ Lines cleared on terminal resize                                                                                                                                                                                      | ⬜                      | ⬜                                        |
| **LaTeX rendering**               | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ LaTeX rendering in CLI                                                                                                                                                                                                | ⬜                      | ⬜                                        |
| **Mouse-wheel scroll**            | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ Mouse-wheel line scroll;`/mouse` toggle for ConPTY phantom mouse injection                                                                                                                                          | ⬜                      | ⬜                                        |
| **CR/LF normalization**           | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ In pasted text                                                                                                                                                                                                        | ⬜                      | ⬜                                        |
| **Native Windows image paste**    | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ Native Windows image paste                                                                                                                                                                                            | ⬜                      | ⬜                                        |
| **Curses fallback TUI**           | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ⬜                                                                                                                                                                                                                       | ⬜                      | 🔧`curses_ui.py` exists but not primary |
| **`/redraw`**                   | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ✅ Force full UI repaint                                                                                                                                                                                                 | ⬜                      | ⬜                                        |

### 8C. Editor & Input

| Feature                               | Pi                                                                | Hermes            | OpenHuman               | Locus |
| ------------------------------------- | ----------------------------------------------------------------- | ----------------- | ----------------------- | ----- |
| **Multiline editing**           | ✅ Full editor with Shift+Enter multi-line                        | ✅ Full editor    | ✅`text_input` module | ❌    |
| **File reference autocomplete** | ✅`@` fuzzy-search, Tab path completion                         | ⬜                | ⬜                      | ⬜    |
| **Syntax highlighting**         | ✅ highlight.js in editor                                         | ⬜                | ⬜                      | ⬜    |
| **External editor**             | ✅ Ctrl+G opens`$VISUAL` or `$EDITOR`                         | ✅ Open-in-editor | ⬜                      | ❌    |
| **Message queue**               | ✅ Enter=steer, Alt+Enter=follow-up, Escape=abort, Alt+Up=restore | ⬜                | ⬜                      | ⬜    |
| **Shell dispatch**              | ✅`!command` sends to model, `!!command` silent               | ⬜                | ⬜                      | ⬜    |
| **Image paste**                 | ✅ Ctrl+V (Alt+V on Windows), drag into terminal                  | ✅ Ctrl+V / Alt+V | ⬜                      | ❌    |
| **Prompt template expansion**   | ✅`/template` in editor                                         | ⬜                | ⬜                      | ⬜    |
| **`editorPaddingX` setting**  | ✅ 0-3                                                            | ⬜                | ⬜                      | ⬜    |

### 8D. Keybindings

| Feature                                  | Pi                                                                                                                                                                                                                                                                                                                 | Hermes                   | OpenHuman | Locus |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ | --------- | ----- |
| **Fully customizable keybindings** | ✅`~/.pi/agent/keybindings.json` — namespaced IDs (`tui.editor.cursorUp`). Legacy auto-migration. `/reload` to apply, `/hotkeys` to display. All keyboard chars, function keys, special keys, multiple bindings per action. Categories: Editor Cursor, Editor Deletion, Input, Navigation, UI, Extensions | ✅ 13+ keyboard handlers | ⬜        | ❌    |

### 8E. Themes

| Feature                | Pi                                                                                                                                                                                                                                                                                                                                                                                                 | Hermes                               | OpenHuman                                                                                                                       | Locus |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Theme system** | ✅ Built-in:`dark`, `light` — auto-detect terminal background. Custom: `~/.pi/agent/themes/*.json`, `.pi/themes/*.json` (trust-gated), packages, settings. JSON format with `$schema`, `name`, `vars` (hex/ANSI/named colors). Color tokens: primary, secondary, background, foreground, borders, syntax, diffs. `/settings` → theme selection, `--theme` CLI, `--no-themes` | ✅ Skin engine (data-driven theming) | ✅ Ocean primary`#4A83DD`, sage/amber/coral semantics. Typography: Inter + Cabinet Grotesk + JetBrains Mono. Dashboard themes | ❌    |

### 8F. Status Bar & Footer

| Feature                        | Pi                                                                 | Hermes                                                                                       | OpenHuman    | Locus |
| ------------------------------ | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | ------------ | ----- |
| **Footer / status bar**  | ✅`footer-data-provider.ts` — cwd, session, tokens, cost, model | ✅`runtime_footer.py`, `/footer` toggle, opt-in runtime-metadata footer on final replies | ✅ Dashboard | ❌    |
| **Provider attribution** | ✅`provider-attribution.ts`                                      | ⬜                                                                                           | ⬜           | ❌    |
| **Diagnostics UI**       | ✅`diagnostics.ts`                                               | ✅`hermes doctor`                                                                          | ⬜           | ⬜    |

---

## 9. CLI Subcommands

### 9A. Pi CLI Subcommands

| Command                                   | Description                                             |
| ----------------------------------------- | ------------------------------------------------------- |
| `pi install <source> [-l]`              | Install package (npm/git/path),`-l` for project-local |
| `pi remove`/`uninstall <source> [-l]` | Remove package                                          |
| `pi update [source\|self\|pi]`            | Update pi + packages + reconcile pinned git refs        |
| `pi update --extensions`                | Packages only                                           |
| `pi update --self [--force]`            | Pi only (platform-specific)                             |
| `pi list`                               | List installed packages                                 |
| `pi config`                             | Enable/disable package resources                        |

### 9B. Hermes CLI Subcommands

| Command                                                                                        | Description                                                                                                                                     |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `hermes config`                                                                              | View/edit/set/path/env-path/check/migrate                                                                                                       |
| `hermes model`                                                                               | Interactive model/provider picker                                                                                                               |
| `hermes setup [section]`                                                                     | Interactive wizard (model\|terminal\|gateway\|tools\|agent)                                                                                     |
| `hermes doctor [--fix]`                                                                      | Dependency/config diagnostics                                                                                                                   |
| `hermes status [--all]`                                                                      | Component status                                                                                                                                |
| `hermes login [--provider]` / `hermes logout`                                              | OAuth login/logout                                                                                                                              |
| `hermes auth add/list/remove/reset`                                                          | Credential pool                                                                                                                                 |
| `hermes insights [--days]`                                                                   | Usage analytics                                                                                                                                 |
| `hermes update [--check]`                                                                    | Self-update                                                                                                                                     |
| `hermes completion bash\|zsh`                                                                 | Shell completions                                                                                                                               |
| `hermes acp`                                                                                 | ACP server for IDE integration                                                                                                                  |
| `hermes claw migrate`                                                                        | Migrate from OpenClaw                                                                                                                           |
| `hermes uninstall`                                                                           | Uninstall                                                                                                                                       |
| `hermes honcho setup/status`                                                                 | Honcho memory integration                                                                                                                       |
| `hermes memory setup/status/off`                                                             | Memory provider config                                                                                                                          |
| `hermes pairing list/approve/revoke`                                                         | DM authorization                                                                                                                                |
| `hermes plugins list/install/remove`                                                         | Plugin management                                                                                                                               |
| `hermes tools`                                                                               | Interactive tool enable/disable (curses UI)                                                                                                     |
| `hermes tools list/enable/disable`                                                           | Tool management                                                                                                                                 |
| `hermes skills list/search/install/inspect/config/check/update/uninstall/publish/browse/tap` | Skill management                                                                                                                                |
| `hermes mcp serve/add/remove/list/test/configure`                                            | MCP management                                                                                                                                  |
| `hermes gateway run/install/start/stop/restart/status/setup`                                 | Gateway lifecycle                                                                                                                               |
| `hermes cron list/add/edit/pause/resume/run/status`                                          | Cron management                                                                                                                                 |
| `hermes webhook subscribe/list/remove/test`                                                  | Webhook management                                                                                                                              |
| `hermes profile list/create/use/delete/show/alias/rename/export/import`                      | Profile management                                                                                                                              |
| `hermes sessions list/export/rename/delete/prune/stats/browse`                               | Session management                                                                                                                              |
| `hermes logs [--follow] [--level] [--session]`                                               | Log viewing                                                                                                                                     |
| `hermes fallback`                                                                            | Managing fallback providers                                                                                                                     |
| `hermes curator`                                                                             | Curator management (status, run, pause, resume, pin, unpin, archive, restore, prune, backup, rollback)                                          |
| `hermes kanban`                                                                              | init, create, list, show, assign, link, unlink, comment, complete, block, unblock, archive, tail, watch, stats, runs, log, dispatch, daemon, gc |

---

## 10. Slash Commands (In-Session)

### 10A. Pi Slash Commands

| Category          | Commands                                                                                                                |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Session** | `/resume`, `/new`, `/name`, `/session`, `/tree`, `/fork`, `/clone`, `/compact`, `/export`, `/share` |
| **Config**  | `/login`, `/logout`, `/model`, `/scoped-models`, `/settings`, `/trust`                                      |
| **Info**    | `/reload`, `/hotkeys`, `/changelog`, `/quit`                                                                    |
| **Skills**  | `/skill:<name>` + custom extension commands                                                                           |

### 10B. Hermes Slash Commands

| Category               | Commands                                                                                                                                                                                                                                                                                                                                        |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Session**      | `/new`, `/reset`, `/clear`, `/retry`, `/undo`, `/title`, `/compress`, `/stop`, `/rollback`, `/snapshot`, `/background`, `/queue`, `/steer`, `/agents`, `/tasks`, `/resume`, `/goal`, `/redraw`, `/branch`, `/fork`, `/fast`, `/browser`, `/history`, `/save`, `/copy`, `/paste`, `/image` |
| **Config**       | `/config`, `/model`, `/personality`, `/reasoning`, `/verbose`, `/voice`, `/yolo`, `/busy`, `/indicator`, `/footer`, `/skin`, `/statusbar`                                                                                                                                                                               |
| **Tools/Skills** | `/tools`, `/toolsets`, `/skills`, `/skill`, `/reload-skills`, `/reload`, `/reload-mcp`, `/cron`, `/curator`, `/kanban`, `/plugins`                                                                                                                                                                                        |
| **Gateway**      | `/approve`, `/deny`, `/restart`, `/sethome`, `/update`, `/topic`, `/platforms`, `/gateway`                                                                                                                                                                                                                                      |
| **Info**         | `/help`, `/commands`, `/usage`, `/insights`, `/gquota`, `/status`, `/profile`, `/debug`                                                                                                                                                                                                                                         |
| **Exit**         | `/quit`, `/exit`, `/q`                                                                                                                                                                                                                                                                                                                    |
| **Special**      | `/background <prompt>` (fire-and-forget), `/queue <prompt>` (next turn), `/steer <prompt>` (inject after next tool call), `/goal [text\|sub]` (standing goal), `/fast` (priority toggle), `/voice [on\|off\|tts]`, `/mouse` toggle                                                                                                   |

---

## 11. Extensions / Plugins / Skills

### 11A. Extension System (Pi-specific)

| Feature                          | Pi                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Hermes                         | OpenHuman              | Locus |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ | ---------------------- | ----- |
| **Extension architecture** | ✅ TypeScript modules, auto-discovered:`~/.pi/agent/extensions/` (global), `.pi/extensions/` (project, trust-gated). CLI: `-e <source>` (path/npm/git), repeatable. Hot-reload: `/reload`. Dependencies via `package.json`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ⬜ (uses ACP + skills instead) | ⬜ (uses MCP registry) | ⬜    |
| **Extension API**          | ✅`pi.registerTool()`, `pi.registerCommand()`, `pi.on(event, handler)` (15+ events), `pi.appendEntry()`, `pi.registerCustomModel()`, `pi.setCustomHeader()`/`pi.setCustomFooter()`, `pi.setToolRenderer()`/`pi.setMessageRenderer()`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | ⬜                             | ⬜                     | ⬜    |
| **15+ lifecycle events**   | ✅ resource_changed, session_start/end, agent_start/end, pre_llm_call/post_llm_call, tool_call/tool_result (can block/modify), pre_compact/post_compact, pre_branch_summary/post_branch_summary, project_trust, user_message                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | ⬜                             | ⬜                     | ⬜    |
| **Custom UI components**   | ✅`ctx.ui.custom(component)`, `ctx.ui.select()`, `ctx.ui.confirm()`, `ctx.ui.input()`, `ctx.ui.notify()`. Component interface: `render(width)`, `handleInput(data)`, `wantsKeyRelease`, `invalidate()`. Focusable for IME                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ⬜                             | ⬜                     | ⬜    |
| **75+ example extensions** | ✅ Security (confirm-destructive, permission-gate, protected-paths, dirty-repo-guard, project-trust), Git workflows (git-checkpoint, git-merge-and-resolve, auto-commit-on-exit), Custom providers (anthropic, gitlab-duo), Tool extensions (tools, dynamic-tools, tool-override, bash-spawn-hook, inline-bash, truncated-tool, built-in-tool-renderer), UI customization (border-status-editor, custom-footer/header, titlebar-spinner, working-indicator, status-line, model-status, mac-system-theme, hidden-thinking-label, minimal-mode), Input/Message (input-transform, message-renderer, send-user-message), Games (snake, space-invaders, tic-tac-toe, doom-overlay), Sub-agents (subagent, handoff, plan-mode), Compaction (custom-compaction, trigger-compact, rainbow-editor, modal-editor), Integration (github-issue-autocomplete, ssh, gondolin, sandbox), State (bookmark, todo, preset, session-name), Other (claude-rules, event-bus, file-trigger, notify, pirate, prompt-customizer, provider-payload, qna, question, questionnaire, reload-runtime, shutdown-command, structured-output, summarize, system-prompt-header, timed-confirm, widget-placement, working-message-test, overlay-test, overlay-qa-tests, hello, commands, dynamic-resources, interactive-shell, with-deps, rpc-demo, rpc-extension-ui) | ⬜                             | ⬜                     | ⬜    |

### 11B. Plugin System (Hermes-specific)

| Feature                           | Pi | Hermes                                                                                                                                                                                                                                                                                                                                                    | OpenHuman | Locus |
| --------------------------------- | -- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ----- |
| **Plugin architecture**     | ⬜ | ✅`plugins/` directory scanned at startup. Types: `backend` (auto-loaded), `standalone` (opt-in), `kind` field. `plugin.yaml` metadata: name, version, kind, description, hooks, provides_tools, pip_dependencies, external_dependencies, requires_env. Page-scoped plugin slots for dashboard pages. Declarative installation for NixOS module | ⬜        | ⬜    |
| **Plugin registration API** | ⬜ | ✅`register_tool`, `register_hook`, `register_memory_provider`, `register_context_engine`, `register_cli_command`, `register_web_search_provider`, `register_image_gen_provider`, `register_video_gen_provider`                                                                                                                           | ⬜        | ⬜    |
| **Plugin hooks**            | ⬜ | ✅ 11 lifecycle hooks:`pre_api_request`, `post_api_request`, `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `post_tool_call`, `on_session_end`, `on_pre_compress`, `pre_gateway_dispatch`, `pre_approval_request`, `post_approval_response`                                                                                      | ⬜        | ⬜    |
| **20+ plugin types**        | ⬜ | ✅ Context engines, memory providers (9), model providers (30+), image gen providers (4), video gen providers (2), web search providers (8), browser providers (3), platform adapters (8), standalone (disk-cleanup, google_meet, spotify, teams_pipeline), observability (langfuse), achievements                                                        | ⬜        | ⬜    |

### 11C. Skills System

| Feature                         | Pi                                                                                                                                                                                                                                                                                                     | Hermes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | OpenHuman                                                                                                                                                                                                                                                                  | Locus |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Skills architecture**   | ✅ Implements[Agent Skills standard](https://agentskills.io/specification). Cross-harness compatible (Claude Code, OpenAI Codex). Progressive disclosure: descriptions in context, full SKILL.md on-demand. Skills as `/skill:name` commands with arguments                                           | ✅ Agent-created skills: SKILL.md with YAML frontmatter. Skills hub: search, install, inspect, update, unpublish, browse, tap. Install from HTTP(S) URL.`/reload-skills`. Preload: `-s skill1,skill2`. Per-platform enable/disable. Telemetry: `~/.hermes/skills/.usage.json` (use_count, view_count, patch_count, last_activity_at, state, pinned). AST audit, guard, sync. Background review fork for automated generation. `.archive/` excluded                                                                                                                               | ✅ User-installed from Skills tab. Sandboxed with resource limits. Integrate with Memory Tree. Fetch external data, run on schedule, transform info, respond to events. Registry + runtime (QuickJS removed; metadata-only now). Exposed as agent-delegatable capabilities | ⬜    |
| **Bundled skills**        | ✅ 1:`.pi/skills/add-llm-provider.md`                                                                                                                                                                                                                                                                | ✅ 73 across 17 categories: autonomous-ai-agents, creative, data-science, diagramming, domain, email, gaming, gifs, github, inference-sh, mcp, media, mlops, note-taking, productivity, research, smart-home, social-media, apple, yuanbao                                                                                                                                                                                                                                                                                                                                               | ✅ 1 (demo of format — marketplace is the ecosystem)                                                                                                                                                                                                                      | ⬜    |
| **Optional skills**       | ⬜                                                                                                                                                                                                                                                                                                     | ✅ 97 across 10 categories: autonomous-ai-agents (blackbox, honcho), blockchain (evm, hyperliquid, solana), communication, creative (blender-mcp, concept-diagrams, hyperframes, kanban-video, meme-generation), devops (cli, docker, pinggy-tunnel, watchers), dogfood, email (agentmail), finance (3-statement-model, comps, dcf, excel, lbo, merger, pptx, stocks), health (fitness-nutrition, neuroskill-bci), mcp (fastmcp, mcporter), migration (openclaw), security (1password, oss-forensics, sherlock), software-development (rest-graphql-debug), web-development (page-agent) | ⬜                                                                                                                                                                                                                                                                         | ⬜    |
| **Agent Skills standard** | ✅ (spec-compliant)                                                                                                                                                                                                                                                                                    | ❌ (custom format)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ❌ (metadata-only now)                                                                                                                                                                                                                                                     | ⬜    |
| **Skill locations**       | ✅ Global:`~/.pi/agent/skills/`, `~/.agents/skills/`. Project: `.pi/skills/`, `.agents/skills/`. Packages: `skills/` dir or `pi.skills` in `package.json`. Settings: `skills` array with globs. CLI: `--skill <path>`. Cross-harness: load `~/.claude/skills`, `~/.codex/skills` | ✅`~/.hermes/skills/`, external_dirs, skills hub                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ✅ Skills tab in desktop app, marketplace install                                                                                                                                                                                                                          | ⬜    |
| **Skill protection**      | ⬜                                                                                                                                                                                                                                                                                                     | ✅ Bundled + hub skills protected from mutation. Pinned skills exempt from auto-transitions.`skill_manage` refuses writes on pinned skills                                                                                                                                                                                                                                                                                                                                                                                                                                             | ⬜                                                                                                                                                                                                                                                                         | ⬜    |

### 11D. Managed Integrations (OpenHuman-specific)

| Feature                            | Pi | Hermes | OpenHuman                                                                                                                                                                                                                                                                                                                                                                              | Locus |
| ---------------------------------- | -- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Integration architecture** | ⬜ | ⬜     | ✅ 118+ managed connectors via Composio layer. Backend-proxied access. One-click OAuth. Zero API keys in managed mode. Direct Composio mode supported. Four exposure surfaces: agent tool, memory source (auto-fetch), profile signal, trigger source                                                                                                                                  | ⬜    |
| **Integration categories**   | ⬜ | ⬜     | ✅ Email & Calendar (Gmail, Outlook, Google Calendar, Apple Calendar), Docs & Storage (Google Docs, Drive, Notion, Dropbox, Airtable), Code & Dev (GitHub, Linear, Jira, Figma), Comms (Slack, Discord, Teams, Telegram, WhatsApp), CRM & Sales (Salesforce, HubSpot), Commerce (Stripe, Shopify), Project (Asana, Trello), Social (Twitter/X, Spotify, YouTube), Finance (Polymarket) | ⬜    |
| **Auto-Fetch**               | ⬜ | ⬜     | ✅ 20-minute loop walks active connections. Pulls fresh data into Memory Tree. Per-provider sync interval (e.g., Gmail every 15 min). Daily budget cap per connection. OAuth scope binding. Revocation stops syncing at next tick; existing chunks remain local                                                                                                                        | ⬜    |

### 11E. Prompt Templates (Pi-specific)

| Feature                    | Pi                                                                                                                                                                                                                                                                                                                                                                                     | Hermes | OpenHuman | Locus |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | --------- | ----- |
| **Prompt templates** | ✅ Markdown files with YAML frontmatter, expanded via`/name` in editor. Frontmatter: `description`, `argument-hint`. Locations: `~/.pi/agent/prompts/`, `.pi/prompts/`, packages, settings. CLI: `--prompt-template`, `--no-prompt-templates`. 5 bundled: `cl.md` (changelog), `is.md` (issues), `pr.md` (PR review), `sa.md` (summary), `wr.md` (work review) | ⬜     | ⬜        | ⬜    |

### 11F. Pi Packages

| Feature                  | Pi                                                                                                                                                                                                                                                                                               | Hermes | OpenHuman | Locus |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | --------- | ----- |
| **Package system** | ✅ Bundle extensions, skills, prompts, themes for npm/git/path distribution. Sources: npm (`npm:@scope/pkg@1.2.3`), git (`git:github.com/user/repo@v1`), path, URL. `-l` for project-local. `-e` for one-time use. Auto-install missing project packages after trust. Resource filtering | ⬜     | ⬜        | ⬜    |

### 11G. ACP Protocol (Hermes-specific)

| Feature               | Pi | Hermes                                                                                                                                                                                                                                | OpenHuman | Locus |
| --------------------- | -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ----- |
| **ACP adapter** | ⬜ | ✅`hermes acp` ACP server mode. Modules: entry, server, session, auth, permissions, edit_approval, tools, events. Transports: Hermes tools as MCP server, Copilot ACP client, Codex transport. IDE support: VS Code, Zed, JetBrains | ⬜        | ⬜    |

---

## 12. Learning & Self-Improvement

| Feature                                   | Pi | Hermes                                       | OpenHuman                                                                                                                                         | Locus                                                                                          |
| ----------------------------------------- | -- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Post-session learning**           | ⬜ | ✅ Curator → insights → memory nudge       | ✅ Post-turn hooks: Archivist, Reflection, ToolTracker, UserProfile                                                                               | 🔧`reflector.py` (basic LLM reflection)                                                      |
| **Cross-session search / recall**   | ⬜ | ✅ FTS5 full-text search + LLM summarization | ✅`memory_search`                                                                                                                               | ⬜                                                                                             |
| **User profile building**           | ⬜ | ✅ Honcho dialectic modeling                 | ✅ Ambient profile facets + PROFILE.md injection + stability detector (30min) +`user_profile.rs`, `reflection.rs`, `linkedin_enrichment.rs` | 📐 User Identity Profile (behavioral tendencies, peak windows, stressors, communication style) |
| **Tool usage tracking**             | ⬜ | ⬜                                           | ✅`ToolTrackerHook`                                                                                                                             | ✅`tool_tracker.py`                                                                          |
| **Agent experience tracking**       | ⬜ | ⬜                                           | ✅`agent_experience` module                                                                                                                     | ⬜                                                                                             |
| **Codegraph**                       | ⬜ | ⬜                                           | ✅`codegraph/` — codebase knowledge graph with full-text index, symbol/code search, graph store, codegraph tools for agent                     | ⬜                                                                                             |
| **Personal Reward Model**           | ⬜ | ⬜                                           | ⬜                                                                                                                                                | 📐 sklearn LogisticRegression (👍/👎 feedback, weekly retrain, ≥0.6 threshold)                |
| **Hebbian learning rules**          | ⬜ | ⬜                                           | ⬜                                                                                                                                                | 📐 Neo4j edge weights with biological decay, STDP reinforcement                                |
| **Multi-horizon pattern detection** | ⬜ | ⬜                                           | ⬜                                                                                                                                                | 📐 5 horizons (H1: 6h, H2: 24h, H3: 7d, H4: 30d, H5: all-time)                                 |
| **Self-evolving Architect Bot**     | ⬜ | ⬜                                           | ⬜                                                                                                                                                | 📐 Scans reward signals, generates patches, risk-gated deploy                                  |

---

## 13. Agent Orchestration & Teams

| Feature                            | Pi                           | Hermes                                                                                         | OpenHuman                                                                                                                                                                                                                             | Locus                                                        |
| ---------------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **Subagent spawning**        | ✅ Built-in subagent tool    | ✅`delegate_task` for single or batch parallel. `agent_init.py` + `process_bootstrap.py` | ✅ 3-tier hierarchy.`spawn_subagent`, `spawn_worker_thread`, `delegate`, `archetype_delegation`, `skill_delegation`                                                                                                         | 🔧`delegation/subagent.py`                                 |
| **Subagent archetypes**      | ⬜                           | ⬜                                                                                             | ✅ 14 built-in (`.claude/agents/`): architectobot, build-agent, codecrusher, deploy-agent, designguru, dev-agent, memory-keeper, mobile-agent, pr-manager/lite, pr-reviewer, qualityqueen, taskmaster, test-agent, ship-and-babysit | 📐 4 faction sub-agents (Planner, Curator, Analyst, Builder) |
| **Depth limiting**           | ⬜                           | ✅ depth=1 by default                                                                          | ✅ MAX_SPAWN_DEPTH=3                                                                                                                                                                                                                  | ⬜                                                           |
| **RPC-based subagents**      | ✅ RPC mode                  | ✅`codex_runtime.py` (RPC)                                                                   | ⬜                                                                                                                                                                                                                                    | ⬜                                                           |
| **Coding agent**             | ✅ Full coding agent package | ⬜                                                                                             | ✅`code_executor` archetype                                                                                                                                                                                                         | 🔧`delegation/coding_agent.py`                             |
| **ACP client for subagents** | ⬜                           | ✅`copilot_acp_client.py`                                                                    | ⬜                                                                                                                                                                                                                                    | ⬜                                                           |
| **Command Center**           | ⬜                           | ⬜                                                                                             | ✅`agent_orchestration/command_center/` — central dispatch                                                                                                                                                                         | ⬜                                                           |
| **Workflows**                | ⬜                           | ⬜                                                                                             | ✅`workflows/` — multi-step workflows, `workflow_runs/` — execution tracking                                                                                                                                                    | ⬜                                                           |
| **Worktree management**      | ⬜                           | ✅ Worktree mode:`hermes -w`                                                                 | ✅`worktree.rs` — git worktree management for parallel agent work                                                                                                                                                                  | ⬜                                                           |
| **Agent teams config**       | ⬜                           | ⬜                                                                                             | ✅`[orchestrator]` — lead model, `[teams.research]` — lead_model + agent_model, `[teams.code]` — agent_model                                                                                                                 | ⬜                                                           |
| **Agent registry**           | ⬜                           | ⬜                                                                                             | ✅`agent_registry/` — available agents registry                                                                                                                                                                                    | ⬜                                                           |

---

## 14. Scheduling & Cron

| Feature                                 | Pi | Hermes                                                                                                                                                                                                                                                                                                                                          | OpenHuman                                                                                                                                                                                                                                                                             | Locus                                                               |
| --------------------------------------- | -- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **Cron / scheduled tasks**        | ⬜ | ✅ CLI:`hermes cron list/add/edit/pause/resume/run/status`. Slash: `/cron`. Schedules: duration, natural language, cron, ISO timestamp. Per-job overrides: skills, model/provider, script, no_agent, context_from, workdir, profile, deliver, enabled_toolsets. 3-minute hard interrupt; `.tick.lock`; skip_memory; header/footer framing | ✅`cron/` + `scheduler_gate/`: recurring jobs, one-off reminders, arbitrary agent runs on schedule, run history per job. Backend: `cron` crate. Battery-aware scheduling (laptop throttling via `starship-battery`), system signal monitoring, background LLM work throttling | ✅`cron_runner.py`                                                |
| **Cron tools (agent-facing)**     | ⬜ | ✅`cronjob` tool — scheduled task management                                                                                                                                                                                                                                                                                                 | ✅`cron_add`, `cron_list`, `cron_update`, `cron_remove`, `cron_run`, `cron_runs`                                                                                                                                                                                          | ⬜                                                                  |
| **Task sources**                  | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                              | ✅`task_sources` module                                                                                                                                                                                                                                                             | ✅`scheduler/task_sources.py`                                     |
| **Background processes**          | ⬜ | ✅`terminal(background=True, notify_on_complete=True)`. `process` tool: list/poll/log/wait/kill/write/close                                                                                                                                                                                                                                 | ⬜                                                                                                                                                                                                                                                                                    | ⬜                                                                  |
| **Webhooks**                      | ⬜ | ✅`hermes webhook subscribe/list/remove/test`. Safe-tools-only execution                                                                                                                                                                                                                                                                      | ✅`webhooks/` — incoming webhook triggers, safe-tools-only execution                                                                                                                                                                                                               | ✅`webhooks.py`                                                   |
| **Inner Loop (proactive)**        | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                              | ⬜                                                                                                                                                                                                                                                                                    | 📐 APScheduler every 90min (07:00–00:00), fires without user input |
| **Structured check-in reminders** | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                              | ⬜                                                                                                                                                                                                                                                                                    | 📐 07:30/13:00/18:00/22:00 IST → Telegram inline keyboards         |
| **Heartbeat / notification**      | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                              | ✅`heartbeat` module                                                                                                                                                                                                                                                                | ✅`heartbeat/notification.py` + `subconscious.py`               |

---

## 15. Subconscious & Background Intelligence

| Feature                     | Pi | Hermes | OpenHuman                                                                                                                                                                                                                                                                                                                                                                                             | Locus                                 |
| --------------------------- | -- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **Subconscious loop** | ⬜ | ⬜     | ✅`subconscious` module — periodic tick evaluation, loads user-defined and system tasks, reads workspace state and recent memory, decides: skip/act/escalate. System tasks: check connected skills, review new memory, monitor health. User tasks: check emails, send daily summary, summarize updates. Decisions: Skip (noop), Act (execute, write-intent escalates), Escalate (deeper reasoning) | ✅`subconscious.py` + 📐 Inner Loop |
| **Dreaming state**    | ⬜ | ⬜     | ✅ Offline consolidation when user away. Distills day's chunks into longer-horizon summaries. Refreshes topic trees for heated entities. Surfaces patterns across sources. Mascot animates differently while dreaming. Dreams folded into Memory Tree on wake                                                                                                                                         | ⬜                                    |

---

## 16. Security & Sandboxing

| Feature                                | Pi                                                                                                                                                                                                                                                                                                                                                        | Hermes                                                                                                                                             | OpenHuman                                                                                                                                                                                                             | Locus                                |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| **Project trust management**     | ✅`trust-manager.ts` — interactive prompt, trust saved in `~/.pi/agent/trust.json` (per-folder, inherited). `/trust` to save, `--approve`/`-a`, `--no-approve`/`-na`. `defaultProjectTrust` fallback (ask/always/never). Before trust: only context + user/global extensions. After trust: project extensions, packages, settings loaded | ⬜                                                                                                                                                 | ⬜                                                                                                                                                                                                                    | ⬜                                   |
| **Autonomy tiers**               | ⬜                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                 | ✅`[autonomy]` config → `SecurityPolicy`: `readonly` / `supervised` / `full`. `workspace_only` flag, `trusted_roots`, `allow_tool_install` gate. Via Settings or `config.update_autonomy_settings` | ⬜                                   |
| **Approval gate**                | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅ Approval modes: manual, smart, off. ACP edit approval.`/approve`, `/deny` in gateway. Active-session guard bypass for approve/deny/stop/new | ✅ ON by default (`OPENHUMAN_APPROVAL_GATE=0` to opt out). Parks interactive chat turns only; background/cron allowed. `ApprovalRequestCard`. 10-min TTL → Auto-Deny                                             | ✅`approval_store.py`              |
| **Path security**                | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅`path_security.py` for path sandboxing, `tirith_security.py` for website/shell blocklists                                                    | ✅`action_dir` (agent read/write root), `workspace_dir` (internal state, agent CANNOT write). `is_workspace_internal_path` fail-closed. `is_always_forbidden` — system/credential dirs blocked               | ⬜                                   |
| **Shell command classification** | ⬜                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                 | ✅`classify_command` → `CommandClass` (Read/Write/Network/Install/Destructive). Unrecognized → Write. `gate_decision(class, tier)` → Allow/Prompt/Block                                                      | ✅`shell_exec.py` BLOCKED_PATTERNS |
| **File safety checks**           | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅`file_safety.py`                                                                                                                               | ✅`file_state`, `cwd_jail`                                                                                                                                                                                        | ⬜                                   |
| **Sandbox backends**             | ⬜                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                 | ✅ Docker (remote/cron), Local OS jail: Landlock (Linux), Seatbelt (macOS), AppContainer (Windows), Noop fallback.`sandbox_mode = "sandboxed"` opt-in per agent                                                     | ⬜                                   |
| **Containerization**             | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅ Docker terminal backend: run container as host user                                                                                             | ⬜                                                                                                                                                                                                                    | ⬜                                   |
| **Data redaction**               | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅`redact.py`, `redact_secrets` / `redact_pii` config                                                                                        | ⬜                                                                                                                                                                                                                    | ⬜                                   |
| **Think token scrubbing**        | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅`think_scrubber.py`                                                                                                                            | ⬜                                                                                                                                                                                                                    | ⬜                                   |
| **Message sanitization**         | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅`message_sanitization.py`                                                                                                                      | ⬜                                                                                                                                                                                                                    | ⬜                                   |
| **Prompt injection protection**  | ⬜                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                 | ✅`prompt_injection/` — detection and mitigation                                                                                                                                                                   | ⬜                                   |
| **Secret prompt encryption**     | ⬜                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                 | ⬜                                                                                                                                                                                                                    | ✅`secret_prompt.py`               |
| **Encryption / keyring**         | ⬜                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                 | ✅`encryption/` domain, OS keyring (`keyring/`): Apple Keychain, Windows Credential Manager, Linux Secret Service / kernel keyring. `keyring_consent/` permission flows                                         | ⬜                                   |
| **TLS**                          | ⬜                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                 | ✅`tls/` — rustls with platform-native certs                                                                                                                                                                       | ⬜                                   |
| **Privacy model**                | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅ SSRF protection, cron path traversal hardening, cross-session isolation, DM pairing                                                             | ✅ Core never calls third-party API directly (managed mode). OAuth tokens never on disk in plaintext. Agent only sees tool call results, not credentials. Audio capture local. Memory Tree data stays on device       | ⬜                                   |
| **Proxy support**                | ✅`node-http-proxy.ts`                                                                                                                                                                                                                                                                                                                                  | ⬜                                                                                                                                                 | ✅`proxy` config                                                                                                                                                                                                    | ✅`proxy.py`                       |
| **Gondolin (micro-VM sandbox)**  | ✅ Extension: tools → local micro-VM while auth stays on host                                                                                                                                                                                                                                                                                            | ⬜                                                                                                                                                 | ⬜                                                                                                                                                                                                                    | ⬜                                   |
| **OpenShell policy sandbox**     | ✅ NVIDIA OpenShell                                                                                                                                                                                                                                                                                                                                       | ⬜                                                                                                                                                 | ⬜                                                                                                                                                                                                                    | ⬜                                   |
| **Credential management**        | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅`credential_pool` / `credential_sources` / `credential_persistence`. Bitwarden secret source. Exhaustion-aware rotation                    | ⬜                                                                                                                                                                                                                    | ⬜                                   |
| **DM authorization / pairing**   | ⬜                                                                                                                                                                                                                                                                                                                                                        | ✅`hermes pairing list/approve/revoke`. PairingStore atomic writes. Approval session key isolated per turn                                       | ⬜                                                                                                                                                                                                                    | ⬜                                   |

---

## 17. Voice & Meetings

| Feature                          | Pi | Hermes                                                                                                                                                                                                                                                                                                 | OpenHuman                                                                                                                                                                                                                                                                                                                 | Locus                                                                  |
| -------------------------------- | -- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **STT (Speech-to-Text)**   | ⬜ | ✅ Provider auto-detection: 1. Local faster-whisper (free), 2. Groq Whisper (free tier), 3. OpenAI Whisper (paid), 4. Mistral Voxtral. Config:`stt.enabled`, `stt.provider`, `stt.local.model`. Models: tiny, base, small, medium, large-v3                                                      | ✅ Hotkey push-to-talk and toggle modes. Cross-platform mic capture with voice-activity detection. Streaming transcription via whisper-rs (local, Metal-accelerated on macOS). Hallucination filter. Postprocess: punctuation, capitalization, dictation cleanup. Can replace active text input or send directly to agent | ✅ 4 backends (Whisper local, Azure, Groq, OpenAI)                     |
| **TTS (Text-to-Speech)**   | ⬜ | ✅`text_to_speech` tool with provider config. TTS provider registry. NeuTTS lib (`neutts_samples`, `neutts_synth.py`)                                                                                                                                                                            | ✅ Hosted TTS model with configurable voice. Natural timing and prosody. Viseme map for mascot lip-sync                                                                                                                                                                                                                   | ✅ 4 backends (Edge TTS, ElevenLabs, OpenAI, Piper)                    |
| **Voice recording in-app** | ⬜ | ✅ Ctrl+R in TUI                                                                                                                                                                                                                                                                                       | ⬜                                                                                                                                                                                                                                                                                                                        | ⬜                                                                     |
| **Dictation**              | ⬜ | ⬜                                                                                                                                                                                                                                                                                                     | ✅`dictation` module — `dictation_hotkeys` in Tauri shell                                                                                                                                                                                                                                                            | ✅`dictation.py`                                                     |
| **Voice call interface**   | ⬜ | ⬜                                                                                                                                                                                                                                                                                                     | ⬜                                                                                                                                                                                                                                                                                                                        | 📐 Audio → Groq Whisper → pipeline → Kokoro TTS → vault transcript |
| **Audio toolkit**          | ⬜ | ⬜                                                                                                                                                                                                                                                                                                     | ✅`audio_toolkit/` — CPAL for cross-platform audio, Hound for WAV encoding                                                                                                                                                                                                                                             | ⬜                                                                     |
| **Live Google Meet agent** | ⬜ | ✅ v1: transcribe-only (headless Chromium + live captions). v2: realtime duplex audio (OpenAI Realtime + BlackHole/PulseAudio). v3: remote node host. Tools:`meet_join`, `meet_leave`, `meet_status`, `meet_transcript`, `meet_say`. Explicit-by-design: only joins `meet.google.com` URLs | ✅ Joins via embedded webview, streams audio to STT, transcribes everyone, writes notes into Memory Tree, speaks back, mascot face piped as camera feed                                                                                                                                                                   | ⬜                                                                     |
| **Transcription tools**    | ⬜ | ✅`transcription_tools` — STT-provider tools                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                                                                                                                                                                                        | ⬜                                                                     |

---

## 18. Desktop Companion (OpenHuman-specific)

| Feature                      | Pi | Hermes | OpenHuman                                                                                                                                                                                                                                                                                                                                                                    | Locus |
| ---------------------------- | -- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Animated mascot**    | ⬜ | ⬜     | ✅ Rive animation (`tiny_mascot.riv`). Mood states: idle, thinking, listening, talking, surprised, dreaming. Transitions based on agent activity. Lip-sync via viseme map. Conversation-level cue reactions. Memory-backed personality. Dreaming animation during offline consolidation. Native window management (`mascot_native_window`). Position and overlay control | ⬜    |
| **Companion pipeline** | ⬜ | ⬜     | ✅`desktop_companion/`: `pipeline.rs`, `session.rs`, `handoff.rs`, `bus.rs`, `pointing.rs`                                                                                                                                                                                                                                                                       | ⬜    |

---

## 19. Messaging Channels / Gateway

### 19A. Platform Support

| Platform                          | Pi                   | Hermes                                                                                                                                                                                                                       | OpenHuman                                                                                          | Locus                                              |
| --------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **Telegram**                | ⬜                   | ✅ Chat allowlists, emoji reactions for approval, group topics skill binding, fresh finals, markdown table bullets, native multi-image, centralized audio routing + FLAC, command sanitization, per-platform disabled skills | ✅ Primary channel, two-way, 80+ actions, encrypted credentials, group topics                      | ✅ Primary interface (PTB, auth, inline keyboards) |
| **Discord**                 | ⬜                   | ✅ Opt-in toolsets, ID injection, tool split, Feishu wiring, coerce limit, channel ignored/no_thread_channels, skills as native slash commands,`/approve`/`/deny`/`/queue`/`/background`/`/btw`                    | ✅ Send/receive, channel management, skills as native slash commands                               | ✅ Channel module                                  |
| **Slack**                   | ⬜                   | ✅ Thread engagement (auto-respond in bot-started + mentioned threads),`strict_mention`, `channel_skill_bindings`, approval buttons + thread context, mrkdwn in edit_message                                             | ✅ Thread engagement, strict_mention, channel skill bindings, approval buttons, mrkdwn             | ✅ Channel module                                  |
| **WhatsApp**                | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ✅ WhatsApp Web via WhatsApp-Rust v0.5, SQLiteStore, group sender-key, LID-addressed contacts      | ✅ Channel module                                  |
| **Signal**                  | ⬜                   | ✅ Native formatting (markdown → bodyRanges, reply quotes, reactions), full MEDIA tag delivery (send_image_file, send_voice, send_video)                                                                                    | ✅ Native formatting, reply quotes, reactions, full MEDIA tag delivery                             | ✅ Channel module                                  |
| **Matrix**                  | ⬜                   | ✅ Tier 1 parity: reactions, read receipts, rich formatting, room management. MATRIX_REQUIRE_MENTION, MATRIX_AUTO_THREAD. Encrypted media, auth recovery, cron E2EE, Synapse compat. CJK input, E2EE, reconnect              | ✅ E2E encryption, reactions, read receipts, rich formatting, room management, Synapse compat, CJK | ✅ Channel module                                  |
| **Email (IMAP/SMTP)**       | ⬜                   | ✅ Via Himalaya                                                                                                                                                                                                              | ✅ Himalaya-backed, Gmail native ingest, Outlook                                                   | ✅ Channel module                                  |
| **SMS**                     | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ⬜                                                                                                 | ⬜                                                 |
| **Mattermost**              | ⬜                   | ✅ File attachments (DOCUMENT type), native multi-image                                                                                                                                                                      | ✅ File attachments, multi-image                                                                   | ✅ Channel module                                  |
| **Home Assistant**          | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ⬜                                                                                                 | ⬜                                                 |
| **DingTalk**                | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ✅ Messaging                                                                                       | ✅ Channel module                                  |
| **Feishu / Lark**           | ⬜                   | ✅ Interactive card approval buttons, reconnect + ACL, native multi-image                                                                                                                                                    | ✅ Interactive card approval, reconnect, multi-image, ACL                                          | ✅ Channel module                                  |
| **WeCom**                   | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ✅ Messaging                                                                                       | ⬜                                                 |
| **iMessage (BlueBubbles)**  | ⬜                   | ✅ Gateway adapter (macOS)                                                                                                                                                                                                   | ✅ Via BlueBubbles on macOS                                                                        | ✅ Channel module                                  |
| **Weixin (WeChat)**         | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ⬜                                                                                                 | ⬜                                                 |
| **Yuanbao (Tencent)**       | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ✅ COS HMAC-SHA1 signing                                                                           | ⬜                                                 |
| **IRC**                     | ⬜                   | ✅ Plugin                                                                                                                                                                                                                    | ✅ IRC channel                                                                                     | ✅ Channel module                                  |
| **Google Chat**             | ⬜                   | ✅ Plugin                                                                                                                                                                                                                    | ⬜                                                                                                 | ✅ Channel module                                  |
| **Microsoft Teams**         | ⬜                   | ✅ Plugin: Graph-backed transcripts, operator CLI, meetings                                                                                                                                                                  | ✅ Graph-backed transcripts, operator CLI, meetings (plugin)                                       | ✅ Channel module                                  |
| **NTFY**                    | ⬜                   | ✅ Plugin                                                                                                                                                                                                                    | ⬜                                                                                                 | ⬜                                                 |
| **Simplex**                 | ⬜                   | ✅ Plugin                                                                                                                                                                                                                    | ⬜                                                                                                 | ⬜                                                 |
| **Line**                    | ⬜                   | ✅ Plugin                                                                                                                                                                                                                    | ⬜                                                                                                 | ⬜                                                 |
| **QQ Bot**                  | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ✅ QQ bot                                                                                          | ⬜                                                 |
| **Webhook**                 | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ⬜                                                                                                 | ⬜                                                 |
| **API Server / Open WebUI** | ⬜                   | ✅ Gateway adapter                                                                                                                                                                                                           | ⬜                                                                                                 | ⬜                                                 |
| **Web (browser-based)**     | ⬜                   | ⬜                                                                                                                                                                                                                           | ✅ Browser-based chat within desktop app, messages stay local                                      | ⬜                                                 |
| **CLI / Terminal**          | ✅ Primary interface | ✅`cli.py`                                                                                                                                                                                                                 | ✅ CLI mode                                                                                        | ✅ Basic CLI                                       |
| **Desktop app**             | ⬜                   | ✅ TUI (Ink/React)                                                                                                                                                                                                           | ✅ Tauri v2 desktop                                                                                | ❌ Deliberately rejected                           |
| **Platform count**          | 1 (CLI)              | 25                                                                                                                                                                                                                           | 17                                                                                                 | 15+                                                |

### 19B. Gateway Architecture

| Feature                                    | Pi | Hermes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | OpenHuman                                                                                                                                                                                          | Locus                |
| ------------------------------------------ | -- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| **Gateway core**                     | ⬜ | ✅`gateway/run.py` + `gateway/session.py`. `gateway/platforms/<name>/adapter.py` per platform. `builtin_hooks/` extension point. Runtime-metadata footer. Inactivity-based agent timeout (tracks tool activity). Infinite timeout + periodic notifications. Duplicate message prevention + dedup. Typing indicator paused during approval waits. Caption exact-line match. MEDIA tag extraction/stripping. Make-hygiene hard message limit configurable. `pre_gateway_dispatch` hook | ✅`channels/traits.rs`, `channels/context.rs`, `channels/proactive.rs`, `channels/routes.rs`, `channels/controllers/`, `channels/cli.rs`/`channels/commands.rs`, `channels/bus.rs` | ✅ Platform registry |
| **Backfill binaries**                | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅`slack-backfill`, `gmail-backfill-3d`                                                                                                                                                        | ⬜                   |
| **Cross-platform message mirroring** | ⬜ | ✅`mirror.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Channel-specific display config**  | ⬜ | ✅`display_config.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Device pairing**                   | ⬜ | ✅`pairing.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ✅`devices/` — multi-device, E2E encrypted XChaCha20-Poly1305 tunnel transport                                                                                                                  | ⬜                   |
| **Sticker / media cache**            | ⬜ | ✅`sticker_cache.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Graceful restart**                 | ⬜ | ✅`restart.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Shutdown forensics**               | ⬜ | ✅`shutdown_forensics.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Kanban watchers**                  | ⬜ | ✅`kanban_watchers.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Memory monitor**                   | ⬜ | ✅`memory_monitor.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Gateway hooks**                    | ⬜ | ✅`hooks.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Slash access control**             | ⬜ | ✅`slash_access.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | ⬜                                                                                                                                                                                                 | ⬜                   |
| **Platform scanners**                | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅ Per-platform Tauri scanners:`discord_scanner`, `slack_scanner`, `telegram_scanner`, `whatsapp_scanner`                                                                                  | ⬜                   |
| **Per-platform channel scanners**    | ⬜ | ⬜                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | ✅ Tauri shell scanners                                                                                                                                                                            | ⬜                   |

---

## 20. MCP (Model Context Protocol)

| Feature                 | Pi                      | Hermes                                                                                                                                                                                                                                              | OpenHuman                                                                                                                                                                                                       | Locus                                                      |
| ----------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| **MCP client**    | ⬜ (extensions instead) | ✅ Native MCP client.`hermes mcp serve/add/remove/list/test/configure/reload`. MCP OAuth 2.1 PKCE. OSV malware scanning. Circuit breaker. Dynamic tool discovery. 401 handling. Schema prefix stripping for Anthropic. Auto-discovery from config | ✅`mcp_client/`: `client.rs`, `client_helpers.rs`, `registry.rs`, `sanitize.rs`, `setup_agent.rs`, `stdio.rs`. Dynamic tool discovery. Tool result proxying. Integration tests                    | ✅`mcp_client.py`                                        |
| **MCP server**    | ⬜                      | ✅ (ACP serves as MCP server for IDE integration)                                                                                                                                                                                                   | ✅`mcp_server/`: `http.rs` (HTTP+SSE), `stdio.rs`, `protocol.rs` (JSON-RPC), `resources.rs`, `session.rs`, `tools/dispatch.rs`, `write_dispatch.rs`. SearXNG search exposed to external clients | ⬜                                                         |
| **MCP registry**  | ⬜                      | ⬜                                                                                                                                                                                                                                                  | ✅`mcp_registry/` — dynamic registration and removal, server metadata, capabilities, health status                                                                                                           | ⬜                                                         |
| **MCP audit**     | ⬜                      | ⬜                                                                                                                                                                                                                                                  | ✅`mcp_audit/` — audit trail, security/compliance, call provenance, result logging                                                                                                                           | ⬜                                                         |
| **MCP test stub** | ⬜                      | ⬜                                                                                                                                                                                                                                                  | ✅`src/bin/test_mcp_stub.rs` — standalone test server binary                                                                                                                                                 | ⬜                                                         |
| **Obsidian MCP**  | ⬜                      | ⬜                                                                                                                                                                                                                                                  | ⬜                                                                                                                                                                                                              | 📐 vault_read/write/search/tag/stats (localhost, .md only) |

---

## 21. Wallet & Web3 (OpenHuman-specific)

| Feature          | Pi | Hermes | OpenHuman                                                                                                                                                                                                                                                                                                                                                                          | Locus |
| ---------------- | -- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Wallet** | ⬜ | ⬜     | ✅ Multi-chain signing. BIP-39 mnemonic → seed.**Bitcoin**: P2WPKH PSBT build/sign/broadcast, HASH160, secp256k1. **Ethereum/EVM**: ethers-core + ethers-signers. **Solana**: ed25519, ATA derivation, base58, curve25519-dalek. **Tron**: base58check, secp256k1. ABI encoding/decoding. Chain configs. RPC endpoint management. Wallet execution engine | ⬜    |
| **Web3**   | ⬜ | ⬜     | ✅`web3/`: DApp integration, token swaps, cross-chain bridge, Web3 client, store                                                                                                                                                                                                                                                                                                 | ⬜    |
| **x402**   | ⬜ | ⬜     | ✅ HTTP 402 Payment Required protocol, blockchain-based micropayments for API access                                                                                                                                                                                                                                                                                               | ⬜    |

---

## 22. Team, Billing & Monitoring

| Feature                   | Pi | Hermes | OpenHuman                                                                               | Locus |
| ------------------------- | -- | ------ | --------------------------------------------------------------------------------------- | ----- |
| **Team features**   | ⬜ | ⬜     | ✅`team/` — multi-user workspace, team invitations (`/invites`), role-based access | ⬜    |
| **People**          | ⬜ | ⬜     | ✅`people/` — contact/people management, entity tracking                             | ⬜    |
| **Billing**         | ⬜ | ⬜     | ✅`billing/` — subscription management, plan tiers, usage tracking                   | ⬜    |
| **Cost tracking**   | ⬜ | ⬜     | ✅`cost/` — per-call token cost, model pricing awareness, cost aggregation           | ⬜    |
| **Referral system** | ⬜ | ⬜     | ✅`referral` module                                                                   | ⬜    |

---

## 23. Health & Observability

| Feature                              | Pi                                                                                                                                                                             | Hermes                                                                                                                                                                                                                   | OpenHuman                                                                                                                                                                        | Locus |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **Observability**              | ✅`telemetry.ts` (anonymous version ping)                                                                                                                                    | ✅ Langfuse plugin with pre/post hooks. Insights analytics, per-skill telemetry, account usage, rate limits                                                                                                              | ✅ Prometheus metrics, Sentry error tracking (with`before_send` filter), OpenTelemetry tracing and metrics (OTLP), structured logging via `tracing` + `tracing-subscriber` | ⬜    |
| **Health endpoints**           | ⬜                                                                                                                                                                             | ✅`gateway/status.py`                                                                                                                                                                                                  | ✅`health/` — system health, `heartbeat/` — liveness checks, `monitor/` — system monitoring                                                                             | ⬜    |
| **Achievements**               | ⬜                                                                                                                                                                             | ✅`hermes-achievements` — gamified tracking, scans local session history. Tiers: Copper → Silver → Gold → Diamond → Olympian. 60+ achievements. Share cards (1200×630 PNG). Dashboard integration. API endpoints | ⬜                                                                                                                                                                               | ⬜    |
| **Telemetry**                  | ✅`enableInstallTelemetry` (default: true). `PI_SKIP_VERSION_CHECK=1`, `PI_OFFLINE=1` to disable. `enableAnalytics` (default: false, opt-in via `PI_EXPERIMENTAL=1`) | ⬜                                                                                                                                                                                                                       | ✅`observability` config                                                                                                                                                       | ⬜    |
| **Experimental features flag** | ✅`experimental.ts`                                                                                                                                                          | ⬜                                                                                                                                                                                                                       | ⬜                                                                                                                                                                               | ⬜    |

---

## 24. i18n & Localization

| Feature                | Pi | Hermes | OpenHuman                                                                                                    | Locus |
| ---------------------- | -- | ------ | ------------------------------------------------------------------------------------------------------------ | ----- |
| **Translations** | ⬜ | ⬜     | ✅ 14+ languages (ar, bn, de, es, fr, hi, id, it, ko, pl, pt, ru, zh-CN).`useT()` hook, CI enforces parity | ⬜    |

---

## 25. Connectivity & Devices

| Feature                           | Pi | Hermes | OpenHuman                                                                                                        | Locus |
| --------------------------------- | -- | ------ | ---------------------------------------------------------------------------------------------------------------- | ----- |
| **Multi-device management** | ⬜ | ⬜     | ✅`devices/` — pairing, tunnel transport (E2E encrypted XChaCha20-Poly1305)                                   | ⬜    |
| **iOS client**              | ⬜ | ⬜     | ✅ (experimental) React screens, PTT plugin,`LanHttpTransport`/`TunnelTransport`/`CloudHttpTransport`      | ⬜    |
| **Deep links**              | ⬜ | ⬜     | ✅`openhuman://` protocol. macOS requires built `.app`; Windows via `tauri-plugin-deep-link::register_all` | ⬜    |
| **Connectivity**            | ⬜ | ⬜     | ✅`connectivity/` — network state monitoring, connection fallback                                             | ⬜    |

---

## 26. SDK (Pi-specific)

| Feature       | Pi                                                                                                                                                                                                                                                                                                                                                                                                                                                | Hermes | OpenHuman | Locus |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | --------- | ----- |
| **SDK** | ✅`createAgentSession(options)` — main factory. `SessionManager.inMemory()`/`.file()`. `AuthStorage.create()`. `ModelRegistry.create(authStorage)`. `ResourceLoader`/`DefaultResourceLoader`. `session.prompt()`, `session.subscribe()`, `session.cancel()`, `session.setModel()`, `session.setThinking()`, `session.fork()`, `session.compact()`. 13 examples (`01-minimal.ts` through `13-session-runtime.ts`) | ⬜     | ⬜        | ⬜    |

---

## 27. Export & Artifacts

| Feature                           | Pi                    | Hermes                           | OpenHuman                                                                  | Locus                                                |
| --------------------------------- | --------------------- | -------------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------- |
| **HTML session export**     | ✅`export-html/`    | ⬜                               | ⬜                                                                         | ⬜                                                   |
| **JSON session export**     | ✅`--export json`   | ⬜                               | ⬜                                                                         | ⬜                                                   |
| **Markdown session export** | ✅`--export md`     | ⬜                               | ⬜                                                                         | ⬜                                                   |
| **Trajectory recording**    | ⬜                    | ✅`trajectory.py` (1321 lines) | ⬜                                                                         | ⬜                                                   |
| **ANSI → HTML conversion** | ✅`ansi-to-html.ts` | ⬜                               | ⬜                                                                         | ⬜                                                   |
| **Artifacts**               | ⬜                    | ⬜                               | ✅`artifacts/` — `store.rs`, `ops.rs`, `schemas.rs`, `tools.rs` | ⬜                                                   |
| **Daily AI Chat Archiver**  | ⬜                    | ⬜                               | ⬜                                                                         | 📐 Nightly 23:45 Telegram → vault .md → git commit |

---

## 28. Integrations

| Feature                      | Pi | Hermes                | OpenHuman                                      | Locus                                              |
| ---------------------------- | -- | --------------------- | ---------------------------------------------- | -------------------------------------------------- |
| **Composio**           | ⬜ | ⬜                    | ✅`integrations` module (118+ connectors)    | ✅`composio.py` (📐 replacing with manual OAuth) |
| **Polymarket**         | ⬜ | ⬜                    | ⬜                                             | ✅`polymarket.py`                                |
| **Webhooks**           | ⬜ | ✅ Webhook tool       | ✅`webhooks` module                          | ✅`webhooks.py`                                  |
| **Google Calendar**    | ⬜ | ⬜                    | ✅ (via Composio)                              | 📐 Manual OAuth integration                        |
| **Gmail**              | ⬜ | ⬜                    | ✅ (via Composio)                              | 📐 Manual OAuth integration                        |
| **Calendly**           | ⬜ | ⬜                    | ⬜                                             | 📐 Via setup wizard                                |
| **Web3 / wallet**      | ⬜ | ⬜                    | ✅`wallet`, `web3`, `x402` modules       | ⬜                                                 |
| **Meet / video calls** | ⬜ | ✅ Google Meet plugin | ✅`meet`, `meet_agent`, `agent_meetings` | ⬜                                                 |
| **Team collaboration** | ⬜ | ⬜                    | ✅`team`, `people` modules                 | ⬜                                                 |

---

## 29. Install & Distribution

| Feature           | Pi                                         | Hermes                                 | OpenHuman                                                                            | Locus       |
| ----------------- | ------------------------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------ | ----------- |
| **macOS**   | ✅ npm install                             | ✅ (pip / source)                      | ✅ Homebrew tap (`brew install openhuman`), script install                         | ⬜          |
| **Linux**   | ✅ npm install                             | ✅ (pip / source / Nix flake / Docker) | ✅ Signed apt repo, AUR (`openhuman-bin`), `.deb`, `.AppImage`, script install | ⬜          |
| **Windows** | ✅ npm install +`windows-self-update.ts` | ✅ (pip / source)                      | ✅ Signed`.msi` installer, `irm                                                    | iex` script |
| **Docker**  | ⬜                                         | ✅ Docker builds                       | ✅ Docker builds (Fly.io, DigitalOcean, Docker)                                      | ⬜          |
| **Nix**     | ⬜                                         | ✅ Nix flake + NixOS module            | ⬜                                                                                   | ⬜          |
| **Tauri**   | ⬜                                         | ⬜                                     | ✅ Tauri v2 with vendored CEF                                                        | ⬜          |
| **Termux**  | ✅ Termux for Android                      | ⬜                                     | ⬜                                                                                   | ⬜          |

---

## 30. CI/CD & Testing

| Feature                           | Pi                                                                                                                                        | Hermes                                                    | OpenHuman                                    | Locus |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------- | ----- |
| **Unit tests**              | ✅ Vitest for all packages                                                                                                                | ✅ pytest                                                 | ✅ cargo test                                | ⬜    |
| **CI pipeline**             | ✅ GitHub Actions:`ci.yml`, `build-binaries.yml`, `npm-audit.yml`, `pr-gate.yml`, `issue-gate.yml`, `approve-contributor.yml` | ✅ Full CI (lint, test, typecheck, docker, nix, security) | ✅ Full CI (build, test, deploy, e2e, smoke) | ⬜    |
| **Linting**                 | ✅ ESLint                                                                                                                                 | ✅ Ruff/flake8                                            | ✅ clippy                                    | ⬜    |
| **Type checking**           | ✅ TypeScript composite project references                                                                                                | ✅ mypy                                                   | ✅ Rust compiler                             | ⬜    |
| **Docker builds**           | ⬜                                                                                                                                        | ✅ Docker builds                                          | ✅ Docker builds                             | ⬜    |
| **Nix**                     | ⬜                                                                                                                                        | ✅ Nix flake                                              | ⬜                                           | ⬜    |
| **Batch trajectory runner** | ⬜                                                                                                                                        | ✅`trajectory.py` (1321 lines)                          | ⬜                                           | ⬜    |
| **E2E tests**               | ✅ LLM-dependent suites                                                                                                                   | ⬜                                                        | ✅ E2E + smoke tests                         | ⬜    |

---

## 31. Utilities

| Feature                              | Pi                                                                                    | Hermes                                                                          | OpenHuman                                                       | Locus                              |
| ------------------------------------ | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------- |
| **Clipboard**                  | ✅`clipboard.ts` + native + image (`clipboard-native.ts`, `clipboard-image.ts`) | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **Git integration**            | ✅`git.ts`                                                                          | ✅ (built-in tools)                                                             | ⬜                                                              | ✅`git_ops.py`                   |
| **Image handling**             | ✅ Resize, convert, EXIF orientation, Photon WASM                                     | ⬜                                                                              | ✅`image` module                                              | ⬜                                 |
| **Syntax highlighting**        | ✅`syntax-highlight.ts` + highlight.js                                              | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **MIME detection**             | ✅`mime.ts`                                                                         | ✅`binary_extensions.py` — binary detection                                  | ⬜                                                              | ⬜                                 |
| **Open browser**               | ✅`open-browser.ts`                                                                 | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **ANSI escape handling**       | ✅`ansi.ts`                                                                         | ✅`ansible_strip.py` — ANSI stripping                                        | ⬜                                                              | ⬜                                 |
| **Shell integration**          | ✅`shell.ts`                                                                        | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **Frontmatter parser**         | ✅`frontmatter.ts`                                                                  | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **File system watcher**        | ✅`fs-watch.ts`                                                                     | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **Unicode sanitization**       | ✅`sanitize-unicode.ts`                                                             | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **JSON safe parsing**          | ✅`json-parse.ts`                                                                   | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **Schema validation**          | ✅ TypeBox helpers                                                                    | ⬜                                                                              | ⬜                                                              | ⬜                                 |
| **Colors / output formatting** | ⬜                                                                                    | ⬜                                                                              | ⬜                                                              | ✅`colors.py`, `cli_output.py` |
| **Slash commands handler**     | ⬜                                                                                    | ⬜                                                                              | ⬜                                                              | ✅`slash_commands.py`            |
| **SSH deployment**             | ⬜                                                                                    | ⬜                                                                              | ⬜                                                              | ✅`deployment` module            |
| **Fuzzy matching**             | ⬜                                                                                    | ✅`fuzzy_match.py`                                                            | ⬜                                                              | ⬜                                 |
| **URL safety checks**          | ⬜                                                                                    | ✅`url_safety.py`                                                             | ⬜                                                              | ⬜                                 |
| **Website policy**             | ⬜                                                                                    | ✅`website_policy.py`                                                         | ⬜                                                              | ⬜                                 |
| **Lazy dependency imports**    | ⬜                                                                                    | ✅`lazy_deps.py`                                                              | ⬜                                                              | ⬜                                 |
| **FAL common**                 | ⬜                                                                                    | ✅`fal_common.py` — FAL shared                                               | ⬜                                                              | ⬜                                 |
| **xAI HTTP helpers**           | ⬜                                                                                    | ✅`xai_http.py`                                                               | ⬜                                                              | ⬜                                 |
| **Auth storage**               | ✅`auth-storage.ts` + `auth-guidance.ts`                                          | ✅`authz_mixin.py`                                                            | ✅`keyring`                                                   | ⬜                                 |
| **Error classifier**           | ⬜                                                                                    | ✅`error_classifier.py`                                                       | ⬜                                                              | ⬜                                 |
| **Auxiliary LLM client**       | ⬜                                                                                    | ✅`auxiliary_client.py` — resolves named custom providers and `main` alias | ✅`model_council`                                             | ⬜                                 |
| **Runtime JS/Python**          | ⬜                                                                                    | ⬜                                                                              | ✅`runtime_node`, `runtime_python`                          | ⬜                                 |
| **About app**                  | ⬜                                                                                    | ⬜                                                                              | ✅`about_app` module                                          | ⬜                                 |
| **Socket/WebSocket**           | ⬜                                                                                    | ✅`gateway/stream_consumer.py`                                                | ✅`socket` module                                             | ⬜                                 |
| **Redirect links**             | ⬜                                                                                    | ⬜                                                                              | ✅`redirect_links` module                                     | ⬜                                 |
| **Provider surfaces**          | ⬜                                                                                    | ⬜                                                                              | ✅`provider_surfaces` module                                  | ⬜                                 |
| **Service orchestration**      | ⬜                                                                                    | ⬜                                                                              | ✅`service` module — background service, systemd integration | ⬜                                 |
| **Workspace management**       | ⬜                                                                                    | ⬜                                                                              | ✅`workspace` module                                          | ⬜                                 |
| **Agent tool policy**          | ⬜                                                                                    | ⬜                                                                              | ✅`agent_tool_policy` module                                  | ⬜                                 |
| **Test support**               | ⬜                                                                                    | ⬜                                                                              | ✅`test_support` module                                       | ⬜                                 |
| **Notifications**              | ⬜                                                                                    | ⬜                                                                              | ✅`notifications` module                                      | ✅`heartbeat/notification.py`    |
| **Autocomplete**               | ⬜                                                                                    | ⬜                                                                              | ✅`autocomplete/` — command and query autocomplete           | ⬜                                 |
| **HTTP host**                  | ⬜                                                                                    | ⬜                                                                              | ✅`http_host/` — embedded HTTP server for RPC                | ⬜                                 |

---

## 32. Life OS — Behavioral Metrics (Locus-only domain)

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

## 33. Proactive Reasoning / Brain Engine (Locus-only domain)

| Feature                                       | Pi | Hermes | OpenHuman | Locus                                                           |
| --------------------------------------------- | -- | ------ | --------- | --------------------------------------------------------------- |
| **Inner Loop (Proactive Thinker)**      | ⬜ | ⬜     | ⬜        | 📐 Every 90min, unprompted reasoning, Reward Model gate         |
| **State Engine + Inferred Cause Chain** | ⬜ | ⬜     | ⬜        | 📐 Psychological + operational state + causal explanation       |
| **Multi-Horizon Pattern Engine**        | ⬜ | ⬜     | ⬜        | 📐 H1(6h)–H5(all-time), confidence-based promotion             |
| **Context Forge**                       | ⬜ | ⬜     | ⬜        | 📐 800-token 6-layer assembler                                  |
| **Query Router / Intent Classifier**    | ⬜ | ⬜     | ⬜        | 📐 8 intent types, source routing matrix                        |
| **Inferred Cause Chain Engine**         | ⬜ | ⬜     | ⬜        | 📐 Cross-reference state+patterns+history → causal explanation |
| **Personality + "Wants" Engine**        | ⬜ | ⬜     | ⬜        | 📐 SOUL.md rules + WantNodes in Neo4j                           |
| **Weekly Full Vault Synthesis**         | ⬜ | ⬜     | ⬜        | 📐 Sunday 02:00, personality drift + faction narrative          |

---

## 34. Vault & Knowledge Intelligence (Locus-only domain)

| Feature                                     | Pi | Hermes | OpenHuman | Locus                                                                          |
| ------------------------------------------- | -- | ------ | --------- | ------------------------------------------------------------------------------ |
| **PageIndex (vectorless tree index)** | ⬜ | ⬜     | ⬜        | 📐 Markdown headers→tree structure, LLM reasoning-based retrieval, no vectors |
| **Nightly Vault Ingestion Pipeline**  | ⬜ | ⬜     | ⬜        | 📐 Multi-account Playwright scraping (ChatGPT×3, Claude, Gemini, Perplexity)  |
| **LOCUS_SHORTHAND**                   | ⬜ | ⬜     | ⬜        | 📐 ~4× token compression, dedicated encode/decode                             |
| **Obsidian as Primary Dashboard**     | ⬜ | ⬜     | ⬜        | 📐 8 panels via Dataview/Charts, replaces PWA                                  |
| **3-Level Tag Hierarchy**             | ⬜ | ⬜     | ⬜        | 📐 faction/domain/specific, PG tag registry                                    |
| **Rough Note Parser / Idea Tracker**  | ⬜ | ⬜     | ⬜        | 📐 /idea → expand → promote/research/archive                                 |
| **Link Dump / Resource Logger**       | ⬜ | ⬜     | ⬜        | 📐 /link → captures table → vault note                                       |
| **Excalidraw MCP Skill**              | ⬜ | ⬜     | ⬜        | 📐 Autonomous diagram generation via MCP                                       |

---

## 35. Interface Philosophy & Infrastructure Decisions (Locus-only domain)

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
| **AI model V4 Flash only**            | ⬜ | ⬜     | ⬜        | ✅ ~$0.012/day, ~$4/year — architectural decision                  |
| **Zero-cost 1st-class constraint**    | ⬜ | ⬜     | ⬜        | ✅ $5 credit → ~416 days                                           |
| **Minimum AI in harness**             | ⬜ | ⬜     | ⬜        | ✅ LLM only for reasoning/generation, deterministic logic elsewhere |

---

## 36. Obsidian & Note-Taking

| Feature                        | Pi | Hermes                                                                                                                             | OpenHuman                                                                                   | Locus                            |
| ------------------------------ | -- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | -------------------------------- |
| **Obsidian integration** | ⬜ | ✅ Via`note-taking` skill: read, search, create, edit markdown notes in local vault. Interacts with frontmatter, wikilinks, tags | ✅ Memory Tree Markdown vault (`wiki/`) is Obsidian-compatible with wikilinks/frontmatter | 📐 Obsidian as Primary Dashboard |
| **Excalidraw**           | ⬜ | ✅ Via`diagramming/excalidraw` skill: hand-drawn style JSON diagrams, embed/render in notes                                      | ⬜                                                                                          | 📐 Excalidraw MCP Skill          |

---

## 37. Key Paths

### Pi Key Paths

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

### Hermes Key Paths

| Path                           | Purpose      |
| ------------------------------ | ------------ |
| `~/.hermes/config.yaml`      | Config       |
| `~/.hermes/.env`             | Environment  |
| `~/.hermes/state.db`         | SQLite state |
| `~/.hermes/sessions/`        | Sessions     |
| `~/.hermes/logs/`            | Logs         |
| `~/.hermes/skills/`          | Skills       |
| `~/.hermes/plugins/`         | Plugins      |
| `~/.hermes/memories/`        | Memories     |
| `~/.hermes/auth.json`        | Auth         |
| `~/.hermes/state-snapshots/` | Snapshots    |
| `~/.hermes/profiles/<name>/` | Profile dirs |
| `~/.hermes/hermes-agent/`    | Source       |

### OpenHuman Key Paths

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

---

## Summary Counts

| Category                      | Pi | Hermes | OpenHuman | Locus (✅+🔧) | Locus (📐 designed) |
| ----------------------------- | -- | ------ | --------- | ------------- | ------------------- |
| Agent Core / Runtime          | 9  | 16     | 8         | 4             | 1                   |
| LLM Providers                 | 15 | 12     | 5         | 2             | 0                   |
| Tools / Tool Execution        | 11 | 11     | 13        | 10            | 0                   |
| Memory & Persistence          | 4  | 5      | 10        | 5             | 5                   |
| Sessions                      | 8  | 3      | 2         | 1             | 0                   |
| Context Management            | 2  | 4      | 3         | 1             | 2                   |
| TUI / Terminal                | 12 | 12     | 5         | 1             | 0                   |
| CLI                           | 6  | 5      | 4         | 5             | 0                   |
| Extensions / Plugins / Skills | 5  | 6      | 3         | 1             | 0                   |
| Learning & Self-Improvement   | 0  | 3      | 5         | 2             | 3                   |
| Subagents / Orchestration     | 3  | 3      | 3         | 1             | 1                   |
| Scheduling & Cron             | 0  | 2      | 3         | 2             | 3                   |
| Security & Sandboxing         | 2  | 4      | 8         | 3             | 0                   |
| Voice & Meetings              | 0  | 2      | 2         | 3             | 1                   |
| Web Search                    | 0  | 1      | 1         | 5             | 0                   |
| Browser Automation            | 0  | 1      | 2         | 3             | 0                   |
| Channels / Gateway            | 2  | 15     | 5         | 16            | 0                   |
| MCP                           | 0  | 0      | 4         | 1             | 1                   |
| Export & Artifacts            | 4  | 1      | 0         | 0             | 1                   |
| Computer Use                  | 0  | 0      | 2         | 4             | 0                   |
| Integrations                  | 0  | 1      | 6         | 2             | 3                   |
| Health & Observability        | 1  | 3      | 4         | 0             | 0                   |
| Wallet / Web3                 | 0  | 0      | 3         | 0             | 0                   |
| Team / Billing                | 0  | 0      | 4         | 0             | 0                   |
| i18n                          | 0  | 0      | 1         | 0             | 0                   |
| Connectivity / Devices        | 0  | 0      | 3         | 0             | 0                   |
| SDK                           | 1  | 0      | 0         | 0             | 0                   |
| Life OS Metrics               | 0  | 0      | 0         | 0             | 16                  |
| Brain Engine                  | 0  | 0      | 0         | 0             | 8                   |
| Vault Intelligence            | 0  | 0      | 0         | 0             | 8                   |
| Interface Philosophy          | 0  | 0      | 0         | 4             | 7                   |

**Totals:**

- **Pi**: ~85 implemented features
- **Hermes**: ~110 implemented features
- **OpenHuman**: ~99 implemented features
- **Locus (code)**: ~73 implemented features
- **Locus (design)**: ~57 additional designed features → **130 total when built**

---

## Locus Features — Complete Clock-Model Decomposition (v2 FRESH BUILD)

> **Generated:** 2026-06-16 | **Scope:** All 136 features decomposed to atomic gear depth
> **Methodology:** Clock Model — every feature broken into single-responsibility gears with task trees, data contracts, dependencies, and failure modes
> **Gear types:** [D] = Deterministic (pure logic), [AI] = AI-Based (model call primary), [H] = Hybrid (deterministic scaffolding wraps model call)
> **Target:** Single-user PCOS on Oracle Cloud ARM64 VM, AI model V4 Flash only, dual-store (PostgreSQL 16, Neo4j 5.x)

---

## Key Architecture Decisions (v2)

| Decision                | v1 (old)                       | v2 (this)                                              | Why                                                                                                |
| ----------------------- | ------------------------------ | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Retrieval               | LightRAG (black-box hybrid)    | PageIndex (vectorless tree) + Neo4j (graph)            | Query Router + Context Forge already do what LightRAG does. No middle layer.                       |
| Vault sync              | Syncthing (real-time, fragile) | Git (Obsidian Git plugin + GitHub private repo)        | Version history free, no extra service, no port issues. Directory partitioning prevents conflicts. |
| Backend → vault writes | Obsidian Local REST API        | Direct file write to /vault/ on VM + git commit + push | Works even when Obsidian desktop is closed. Git handles sync.                                      |
| Google OAuth            | Composio (managed)             | Keeping it                                             | As is.                                                                                             |
| Vector DB               | Qdrant container               | REMOVED                                                | PageIndex is vectorless. Tree search + graph traversals cover all retrieval needs.                 |
| Secondary vector DB     | ChromaDB                       | REMOVED                                                | Redundant.                                                                                         |
| Cache/state             | Redis (required)               | Redis (optional)                                       | At single-user scale, PG + in-memory dict covers all Redis use cases.                              |
| LLM                     | Multi-provider cascade         | AI model V4 Flash only                                 | One model. One behavior. ~$0.012/day.                                                              |
| Graph DB                | Neo4j 5.x                      | Neo4j 5.x (kept)                                       | Hebbian weighting needs native graph traversals. Apache AGE noted as future consolidation option.  |

---

## "Huh?" Resolutions

These features had ambiguous descriptions in the original annotated list. Research into original project documents resolved them.

### #7: Behavioral Event Stream — Elaborated

**Original annotation:** "Huh? Elaborate..."

**Resolution:** This is the **foundation of the entire analytical stack.** Every FastAPI endpoint must emit events to `behavioral_events` table via PG LISTEN/NOTIFY. Without it wired into every endpoint, nothing downstream (State Engine, Pattern Engine, Faction Stats, Context Forge, Reward Model) has data. The decomposition stands but emphasis: **#7 is critical-path infrastructure, not optional logging.**

### #49: Thinking Pattern Capture — Researched

**Original annotation:** "Huh?"

**Resolution (from Master Doc §10, §9, LOCUS_BRAIN_MODULE_PROMPT):** AI model scans the AI chat vault (03-AI-Chats) for recurring problem-solving approaches — how the user debugs, decomposes problems, what mental models they favor. Creates ConceptNodes in Neo4j with type='thinking_pattern'. Feeds User Identity. Requires 60+ days of chat data. Categories: decomposition, debugging, learning, communication, avoidance.

### #60: State Engine — "Nope" Rejection Explained

**Original annotation:** "Nope"

**Resolution (from architecture_decisions.md v2):** The v1 design was overly complex — Redis pub/sub, constant NOTIFY listening, AI cause chain on every event. v2 simplifies: single PG row `current_state`, updated on check-in and significant events ONLY, NOT on every behavioral event. Cause chain only when explicitly queried with 30-min cache. The "Nope" rejects the v1 design, not the feature itself. Decomposed as v2 revision.

### #68: Inferred Cause Chain Engine — Researched

**Original annotation:** "Huh?"

**Resolution (from Master Doc §9):** The key differentiating feature. Produces plain-language causal explanations citing specific data — cross-references CURRENT_STATE + historical patterns + user_identity + calendar. Not just a prompt; a dedicated engine with confidence scoring, data source tracking, and historical storage.

### #71: Database Diagnostic Script — Researched

**Original annotation:** "Huh?"

**Resolution (from Master Doc One-Week Plan Day 1, Consolidated Sessions, Jules Prompt):** A comprehensive pre-flight health check that MUST be run before every major dev session. Checks: PG row counts, Neo4j node/edge counts, vault file count, Redis key count. The Jules prompt says: "Run scripts/diagnose_databases.py first. Do not proceed until health report is reviewed."

---

## Pen Remark Overrides

These are cases where the Pen Remarks column in the annotated features doc changed the decomposition direction from what the Description/Notes suggested.

| #   | Pen Remark                                                                                                         | Impact on Decomposition                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| 1   | "Design like an OS: each faction is a process fighting for CPU time"                                               | Factions designed as kernel processes with priority scheduling, not just tags                       |
| 12  | "Use slash command or intelligent detection through SOUL.md. Semi-deterministic"                                   | Emergency injection split: deterministic protocol for known emergencies, AI-based for detected ones |
| 13  | "Logic? Determined or Autonomous?"                                                                                 | Confirmed deterministic via cron jobs; Phase 2 AI enhancement optional                              |
| 14  | "Define logic → Deterministic based on data points. Not LLM based at all!"                                        | Removed any LLM from rebalance; pure SQL aggregation                                                |
| 16  | "Autonomously + invokeable sub-agents. Need a doc with problem solving philosophy"                                 | Parallel optimizer is [H] not [D]; requires SOUL.md problem-solving doc                             |
| 24  | "Logic? Deterministic but using AI → Outsource to 'agy'"                                                          | Self-maintenance outsourced to external tool; Locus only creates the trigger task                   |
| 27  | "Define logic → Autonomous yet deterministic. Scope note: ALL ChatGPT accounts (×3), Claude, Gemini, Perplexity" | Nightly ingestion expanded to multi-account scraping, not single                                    |
| 52  | "Self callable Skills + MCPs. Pre-load some skills and MCPs"                                                       | Skills registry designed for self-invocation, not just routing                                      |
| 64  | "Define logic. Deterministic — concrete rules + verification from user, not LLM-decreed"                          | Hebbian weights follow fixed formulas.                       |
| 84  | "Deterministic. Invokeable by /commands + Skill. Use best strategy. Either 5 sub agents or 2 agent debate?"        | Council uses 3 agents (Architect/Reviewer/Pragmatist)                                               |
| 85  | "Already addressed. Make this integration possible through Obsidian or Telegram"                                   | Social integrations implement through existing Telegram/Obsidian channels                           |
| 86  | "Already done / accounted for"                                                                                     | Pi Sub-Agents marked as already covered; minimal decomposition                                      |
| 128 | "Research first. Define weight dimensions + algorithm"                                                             | Dijkstra scheduling starts with research phase before implementation                                |

---

## Feature Consolidations

Features merged from multiple IDs into a single decomposition.

| Consolidated Into                | Original Features                                                                                  | Rationale                                       |
| -------------------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| #27 (Nightly Ingestion)          | #42 (Vault Processing Pipeline) + #46 (Daily AI Chat Archiver) + #80 (Daily AI Chat Archiver Cron) | Same pipeline — crawl, scrape, process, embed. |
| #32 (Self-Evolving Architecture) | #77 (Self-Evolving System Philosophy) + #106 (Self-Improving Architecture)                         | Same mechanism — reward-driven evolution.      |
| #36 (Obsidian Dashboard)         | #54 (Progress Visualization Dashboard)                                                             | Single dashboard, not separate.                 |
| #39 (Structured Check-ins)       | #53 (Push Notification Reminders)                                                                  | Notifications ARE the check-in channel.         |
| #41 (Visual Avatar)              | #78 (Holistic Avatar) + #79 (Avatar Animated States)                                               | Single visual representation.                   |
| #64 (Hebbian Memory)             | #99 (Spaced Repetition) + #107 (Project-Specific Memory Decay)                                     | Same weight math, different decay triggers.     |
| #78 (Dynamic MCP Integration)    | #114 (Inter-Harness Communication) + #115 (GitMCP Repo Parsing) + #116 (Graphify Coding Assistant) | All MCP dynamic capabilities under one feature. |

---

## Deleted / Ignored / Scrapped Features

| #  | Feature                                   | Disposition    | Reason                                                                             |
| -- | ----------------------------------------- | -------------- | ---------------------------------------------------------------------------------- |
| 33 | Multi-Dimensional Graph Nodes             | 🔴 Scrapped    | Unnecessary — Neo4j schema already supports multiple edge types                   |
| 55 | Personality + "Wants" Engine              | ⏭️ Ignored   | Needs brainstorming; SOUL.md already covers identity                               |
| 62 | User Identity Profile                     | ➡️ Duplicate | Addressed within#29 Personality Profile                                            |
| 65 | LOCUS_SHORTHAND Compression               | ⏭️ Ignored   | Was an experiment; outside short-term scope                                        |
| 66 | Multi-Provider LLM Cascade                | 🗑️ Delete    | AI model only. Deprecated by architecture decision.                                |
| 72 | Vilix Evaluation                          | ⏭️ Ignored   | Decision criteria deferred                                                         |
| 73 | Locus "Wants" + Autonomous Goal Formation | ⏭️ Ignored   | Phase 2+; too speculative                                                          |
| 74 | Locus Builds and Operates the Life OS     | ⏭️ Ignored   | Meta-feature; emerges from other features                                          |
| 75 | Obsidian-Centric Interactions             | 🗑️ Delete    | Already accounted for in#36, #39, #43                                              |
| 80 | Local-First Obsidian Storage              | 🗑️ Delete    | DB is not volatile cache; vault is not single source of truth for analytical state |

---

## Feature Decompositions

---

### #1: Four Factions Framework [D] 📐

**Purpose:** Four factions as OS processes fighting for CPU time (attention/hours). Kernel = master scheduler.

**Trigger / Invocation:** Seed on first start; referenced by every task/project/scheduling operation.

**Task Tree:**

- 1.1 [D] Schema — `factions` table: id, name, color_hex, icon, weekly_target_hours, priority_rank
- 1.2 [D] Seed — 4 rows: Health/Stability (#22C55E), Leverage/Money (#3B82F6), Craft/Skills (#F97316), Expression/Exploration (#A855F7)
- 1.3 [D] FK constraint — `projects.faction_id` → `factions.id`, `tasks.faction_id` → `factions.id`

**Data Contracts:**

- `factions`: `{id UUID PK, name TEXT UNIQUE, color_hex TEXT, icon TEXT, weekly_target_hours INT, priority_rank INT, created_at TIMESTAMPTZ}`
- Every task/project requires valid faction_id

**Dependencies:** None (foundational)

**Failure Modes & Fallbacks:** Seed failure → system can't start; all other features depend on this.

---

### #2: Daily Capacity Score (DCS) [D] 📐

**Purpose:** DCS = ((Energy + Mood + Sleep) / 3) × (1 − Stress/20). Morning metric drives operating mode.

**Trigger / Invocation:** Telegram /checkin → inline keyboard → E, M, S, ST (0-10 each), T (top task). GENERATED ALWAYS AS column.

**Task Tree:**

- 2.1 [D] `daily_checkins` table with GENERATED ALWAYS AS dcs column
- 2.2 [D] Telegram InlineKeyboard — tap E (0-10), M (0-10), S (0-10), ST (0-10), T (text)
- 2.3 [D] Mode derivation — CASE statement: ≥ 8 → PEAK, ≥ 6.5 → DEEP_WORK, ≥ 4.5 → NORMAL, ≥ 2.5 → RECOVERY, < 2.5 → SURVIVAL

**Data Contracts:**

- DCS formula columns computed; mode derived via SQL view
- Input via Telegram inline keyboard only

**Dependencies:** #1 (Factions) for task associations

**Failure Modes & Fallbacks:** User skips check-in → no DCS for that day; scheduler uses yesterday's DCS

---

### #3: Five Operating Modes [D] 📐

**Purpose:** DCS range → mode → schedule weightage + expected output of the day.

**Trigger / Invocation:** Derived automatically from DCS on check-in. Propagated to Scheduler as task filter.

**Task Tree:**

- 3.1 [D] Python enum OperatingMode: SURVIVAL, RECOVERY, NORMAL, DEEP_WORK, PEAK
- 3.2 [D] DCS-range mapping dict: (0-2.5→SURVIVAL, 2.5-4.5→RECOVERY, 4.5-6.5→NORMAL, 6.5-8→DEEP_WORK, 8-10→PEAK)
- 3.3 [D] Scheduler filter — only recommend tasks matching current mode difficulty
- 3.4 [D] Stored as TEXT on daily_checkins

**Data Contracts:** Python enum + PG TEXT column; 10 lines of Python

**Dependencies:** #2 (DCS)

**Failure Modes & Fallbacks:** Mode defaults to NORMAL if DCS unavailable

---

### #4: Task Weight Score (TWS) [D] 📐

**Purpose:** TWS = (Priority×0.4) + (Urgency×0.4) + (Difficulty×0.2). Lag bonus applied at scheduling time.

**Trigger / Invocation:** GENERATED ALWAYS AS column on tasks. Lag bonus applied via SQL join at scheduling.

**Task Tree:**

- 4.1 [D] GENERATED ALWAYS AS column on tasks: (priority * 0.4 + urgency * 0.4 + difficulty * 0.2)
- 4.2 [D] Lag bonus dynamic at scheduling time via SQL JOIN to faction_weekly_stats — NOT stored on task

**Data Contracts:** TWS is computed column, not stored; lag bonus is ephemeral query-time addition

**Dependencies:** #6 (Faction Stats), #11 (Lag Score)

**Failure Modes & Fallbacks:** All fields default to 5 (medium) if not set

---

### #5: Goal Stack Architecture [D] 📐

**Purpose:** 3-layer: Outcomes (WHY, max 7) → Projects (WHAT, max 3 active/faction) → Tasks (HOW). Status: active/paused/completed/dead_node.

**Trigger / Invocation:** Goal distiller parses Goals.md from vault → upserts. Dataview displays goal tree.

**Task Tree:**

- 5.1 [D] Three PG tables: outcomes (max 7), projects (FK to outcomes, max 3 active/faction), tasks (FK to projects)
- 5.2 [D] Status enum: active/paused/completed/dead_node
- 5.3 [D] Goal distiller — read /vault/01-System/Goals.md → parse Markdown headings → upsert to PG
- 5.4 [D] Dataview queries in Obsidian Dashboard display goal tree from JSON pushes

**Data Contracts:** `outcomes: {id, title, description, rank 1-7, status, created_at}`, `projects: {id, outcome_id FK, faction_id FK, title, status, max 3 active per faction}`, `tasks: {id, project_id FK, title, status, ...}`

**Dependencies:** #1 (Factions)

**Failure Modes & Fallbacks:** Goals.md missing → empty goal stack; max 7 enforcement rejects overflow

---

### #6: Faction Weekly Stats Tracking [D] 📐

**Purpose:** Target vs actual hours per faction per week. Compute CR, CS, MS, LS, AG.

**Trigger / Invocation:** APScheduler Sunday cron. Push JSON to vault.

**Task Tree:**

- 6.1 [D] APScheduler Sunday 23:00 IST — compute from task_completions + time_logs
- 6.2 [D] SQL aggregation: completion_rate, completion_score, momentum_score, lag_score, action_gap per faction
- 6.3 [D] Write to faction_weekly_stats table
- 6.4 [D] Push JSON to /vault/00-System-Data/faction_stats.json → git commit + push

**Data Contracts:** `faction_weekly_stats: {id, faction_id, week_start DATE, target_hours, actual_hours, completion_rate FLOAT, completion_score FLOAT, momentum_score FLOAT, lag_score FLOAT, action_gap FLOAT}`

- JSON to vault for Obsidian Charts

**Dependencies:** #1 (Factions), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** No tasks completed → all zeros; cron miss → next run picks up

---

### #7: Behavioral Event Stream [D] 📐

**Purpose:** Log every significant action/inaction as event. Foundation of all downstream analytical features. **Must be wired into every endpoint.**

**Trigger / Invocation:** Every FastAPI endpoint emits on any state change. PG LISTEN/NOTIFY triggers downstream consumers.

**Task Tree:**

- 7.1 [D] `behavioral_events` table: id, event_type (enum), entity_type, entity_id, event_data (JSONB), source (telegram/obsidian/system/cron), created_at
- 7.2 [D] Event emission on: task created/completed/deferred, checkin submitted, project status change, Telegram message, vault change detected, review generated, alert fired
- 7.3 [D] PG LISTEN/NOTIFY on INSERT → real-time subscribers (State Engine, Pattern Engine, Context Forge)
- 7.4 [D] Helper function: `emit_event(event_type, entity_type, entity_id, event_data, source)` — called in every router

**Data Contracts:**

- `behavioral_events: {id UUID PK, event_type behavioral_event_type, entity_type TEXT, entity_id UUID, event_data JSONB, source TEXT, created_at TIMESTAMPTZ}`
- event_type enum: task_created, task_completed, task_deferred, checkin_submitted, project_status_changed, telegram_message, vault_file_changed, review_generated, alert_fired, injection_triggered

**Dependencies:** None (infrastructure feature)

**Failure Modes & Fallbacks:** PG NOTIFY queue full → events still logged (NOTIFY is fire-and-forget); no fallback needed — PG is durable

---

### #8: Action Gap Tracking [D] 📐

**Purpose:** AG = declared_priority − (actual_hrs / target_hrs × 10). Alert if gap > 5.

**Trigger / Invocation:** Computed inside weekly stats job (#6). AG > 5 → Telegram warning.

**Task Tree:**

- 8.1 [D] AG = declared_priority − (actual_hrs / target_hrs × 10) — computed in weekly stats SQL
- 8.2 [D] AG > 5 → INSERT behavioral_event (type='action_gap_alert')
- 8.3 [D] Surfaced in weekly review (#18) and Dashboard

**Data Contracts:** Value 0-10 (negative = faction getting more time than declared priority)

**Dependencies:** #6 (Faction Weekly Stats), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** No time logged → AG cannot be computed → no alert

---

### #9: Deferral Detection (3/5/8+ rule) [D] 📐

**Purpose:** Flag tasks deferred 3×, 5×, 8+ times.

**Trigger / Invocation:** task_deferrals table tracks each deferral with timestamp + reason_code. Affirmative action at thresholds.

**Task Tree:**

- 9.1 [D] task_deferrals table: id, task_id FK, deferred_at, reason_code (enum: blocked/no_time/low_energy/avoidance/other), previous_scheduled_date
- 9.2 [D] Threshold logic: 3× → behavioral_event FLAG type='deferral_threshold_3'; 5× → Telegram alert with task; 8+ → escalate in weekly review + Inner Loop
- 9.3 [D] Count computed via COUNT(*) FROM task_deferrals WHERE task_id = $1

**Data Contracts:** `task_deferrals: {id, task_id FK, deferred_at, reason_code TEXT, previous_scheduled_date DATE}`

**Dependencies:** #5 (Goal Stack), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** None — deferral is always explicit user action

---

### #10: Dead Node Detection [D] 📐

**Purpose:** Flag outcomes/projects untouched 60+ days.

**Trigger / Invocation:** APScheduler weekly cron. Telegram inline keyboard: [Recommit] [Kill] [Pause].

**Task Tree:**

- 10.1 [D] Query: `SELECT * FROM projects WHERE last_touched_at < NOW() - INTERVAL '60 days' AND status = 'active'`
- 10.2 [D] Update status to 'dead_node'
- 10.3 [D] Telegram alert with InlineKeyboard: Recommit (reset last_touched_at), Kill (status→completed), Pause (status→paused)

**Data Contracts:** `last_touched_at` updated on any task completion/creation within project. Status enum: active/paused/completed/dead_node.

**Dependencies:** #7 (Behavioral Events tracks last_touched_at)

**Failure Modes & Fallbacks:** None — pure date comparison

---

### #11: Lag Score + TWS Lag Bonus [D] 📐

**Purpose:** LS = target − actual hours. Lag score > thresholds → TWS bonus at scheduling time.

**Trigger / Invocation:** LS computed in weekly stats (#6). Applied at scheduling via SQL join.

**Task Tree:**

- 11.1 [D] LS = target_hours − actual_hours (from faction_weekly_stats)
- 11.2 [D] Scheduling query: CASE WHEN LS > 6 THEN TWS + 4 WHEN LS > 3 THEN TWS + 2 WHEN faction_ahead THEN TWS − 1 ELSE TWS

**Data Contracts:** LS is per-faction weekly aggregation; NOT persisted on individual tasks

**Dependencies:** #4 (TWS), #6 (Faction Weekly Stats)

**Failure Modes & Fallbacks:** No weekly stats → LS = 0 → no bonus applied

---

### #12: Emergency Task Injection Protocol [H] 📐

**Purpose:** Insert emergency task, recalculate day, protect non-negotiables. Slash command /emergency or intelligent detection via SOUL.md.

**Trigger / Invocation:** Telegram /emergency {task} or detected from user message via AI model intent classification.

**Task Tree:**

- 12.1 [D] New task → compute TWS → compare to all currently scheduled tasks
- 12.2 [D] If TWS > lowest scheduled → replace lowest non-locked task
- 12.3 [D] Deferred task gets urgency + 2
- 12.4 [D] If urgency = 10 → clear ALL discretionary tasks (is_locked must be false)
- 12.5 [AI] Intelligent detection: AI model classifies user message as emergency intent (FACTUAL_PERSONAL with emergency flag)

**Data Contracts:** `tasks.is_locked BOOLEAN` protects non-negotiables; slot replacement is deterministic sort

**Dependencies:** #4 (TWS), #5 (Goal Stack)

**Failure Modes & Fallbacks:** All slots locked → Telegram: "No room today, schedule tomorrow?"; AI false positive → user ignores (no harm)

---

### #13: Exhaustion Predictor [H] 📐

**Purpose:** Predict overload from recent data. Auto-adjust timetable.

**Trigger / Invocation:** APScheduler cron, regular intervals (30-45 days). Deterministic rule fires first; AI enhancement Phase 2.

**Task Tree:**

- 13.1 [D] Rule-based: IF avg_task_difficulty(5d) > 7 AND avg_DCS(5d) < 5 → exhaustion_risk flag
- 13.2 [D] On flag: reduce next-day load 30% (remove tasks from schedule_bucket by lowest TWS)
- 13.3 [AI] Phase 2: AI model analyzes 30-day behavioral window for nuanced patterns
- 13.4 [D] Requires 60+ days logged data for Phase 2

**Data Contracts:** `exhaustion_risk` in behavioral_events; schedule_bucket modification at query time

**Dependencies:** #2 (DCS), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** <60 days → rule-based only; false positive → user adds tasks back manually

---

### #14: Weekly Faction Rebalance [D] 📐

**Purpose:** End-of-week: which faction is starving? Boost next week. Deterministic based on data points, NOT LLM.

**Trigger / Invocation:** Sunday cron (#6). Starving factions get automatic TWS bonus via #11.

**Task Tree:**

- 14.1 [D] Sunday cron (#6) computes lag scores
- 14.2 [D] LS > 3h → starving; TWS bonus applied automatically via #11
- 14.3 [D] Rebalance recommendations written to /vault/06-Reviews/weekly/YYYY-WW.md → git commit + push

**Data Contracts:** Written to weekly review markdown + TWS bonus at scheduling time

**Dependencies:** #6 (Faction Weekly Stats), #11 (Lag Score + TWS Bonus)

**Failure Modes & Fallbacks:** All factions on target → no rebalance needed; no weekly stats → skip

---

### #15: Momentum Score (MS) [D] 📐

**Purpose:** Avg completion rate over last 3 weeks per faction.

**Trigger / Invocation:** Computed in weekly stats (#6). SQL window function.

**Task Tree:**

- 15.1 [D] MS = AVG(completion_rate) FROM faction_weekly_stats WHERE week >= current_week − 3
- 15.2 [D] Displayed in Dashboard via pushed JSON to vault

**Data Contracts:** Single FLOAT per faction; null for <3 weeks of data

**Dependencies:** #6 (Faction Weekly Stats)

**Failure Modes & Fallbacks:** <3 weeks data → null; displays as "building..."

---

### #16: Parallel Task Execution Optimizer [H] 📐

**Purpose:** Identify tasks that can run simultaneously. Phase 2. Requires SOUL.md problem-solving philosophy document.

**Trigger / Invocation:** Scheduling time. Telegram /parallel {tasks}. Autonomous sub-agent invocation.

**Task Tree:**

- 16.1 [D] task_dependencies junction table: task_id, depends_on_task_id, dependency_type (blocks/blocks_if/enables/related)
- 16.2 [AI] AI model identifies parallelizable tasks from descriptions + dependencies
- 16.3 [D] Scheduler: topological sort → independent chains → parallel slots
- 16.4 [D] Display: "These 3 tasks can run simultaneously: [list]"

**Data Contracts:** `task_dependencies: {id PK, task_id FK, depends_on_task_id FK, dependency_type TEXT}`

**Dependencies:** #4 (TWS), #5 (Goal Stack)

**Failure Modes & Fallbacks:** No dependencies defined → "all sequential" (safe default); AI misidentifies → user corrects

---

### #17: Three-Birds-One-Stone Efficiency Mapping [H] 📐

**Purpose:** Tag tasks serving multiple factions. Cross-faction tasks get TWS + 1 per extra faction.

**Trigger / Invocation:** On task creation. AI model suggests cross-faction mapping.

**Task Tree:**

- 17.1 [D] M2M junction table task_factions: task_id, faction_id, weight_share FLOAT (default equal split)
- 17.2 [AI] AI model suggests faction mapping from task description: "This task serves which factions?"
- 17.3 [D] Boost: cross-faction tasks get TWS + 1 per extra faction (capped at +3)
- 17.4 [D] Time splits proportionally among associated factions

**Data Contracts:** `task_factions: {task_id FK, faction_id FK, weight_share FLOAT DEFAULT 1.0}`

**Dependencies:** #1 (Factions), #4 (TWS)

**Failure Modes & Fallbacks:** No cross-faction → single-faction default; AI suggests wrong faction → user reassigns

---

### #18: Review Cadence System [D + AI] 📐

**Purpose:** Daily / Weekly / Monthly / Quarterly reviews with checklists. Deterministic scheduling, AI content.

**Trigger / Invocation:** APScheduler: Daily 22:00, Sunday 20:00, Last day of month, Last day of quarter.

**Task Tree:**

- 18.1 [D] APScheduler triggers per cadence
- 18.2 [AI] Daily: Telegram 3-sentence prompt from AI model: "3 things you accomplished, 1 thing you deferred, readiness for tomorrow"
- 18.3 [AI] Weekly: AI model generates narrative from weekly stats + events
- 18.4 [D] Write to /vault/06-Reviews/{cadence}/YYYY-MM-DD.md → git commit + push

**Data Contracts:** Markdown files in vault with YAML frontmatter; templates in Obsidian Templater

**Dependencies:** #6 (Faction Stats), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** AI model down → review uses template without AI content; cron miss → skipped (next day picks up)

---

### #19: Oracle Cloud ARM64 VM [Infra] ✅

**Purpose:** 4 OCPU, 24GB RAM, 200GB, Ubuntu 22.04 at 140.238.245.25. Always free tier.

**Current state:** Already provisioned and running.

**Dependencies:** None (foundational)

---

### #20: Docker Stack [Infra] 🔧

**Purpose:** Three containers: PG 16, Neo4j 5.x, Redis 7.x (optional). REMOVED: Qdrant, ChromaDB, pgvector.

**Task Tree:**

- 20.1 [D] docker-compose.yml with health checks
- 20.2 [D] Memory limits enforced per container
- 20.3 [D] Volumes for data persistence

**Dependencies:** #19 (VM)

---

### #21: Cloudflare Tunnel [Infra] ✅

**Purpose:** api.locusapp.online → localhost:8000 via cloudflared as systemd service. Already configured.

**Dependencies:** #19 (VM)

---

### #22: Vault Sync via Git [D] 📐

**Purpose:** GitHub private repo for vault. Obsidian Git plugin auto-commit/push/pull. Backend writes directly.

**Trigger / Invocation:** Obsidian Git plugin every 10min; VM cron `git pull` every 5min; Backend writes → git add + commit + push.

**Task Tree:**

- 22.1 [D] Directory partitioning: User writes /01-System/, /02-Captures/, /04-Resources/, /05-Journal/; Backend writes /00-System-Data/, /03-AI-Chats/, /06-Reviews/, /07-Morning-Briefs/
- 22.2 [D] SSH key auth to GitHub
- 22.3 [D] Backend write helper: write_file(path) → git add → git commit → git push
- 22.4 [D] VM cron: git -C /vault pull every 5min

**Data Contracts:** No overlap directories = no merge conflicts

**Dependencies:** Git, GitHub private repo, SSH keys configured

**Failure Modes & Fallbacks:** Git push conflict → stall (no auto-merge); pull fails → wait for next cycle; Obsidian not running → write still works

---

### #23: FastAPI Backend [Infra] 🔧

**Purpose:** Python FastAPI with routers, Uvicorn ASGI, AI model SDK singleton.

**Routers:** /checkins, /tasks, /goals, /factions, /schedule, /brain, /vault, /events, /reviews. All emit behavioral events (#7).

**Dependencies:** #20 (Docker), #21 (Cloudflare)

---

### #24: Self-Maintenance System [H] 📐

**Purpose:** Auto-update deps. If breakage: create P1 fix task + diagnostic. Outsourced to 'agy' (Google Antigravity CLI).

**Trigger / Invocation:** APScheduler monthly cron.

**Task Tree:**

- 24.1 [D] pip-audit for security → if critical → P1 task created
- 24.2 [D] Post-update: run pytest → if failures → Telegram alert with [Rollback] [Fix]
- 24.3 [D] Outsourced to agy CLI for actual execution

**Dependencies:** agy CLI installed

**Failure Modes & Fallbacks:** agy unavailable → manual self-maintenance

---

### #25: Local Database Mirror [D] 📐

**Purpose:** Sync VM databases to local for offline access. Phase 2.

**Trigger / Invocation:** APScheduler nightly: pg_dump → rsync.

**Task Tree:**

- 25.1 [D] pg_dump --format=custom nightly
- 25.2 [D] rsync to local machine via SSH

**Dependencies:** SSH access from local to VM

---

### #26: PageIndex + Direct Retrieval [H] 📐

> **⚠️ CRITICAL CLARIFICATION:** PageIndex is NOT a vector database or embedding pipeline.
> It is a **vectorless, reasoning-based RAG** system that builds a hierarchical tree structure
> index (like a Table of Contents) and uses LLM tree-search for retrieval.
> See: https://github.com/VectifyAI/PageIndex

**Purpose:** PageIndex builds a tree structure index from every Obsidian Markdown note (headers → hierarchy) for reasoning-based, context-aware retrieval. Neo4j provides entity-level graph traversal. Two-store architecture — no middleware, no embeddings, no vector DB.

**Trigger / Invocation:** On every vault file change (via git diff). On every query via Query Router.

**Task Tree — PageIndex (Vectorless Tree Index):**

- 26.1 [D] page_index_md.py: extract Markdown headers (# → ######) → flat node list (title, line_num, level)
- 26.2 [D] Extract text content per node from line ranges; build hierarchical tree (parent/child via header depth)
- 26.3 [D] Tree thinning: nodes < `min_node_token` (500t default) → text merged into parent; tree stays navigable
- 26.4 [AI] Optional node summaries: AI model generates 1-sentence summaries per leaf node for faster LLM reasoning
- 26.5 [D] Store tree in `pageindex_workspace/` as JSON; expose 3 agent tools: `get_document`, `get_document_structure`, `get_page_content(pages="start-end")`

**Task Tree — Neo4j (Graph Layer):**

- 26.6 [AI] AI model entity extraction during ingestion → entities + relationships → Neo4j

**Retrieval Flow (combined at query time):**

1. Query Router (#57) classifies intent
2. PageIndex: LLM reasons over tree structures of vault notes → identifies relevant sections → `get_page_content(pages="X-Y")`
3. Neo4j: graph traversal → related entities/pathways (Context Forge: 150t)
4. Context Forge (#58) assembles token block

**Data Contracts:** PageIndex tree JSON: `{title, node_id, line_num, text, nodes[]}`. Retrieval format: `pages="5-7"` or `"3,8"`.

**Dependencies:** PageIndex Python library (local fork of `VectifyAI/PageIndex`), AI model V4 Flash

**Failure Modes & Fallbacks:** AI model down → skip entity extraction + node summaries, PageIndex tree still builds; PageIndex tree build fails → raw grep over vault as fallback

---

### #27: Nightly Vault Ingestion Pipeline [H] 📐 (Consolidates #42, #46, #80)

**Purpose:** Nightly cron (23:30 IST): scan vault, scrape external AI chats (ChatGPT ×3, Claude, Gemini, Perplexity), parse, extract entities, push to Neo4j.

**Trigger / Invocation:** APScheduler 23:30 IST daily.

**Task Tree:**

- 27.1 [D] Vault crawl via git diff OR MD5 comparison against vault_files table → new/changed only
- 27.2 [H] External chat scraping via Playwright persistent browser contexts (3 ChatGPT accounts, Claude, Gemini, Perplexity)
- 27.3 [D] Tagged .md with YAML frontmatter → /vault/03-AI-Chats/{source}/ → Telegram alert
- 27.4 [D] Ingested .md → PageIndex tree structure update (#26) as part of next tree build
- 27.5 [AI] AI model entity extraction → Neo4j
- 27.6 [D] PDFs/non-text → MinerU (AGPL-3.0, CPU)

**Data Contracts:** New chats identified by unique ID; log changes in old chats; git diff avoids reprocessing

**Dependencies:** #22 (Vault Sync), #26 (PageIndex), Playwright, MinerU

**Failure Modes & Fallbacks:** AI model down → skip entity extraction, PageIndex tree still builds; Playwright timeout → skip scraper for that source; MinerU fails → skip PDF

---

### #28: Weekly Full Vault Synthesis [AI] 📐

**Purpose:** Sunday 02:00 — full behavioral analysis. Generate personality drift report, faction narrative, top 3 observations.

**Trigger / Invocation:** APScheduler Sunday 02:00 IST.

**Task Tree:**

- 28.1 [D] Collect: behavioral_events (7d), faction_weekly_stats, detected_patterns, CURRENT_STATE, top 10 Hebbian pathways
- 28.2 [AI] AI model generates: personality drift report, faction narrative, top 3 observations (~3000 tokens)
- 28.3 [D] Write to weekly_reviews table + /vault/06-Reviews/weekly/YYYY-WW-synthesis.md → git commit + push

**Data Contracts:** ~3000 token AI model call; Markdown + YAML output

**Dependencies:** #6 (Faction Stats), #7 (Events), #61 (Pattern Engine), #60 (State Engine), #64 (Hebbian)

**Failure Modes & Fallbacks:** AI model down → skip; no data this week → "Insufficient data"

---

### #29: Personality Profile Building [H] 📐

**Purpose:** Auto-build user personality model from chats + behavioral graph. Rolling updates when patterns confirmed.

**Trigger / Invocation:** Pattern Engine (#61) auto-updates user_identity when patterns confirmed (confidence > 0.75, count > 2).

**Task Tree:**

- 29.1 [AI] AI model synthesizes quarterly comprehensive profile from all accumulated data
- 29.2 [D] Neo4j Person node mirrors profile properties
- 29.3 [D] Rolling updates: confidence-weighted average, never hard overwrite

**Data Contracts:** Neo4j Person node with profile properties; PG user_identity table updated

**Dependencies:** #61 (Pattern Engine), #62 (User Identity), #7 (Events)

**Failure Modes & Fallbacks:** <30 days data → "still learning"; conflicting signals → store both with confidences

---

### #30: Fine-Tuning / RLHF [Phase 3] 📐

**Purpose:** Fine-tune model on user's data once GPU available. QLoRA via Unsloth on small model.

**Key notes:** Phase 3. Collect 500+ labeled examples from reward_signals. LoRA adapter (50-200MB) via Ollama.

**Dependencies:** #63 (Reward Model), GPU rental via vast.ai

---

### #31: Subagentic Capabilities [Phase 3] 📐

**Purpose:** Spawn agents on-demand for new task types. AI model orchestrates tool calls via MCP: plan → execute → observe → re-plan.

**Dependencies:** #78 (Dynamic MCP), #86 (Pi Sub-Agents), SOUL.md

---

### #32: Self-Evolving Architecture + Architect Bot [H] 📐 (Consolidates #77, #106)

**Purpose:** Internal bot that improves Locus. Three mechanisms: SOUL.md quarterly updates, Reward Model improves quality gate, Hebbian weighting tunes retrieval. No weight changes — behavioral tuning only.

**Trigger / Invocation:** Quarterly (SOUL.md), weekly (Reward Model retrain), continuous (Hebbian).

**Task Tree:**

- 32.1 [H] AI model scans reward_signals for underperforming components → generates patches with tests
- 32.2 [D] LOW risk → auto-deploy; HIGH risk → Telegram /approve
- 32.3 [AI] SOUL.md updated quarterly via AI model + user approval
- 32.4 [D] Reward Model weekly retrain improves quality gate
- 32.5 [D] Hebbian weighting continuous tuning

**Data Contracts:** Patch = code diff + test assertions; Risk assessed by scope (file count, DB schema change)

**Dependencies:** #63 (Reward Model), #64 (Hebbian), SOUL.md

**Failure Modes & Fallbacks:** Patch breaks tests → revert + create fix task; user rejects → discard

---

### #33: Multi-Dimensional Graph Nodes — SCRAPPED ❌

Unnecessary — Neo4j schema already supports multiple edge types between same pair.

---

### #34: 3-Level Tag Hierarchy [D] 📐

**Purpose:** faction/domain/specific tags enforced. Autonomous for every note.

**Trigger / Invocation:** On every ingestion. Python script enforces.

**Task Tree:**

- 34.1 [D] Tags registry in PG tags table
- 34.2 [D] Python script validates tag format: faction/domain/specific
- 34.3 [D] Auto-suggest tags from note content via regex (no AI)

**Data Contracts:** `tags: {id PK, full_path TEXT, level INT, parent_id FK}`

**Dependencies:** #27 (Ingestion)

---

### #35: Audio Transcription Pipeline [H] 📐

**Purpose:** Whisper-large-v3-turbo via Groq. Auto-detect Hinglish. Output → vault .md → PageIndex tree index.

**Trigger / Invocation:** On new audio file in vault. Autonomous for every audio file (voice note, phone call, podcast).

**Task Tree:**

- 35.1 [H] Groq Whisper API (free tier) → transcription
- 35.2 [D] Output → vault .md with YAML frontmatter → git commit + push
- 35.3 [D] PageIndex tree structure rebuild picks up new .md on next ingestion (#26)

**Dependencies:** Groq API key, #26 (PageIndex)

**Failure Modes & Fallbacks:** Groq rate-limited → queue retry; alternative: whisper-cpp local (slower on ARM64)

---

### #36: Obsidian Dashboard + Progress Visualization [D] 📐 (Consolidates #54)

**Purpose:** Central Obsidian dashboard with Dataview queries + Charts. Panels: Today's Schedule, Faction Health, Active Patterns, Goal Stack, Hebbian Pathways, Brain Observations.

**Trigger / Invocation:** On vault sync. Backend pushes stats JSON → Dataview reads.

**Task Tree:**

- 36.1 [D] Dashboard.md with Dataview queries
- 36.2 [D] Backend pushes stats JSON to /vault/00-System-Data/stats.json → git commit + push
- 36.3 [D] Obsidian Charts (Chart.js-based) renders DCS trends, faction time, completion rates

**Panels:** Today's Schedule, Faction Health (CR/MS/LS/AG), Active Patterns, Goal Stack, Hebbian Pathways, Brain Observations, DCS Trend (7d)

**Dependencies:** #22 (Vault Sync), Obsidian Dataview plugin, Obsidian Charts plugin (optional)

---

### #37: Rough Note Parser / Idea Tracker [H] 📐

**Purpose:** Capture rough notes, enhance, convert to tasks. Telegram /idea → captures table. AI model optionally suggests faction mapping + project.

**Trigger / Invocation:** Telegram /idea {text} or /dump {text}. AI model expands autonomously.

**Task Tree:**

- 37.1 [D] captures table: type='idea', raw_text, enhanced_text, faction_id, project_id, status
- 37.2 [AI] AI model optionally: expand idea, research (web search), suggest faction mapping + project
- 37.3 [D] Telegram inline: [Promote to Task] [Research] [Archive]
- 37.4 [D] On Promote to Task: INSERT into tasks, create note in /vault/02-Captures/

**Data Contracts:** `captures: {id, type, raw_text, enhanced_text, url, tags JSONB, faction_id FK, project_id FK, status, created_at}`

**Dependencies:** #5 (Goal Stack), #1 (Factions), #43 (Telegram Bot)

**Failure Modes & Fallbacks:** AI model down → store raw; no faction match → unassigned

---

### #38: Link Dump / Resource Logger [D] 📐

**Purpose:** Save and tag URLs. Telegram /link {url}. Store + archive.

**Trigger / Invocation:** Telegram /link {url} or /dump {url}.

**Task Tree:**

- 38.1 [D] captures table: type='link', url, tags
- 38.2 [D] Note in /vault/04-Resources/ → git commit + push
- 38.3 [H] AI model optional: auto-summary + suggest tags + web scrape page

**Dependencies:** #43 (Telegram Bot)

---

### #39: Structured Check-ins + Push Notifications [D+AI] 📐 (Consolidates #53)

**Purpose:** 4 daily check-ins (Morning/Afternoon/Evening/Night) via Telegram push notifications + inline keyboard. Log anytime. DCS computed automatically.

**Trigger / Invocation:** APScheduler at 07:30/13:00/18:00/22:00 IST. User can also /checkin anytime.

**Task Tree:**

- 39.1 [D] APScheduler 4× daily → Telegram inline keyboard (tap numbers, no typing)
- 39.2 [D] DCS computed automatically (#2)
- 39.3 [D] User can attach notes to justify/explain stats
- 39.4 [AI] Evening 22:00: AI model optional 3-sentence summary of day
- 39.5 [D] Data pushed to /vault/00-System-Data/daily/YYYY-MM-DD.json → git sync

**Data Contracts:** JSON per day with all check-in data + DCS + mode

**Dependencies:** #2 (DCS), #43 (Telegram Bot), #7 (Events)

**Failure Modes & Fallbacks:** User ignores push → no check-in; always allow manual /checkin

---

### #40: Design Thinking UX Overhaul [Phase 2] 📐

**Purpose:** Design principles applied to Dashboard. Custom CSS for Obsidian (dark theme, amber accents).

**Dependencies:** #36 (Dashboard), Obsidian Minimal theme

---

### #41: Visual Health Avatar / Tree of Life [Phase 3] 📐 (Consolidates #78, #79)

**Purpose:** Composite faction score → 5 animated SVG/CSS states (blooming → wilting). Single glance = system health.

**Dependencies:** #36 (Dashboard), Lottie or CSS-animated SVG

---

### #42: Google Calendar Integration [F] 📐

**Purpose:** OAuth + Calendar read/write for schedule injection. Read events as scheduling constraints. Write faction-colored blocks. Never overwrite existing events without authorization.

**Trigger / Invocation:** OAuth flow on setup. APScheduler hourly sync.

**Task Tree:**

- 42.1 [D] Google Cloud Console → Calendar API + Gmail API → OAuth credentials → .env
- 42.2 [D] FastAPI /auth/google → redirect → callback stores refresh_token in PG oauth_tokens (encrypted)
- 42.3 [D] google-auth library auto-refresh
- 42.4 [D] Read events as scheduling constraints → schedule_blocks table
- 42.5 [D] Write faction-colored blocks (Locus-created events tagged, never overwrite user-created)

**Data Contracts:** `oauth_tokens: {id, provider TEXT, encrypted_token TEXT, scopes TEXT[], expires_at}`

**Dependencies:** google-api-python-client, google-auth-oauthlib

**Failure Modes & Fallbacks:** Token expired → auto-refresh; refresh fails → Telegram: "Re-auth Google"; API rate-limit → backoff retry

---

### #43: Telegram Bot (Second Brain Chat) [F] 🔧

**Purpose:** Full conversational pipeline to vault. ALL messages logged. Commands: /checkin, /dcs, /tasks, /schedule, /goals, /idea, /link, /weekly, /debug, /state.

**Trigger / Invocation:** User sends message to Telegram bot.

**Task Tree:**

- 43.1 [D] Intercept ALL messages → log to telegram_logs (#51)
- 43.2 [AI] Query Router (#57) → classify intent (~50 tokens)
- 43.3 [H] Retriever: Neo4j graph traversal + PG structured queries
- 43.4 [D] Context Forge (#58) assembles 800-token context
- 43.5 [AI] AI model generates response
- 43.6 [D] 👍/👎 inline keyboard → reward signal logged (#63)
- 43.7 [D] Nightly backup 23:55: ALL messages → /vault/03-AI-Chats/telegram/YYYY-MM-DD.md

**Dependencies:** #57 (Query Router), #58 (Context Forge), #63 (Reward Model), #51 (Logger)

**Failure Modes & Fallbacks:** AI model down → cached response or "thinking..." + retry; Query Router timeout → default response

---

### #44: Gmail Integration [F] 📐

**Purpose:** Read emails, extract actionable items. Same OAuth as #42.

**Trigger / Invocation:** APScheduler hourly.

**Task Tree:**

- 44.1 [D] Same OAuth token (#42)
- 44.2 [D] Gmail API: read inbox headers + snippets
- 44.3 [AI] AI model classifies: task/event/info/ignore
- 44.4 [D] Actionable items → captures table

**Dependencies:** #42 (Google Calendar OAuth)

---

### #45: Voice Call Interface [Phase 3] 📐

**Purpose:** Voice debriefing with Locus. Audio → Groq Whisper STT → pipeline → Kokoro TTS. Post-call transcript to vault.

**Dependencies:** #35 (Audio Transcription), Kokoro TTS, Twilio/LiveKit

---

### #46: VM Security Hardening [D] ✅

**Purpose:** SSH key-only, fail2ban, UFW, per-device auth. Monthly audit.

**Task Tree:**

- 46.1 [D] SSH key-only (already configured)
- 46.2 [D] fail2ban (already configured)
- 46.3 [D] UFW (already configured)
- 46.4 [D] APScheduler monthly audit → Telegram report

---

### #47: Security Testing [D] 📐

**Purpose:** OWASP top 10, API auth, Docker escape. Quarterly.

**Trigger / Invocation:** APScheduler quarterly.

**Task Tree:**

- 47.1 [D] OWASP ZAP against FastAPI endpoints (Docker image)
- 47.2 [D] Trivy for Docker image scanning

**Dependencies:** OWASP ZAP Docker image, Trivy Docker image

---

### #48: Prompt Injection Protection [D+AI] 📐

**Purpose:** Filter dangerous patterns in user input.

**Task Tree:**

- 48.1 [D] Layer 1: Regex blocklist (sudo, curl, rm, eval, exec, import os, subprocess)
- 48.2 [AI] Layer 2: If code-like AND intent ≠ CODE_HELP → AI model semantic check (~20 tokens)
- 48.3 [D] FastAPI middleware — 30 lines

---

### #49: Thinking Pattern Capture [H] 📐

**Purpose:** Codify how the user thinks and solves problems by mining AI chat history for recurring reasoning patterns.

**Trigger / Invocation:** AI model scans AI chat vault during nightly ingestion. Requires 60+ days of chat data.

**Task Tree:**

- 49.1 [D] Check data sufficiency: COUNT chat files in /vault/03-AI-Chats/ → need 60+ days
- 49.2 [AI] AI model analyzes batch of AI chat transcripts — identifies patterns: problem decomposition style, debugging approach, learning style, communication patterns, avoidance patterns
- 49.3 [D] Create ConceptNode in Neo4j: type='thinking_pattern', confidence FLOAT
- 49.4 [D] Edge: Person →[EXHIBITS]→ ConceptNode, weight = confidence
- 49.5 [D] If pattern confidence > 0.75 AND evidence_count > 2 → feed into user_identity tendencies (rolling average)

**Data Contracts:** Pattern: `{name, description, evidence_quote, confidence 0-1, category}`; Categories: decomposition/debugging/learning/communication/avoidance

**Dependencies:** #27 (Nightly Ingestion), #62 (User Identity), AI model, 60+ days data

**Failure Modes & Fallbacks:** <60 days → skip; low confidence < 0.5 → store but don't surface; chat vault empty → no-op

---

### #50: Excalidraw MCP Skill [Phase 3] 📐

**Purpose:** MCP server for autonomous Excalidraw diagrams. Six MCP tools. Copy from Hermes.

**Dependencies:** FastMCP, Excalidraw JSON spec

---

### #51: Telegram Chat Logger [D] 📐

**Purpose:** Log every Telegram message to PG. Full history. Middleware intercepts before routing.

**Trigger / Invocation:** Every Telegram message.

**Task Tree:**

- 51.1 [D] python-telegram-bot middleware: intercept ALL messages pre-routing
- 51.2 [D] Write to telegram_logs: timestamp, direction, message_id, raw_text, intent (filled post-routing), session_id
- 51.3 [D] Nightly backup 23:55: export day's logs → /vault/03-AI-Chats/telegram/YYYY-MM-DD.md → git commit + push

**Data Contracts:** `telegram_logs: {id PK, timestamp, direction ENUM(in/out), message_id, raw_text, intent TEXT, session_id}`

**Failure Modes & Fallbacks:** PG write fails → log to file fallback

---

### #52: Skill & MCP Toolkit Layer [H] 📐

**Purpose:** Registry of callable skills and MCP tools. Query Router decides: text reply vs skill invocation vs MCP.

**Task Tree:**

- 52.1 [D] skills_registry table: id, name, description, trigger_conditions (JSONB), tool_schema (JSONB), priority, is_active
- 52.2 [H] Query Router (#57) decides: text vs skill vs MCP based on intent + output_type

**Data Contracts:** `skills_registry: {id PK, name, description, trigger_conditions JSONB, tool_schema JSONB, priority INT, is_active BOOL}`

**Dependencies:** #57 (Query Router), FastMCP

---

### #53: Obsidian MCP [D] 📐

**Purpose:** MCP server exposing vault as tool interface. Tools: vault_read, vault_write (append-only), vault_search (grep), vault_tag, vault_stats.

**Task Tree:**

- 53.1 [D] FastMCP server — localhost only
- 53.2 [D] Path traversal blocked (must be within /vault/)
- 53.3 [D] .md only restriction
- 53.4 [D] Surface: vault_read, vault_write (append-only), vault_search (grep), vault_tag, vault_stats

**Dependencies:** #22 (Vault Sync), FastMCP

---

### #54: Locus as Universal MCP Server [D] 📐

**Purpose:** Expose entire backend as single remote MCP server. Streamable HTTP transport. Claude Desktop, ChatGPT, Cursor connect.

**Task Tree:**

- 54.1 [D] FastMCP alongside FastAPI
- 54.2 [D] Tools: store_thought, log_task, retrieve_context, query_patterns, get_current_state, get_schedule, log_mood, defer_task, search_vault, get_goal_stack, get_faction_health
- 54.3 [D] Thin wrappers around FastAPI endpoints

**Dependencies:** FastMCP (`pip install fastmcp`)

---

### #55: Personality + "Wants" Engine — IGNORED ⬜

Needs brainstorming. SOUL.md already covers identity.

---

### #56: Locus Builds Shivam's System — IGNORED ⬜

Meta-feature. Emerges from other features. STRATEGY.md as the guiding document.

---

### #57: Query Router / Intent Classifier [H] 📐

**Purpose:** Every message classified before retrieval. Single AI model call (~50 tokens).

**Trigger / Invocation:** Every incoming message in Telegram bot.

**Task Tree:**

- 57.1 [AI] AI model: structured JSON output — {intent, sources_required: [pageindex/neo4j/pg/web], temporal_scope, requires_deep_reasoning, confidence}
- 57.2 [D] Intents: FACTUAL_PERSONAL, BEHAVIORAL_PATTERN, KNOWLEDGE_RETRIEVAL, TASK_PLANNING, EMOTIONAL_STATE, EXTERNAL_KNOWLEDGE, SYNTHESIS, INFERENCE_REQUEST, COMMAND
- 57.3 [D] confidence < 0.7 → query ALL sources
- 57.4 [D] Source routing matrix: each intent maps to required source set

**Data Contracts:** JSON output, ~50 tokens

**Dependencies:** AI model

**Failure Modes & Fallbacks:** AI model timeout → default KNOWLEDGE_RETRIEVAL + all sources

---

### #58: Context Forge (800-Token Assembler) [D+AI] 📐

**Purpose:** Merge parallel retrieval into coherent context block. Anti-hallucination: if ALL sources empty → tell AI model "No personal data found."

**Task Tree:**

- 58.1 [D] 5 layers with hard token budgets:
  - user_identity: 80t (#62)
  - temporal_context: 60t (time, calendar events)
  - pg_events: 180t (behavioral events)
  - neo4j_pathways: 150t (top Hebbian pathways)
  - pageindex_content: 300t (relevant sections from PageIndex tree search)
  - web_results: 100t (only if EXTERNAL_KNOWLEDGE intent)
  - buffer: 30t
- 58.2 [D] Truncate by relevance score, NOT recency
- 58.3 [D] Increment Hebbian weight +0.1 on every Neo4j traversal
- 58.4 [D] If ALL sources empty → inject "No personal data found"

**Data Contracts:** 800 tokens total; tiktoken for counting

**Dependencies:** #57 (Query Router), #26 (PageIndex), #64 (Hebbian), #62 (User Identity)

**Failure Modes & Fallbacks:** Source unavailable → skip that layer; all empty → tell AI model explicitly

---

### #59: Inner Loop (Proactive Thinker) [AI] 📐

**Purpose:** Background reasoning every 90 min (07:00-00:00 IST). "The Samantha layer." Generates 0-2 observations about the user without being asked.

**Trigger / Invocation:** APScheduler every 90 min. Deep pass 03:00 (30-day analysis). Sunday 03:00 weekly synthesis.

**Task Tree:**

- 59.1 [D] Fetch: CURRENT_STATE, behavioral_alerts, recent events (6h), top Hebbian pathways
- 59.2 [AI] AI model: "You are NOT talking to Shivam. You are thinking about Shivam. Generate 0-2 observations."
- 59.3 [D] Dedup: Neo4j node similarity (title + entity overlap > 0.85) → suppress duplicate observation
- 59.4 [D] Score via Reward Model (#63): ≥ 0.6 to surface
- 59.5 [D] Route: HIGH → Telegram now; MEDIUM → morning brief queue; LOW → discard

**Routing Logic:**

- HIGH: critical alert, new persistent pattern detected, major mood shift
- MEDIUM: mild pattern, gentle observation, non-urgent insight
- LOW: trivial, repetitive, low confidence

**Dependencies:** #60 (State Engine), #61 (Pattern Engine), #63 (Reward Model), #64 (Hebbian)

**Failure Modes & Fallbacks:** AI model down → skip cycle; cron miss → next 90min picks up; deep pass misses → next night

---

### #60: State Engine (CURRENT_STATE) [H] 📐 — v2 REVISED

**Purpose:** Single-row PG table with system's best understanding of user's current state. Updated on check-in and significant events ONLY. Cause chain only when explicitly queried.

**Trigger / Invocation:** POST /checkins → immediate update. Significant events (task completion, emergency, mode change). GET /state/current?explain=true generates cause chain on demand.

**Task Tree:**

- 60.1 [D] Schema — current_state: id INT PK DEFAULT 1 CHECK(id=1), dcs FLOAT, mode TEXT, psychological JSONB {mood_trend, energy_trend, stress_level}, operational JSONB {momentum, deferral_rate_7d, last_meaningful_work, tasks_completed_today}, contextual_flags JSONB {exam_period, deadline_week}, alerts JSONB [{type, severity, message}], cause_chain TEXT?, updated_at TIMESTAMPTZ
- 60.2 [D] Update on check-in: POST /checkins → UPDATE current_state SET dcs, mode, psychological=..., updated_at=NOW()
- 60.3 [D] Update on events: task_completed → increment tasks_completed_today; task_deferred → recalculate deferral_rate_7d; mode_change → update mode
- 60.4 [AI] Cause chain — on demand only: GET /state/current?explain=true → AI model generates causal explanation citing data
- 60.5 [D] Cause chain cached in current_state.cause_chain for 30 min
- 60.6 [D] State API: GET /state/current → full state + optional cause chain; GET /state/summary → 50-token compressed
- 60.7 [D] Periodic snapshot: state_snapshots — INSERT every 6h

**Data Contracts:** `current_state`: single row updated in-place; `state_snapshots`: same columns + snapshot_at

**Dependencies:** #2 (DCS), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** No check-in today → dcs=null, mode=UNKNOWN; cause chain fails → return null; snapshot every 6h → max 4 rows/day

---

### #61: Multi-Horizon Pattern Engine — IGNORED (deemed unnecessary) ⬜

---

### #62: User Identity Profile — Already addressed (in #29) 📐

---

### #63: Personal Reward Model [D-ML] 📐

**Purpose:** sklearn LogisticRegression on 👍/👎 feedback. Predicts whether an Inner Loop observation will be valuable.

**Trigger / Invocation:** Every 👍/👎 logged. Retrain weekly APScheduler Sunday 04:00.

**Task Tree:**

- 63.1 [D] reward_signals table: response_id, signal (positive/negative), response_type, time_of_day, faction, intent, context_layers_used, pathway_ids
- 63.2 [D] Feature vector: (intent one-hot, faction one-hot, time_of_day, context_layers_count, pathway_count)
- 63.3 [D] sklearn LogisticRegression — retrain weekly Sunday 04:00
- 63.4 [D] Inference threshold: predicted ≥ 0.6 to surface (Inner Loop gate)
- 63.5 [D] Weights stored: joblib → PG bytea

**Data Contracts:** Min 50 samples before first training; threshold ≥ 0.6

**Dependencies:** #7 (Behavioral Events), #43 (Telegram Bot — 👍/👎), scikit-learn

---

### #64: Hebbian Memory System [D] 📐 (Consolidates #99, #107)

**Purpose:** Neo4j edge weight reinforcement, global weekly decay, spaced repetition surfacing, and project-specific memory decay. Pure graph math, no AI.

**Trigger / Invocation:** Traversal → +0.1. 👍 → ×1.3. 👎 → ×0.7. Sunday 03:30: weekly decay ×0.95.

**Task Tree:**

- 64.1 [D] Traversal → edge weight + 0.1
- 64.2 [D] 👍 → session weights × 1.3
- 64.3 [D] 👎 → session weights × 0.7
- 64.4 [D] Weekly decay: ALL weights × 0.95 (APScheduler Sunday 03:30)
- 64.5 [D] STDP: response latency < 2 min → reinforcement × 1.5
- 64.6 [D] GET /brain/pathways → top 10 for Dashboard
- 64.7 [D] Spaced repetition: track last_traversed_at on Neo4j nodes → nodes approaching decay + connected to active outcomes → Inner Loop surfaces
- 64.8 [D] Project decay: PG trigger on projects.status change → Cypher: MATCH (p:Project {id:$id})-[r]-() SET r.weight = r.weight * 0.5

**Data Contracts:** Weight cap 10.0; weekly decay ×0.95; traversal +0.1; 👍×1.3; 👎×0.7; STDP <2min → ×1.5; project status change → ×0.5

**Dependencies:** Neo4j, #7 (Behavioral Events), #59 (Inner Loop)

---

### #65: LOCUS_SHORTHAND Compression — IGNORED ⬜

---

### #66: Multi-Provider LLM Cascade — DELETED ❌

---

### #67: Quarterly QLoRA Pipeline — Phase 3 (same as #30) 📐

---

### #68: Inferred Cause Chain Engine [H] 📐

**Purpose:** Generate specific, data-cited causal explanations of why the user is in their current state. Cross-references CURRENT_STATE + historical patterns + user_identity + calendar.

**Trigger / Invocation:** INFERENCE_REQUEST intent from Query Router (#57). HIGH severity alerts from State Engine (#60). Inner Loop deep pass. Explicit GET /inference/explain.

**Task Tree:**

- 68.1 [D] Data collection: CURRENT_STATE, last 7d behavioral_events, active calendar events (7d), user_identity known patterns, historical patterns matching current state, DCS trend (14d)
- 68.2 [AI] AI model: "Write ONE paragraph explaining WHY the user is in their current state. Cite exact numbers and dates. Identify primary cause, secondary factors."
- 68.3 [D] Confidence scoring: weighted sum of available data dimensions — has_dcs_data (0.2) + has_historical_pattern (0.3) + has_calendar (0.2) + has_behavioral_evidence (0.2) + has_identity_trait (0.1)
- 68.4 [D] If confidence < 0.5 → append "Low confidence — limited data available."
- 68.5 [D] Store in current_state.cause_chain + cause_chains table (history)

**Data Contracts:** `cause_chains: {id PK, cause_chain TEXT, confidence FLOAT 0-1, data_snapshot JSONB, created_at}`

**Dependencies:** #60 (State Engine), #61 (Pattern Engine), #62 (User Identity), #42 (Calendar), #7 (Events), #58 (Context Forge)

**Failure Modes & Fallbacks:** AI model down → return null; insufficient data (<30d) → "insufficient data"; conflicting evidence → present both with confidences

---

### #69: Migration from Hermes/OpenClaw [D] 📐

**Purpose:** Extract history, archive configs, document patterns. ~2 hours manual.

---

### #70: Automated VPS Setup Agent — Phase 3 📐

---

### #71: Database Diagnostic Script [D] 📐

**Purpose:** Pre-flight health check of all data stores. Must run before every major dev session.

**Trigger / Invocation:** CLI: `python scripts/diagnose_databases.py`. POST /system/diagnose. Auto-run on FastAPI startup.

**Task Tree:**

- 71.1 [D] PostgreSQL: connection check, row counts per table, missing tables check
- 71.2 [D] Neo4j: connection check, node counts by label, edge counts by type
- 71.3 [D] Vault: path accessible?, total .md file count, file count per directory, last git sync timestamp
- 71.4 [D] Report: console output + optional Telegram if issues found

**Data Contracts:** Output: `{timestamp, pg: {connected, tables: [{name, row_count, exists}], missing_tables}, neo4j: {connected, node_counts, edge_count}, vault: {accessible, file_count, per_dir, last_git_sync}, errors, status: 'healthy'|'degraded'|'critical'}`

**Status Logic:** healthy (all connected), degraded (1 store down), critical (2+ stores down)

**Dependencies:** All databases (PG, Neo4j), vault filesystem, Git

---

### #72: Vilix Evaluation — IGNORED ⬜

---

### #73: Locus "Wants" + Autonomous Goal Formation — IGNORED ⬜

---

### #74: Locus Builds and Operates the Life OS — IGNORED ⬜

---

### #75: Obsidian-Centric Interactions — DELETED (already accounted for) ❌

---

### #76: NotebookLM Integration [D] 📐

**Purpose:** Integrate Google's NotebookLM via `teng-lin/notebooklm-py` to generate audio briefs/summaries from vault content.

**Trigger / Invocation:** Morning brief generation. On-demand `/brief` Telegram command.

**Task Tree:**

- 76.1 [D] Install teng-lin/notebooklm-py as dependency
- 76.2 [D] Select content: recent vault notes (24h) or specific topic
- 76.3 [D] notebooklm.generate_audio(text, format='podcast') → .wav/.mp3
- 76.4 [D] Store in /vault/07-Morning-Briefs/audio/ → git commit
- 76.5 [D] Send audio via Telegram + save text transcript

**Scope:** Only briefs; no conversational NotebookLM querying

---

### #77: Excalidraw Canvas Skill — Already done (merged into #50) 📐

---

### #78: Dynamic MCP Integration [D] 📐 (Consolidates #114, #115, #116)

**Purpose:** Dynamically create/register MCP servers on demand; auto-detect other agent harnesses; clone/query remote repos via GitMCP; construct dependency maps via Graphify.

**Task Tree:**

- 78.1 [D] FastMCP server template — dynamic tool registration from skills_registry
- 78.2 [D] Inter-harness: scan ~/.config/ for .locus, .hermes directories → read session data/tasks/logs
- 78.3 [D] GitMCP: clone_repo(url), search(pattern), extract(path)
- 78.4 [D] Graphify: analyze(path) → dependency graph JSON
- 78.5 [D] All MCPs registered in skills_registry table

---

### #79: Standard Skills Library [D] 📐

**Purpose:** Pre-packaged core utilities, shell helpers, automation blueprints. Copy from Hermes.

**Task Tree:**

- 79.1 [D] Load Hermes std_lib SKILL.md patterns
- 79.2 [D] Port to locus_std_lib/ directory
- 79.3 [D] Register in skills_registry

---

### #80: Local-First Obsidian Storage — DELETED ❌

---

### #81: Stateless 24-Hour Session Logs [D] 📐
Build a python file that takes every message generated by the telegram bot or whatever other platform the user is interacting with Locus on, and then the user's messages and the AI generated messages, all get automatically logged into a CHAT_LOG.md file which will be present in the vault in realtime. Also, at the same time, all the chats also get logged into a PostgreSQL database.

---

### #82: First-Class Local Model Support [D] 📐

**Purpose:** Native config to specify local LLM endpoints (Ollama, LMStudio) alongside AI model.

**Task Tree:**

- 82.1 [D] Config schema: providers: [{name, base_url, api_key_optional, model_list}]
- 82.2 [D] OpenAI-compatible client wrapper — same interface as AI model, different base_url
- 82.3 [D] Fallback chain: Local → AI model if local unavailable
- 82.4 [D] Query Router (#57) routes based on intent + model capability

---

### #83: Automated LLM Capability Audit [D] 📐

**Purpose:** Benchmark configured LLMs against standard prompts to determine capability per task type. Integrate existing benchmark repo.

**Task Tree:**

- 83.1 [D] Integrate existing benchmark (lm-evaluation-harness or similar)
- 83.2 [D] Run validation prompts: factual, reasoning, code, creative
- 83.3 [D] Score: accuracy per category → PG llm_capability_scores
- 83.4 [D] Feed Query Router (#57) — route to best provider per task type

---

### #84: Single-Provider Invokable Council [M] 📐

**Purpose:** Spawn advisory board of 3 agents (Architect, Reviewer, Pragmatist) using same LLM to debate code/design decisions.

**Trigger / Invocation:** /council {question} — Telegram command.

**Task Tree:**

- 84.1 [D] Spawn 3 agents with distinct personas: Architect (design), Reviewer (bug-hunt), Pragmatist (tradeoffs)
- 84.2 [AI] Each agent responds independently — AI model with role-specific system prompt
- 84.3 [D] Collate responses → identify agreements/conflicts → Markdown report

---

### #85: Unified Social & Google Integrations [D] 📐

**Purpose:** Borrow account-linking patterns from OpenHuman for WhatsApp, Instagram, Google integrations.

**Task Tree:**

- 85.1 [D] OpenHuman schema analysis (interface only — EXTERNAL)
- 85.2 [D] OAuth flow pattern per platform
- 85.3 [D] Unified token storage: oauth_tokens extended with platform column

**Implementation priority:** Passive loggers first; active gateways Phase 2/3

---

### #86: Pi Agent Sub-Agents [D] 📐

**Purpose:** Spawn sub-agents as isolated subprocesses for scouts (fs), researchers (web), workers (code). Already accounted for.

**Task Tree:**

- 86.1 [D] subprocess.Popen with isolated Python environment
- 86.2 [D] Restricted tool subset per agent type: Scout (grep/read/glob), Researcher (webfetch/websearch), Worker (bash sandbox/code)
- 86.3 [D] TUI observability: indented logs with cost/tokens
- 86.4 [D] stdout capture → parent context

---

### #87-#123: Hermes Copy Features — [EXTERNAL ADAPTATION] 📐

**Common Pattern:**

```
├── 1. [D] Interface Definition — I/O contract between Locus and Hermes component
│   File: docs/hermes-{feature-name}-interface.md
├── 2. [D] Code Port — Copy Hermes source, adapt to Locus conventions
│   Steps: (a) Create elaborate doc, (b) implement, (c) debug
│   Note: Replace multi-provider with single AI model where applicable
├── 3. [D] Adapter Layer — thin wrapper matching Locus's internal signatures
└── 4. [D] Integration Test — verify inside Locus pipeline
```

| #   | Feature                                | Status | What it does                                                              | Locus integration point                                                   |
| --- | -------------------------------------- | ------ | ------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| 87  | Agent Loop                             | 📐     | Core execution loop with iteration budgets, grace turns, interrupt checks | Wraps Locus's query pipeline; replaces Hermes' context with Context Forge |
| 88  | Context Compression                    | 📐     | Auto-compress at token limit, /compress command, sandbox-aware saving     | Plugin into Context Forge (#58) when budget exceeded                      |
| 89  | Pluggable Context Engines              | 📐     | plugins/context_engine/ with compressor as default                        | Plugin directory for context strategies; default = Context Forge          |
| 90  | Provider / Model Plugin                | 📐     | 30+ providers, rotating credentials, fallback commands                    | Extended by#82; Locus keeps AI model primary, adds plugin routing         |
| 91  | Multiple Isolated Profiles             | 📐     | Multi-profile with memory isolation, worktree mode                        | Profile switching; each profile has own user_identity + vault path        |
| 92  | SQLite & FTS5 Session Store            | 📐     | Session persistence, FTS5 indexing, JSONL export                          | Runs alongside PG; keeps Hermes session branching                         |
| 93  | Self-Improvement Loop                  | 📐     | Background fork grades/improves skills                                    | Feeds into#32 (Self-Evolving); uses Reward Model for grading              |
| 94  | Autonomous Curator                     | 📐     | Background agent curates skill library by usage telemetry                 | Scans skills_registry for unused skills; archives low-usage               |
| 95  | Hermes CLI & Skin Engine               | 📐     | Shell chat interface, yolo mode, spinner, paste normalization             | Locus CLI interface; adapt for Locus-specific commands                    |
| 96  | Ink-React TUI                          | 📐     | React terminal UI with JSON-RPC gateway                                   | Optional — Telegram is primary UI                                        |
| 97  | CLI Subcommands                        | 📐     | config, doctor, setup, models, mcp, cron                                  | Thin wrappers around FastAPI endpoints                                    |
| 98  | In-Session Slash Commands              | 📐     | /commands routing in chat                                                 | Adapt to Telegram inline keyboard + text commands                         |
| 99  | Tool Registry & Sandboxing             | 📐     | Central registry, path sandboxing, output limits                          | Extends skills_registry with sandbox config                               |
| 100 | Built-In Core Tools                    | 📐     | search, terminal, files, patch, vision, speech, delegate, cron            | Maps to existing Locus endpoints; adds missing handlers                   |
| 101 | Smart Browser Automation               | 📐     | CDP Playwright with Camofox/Chromium                                      | Extends#27 (chat scraping) with general browser automation                |
| 102 | Code Execution Backends                | 📐     | Local/Docker/SSH/Modal sandboxed execution                                | Adds execution backends to Locus tool system                              |
| 103 | Skill MD Registry                      | 📐     | SKILL.md YAML-based with HTTP downloads, AST audits                       | Replaces/extends Locus skill loading                                      |
| 104 | Bundled & Optional Skills              | 📐     | Pre-loaded data science, diagrams, email, GitHub, productivity            | Standard library from#79                                                  |
| 105 | Scanned Hook Architecture              | 📐     | Startup directory scanning with lifecycle hooks                           | Hook points: pre_request, post_tool_call, on_startup, on_shutdown         |
| 106 | Memory & Model Providers Plugins       | 📐     | Honcho, mem0, holographic memory                                          | Optional — Locus tri-store is primary                                    |
| 107 | Standalone Plugins (Meet, Spotify)     | 📐     | Google Meet audio, Spotify PKCE, Teams transcripts                        | New plugin category: standalone service integrations                      |
| 108 | Achievements System                    | 📐     | Gamified session scanning with levels, share cards                        | Fun add-on; deterministic scan of telemetry                               |
| 109 | Multi-Platform Gateway                 | 📐     | 25 chat integrations with timeouts, dedup                                 | Extends Telegram bot (#43) into multi-platform                            |
| 110 | Platform Adapters (TG, Discord, Slack) | 📐     | Dedicated adapters per platform                                           | Phase 2; Telegram is primary                                              |
| 111 | Signal, Matrix & Enterprise            | 📐     | Signal E2EE, Matrix sync, Feishu cards                                    | Phase 3                                                                   |
| 112 | Voice Transcription & STT              | 📐     | faster-whisper, Groq/OpenAI STT                                           | Extends#35 (Audio Transcription)                                          |
| 113 | Provider Integration Inventory         | 📐     | OpenRouter, Nous, AI model, Google, Ollama                                | Extended by#82; standardized OpenAI-compatible wrappers                   |
| 114 | Memory System Scopes                   | 📐     | Session hooks, thread-scoping, memory registers                           | Feeds into Context Forge temporal scope (#58)                             |
| 115 | MCP Client                             | 📐     | Native MCP with PKCE OAuth, circuit breakers, OSV scanning                | Underlies#78 (Dynamic MCP)                                                |
| 116 | ACP Server                             | 📐     | Agent Communication Protocol for IDE integration                          | VS Code, Zed, JetBrains plugin support                                    |
| 117 | Cron Scheduler & Webhooks              | 📐     | CLI cron/NL schedules, override profiles, webhooks                        | Extends APScheduler with webhook targets                                  |
| 118 | Multi-Agent Work Queue                 | 📐     | SQLite durable task board, dispatcher daemon                              | Optional — Locus uses PG for task queue                                  |
| 119 | Subagentic Delegation                  | 📐     | Sync batch parallel delegation                                            | Extends#86 (Pi Sub-Agents) with orchestrated delegation                   |
| 120 | Security & Pairing Hardening           | 📐     | Smart approval, PII redaction, pairing tokens                             | Adds to#46-48 security stack                                              |
| 121 | Langfuse Observatory                   | 📐     | API/LLM request telemetry hooks                                           | Optional middleware                                                       |
| 122 | Special Capabilities                   | 📐     | V4A patches, LSP workspace, terminal checkpoints, Bitwarden               | Standalone tool integrations                                              |
| 123 | Cross-Device & Hybrid Execution        | 📐     | Remote VM + local tools sync                                              | SQLite replication; Locus already runs on VM                              |

---

### #124: Admin Dashboard [D] 📐

**Purpose:** System health monitoring — container status, PG row counts, error rates, API latency, cron health.

**Task Tree:**

- 126.1 [D] FastAPI admin routes + basic web UI
- 126.2 [D] Read-only first; add controls in Phase 2
- 126.3 [D] Auth-guarded via admin_token in .env

---

### #125: Dev Branch / Staging [D] 📐

**Purpose:** develop branch → dev.locusapp.online for safe testing.

**Task Tree:**

- 127.1 [D] Git: main + develop branches
- 127.2 [D] Docker Compose override for staging env vars
- 127.3 [D] Cloudflare subdomain: dev.locusapp.online

---

### #1269: Daily Research / News Digest [AI] 📐

**Purpose:** Curated digest relevant to active goals/projects.

**Trigger / Invocation:** APScheduler 07:30 IST.

**Task Tree:**

- 129.1 [D] Collect active outcomes/projects → extract keywords
- 129.2 [AI] AI model generates 3-5 search queries
- 129.3 [D] websearch per query → collect top results
- 129.4 [AI] AI model summarizes top 5 items with source links
- 129.5 [D] Write to /vault/07-Morning-Briefs/digest-YYYY-MM-DD.md → Telegram summary

**Dependencies:** #5 (Goal Stack), websearch

---

### #127: Scheduled Voice Calls for Debriefing [M — Phase 2] 📐

**Purpose:** Locus initiates voice calls for audio journaling/brainstorming at scheduled times.

**Task Tree:**

- 130.1 [D] APScheduler configurable triggers
- 130.2 [External] Outbound call via Twilio Voice API or Telegram
- 130.3 [AI] AI model guides conversation flow
- 130.4 [D] Groq Whisper STT → transcript to vault
- 130.5 [D] Fallback: Telegram text version if voice unavailable

**Dependencies:** #45 (Voice Call Interface — Phase 3 disables this until then)

---

### #129: Multi-Dimensional Habit Graph [H] 📐

**Purpose:** Graph tasks vs energy vs time-of-day vs device to find peak productivity windows.

**Task Tree:**

- 131.1 [D] Data collection (60 days min): device, time_of_day, energy_at_start, task_difficulty, completion_quality, duration_vs_estimate
- 131.2 [D] After 60d: per faction, find (time_of_day, energy_range) with highest quality → peak window
- 131.3 [D] Feed scheduler: schedule heavy tasks to peak windows
- 131.4 [D] JSON to vault → Obsidian Charts heatmap

**Dependencies:** #7 (Events), #6 (Stats), #132 (Task Quality Score)

---

### #130: Task Quality Score [D] 📐

**Purpose:** Post-completion quality audit (1-10) per task. Low quality + high TWS = alert.

**Task Tree:**

- 132.1 [D] Telegram inline keyboard: "Quality of completion? 1-10"
- 132.2 [D] task_completions: quality_score, time_taken_vs_estimated, notes
- 132.3 [D] Weekly avg per faction
- 132.4 [D] IF quality < 5 AND TWS > 7 → Telegram alert

**Dependencies:** #4 (TWS)

---

### #131: Instagram Integration [Phase 3] 📐

**Purpose:** Import DMs, saved posts, activity. Playwright scraping or Graph API.

---


## Quick Dependency Graph

> **Atomic precision.** Every arrow = a direct dependency. Every feature here exists in the FRESH BUILD section above.
> Organised by the architecture pyramid: Infrastructure → Storage → Ingestion → Retrieval → Intelligence → Orchestration → Scheduling → Interface → Feedback → Self-Maintenance.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      INFRASTRUCTURE                                              │
│                                                                                                  │
│  #19 Oracle VM ─────────────────────────► #20 Docker Stack ──────► #23 FastAPI Backend            │
│      │                                       │   ▲  ▲  ▲             │   ▲                       │
│      │                                       │   │  │  │             │   │                       │
│      └──► #21 Cloudflare Tunnel ────────────►┘   │  │  │             │   │                       │
│      └──► #46 VM Hardening                        │  │  │             │   │                       │
│                                                    │  │  │             │   │                       │
│  #20 Docker Stack provisions:                      │  │  │             │   │                       │
│    • PostgreSQL 16 ────────────────────────────────┘  │  │             │   │                       │
│    • Neo4j 5.x ───────────────────────────────────────┘  │             │   │                       │
│    • Redis 7.x (optional cache) ─────────────────────────┘             │   │                       │
│                                                                         │   │                       │
│  #22 Vault Sync (Git) ──────────────────────────► Vault filesystem      │   │                       │
│  #25 Local DB Mirror ───────────────────────────► (offline backup)      │   │                       │
│                                                                         │   │                       │
└─────────────────────────────────────────────────────────────────────────┼───┼───────────────────────┘
                                                                          │   │
┌─────────────────────────────────────────────────────────────────────────┼───┼───────────────────────┐
│                                      INGESTION                          │   │                       │
│                                                                         │   │                       │
│  #27 Nightly Vault Ingestion ──────────────────► scans vault filesystem │   │                       │
│      │   • git diff → changed .md files          (via #22)              │   │                       │
│      │   • Playwright → external AI chat scraping                       │   │                       │
│      │   • MinerU → PDF/non-text processing                             │   │                       │
│      │                                                                  │   │                       │
│      ├──► #26 PageIndex ────────────────────────► tree structure JSONs  │   │                       │
│      ├──► #34 3-Level Tag Hierarchy ────────────► tags table (PG)       │   │                       │
│      ├──► #35 Audio Transcription ──────────────► .md → vault           │   │                       │
│      ├──► #49 Thinking Pattern Capture ─────────► detected_patterns     │   │                       │
│      └──► #76 NotebookLM Integration ───────────► notebook queries      │   │                       │
│                                                                         │   │                       │
│  #39 Check-ins ─────────────────────────────────► behavioral_events     │   │                       │
│  #43 Telegram Bot (ALL messages) ────► #51 Logger ► behavioral_events   │   │                       │
│                                                                         │   │                       │
└─────────────────────────────────────────────────────────────────────────┼───┼───────────────────────┘
                                                                          │   │
┌─────────────────────────────────────────────────────────────────────────┼───┼───────────────────────┐
│                                        DATA HUB (#7)                    │   │                       │
│                                                                         │   │                       │
│  ┌────────────────────── #7 BEHAVIORAL EVENT STREAM ────────────────────┐│   │                       │
│  │  Every endpoint emits. PG LISTEN/NOTIFY triggers downstream.         ││   │                       │
│  │  Single source of chronological truth.                               ││   │                       │
│  └──────────────────────────────────────────────────────────────────────┘│   │                       │
│      │                                                                   │   │                       │
│      │   (metric definitions from #1 Factions, #2 DCS, #4 TWS, #5 Goals)│   │                       │
│      │                                                                   │   │                       │
│      ├──► #6 Weekly Stats ────────────────────────► faction_weekly_stats │   │                       │
│      │       ├──► #11 Lag Score + TWS Bonus ──────► #14 Rebalance        │   │                       │
│      │       └──► #15 Momentum Score ─────────────► #14 Rebalance        │   │                       │
│      │                                                                   │   │                       │
│      ├──► #8 Action Gap ─────────────────────────► declared vs actual    │   │                       │
│      ├──► #9 Deferral Detection ─────────────────► 3/5/8+ rule           │   │                       │
│      ├──► #10 Dead Node Detection ───────────────► 60d untouched alert   │   │                       │
│      ├──► #13 Exhaustion Predictor ──────────────► burnout prevention    │   │                       │
│      │                                                                   │   │                       │
│      └──► #130 Task Quality Score ───────────────► task_completions      │   │                       │
│                                                                          │   │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      RETRIEVAL LAYER                     │  │                       │
│                                                                          │  │                       │
│  #26 PageIndex + Direct Retrieval ─────────────────┐                     │  │                       │
│      │   • Markdown headers → tree structure index  │                     │  │                       │
│      │   • LLM tree-search → get_page_content()     │                     │  │                       │
│      │   • DeepSeek entity extraction → Neo4j       │                     │  │                       │
│      │   • Depends: #22 (vault path), #27 (trigger) │                     │  │                       │
│      │                                              ▼                     │  │                       │
│      └──► pageindex_workspace/ (JSON trees) + Neo4j entities             │  │                       │
│                                                                          │  │                       │
│  #53 Obsidian MCP ────────────────────────────────► vault tools           │  │                       │
│      │   • vault_read, vault_write (append-only)                         │  │                       │
│      │   • vault_search (grep), vault_tag, vault_stats                   │  │                       │
│      └──► Depends: #22 (vault path)                                      │  │                       │
│                                                                          │  │                       │
│  #54 Universal MCP Server ────────────────────────► exposes ALL tools     │  │                       │
│      └──► Depends: #23 (FastAPI), #53, #26, #52                          │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      INTELLIGENCE PIPELINE               │  │                       │
│                                                                          │  │                       │
│  ┌─ #60 State Engine ◄── #7 Behavioral Events (PG LISTEN/NOTIFY) ──────┐│  │                       │
│  │      │  • Maintains CURRENT_STATE in PG (single-row, TTL 6h)         ││  │                       │
│  │      │  • psychological: mood_trend, stress, energy                  ││  │                       │
│  │      │  • operational: momentum, deferral_rate, last_meaningful_work ││  │                       │
│  │      │  • contextual: exam_period, sleep_quality, time_of_day        ││  │                       │
│  │      │  • behavioral_alerts: avoidance, momentum_loss, deadline_risk ││  │                       │
│  │      │                                                               ││  │                       │
│  │      ├──► #68 Cause Chain Engine ───────────────► cause_chains (PG)  ││  │                       │
│  │      │       • Cross-refs state + patterns + identity                ││  │                       │
│  │      │       • Plain-text explanation citing specific data           ││  │                       │
│  │      │       • Depends: #60, #62, #49                               ││  │                       │
│  │      │                                                               ││  │                       │
│  │      ├──► #58 Context Forge (temporal_context layer, 60t) ──────────►││  │                       │
│  │      ├──► #59 Inner Loop (CURRENT_STATE read) ──────────────────────►││  │                       │
│  │      └──► #39 Push Notifications (alerts)                            ││  │                       │
│  └──────────────────────────────────────────────────────────────────────┘│  │                       │
│                                                                          │  │                       │
│  #62 User Identity ◄── #29 Personality Profile ─────► user_identity (PG) │  │                       │
│      │  • Single-row, rolling-average updates                           │  │                       │
│      │  • known_behavioral_tendencies, peak_windows, communication_style│  │                       │
│      │  • Depends: #28 (weekly synthesis), #49 (thinking patterns)      │  │                       │
│      │                                                                  │  │                       │
│      └──► #58 Context Forge (user_identity layer, 80t)                  │  │                       │
│                                                                          │  │                       │
│  #49 Thinking Pattern Capture ───────────────► ConceptNodes (Neo4j)      │  │                       │
│      └──► #29 Personality Profile (#62)                                  │  │                       │
│                                                                          │  │                       │
│  #129 Multi-Dimensional Habit Graph ──────────► peak windows              │  │                       │
│      │  • task vs energy vs time-of-day vs device                       │  │                       │
│      │  • Depends: #7 (events), #6 (stats), #130 (quality)              │  │                       │
│      └──► feeds Scheduler (optimal time blocks)                          │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      ORCHESTRATION (Tier 1)              │  │                       │
│                                                                          │  │                       │
│  ┌─ #57 Query Router ◄── #43 Telegram (every message, ~50 tokens) ─────┐│  │                       │
│  │      │  • 8 intents: FACTUAL_PERSONAL, BEHAVIORAL_PATTERN,           ││  │                       │
│  │      │    KNOWLEDGE_RETRIEVAL, TASK_PLANNING, EMOTIONAL_STATE,        ││  │                       │
│  │      │    EXTERNAL_KNOWLEDGE, SYNTHESIS, INFERENCE_REQUEST            ││  │                       │
│  │      │  • confidence < 0.7 → ALL sources                             ││  │                       │
│  │      │  • Depends: #48 (prompt injection filter first)               ││  │                       │
│  │      │                                                               ││  │                       │
│  │      ├──► #58 Context Forge (source list, temporal scope)            ││  │                       │
│  │      ├──► #59 Inner Loop (intent routing)                            ││  │                       │
│  │      ├──► #68 Cause Chain (INFERENCE_REQUEST intent)                 ││  │                       │
│  │      ├──► #52 Skill/MCP Toolkit (skill routing)                      ││  │                       │
│  │      └──► #83 LLM Capability Audit (monitoring)                      ││  │                       │
│  └──────────────────────────────────────────────────────────────────────┘│  │                       │
│                                                                          │  │                       │
│  ┌─ #58 Context Forge (800-token assembler) ───────────────────────────┐ │  │                       │
│  │      │  • 5 layers with hard token budgets:                          │ │  │                       │
│  │      │    user_identity:      80t ← #62                             │ │  │                       │
│  │      │    temporal_context:   60t ← #60                             │ │  │                       │
│  │      │    pg_events:         180t ← #7 (compressed)                 │ │  │                       │
│  │      │    neo4j_pathways:    150t ← #64 (top Hebbian paths)         │ │  │                       │
│  │      │    pageindex_content: 300t ← #26 (tree search results)       │ │  │                       │
│  │      │    web_results:       100t ← only if EXTERNAL_KNOWLEDGE      │ │  │                       │
│  │      │    buffer:             30t                                   │ │  │                       │
│  │      │                                                               │ │  │                       │
│  │      ├──► Truncate by relevance score, NOT recency                   │ │  │                       │
│  │      ├──► Every Neo4j traversal → #64 Hebbian +0.1                   │ │  │                       │
│  │      ├──► All sources empty → inject "No personal data found"       │ │  │                       │
│  │      │                                                               │ │  │                       │
│  │      ├──► #43 Telegram Bot (assembled context → LLM → response)      │ │  │                       │
│  │      ├──► #28 Weekly Synthesis (Sunday deep analysis)                │ │  │                       │
│  │      └──► #59 Inner Loop (observation context)                       │ │  │                       │
│  │                                                                      │ │  │                       │
│  │  Depends: #57 (source list), #26 (pageindex), #60 (state), #62 (id),│ │  │                       │
│  │           #7 (events), #64 (hebbian), web_search (for web_results)   │ │  │                       │
│  └──────────────────────────────────────────────────────────────────────┘ │  │                       │
│                                                                          │  │                       │
│  ┌─ #59 Inner Loop (proactive thinker, every 90min + 03:00 deep) ─────┐ │  │                       │
│  │      │  • "You are NOT talking to Shivam. You are thinking about     │ │  │                       │
│  │      │    Shivam." Generates 0-2 evidence-based observations.        │ │  │                       │
│  │      │                                                               │ │  │                       │
│  │      │  Data sources:                                                │ │  │                       │
│  │      │    ├── #60 State Engine → CURRENT_STATE                       │ │  │                       │
│  │      │    ├── #7 Behavioral Events → recent events (6h/48h)          │ │  │                       │
│  │      │    ├── #64 Hebbian → top pathways for current time-of-day     │ │  │                       │
│  │      │    └── #28 Weekly Synthesis → previous week's narrative        │ │  │                       │
│  │      │                                                               │ │  │                       │
│  │      │  Gates applied:                                               │ │  │                       │
│  │      │    1. #63 Reward Model → score ≥ 0.6 to surface               │ │  │                       │
│  │      │    2. Neo4j dedup → title+entity overlap > 0.85 = suppress   │ │  │                       │
│  │      │                                                               │ │  │                       │
│  │      │  Routing:                                                     │ │  │                       │
│  │      │    ├── HIGH → #43 Telegram now                                │ │  │                       │
│  │      │    ├── MEDIUM → #39 morning brief queue                       │ │  │                       │
│  │      │    ├── PATTERN → #49 Thinking Patterns (if confidence > 0.85) │ │  │                       │
│  │      │    └── DISCARD → silent                                        │ │  │                       │
│  │      │                                                               │ │  │                       │
│  │      │  Depends: #60, #7, #64, #63, #28                             │ │  │                       │
│  │      └──► #43 Telegram (proactive messages)                          │ │  │                       │
│  └──────────────────────────────────────────────────────────────────────┘ │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      SCHEDULING (Core Value)             │  │                       │
│                                                                          │  │                       │
│  ┌─ #1 Four Factions Framework ───────────────────────────────────────┐ │  │                       │
│  │      │  Health/Stability, Leverage/Money, Craft/Skills, Expression  │ │  │                       │
│  │      │  Crisis hierarchy + target allocations (25/25/30/20%)        │ │  │                       │
│  │      │  Non-negotiables per faction defined                         │ │  │                       │
│  │      │                                                              │ │  │                       │
│  │      ├──► #5 Goal Stack ───────────────────► Outcomes→Projects→Tasks│ │  │                       │
│  │      │       ├──► #37 Idea Tracker                                    │ │  │                       │
│  │      │       ├──► #130 Task Quality Score                             │ │  │                       │
│  │      │       └──► #18 Review Cadence                                  │ │  │                       │
│  │      │                                                              │ │  │                       │
│  │      ├──► #2 DCS ──────────────────────────► Daily Capacity Score    │ │  │                       │
│  │      │       │  E + M + S / 3 × (1 − ST/20)                         │ │  │                       │
│  │      │       │                                                       │ │  │                       │
│  │      │       ├──► #3 Five Operating Modes ─► SURVIVAL / RECOVERY /   │ │  │                       │
│  │      │       │      NORMAL / DEEP_WORK / PEAK                        │ │  │                       │
│  │      │       │      • Mode dictates task difficulty ceiling           │ │  │                       │
│  │      │       │      • Feeds ALL scheduling decisions                  │ │  │                       │
│  │      │       │                                                       │ │  │                       │
│  │      │       ├──► #13 Exhaustion Predictor                           │ │  │                       │
│  │      │       ├──► #60 State Engine                                   │ │  │                       │
│  │      │       └──► #39 Check-ins (morning DCS capture)                │ │  │                       │
│  │      │                                                              │ │  │                       │
│  │      ├──► #4 TWS ──────────────────────────► Task Weight Score       │ │  │                       │
│  │      │       │  (P×0.4)+(U×0.4)+(D×0.2)                             │ │  │                       │
│  │      │       │                                                       │ │  │                       │
│  │      │       ├──► #11 Lag Bonus (LS>3h→+2, LS>6h→+4)                │ │  │                       │
│  │      │       ├──► #12 Emergency Injection                            │ │  │                       │
│  │      │       ├──► #16 Parallel Task Execution                        │ │  │                       │
│  │      │       └──► #130 Task Quality Score                            │ │  │                       │
│  │      │                                                              │ │  │                       │
│  │      ├──► #6 Weekly Stats                                            │ │  │                       │
│  │      │       ├──► #11 Lag Score + TWS Bonus                          │ │  │                       │
│  │      │       ├──► #14 Weekly Faction Rebalance                       │ │  │                       │
│  │      │       │       └──► #42 Google Calendar (writes schedule)      │ │  │                       │
│  │      │       └──► #15 Momentum Score                                 │ │  │                       │
│  │      │                                                              │ │  │                       │
│  │      ├──► #17 Three-Birds-One-Stone ────────► cross-faction mapping  │ │  │                       │
│  │      └──► #129 Multi-Dimensional Habit Graph ─► peak windows         │ │  │                       │
│  └──────────────────────────────────────────────────────────────────────┘ │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      INTERFACE LAYER                     │  │                       │
│                                                                          │  │                       │
│  #43 Telegram Bot (PRIMARY) ◄── ALL user interaction ───────────────────┐│  │                       │
│      │  • Every message: #48 (security) → #57 (classify) → #58 (forge)  ││  │                       │
│      │  • 👍/👎 inline keyboard → #63 Reward Model                       ││  │                       │
│      │  • /debug, /checkin, /dcs, /tasks, /schedule, /goals, etc.       ││  │                       │
│      │  • Depends: #23 (FastAPI), #21 (Cloudflare), #51 (logger)        ││  │                       │
│      └──────────────────────────────────────────────────────────────────┘│  │                       │
│                                                                          │  │                       │
│  #36 Obsidian Dashboard ─────────────────────────► Dataview + Charts     │  │                       │
│      │  • Panels: DCS, faction health, active tasks, patterns, state    │  │                       │
│      │  • Depends: #22 (vault path as source)                           │  │                       │
│      └──► reads vault data directly via Dataview                         │  │                       │
│                                                                          │  │                       │
│  #39 Check-ins + Push Notifications ────────────► structured touchpoints │  │                       │
│      │  • Morning/Afternoon/Evening/Night                                │  │                       │
│      │  • Depends: #43 (Telegram delivery), #2 (DCS), #3 (mode)         │  │                       │
│      └──► #7 Behavioral Events (emits check-in events)                   │  │                       │
│                                                                          │  │                       │
│  #42 Google Calendar ───────────────────────────► two-way sync           │  │                       │
│      │  • Reads: existing events → Scheduler constraints                │  │                       │
│      │  • Writes: scheduled tasks → calendar events                     │  │                       │
│      │  • Depends: #14 (rebalance output), #12 (emergency injection)    │  │                       │
│      └──► OAuth2 + Calendly webhook                                      │  │                       │
│                                                                          │  │                       │
│  #45 Voice Call Interface [Phase 3] ────────────► Twilio/WebRTC          │  │                       │
│  #127 Scheduled Voice Calls [Phase 2]           ► proactive debriefs     │  │                       │
│  #44 Gmail Integration [Phase 2]                ► email context          │  │                       │
│  #131 Instagram Integration [Phase 3]           ► content publishing     │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      FEEDBACK + LEARNING                 │  │                       │
│                                                                          │  │                       │
│  ┌─ #63 Reward Model (sklearn LogisticRegression) ─────────────────────┐ │  │                       │
│  │      │  • 👍/👎 from #43 (every Telegram response)                   │ │  │                       │
│  │      │  • Retrained weekly Sunday 04:00 IST                          │ │  │                       │
│  │      │                                                               │ │  │                       │
│  │      ├──► #59 Inner Loop (observation gate, score ≥ 0.6)            │ │  │                       │
│  │      └──► #32 Self-Evolving Architecture                             │ │  │                       │
│  └──────────────────────────────────────────────────────────────────────┘ │  │                       │
│                                                                          │  │                       │
│  ┌─ #64 Hebbian Memory System ────────────────────────────────────────┐  │  │                       │
│  │      │  Neo4j edge weights:                                          │  │                       │
│  │      │    • +0.1 per traversal (via #58 Context Forge)               │  │                       │
│  │      │    • ×1.3 on 👍 (via #63); ×0.7 on 👎                         │  │                       │
│  │      │    • ×0.95 weekly decay (Sunday 03:30 IST)                    │  │                       │
│  │      │    • ×0.5 on project completion/inactive                      │  │                       │
│  │      │                                                               │  │                       │
│  │      ├──► #58 Context Forge (neo4j_pathways layer, 150t)            │  │                       │
│  │      ├──► #59 Inner Loop (time-of-day pathway lookup)                │  │                       │
│  │      └──► #28 Weekly Synthesis                                       │  │                       │
│  │                                                                      │  │                       │
│  │      Depends: #58 (traversal events), #63 (feedback signals)         │  │                       │
│  └──────────────────────────────────────────────────────────────────────┘  │  │                       │
│                                                                          │  │                       │
│  #30 Fine-Tuning / RLHF [Phase 3] ──────────► data collection only now   │  │                       │
│      │  • Collect #63 reward_signals → export JSONL instruction pairs    │  │                       │
│      │  • Quarterly: rent GPU → Unsloth QLoRA → LoRA adapter             │  │                       │
│      │  • Depends: #63 (needs 500+ labelled examples first)             │  │                       │
│      └──► Personalized model for CONVERSATIONAL intent (future)          │  │                       │
│                                                                          │  │                       │
│  #32 Self-Evolving Architecture ───────────────► Architect Bot            │  │                       │
│      │  • Auto-generates code patches for underperforming components     │  │                       │
│      │  • Depends: #63 (reward signals per intent), #59 (inner loop log)│  │                       │
│      └──► LOW risk: auto-deploy; HIGH risk: Telegram approval request    │  │                       │
│                                                                          │  │                       │
│  #84 Single-Provider Council ──────────────────► multi-model deliberation │  │                       │
│      └──► Depends: #82 (Local Model Support)                             │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      REVIEW + SYNTHESIS                  │  │                       │
│                                                                          │  │                       │
│  #18 Review Cadence ────────────────────────────► daily/weekly/monthly   │  │                       │
│      │  • Daily: E/M/S/ST log, task completions (A, Q), deferrals       │  │                       │
│      │  • Weekly: faction hours, lag scores, CR/CS, action gaps          │  │                       │
│      │  • Monthly: faction balance audit, outcome progress              │  │                       │
│      │  • Quarterly: outcome truth check, faction rebalancing           │  │                       │
│      │                                                                  │  │                       │
│      ├──► #28 Weekly Full Vault Synthesis ──────► DeepSeek (Sunday 02:00)│ │                       │
│      │       • Personality drift report                                  │  │                       │
│      │       • Faction narrative                                        │  │                       │
│      │       • Top 3 observations (~3000 tokens)                        │  │                       │
│      │       • Depends: #7, #6, #64, #60, #62                          │  │                       │
│      │       • Output: weekly_reviews table + vault .md                 │  │                       │
│      │                                                                  │  │                       │
│      ├──► #29 Personality Profile ───────────────► #62 User Identity     │  │                       │
│      │       • Auto-builds from chats + behavioral graph                │  │                       │
│      │       • Rolling updates when patterns confirmed                  │  │                       │
│      │       • Depends: #7, #49, #28                                   │  │                       │
│      │                                                                  │  │                       │
│      └──► #1269 Daily Research Digest ─────────► morning briefs (07:30)  │  │                       │
│              • Extracts keywords from active goals/projects             │  │                       │
│              • AI search → top 5 items → vault + Telegram summary       │  │                       │
│              • Depends: #5 (Goal Stack), web_search                     │  │                       │
│                                                                          │  │                       │
│  #37 Idea Tracker ──────────────────────────────► rough note → promote   │  │                       │
│  #38 Link Dump ─────────────────────────────────► captures → vault       │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      SELF-MAINTENANCE + SECURITY         │  │                       │
│                                                                          │  │                       │
│  #24 Self-Maintenance System ───────────────────► auto-update deps        │  │                       │
│      │  • If post-update tests fail → P1 fix task + Telegram alert      │  │                       │
│      └──► Depends: #23 (FastAPI health checks)                          │  │                       │
│                                                                          │  │                       │
│  #71 Database Diagnostic ───────────────────────► pre-flight health check │  │                       │
│      │  • PG: connection, row counts, missing tables                    │  │                       │
│      │  • Neo4j: connection, node/edge counts                           │  │                       │
│      │  • Vault: accessible?, file count, last git sync                 │  │                       │
│      │  • Status: healthy / degraded / critical                         │  │                       │
│      └──► Run before EVERY major dev session                            │  │                       │
│                                                                          │  │                       │
│  #48 Prompt Injection Protection ───────────────► #43 (pre-filter)       │  │                       │
│      │  • Regex: sudo, exec, curl pipe patterns                         │  │                       │
│      │  • Blocklist: known adversarial prefixes                         │  │                       │
│      │  • Depends: #46 (VM hardened baseline)                           │  │                       │
│      └──► Must run BEFORE #57 Query Router                              │  │                       │
│                                                                          │  │                       │
│  #47 Security Testing ─────────────────────────► OWASP top 10 audit      │  │                       │
│  #124 Admin Dashboard ──────────────────────────► system health web UI   │  │                       │
│  #125 Dev Branch / Staging ─────────────────────► dev.locusapp.online    │  │                       │
│  #69 Migration from Hermes/OpenClaw ────────────► cleanup legacy code     │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      TOOLS + INTEGRATIONS                │  │                       │
│                                                                          │  │                       │
│  #34 3-Level Tag Hierarchy ─────────────────────► faction/domain/specific│  │                       │
│  #50 Excalidraw MCP [Phase 3] ──────────────────► diagram generation     │  │                       │
│  #52 Skill/MCP Toolkit ─────────────────────────► skill registry + MCP   │  │                       │
│  #78 Dynamic MCP ───────────────────────────────► auto-tool registration │  │                       │
│  #79 Standard Skills Library ───────────────────► bundled skills         │  │                       │
│  #81 Stateless Session Logs ────────────────────► 24h session tracking   │  │                       │
│  #82 Local Model Support ───────────────────────► Ollama/vLLM integration │  │                       │
│  #83 LLM Capability Audit ──────────────────────► provider benchmarking  │  │                       │
│  #85 Unified Social/Google ─────────────────────► consolidated OAuth     │  │                       │
│  #86 Pi Sub-Agents ─────────────────────────────► parallel task agents   │  │                       │
│  #31 Subagentic Capabilities [Phase 3] ─────────► specialist sub-agents  │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
                                                                           │  │
┌──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┐
│                                      EXTERNAL ADAPTATION (#87-123)       │  │                       │
│                                                                          │  │                       │
│  #87-#123 Hermes Copy Features ─────────────────► adapt to Locus          │  │                       │
│      │  • Agent Loop, Context Compression, Profiles                     │  │                       │
│      │  • Session Store, Self-Improvement Loop, Curator                 │  │                       │
│      │  • CLI/TUI, Slash Commands, Tool Registry + Sandbox              │  │                       │
│      │  • Browser Automation, Code Execution Backends                   │  │                       │
│      │  • Skill MD Registry, Bundled Skills, Hook Architecture          │  │                       │
│      │  • Platform Adapters (TG, Discord, Slack), Multi-Platform Gateway│  │                       │
│      │  • Voice STT, Provider Inventory, Memory System Scopes          │  │                       │
│      │  • MCP Client, ACP Server, Cron/Webhooks, Multi-Agent Queue     │  │                       │
│      │  • Subagentic Delegation, Security Hardening, Langfuse Obs       │  │                       │
│      └──► Interface contract per feature → code port → adapter → test   │  │                       │
│                                                                          │  │                       │
└──────────────────────────────────────────────────────────────────────────┼──┼───────────────────────┘
```

---

> **End of decomposition.** All 136 features broken to atomic gear depth with task trees, data contracts, dependencies, and failure modes. Ready for implementation phase ordering.
