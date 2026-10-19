# Complete Feature Matrix — Pi · Hermes · OpenHuman · Locus OS

> **Legend**
> - ✅ = Implemented in code
> - 📐 = Designed / documented, not yet in code
> - 🔧 = Partial / basic implementation
> - ⬜ = Not present
> - ❌ = Deliberately rejected by design

---

## 1. Agent Core / Runtime

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Main agent loop** | ✅ Two-entry (tooled + simple) | ✅ Conversation loop + background review | ✅ Unified turn engine, 5 seams, 3 dispatchers | ✅ ToolRegistry + LlmProvider |
| **Turn context management** | ✅ Harness state machine | ✅ `turn_context.py` per-turn state | ✅ Fork/memory/sandbox/worktree contexts | 🔧 Basic request/response |
| **Turn retry / error recovery** | ✅ Retry in agent loop | ✅ `turn_retry_state.py` | ✅ Self-healing (ToolMaker polyfill, circuit breakers) | ⬜ |
| **System prompt builder** | ✅ Dynamic assembly + skills injection | ✅ `system_prompt.py` + `prompt_builder.py` | ✅ Built into turn engine | 🔧 Static system prompt |
| **Prompt caching** | ✅ `openai-prompt-cache.ts` | ✅ `prompt_caching.py` | ⬜ | ⬜ |
| **Iteration budget / limits** | ⬜ | ✅ `iteration_budget.py` | ✅ `token_budget` | ⬜ |
| **Background review / post-turn** | ⬜ | ✅ `background_review.py` | ✅ Post-turn hooks (4 types) | 📐 Inner Loop (not post-turn, proactive) |
| **Stream diagnostics** | ✅ Event stream utilities | ✅ `stream_diag.py` | ⬜ | ⬜ |
| **Rate limit tracking** | ⬜ | ✅ `rate_limit_tracker.py` | ✅ Health probes (30s TTL) | ⬜ |
| **Usage / cost tracking** | ⬜ | ✅ `usage_pricing.py` + `credits_tracker.py` + `account_usage.py` | ✅ `cost`, `tokenjuice` modules | ⬜ |
| **Title generation** | ⬜ | ✅ `title_generator.py` | ⬜ | ⬜ |
| **Onboarding flow** | ✅ Project trust prompt | ✅ `onboarding.py` | ⬜ | ✅ CLI setup wizard + 📐 in-chat setup wizard |
| **Agent initialization** | ✅ `agent-harness.ts` | ✅ `agent_init.py` | ✅ `app_state`, `startup` | ✅ `core/agent.py` |

---

## 2. LLM Providers

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Provider count** | ✅ 10+ APIs, 36+ models | ✅ 15+ providers | ✅ 5 provider types | ✅ 1 (DeepSeek V4 Flash — intentional) |
| **OpenAI / OpenAI-compatible** | ✅ Responses + Completions + Codex | ✅ Generic adapter | ✅ `OpenAiCompatible` (BYOK) | ✅ via httpx |
| **Anthropic** | ✅ `anthropic.ts` | ✅ `anthropic_adapter.py` | ✅ `ClaudeAgentSdk` (subprocess) | ⬜ |
| **Google Gemini** | ✅ `google.ts` + `google-vertex.ts` | ✅ `gemini_native_adapter.py` + `gemini_cloudcode_adapter.py` + `google_code_assist.py` | ⬜ | ⬜ |
| **AWS Bedrock** | ✅ `amazon-bedrock.ts` | ✅ `bedrock_adapter.py` | ⬜ | ⬜ |
| **Azure OpenAI** | ✅ `azure-openai-responses.ts` | ✅ `azure_identity_adapter.py` | ⬜ | ⬜ |
| **Cloudflare** | ✅ `cloudflare.ts` | ⬜ | ⬜ | ⬜ |
| **Mistral** | ✅ `mistral.ts` | ⬜ | ⬜ | ⬜ |
| **Moonshot / Kimi** | ⬜ | ✅ `moonshot_schema.py` | ⬜ | ⬜ |
| **LM Studio (local)** | ⬜ | ✅ `lmstudio_reasoning.py` | ⬜ | ⬜ |
| **GitHub Copilot** | ✅ `github-copilot-headers.ts` | ⬜ | ⬜ | ⬜ |
| **Intelligent routing (auto-select)** | ⬜ | ⬜ | ✅ `IntelligentRouting` (local+cloud fallback) | ❌ Single-provider by design |
| **Refusal detection** | ⬜ | ⬜ | ✅ Aho-Corasick DFA | ⬜ |
| **Provider registry** | ✅ `api-registry.ts` + auto-register | ✅ `model_metadata.py` | ✅ `RouterProvider` (hint-based) | 🔧 `resolve_provider()` |
| **OAuth (device code, PKCE)** | ✅ `oauth.ts` | ⬜ | ⬜ | ⬜ |
| **Model list/discovery** | ✅ `--list-models` flag | ✅ `model_metadata.py` | ⬜ | ⬜ |
| **Image generation providers** | ✅ `images.ts` + registry | ⬜ | ⬜ | ⬜ |
| **Mock / test provider** | ✅ `faux.ts` | ⬜ | ⬜ | ⬜ |
| **Streaming (SSE)** | ✅ `stream.ts` + event stream | ✅ `stream_consumer.py` + `stream_dispatch.py` | ⬜ | ⬜ |

---

## 3. Tools / Tool Execution

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **File read** | ✅ `read.ts` | ✅ (built-in) | ✅ (native dispatcher) | ✅ `read` |
| **File write / create** | ✅ `write.ts` | ✅ (built-in) | ✅ (native dispatcher) | ✅ `write` |
| **File edit (precise)** | ✅ `edit.ts` + `edit-diff.ts` | ✅ (built-in) | ✅ (native dispatcher) | ✅ `edit` + `edit_file` |
| **Shell / bash execution** | ✅ `bash.ts` | ✅ (built-in) | ✅ (sandboxed, 4 backends) | ✅ `run_shell` (blocklist sandbox) |
| **Grep / search files** | ✅ `grep.ts` | ✅ (built-in) | ✅ (native) | ⬜ (uses web_search) |
| **List directory** | ✅ `ls.ts` | ✅ (built-in) | ✅ (native) | ✅ `list_directory` |
| **Find files** | ✅ `find.ts` | ✅ (built-in) | ✅ (native) | ⬜ |
| **Web search** | ⬜ | ✅ (via plugins) | ✅ (web search tools) | ✅ `web_search` (5 providers) |
| **Web fetch / scrape** | ⬜ | ✅ (via plugins) | ✅ (web tools) | ✅ `web_fetch` |
| **Git status** | ⬜ | ✅ (built-in) | ⬜ | ✅ `git_status` |
| **Git diff** | ⬜ | ✅ (built-in) | ⬜ | ✅ `git_diff` |
| **Git commit** | ⬜ | ✅ (built-in) | ⬜ | ✅ `git_commit` |
| **System info** | ⬜ | ⬜ | ⬜ | ✅ `system_info` |
| **Tool call validation** | ✅ `tool-definition-wrapper.ts` | ✅ `tool_guardrails.py` | ✅ `tool_filter` | 🔧 Basic validation |
| **Tool result classification** | ⬜ | ✅ `tool_result_classification.py` | ⬜ | ⬜ |
| **Tool output accumulator** | ✅ `output-accumulator.ts` | ⬜ | ✅ 16 KiB tool result budget | ⬜ |
| **File mutation queue** | ✅ `file-mutation-queue.ts` | ⬜ | ⬜ | ⬜ |
| **Tool timeout / budget** | ⬜ | ⬜ | ✅ `tool_timeout` | ⬜ |
| **XML tool dispatch** | ⬜ | ⬜ | ✅ `<tool_call>` XmlDispatcher | ⬜ |
| **Compact tool dispatch** | ⬜ | ⬜ | ✅ PFormat dispatcher | ⬜ |

---

## 4. Memory & Persistence

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Primary storage** | ✅ JSONL (append-only) | ✅ SQLite (FTS5) | ✅ SQLite + JSONL | ✅ SQLite (WAL) |
| **In-memory backend** | ✅ `memory-storage.ts` | ⬜ | ⬜ | ⬜ |
| **Graph memory** | ⬜ | ⬜ | ✅ `memory_graph` | ✅ Neo4j |
| **Vector embeddings** | ⬜ | ⬜ | ✅ `embeddings` module | ✅ pgvector (📐 PageIndex) |
| **Full-text search** | ⬜ | ✅ FTS5 session search | ✅ `memory_search` | ⬜ |
| **Memory tree / cascade** | ⬜ | ⬜ | ✅ Bucket-seal cascade | ⬜ |
| **Entity extraction** | ⬜ | ⬜ | ✅ `memory_entities` | 📐 DeepSeek entity extraction → Neo4j |
| **Memory sync** | ⬜ | ⬜ | ✅ `memory_sync` | ⬜ |
| **Memory queue** | ⬜ | ⬜ | ✅ `memory_queue` | ⬜ |
| **Memory diff** | ⬜ | ⬜ | ✅ `memory_diff` | ⬜ |
| **Holographic HRR** | ⬜ | ⬜ | ⬜ | ✅ SHA-256 deterministic vectors, bind/unbind/bundle |
| **Hebbian pathway weighting** | ⬜ | ⬜ | ⬜ | 📐 Neo4j edge weights (+0.1 traversal, ×1.3/×0.7 feedback, ×0.95 weekly decay) |
| **STDP (Spike-Timing Dependent Plasticity)** | ⬜ | ⬜ | ⬜ | 📐 Response latency < 2min = ×1.5 reinforcement |
| **Spaced repetition reinforcement** | ⬜ | ⬜ | ⬜ | 📐 Nodes near decay + active outcomes → Inner Loop surfaces |
| **Project-specific memory decay** | ⬜ | ⬜ | ⬜ | 📐 Cypher: `SET r.weight = r.weight * 0.5` on completion |
| **User modeling store** | ⬜ | ✅ Honcho dialectic modeling | ✅ Ambient profile facets + stability detector | 📐 User Identity Profile (PG single-row, rolling-average) |
| **Memory orchestrator** | ⬜ | ✅ `memory_manager.py` | ✅ `memory_store` | ✅ `memory_manager.py` |
| **Approval store** | ⬜ | ⬜ | ✅ Approval gate (10-min TTL) | ✅ `approval_store.py` |
| **Session manager** | ✅ `session-manager.ts` | ✅ `gateway/session.py` | ✅ `session_db` | ✅ `session_manager.py` |

---

## 5. Sessions

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Session format** | ✅ Tree-based JSONL (v3, 9 entry types) | ✅ SQLite sessions | ✅ JSONL + bucket-seal | ✅ SQLite (conversations, sessions, documents) |
| **Session branching / fork** | ✅ `--fork` flag | ⬜ | ⬜ | ⬜ |
| **Session resume** | ✅ `--resume` / `--continue` | ✅ Session history | ⬜ | ⬜ |
| **Session naming** | ✅ `--name` flag | ✅ `title_generator.py` | ⬜ | ⬜ |
| **Session picker UI** | ✅ `session-picker.ts` | ⬜ | ⬜ | ⬜ |
| **Session compression** | ✅ Compaction engine + branch summarization | ✅ `conversation_compression.py` | ✅ Microcompact + summarizer | 🔧 `compression.py` (basic) |
| **Session export** | ✅ HTML, JSON, MD | ✅ Trajectory recording | ⬜ | ⬜ |
| **No-session mode** | ✅ `--no-session` flag | ⬜ | ⬜ | ⬜ |
| **Custom session directory** | ✅ `--session-dir` flag | ⬜ | ⬜ | ⬜ |

---

## 6. Context Management

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Context window management** | ✅ Compaction engine | ✅ `context_engine.py` + `context_compressor.py` | ✅ Guard (0.90/0.95 thresholds) | 🔧 `token_counter.py` only |
| **Context references** | ⬜ | ✅ `context_references.py` | ⬜ | ⬜ |
| **Coding-specific context** | ⬜ | ✅ `coding_context.py` | ⬜ | ⬜ |
| **Manual compression feedback** | ⬜ | ✅ `manual_compression_feedback.py` | ⬜ | ⬜ |
| **Token overflow handling** | ✅ `overflow.ts` | ✅ (via context compressor) | ✅ 16 KiB tool result cap | 🔧 Basic compactor |
| **Context Forge (multi-source assembly)** | ⬜ | ⬜ | ⬜ | 📐 800-token, 6-layer: identity(80t) + temporal(60t) + PG events(180t) + Neo4j(150t) + pgvector(200t) + web(100t) |
| **Query Router / Intent Classifier** | ⬜ | ⬜ | ⬜ | 📐 8 intent types, source routing matrix |

---

## 7. TUI / Terminal Interface

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Full TUI framework** | ✅ React/Ink component library | ✅ `cli.py` (650K) | ✅ Tauri desktop + web (React/TS) | ❌ Deliberately rejected |
| **Multiline editing** | ✅ Full editor | ✅ Full editor | ✅ `text_input` module | ❌ |
| **Keyboard shortcuts** | ✅ 15+ configurable keybindings | ✅ 13+ handlers | ✅ Keyboard layer | ❌ |
| **Themes (dark/light/custom)** | ✅ Theme system | ⬜ | ✅ Dashboard themes | ❌ |
| **Slash command autocomplete** | ✅ `slash-commands.ts` | ✅ Built into TUI | ✅ `autocomplete` module | ⬜ (Telegram /commands instead) |
| **Streaming tool output** | ✅ Real-time streaming | ✅ Streaming TUI | ⬜ | 🔧 `streaming_tui.py` (basic) |
| **Voice recording in TUI** | ⬜ | ✅ Ctrl+R voice recording | ⬜ | ❌ |
| **Paste support** | ✅ System clipboard | ✅ Ctrl+V / Alt+V | ⬜ | ❌ |
| **Editor integration ($EDITOR)** | ⬜ | ✅ Open-in-editor | ⬜ | ❌ |
| **Session picker** | ✅ Interactive session selection | ⬜ | ⬜ | ❌ |
| **Status bar / footer** | ✅ `footer-data-provider.ts` | ✅ `runtime_footer.py` | ✅ Dashboard | ❌ |
| **Provider attribution display** | ✅ `provider-attribution.ts` | ⬜ | ⬜ | ❌ |
| **Diagnostics UI** | ✅ `diagnostics.ts` | ✅ `hermes doctor` | ⬜ | ⬜ |
| **Curses fallback TUI** | ⬜ | ⬜ | ⬜ | 🔧 `curses_ui.py` exists but not primary |

---

## 8. CLI

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **CLI flags count** | ✅ 39 flags | ✅ 13+ keyboard handlers | ✅ JSON-RPC + CLI | ✅ 18 CLI commands |
| **Run modes** | ✅ Interactive, Print, RPC, JSON | ✅ CLI, Gateway | ✅ Desktop, Web, CLI, MCP | ✅ CLI, Gateway |
| **Batch mode (one-shot)** | ✅ `--print` flag | ⬜ | ⬜ | ⬜ |
| **RPC / daemon mode** | ✅ JSON-RPC protocol | ⬜ | ✅ JSON-RPC | ⬜ |
| **Self-update** | ✅ `version-check.ts` + `windows-self-update.ts` | ✅ `hermes update` | ✅ `update` module | ⬜ |
| **Doctor / diagnostics** | ⬜ | ✅ `hermes doctor` | ✅ `doctor` module | ⬜ |
| **Config management** | ✅ `config.ts` + migrations | ✅ `cli-config.yaml` | ✅ ~70 schema files | ✅ `locus config show/set/path/env-path/check/migrate` |
| **Gateway lifecycle** | ⬜ | ✅ `hermes gateway run/start/stop` | ⬜ | ✅ `locus gateway run/start/stop/restart/status/install/uninstall` |
| **Setup wizard** | ✅ Project trust prompt | ✅ `onboarding.py` | ⬜ | ✅ `locus setup` + `locus setup gateway` |

---

## 9. Extensions / Plugins / Skills

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Extension system** | ✅ Loader, runner, wrapper, 25+ lifecycle events | ⬜ (uses ACP + skills instead) | ⬜ (uses MCP registry) | ⬜ |
| **Skills system** | ✅ SKILL.md frontmatter discovery | ✅ Skill bundles, commands, preprocessing, 15 categories | ✅ `skill_registry` + `skill_runtime` | ⬜ |
| **Skills marketplace** | ⬜ | ✅ 4 marketplace indexes (Anthropic, Claude, LobeHub, OpenAI) | ✅ Smithery.ai dynamic install | ⬜ |
| **Prompt templates** | ✅ `prompt-templates.ts` | ⬜ | ⬜ | ⬜ |
| **ACP protocol** | ⬜ | ✅ Full ACP adapter (server, session, auth, approval, provenance, tools) | ⬜ | ⬜ |
| **Plugin LLM** | ⬜ | ✅ `plugin_llm.py` | ⬜ | ⬜ |
| **Register custom tools** | ✅ Via extensions | ✅ Via skills | ✅ Via MCP registry | ⬜ |
| **Register custom commands** | ✅ Via extensions | ✅ Via skill commands | ⬜ | ✅ Telegram /commands |
| **Context file loading** | ✅ AGENTS.md, CLAUDE.md auto-discovery | ⬜ | ⬜ | ✅ SOUL.md |

---

## 10. Learning & Self-Improvement

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Post-session learning** | ⬜ | ✅ Curator → insights → memory nudge | ✅ Post-turn hooks (Archivist, Reflection, ToolTracker, UserProfile) | 🔧 `reflector.py` (basic LLM reflection) |
| **Cross-session search / recall** | ⬜ | ✅ FTS5 full-text search + LLM summarization | ✅ `memory_search` | ⬜ |
| **User profile building** | ⬜ | ✅ Honcho dialectic modeling | ✅ Ambient profile facets + PROFILE.md injection | 📐 User Identity Profile (behavioral tendencies, peak windows, stressors, communication style) |
| **Stability detection** | ⬜ | ⬜ | ✅ Stability detector (30min) | ⬜ |
| **Tool usage tracking** | ⬜ | ⬜ | ✅ `ToolTrackerHook` | ✅ `tool_tracker.py` |
| **Personal Reward Model** | ⬜ | ⬜ | ⬜ | 📐 sklearn LogisticRegression (👍/👎 feedback, weekly retrain, ≥0.6 threshold) |
| **Hebbian learning rules** | ⬜ | ⬜ | ⬜ | 📐 Neo4j edge weights with biological decay, STDP reinforcement |
| **Multi-horizon pattern detection** | ⬜ | ⬜ | ⬜ | 📐 5 horizons (H1: 6h, H2: 24h, H3: 7d, H4: 30d, H5: all-time) |
| **Self-evolving Architect Bot** | ⬜ | ⬜ | ⬜ | 📐 Scans reward signals, generates patches, risk-gated deploy |
| **Agent experience tracking** | ⬜ | ⬜ | ✅ `agent_experience` module | ⬜ |

---

## 11. Subagents / Delegation

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Subagent spawning** | ✅ Built-in subagent tool | ✅ `agent_init.py` + `process_bootstrap.py` | ✅ 3-tier hierarchy | 🔧 `delegation/subagent.py` |
| **Subagent archetypes** | ⬜ | ⬜ | ✅ 15 built-in (orchestrator, planner, researcher, critic, etc.) | 📐 4 faction sub-agents (Planner, Curator, Analyst, Builder) |
| **Depth limiting** | ⬜ | ⬜ | ✅ MAX_SPAWN_DEPTH=3 | ⬜ |
| **RPC-based subagents** | ✅ RPC mode | ✅ `codex_runtime.py` (RPC) | ⬜ | ⬜ |
| **Coding agent** | ✅ Full coding agent package | ⬜ | ✅ `code_executor` archetype | 🔧 `delegation/coding_agent.py` |
| **ACP client for subagents** | ⬜ | ✅ `copilot_acp_client.py` | ⬜ | ⬜ |

---

## 12. Scheduling & Cron

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Cron / scheduled tasks** | ⬜ | ✅ Natural language cron scheduling | ✅ `cron` + `scheduler_gate` modules | ✅ `cron_runner.py` |
| **Task sources** | ⬜ | ⬜ | ✅ `task_sources` module | ✅ `scheduler/task_sources.py` |
| **Scheduled automations** | ⬜ | ✅ Daily reports, nightly backups, weekly audits | ✅ Via cron module | 📐 Nightly vault ingestion, weekly synthesis, daily check-ins |
| **Inner Loop (proactive, unprompted)** | ⬜ | ⬜ | ⬜ | 📐 APScheduler every 90min (07:00–00:00), fires without user input |
| **Structured check-in reminders** | ⬜ | ⬜ | ⬜ | 📐 07:30/13:00/18:00/22:00 IST → Telegram inline keyboards |
| **Heartbeat / notification** | ⬜ | ⬜ | ✅ `heartbeat` module | ✅ `heartbeat/notification.py` + `subconscious.py` |

---

## 13. Security & Sandboxing

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Project trust management** | ✅ `trust-manager.ts` | ⬜ | ⬜ | ⬜ |
| **Shell command blocklist** | ⬜ | ⬜ | ✅ Policy engine (command classification) | ✅ `shell_exec.py` BLOCKED_PATTERNS |
| **File safety checks** | ⬜ | ✅ `file_safety.py` | ✅ `file_state`, `cwd_jail` | ⬜ |
| **Sandbox backends** | ⬜ | ⬜ | ✅ 4 (bubblewrap, docker, firejail, landlock) | ⬜ |
| **Autonomy tiers** | ⬜ | ⬜ | ✅ readonly / supervised / full | ⬜ |
| **Approval gate** | ⬜ | ✅ ACP edit approval | ✅ 10-min TTL approval gate | ✅ `approval_store.py` |
| **Data redaction** | ⬜ | ✅ `redact.py` | ⬜ | ⬜ |
| **Prompt injection protection** | ⬜ | ⬜ | ✅ `prompt_injection` module | ⬜ |
| **Think token scrubbing** | ⬜ | ✅ `think_scrubber.py` | ⬜ | ⬜ |
| **Message sanitization** | ⬜ | ✅ `message_sanitization.py` | ⬜ | ⬜ |
| **Secret prompt encryption** | ⬜ | ⬜ | ⬜ | ✅ `secret_prompt.py` |
| **Proxy support** | ✅ `node-http-proxy.ts` | ⬜ | ✅ `proxy` config | ✅ `proxy.py` |
| **Encryption / keyring** | ⬜ | ⬜ | ✅ `encryption`, `keyring` modules | ⬜ |
| **TLS** | ⬜ | ⬜ | ✅ `tls` module | ⬜ |

---

## 14. Voice

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **STT (Speech-to-Text)** | ⬜ | ✅ Via plugins | ✅ Voice inference module | ✅ 4 backends (Whisper local, Azure, Groq, OpenAI) |
| **TTS (Text-to-Speech)** | ⬜ | ✅ Via plugins | ✅ Voice inference module | ✅ 4 backends (Edge TTS, ElevenLabs, OpenAI, Piper) |
| **Voice recording in-app** | ⬜ | ✅ Ctrl+R in TUI | ⬜ | ⬜ |
| **Voice call interface** | ⬜ | ⬜ | ⬜ | 📐 Audio → Groq Whisper → pipeline → Kokoro TTS → vault transcript |
| **Dictation** | ⬜ | ⬜ | ✅ `dictation` module | ✅ `dictation.py` |

---

## 15. Web Search

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Search provider count** | ⬜ | ✅ Via plugins | ✅ `search` module | ✅ 5 providers |
| **Brave Search** | ⬜ | ⬜ | ⬜ | ✅ |
| **Exa** | ⬜ | ⬜ | ⬜ | ✅ |
| **Firecrawl** | ⬜ | ⬜ | ⬜ | ✅ |
| **SearXNG** | ⬜ | ⬜ | ⬜ | ✅ |
| **Tavily** | ⬜ | ⬜ | ⬜ | ✅ |

---

## 16. Browser Automation

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Browser automation** | ⬜ | ✅ Browser provider | ✅ `screen_intelligence` module | ✅ Playwright (`browserbase.py`, `playwright_backend.py`) |
| **Screenshot** | ⬜ | ⬜ | ✅ Screen intelligence | ✅ `screenshot.py` |
| **Vision / screen analysis** | ⬜ | ⬜ | ✅ Screen intelligence + overlay | ✅ `vision.py` |

---

## 17. Channels / Gateway / Messaging

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Telegram** | ⬜ | ✅ Via gateway adapter | ⬜ | ✅ Primary interface (PTB, auth, inline keyboards) |
| **Discord** | ⬜ | ✅ Via gateway adapter | ⬜ | ✅ Channel module |
| **Slack** | ⬜ | ✅ Via gateway adapter | ⬜ | ✅ Channel module |
| **WhatsApp** | ⬜ | ✅ `whatsapp_identity.py` | ⬜ | ✅ Channel module |
| **Signal** | ⬜ | ✅ Via `apps/shared` | ⬜ | ✅ Channel module |
| **IRC** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **Matrix** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **Mattermost** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **Teams** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **Lark** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **DingTalk** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **Google Chat** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **Email** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **iMessage** | ⬜ | ⬜ | ⬜ | ✅ Channel module |
| **CLI / Terminal** | ✅ Primary interface | ✅ `cli.py` | ✅ CLI mode | ✅ Basic CLI |
| **Desktop app** | ⬜ | ✅ Electron (38+ modules) | ✅ Tauri v2 desktop | ❌ Deliberately rejected |
| **Web interface** | ⬜ | ⬜ | ✅ React/TS web app | ⬜ |
| **Platform registry** | ⬜ | ✅ `platform_registry.py` | ✅ `channels` module | ✅ Platform registry |
| **Cross-platform message mirroring** | ⬜ | ✅ `mirror.py` | ⬜ | ⬜ |
| **Channel-specific display config** | ⬜ | ✅ `display_config.py` | ⬜ | ⬜ |
| **Device pairing** | ⬜ | ✅ `pairing.py` | ✅ `devices` module | ⬜ |
| **Sticker / media cache** | ⬜ | ✅ `sticker_cache.py` | ⬜ | ⬜ |
| **Graceful restart** | ⬜ | ✅ `restart.py` | ⬜ | ⬜ |
| **Shutdown forensics** | ⬜ | ✅ `shutdown_forensics.py` | ⬜ | ⬜ |
| **Kanban watchers** | ⬜ | ✅ `kanban_watchers.py` | ⬜ | ⬜ |
| **Memory monitor** | ⬜ | ✅ `memory_monitor.py` | ⬜ | ⬜ |
| **Gateway hooks** | ⬜ | ✅ `hooks.py` | ⬜ | ⬜ |
| **Slash access control** | ⬜ | ✅ `slash_access.py` | ⬜ | ⬜ |

---

## 18. MCP (Model Context Protocol)

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **MCP client** | ⬜ (extensions instead) | ⬜ (ACP instead) | ✅ HTTP + stdio, protocol 2024–2025 | ✅ `mcp_client.py` |
| **MCP server** | ⬜ | ⬜ | ✅ Axum HTTP + SSE | ⬜ |
| **MCP registry** | ⬜ | ⬜ | ✅ Dynamic install, Smithery.ai, 60s reconnect | ⬜ |
| **MCP audit** | ⬜ | ⬜ | ✅ `mcp_audit` | ⬜ |
| **Obsidian MCP** | ⬜ | ⬜ | ⬜ | 📐 vault_read/write/search/tag/stats (localhost, .md only) |

---

## 19. Export & Artifacts

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **HTML session export** | ✅ `export-html/` | ⬜ | ⬜ | ⬜ |
| **JSON session export** | ✅ Via `--export json` | ⬜ | ⬜ | ⬜ |
| **Markdown session export** | ✅ Via `--export md` | ⬜ | ⬜ | ⬜ |
| **Trajectory recording** | ⬜ | ✅ `trajectory.py` (1321 lines) | ⬜ | ⬜ |
| **ANSI → HTML conversion** | ✅ `ansi-to-html.ts` | ⬜ | ⬜ | ⬜ |
| **Daily AI Chat Archiver** | ⬜ | ⬜ | ⬜ | 📐 Nightly 23:45 Telegram → vault .md → git commit |

---

## 20. Computer Use

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Native desktop control** | ⬜ | ⬜ | ✅ `desktop_companion` + `overlay` | ✅ `native.py` |
| **VNC remote control** | ⬜ | ⬜ | ⬜ | ✅ `vnc.py` |
| **Screen capture** | ⬜ | ⬜ | ✅ `screen_intelligence` | ✅ `capture.py` |
| **Screen intelligence / vision** | ⬜ | ⬜ | ✅ `screen_intelligence` | ✅ `vision.py` |

---

## 21. Integrations

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Composio** | ⬜ | ⬜ | ✅ `integrations` module | ✅ `composio.py` (📐 replacing with manual OAuth) |
| **Polymarket** | ⬜ | ⬜ | ⬜ | ✅ `polymarket.py` |
| **Webhooks** | ⬜ | ⬜ | ✅ `webhooks` module | ✅ `webhooks.py` |
| **Google Calendar** | ⬜ | ⬜ | ⬜ | 📐 Manual OAuth integration |
| **Gmail** | ⬜ | ⬜ | ⬜ | 📐 Manual OAuth integration |
| **Calendly** | ⬜ | ⬜ | ⬜ | 📐 Via setup wizard |
| **Web3 / wallet** | ⬜ | ⬜ | ✅ `wallet`, `web3`, `x402` modules | ⬜ |
| **Billing** | ⬜ | ⬜ | ✅ `billing` module | ⬜ |
| **Meet / video calls** | ⬜ | ⬜ | ✅ `meet`, `meet_agent`, `agent_meetings` | ⬜ |
| **Team collaboration** | ⬜ | ⬜ | ✅ `team`, `people` modules | ⬜ |
| **Referral system** | ⬜ | ⬜ | ✅ `referral` module | ⬜ |

---

## 22. Configuration

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Config format** | ✅ YAML/JSON | ✅ `cli-config.yaml` | ✅ ~70 JSON schema files | ✅ SETTINGS.md (56KB, 28 sections) |
| **Config migration** | ✅ `migrations.ts` | ⬜ | ✅ `migration`, `migrations` modules | ✅ `locus config migrate` |
| **Environment variable management** | ✅ `env-api-keys.ts` | ⬜ | ⬜ | ✅ `locus config env-path` |
| **Config section count** | ~10 | ~5 | ~70 schema files | 28 sections |

---

## 23. CI/CD & Testing

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Unit tests** | ✅ Vitest | ✅ pytest | ✅ cargo test | ⬜ |
| **CI pipeline** | ✅ GitHub Actions | ✅ Full CI (lint, test, typecheck, docker, nix, security) | ✅ Full CI (build, test, deploy, e2e, smoke) | ⬜ |
| **Linting** | ✅ ESLint | ✅ Ruff/flake8 | ✅ clippy | ⬜ |
| **Type checking** | ✅ TypeScript | ✅ mypy | ✅ Rust compiler | ⬜ |
| **Docker** | ⬜ | ✅ Docker builds | ✅ Docker builds | ⬜ |
| **Nix** | ⬜ | ✅ Nix flake | ⬜ | ⬜ |
| **Batch trajectory runner** | ⬜ | ✅ `trajectory.py` (1321 lines) | ⬜ | ⬜ |

---

## 24. Utilities

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Clipboard** | ✅ `clipboard.ts` + native + image | ⬜ | ⬜ | ⬜ |
| **Git integration** | ✅ `git.ts` | ✅ (built-in tools) | ⬜ | ✅ `git_ops.py` |
| **Image handling** | ✅ Resize, convert, EXIF orientation, Photon | ⬜ | ✅ `image` module | ⬜ |
| **Syntax highlighting** | ✅ `syntax-highlight.ts` + highlight.js | ⬜ | ⬜ | ⬜ |
| **MIME detection** | ✅ `mime.ts` | ⬜ | ⬜ | ⬜ |
| **Open browser** | ✅ `open-browser.ts` | ⬜ | ⬜ | ⬜ |
| **ANSI escape handling** | ✅ `ansi.ts` | ⬜ | ⬜ | ⬜ |
| **Shell integration** | ✅ `shell.ts` | ⬜ | ⬜ | ⬜ |
| **Frontmatter parser** | ✅ `frontmatter.ts` | ⬜ | ⬜ | ⬜ |
| **File system watcher** | ✅ `fs-watch.ts` | ⬜ | ⬜ | ⬜ |
| **Unicode sanitization** | ✅ `sanitize-unicode.ts` | ⬜ | ⬜ | ⬜ |
| **JSON safe parsing** | ✅ `json-parse.ts` | ⬜ | ⬜ | ⬜ |
| **Schema validation** | ✅ TypeBox helpers | ⬜ | ⬜ | ⬜ |
| **Colors / output formatting** | ⬜ | ⬜ | ⬜ | ✅ `colors.py`, `cli_output.py` |
| **Slash commands handler** | ⬜ | ⬜ | ⬜ | ✅ `slash_commands.py` |
| **SSH deployment** | ⬜ | ⬜ | ⬜ | ✅ `deployment` module |

---

## 25. Life OS — Behavioral Metrics *(Locus-only domain)*

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Four Factions Framework** | ⬜ | ⬜ | ⬜ | 📐 Health/Leverage/Craft/Expression with weekly hour targets |
| **Daily Capacity Score (DCS)** | ⬜ | ⬜ | ⬜ | 📐 `((E+M+S)/3) × (1−ST/20)` → 5 operating modes |
| **Five Operating Modes** | ⬜ | ⬜ | ⬜ | 📐 SURVIVAL / RECOVERY / NORMAL / DEEP_WORK / PEAK |
| **Task Weight Score (TWS)** | ⬜ | ⬜ | ⬜ | 📐 `(P×0.4)+(U×0.4)+(D×0.2)` sorting key |
| **Three-Layer Goal Stack** | ⬜ | ⬜ | ⬜ | 📐 Outcomes (max 7) → Projects (max 3/faction) → Tasks |
| **Action Gap Tracking** | ⬜ | ⬜ | ⬜ | 📐 declared_priority − actual performance metric |
| **Deferral Detection (3/5/8+)** | ⬜ | ⬜ | ⬜ | 📐 Progressive alerts: flag → Telegram → Inner Loop |
| **Lag Score + TWS Lag Bonus** | ⬜ | ⬜ | ⬜ | 📐 Lagging faction TWS +2/+4, ahead faction −1 |
| **Emergency Task Injection** | ⬜ | ⬜ | ⬜ | 📐 TWS comparison, `is_locked` protection |
| **Exhaustion Predictor** | ⬜ | ⬜ | ⬜ | 📐 5-day difficulty vs DCS average → load reduction |
| **Weekly Faction Rebalance** | ⬜ | ⬜ | ⬜ | 📐 Starving faction gets priority boost |
| **Cross-Faction Efficiency** | ⬜ | ⬜ | ⬜ | 📐 Multi-faction tasks get TWS +1/extra faction |
| **Review Cadence System** | ⬜ | ⬜ | ⬜ | 📐 Daily(7min)/Weekly(30-45min)/Monthly(60min)/Quarterly(2-3hrs) |
| **Goal Stack Enforcement** | ⬜ | ⬜ | ⬜ | 📐 Dead node detection (60d), stall detection (CR<20% @ 30d) |
| **6-Step Scheduling Algorithm** | ⬜ | ⬜ | ⬜ | 📐 Non-negotiables → DCS filter → lag bonus → TWS sort → balance → assign |
| **4-Level Emergency Protocol** | ⬜ | ⬜ | ⬜ | 📐 Disruption classification, 2-week recovery rule |

---

## 26. Proactive Reasoning / Brain Engine *(Locus-only domain)*

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Inner Loop (Proactive Thinker)** | ⬜ | ⬜ | ⬜ | 📐 Every 90min, unprompted reasoning, Reward Model gate |
| **State Engine + Inferred Cause Chain** | ⬜ | ⬜ | ⬜ | 📐 Psychological + operational state + causal explanation |
| **Multi-Horizon Pattern Engine** | ⬜ | ⬜ | ⬜ | 📐 H1(6h)–H5(all-time), confidence-based promotion |
| **Context Forge** | ⬜ | ⬜ | ⬜ | 📐 800-token 6-layer assembler (identity/temporal/PG/Neo4j/pgvector/web) |
| **Query Router / Intent Classifier** | ⬜ | ⬜ | ⬜ | 📐 8 intent types, source routing matrix |
| **Inferred Cause Chain Engine** | ⬜ | ⬜ | ⬜ | 📐 Cross-reference state+patterns+history → causal explanation |
| **Personality + "Wants" Engine** | ⬜ | ⬜ | ⬜ | 📐 SOUL.md rules + WantNodes in Neo4j |
| **Weekly Full Vault Synthesis** | ⬜ | ⬜ | ⬜ | 📐 Sunday 02:00, personality drift + faction narrative |

---

## 27. Vault & Knowledge Intelligence *(Locus-only domain)*

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **PageIndex (whole-note embedding)** | ⬜ | ⬜ | ⬜ | 📐 200-800 word notes embedded whole, long chats chunked at sentence boundaries |
| **Nightly Vault Ingestion Pipeline** | ⬜ | ⬜ | ⬜ | 📐 Multi-account Playwright scraping (ChatGPT×3, Claude, Gemini, Perplexity) |
| **LOCUS_SHORTHAND** | ⬜ | ⬜ | ⬜ | 📐 ~4× token compression, dedicated encode/decode |
| **Obsidian as Primary Dashboard** | ⬜ | ⬜ | ⬜ | 📐 8 panels via Dataview/Charts, replaces PWA |
| **3-Level Tag Hierarchy** | ⬜ | ⬜ | ⬜ | 📐 faction/domain/specific, PG tag registry |
| **Rough Note Parser / Idea Tracker** | ⬜ | ⬜ | ⬜ | 📐 /idea → expand → promote/research/archive |
| **Link Dump / Resource Logger** | ⬜ | ⬜ | ⬜ | 📐 /link → captures table → vault note |
| **Excalidraw MCP Skill** | ⬜ | ⬜ | ⬜ | 📐 Autonomous diagram generation via MCP |

---

## 28. Interface Philosophy & Infrastructure Decisions *(Locus-only domain)*

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Telegram-native headless** | ⬜ | ⬜ | ⬜ | ✅ Primary interface is Telegram, no GUI/TUI |
| **4 Daily Structured Check-ins** | ⬜ | ⬜ | ⬜ | 📐 Morning/Afternoon/Evening/Night via inline keyboards |
| **Voice Call Interface** | ⬜ | ⬜ | ⬜ | 📐 Groq Whisper → pipeline → Kokoro TTS → vault transcript |
| **Obsidian Dashboard replaces PWA** | ⬜ | ⬜ | ⬜ | 📐 PWA explicitly removed from architecture |
| **Git for vault sync** | ⬜ | ⬜ | ⬜ | 📐 Directory partitioning (backend vs user writes) |
| **Manual Google OAuth** | ⬜ | ⬜ | ⬜ | 📐 50 lines, replacing Composio |
| **pgvector replaces Qdrant+ChromaDB** | ⬜ | ⬜ | ⬜ | 📐 <50K vectors, one fewer container |
| **Redis optional** | ⬜ | ⬜ | ⬜ | 📐 PG + in-memory dict at single-user scale |
| **DeepSeek V4 Flash only** | ⬜ | ⬜ | ⬜ | ✅ ~$0.012/day, ~$4/year — architectural decision |
| **Zero-cost 1st-class constraint** | ⬜ | ⬜ | ⬜ | ✅ $5 credit → ~416 days |
| **Minimum AI in harness** | ⬜ | ⬜ | ⬜ | ✅ LLM only for reasoning/generation, deterministic logic elsewhere |

---

## 29. Miscellaneous / Uncategorized

| Feature | Pi | Hermes | OpenHuman | Locus |
|---|---|---|---|---|
| **Telemetry** | ✅ `telemetry.ts` | ⬜ | ✅ `observability` config | ⬜ |
| **Experimental features flag** | ✅ `experimental.ts` | ⬜ | ⬜ | ⬜ |
| **Auth storage** | ✅ `auth-storage.ts` + `auth-guidance.ts` | ✅ `authz_mixin.py` | ✅ `keyring` | ⬜ |
| **Resource loader** | ✅ `resource-loader.ts` | ⬜ | ⬜ | ⬜ |
| **Error classifier** | ⬜ | ✅ `error_classifier.py` | ⬜ | ⬜ |
| **Auxiliary LLM client** | ⬜ | ✅ `auxiliary_client.py` | ✅ `model_council` | ⬜ |
| **Model council / committee** | ⬜ | ⬜ | ✅ `council_registry`, `model_council` | ⬜ |
| **Accessibility** | ⬜ | ⬜ | ✅ `accessibility` module | ⬜ |
| **Connectivity checks** | ⬜ | ⬜ | ✅ `connectivity` module | ⬜ |
| **Code graph analysis** | ⬜ | ⬜ | ✅ `codegraph` module | ⬜ |
| **Runtime JS/Python** | ⬜ | ⬜ | ✅ `runtime_node`, `runtime_python` | ⬜ |
| **About app** | ⬜ | ⬜ | ✅ `about_app` module | ⬜ |
| **Workflows** | ⬜ | ⬜ | ✅ `workflows` module | ⬜ |
| **Health checks** | ⬜ | ✅ `gateway/status.py` | ✅ `health` module | ⬜ |
| **Notifications** | ⬜ | ⬜ | ✅ `notifications` module | ✅ `heartbeat/notification.py` |
| **Socket/WebSocket** | ⬜ | ✅ `gateway/stream_consumer.py` | ✅ `socket` module | ⬜ |
| **Redirect links** | ⬜ | ⬜ | ✅ `redirect_links` module | ⬜ |
| **Provider surfaces** | ⬜ | ⬜ | ✅ `provider_surfaces` module | ⬜ |
| **Service orchestration** | ⬜ | ⬜ | ✅ `service` module | ⬜ |
| **Workspace management** | ⬜ | ⬜ | ✅ `workspace` module | ⬜ |
| **Agent tool policy** | ⬜ | ⬜ | ✅ `agent_tool_policy` module | ⬜ |
| **Test support** | ⬜ | ⬜ | ✅ `test_support` module | ⬜ |
| **Subconscious background** | ⬜ | ⬜ | ✅ `subconscious` module | ✅ `subconscious.py` + 📐 Inner Loop |

---

## Summary Counts

| Category | Pi | Hermes | OpenHuman | Locus (✅+🔧) | Locus (📐 designed) |
|---|---|---|---|---|---|
| Agent Core | 9 | 16 | 8 | 4 | 1 |
| LLM Providers | 15 | 12 | 5 | 2 | 0 |
| Tools | 11 | 11 | 13 | 10 | 0 |
| Memory | 4 | 5 | 10 | 5 | 5 |
| Sessions | 8 | 3 | 2 | 1 | 0 |
| Context | 2 | 4 | 3 | 1 | 2 |
| TUI | 12 | 12 | 5 | 1 | 0 |
| CLI | 6 | 5 | 4 | 5 | 0 |
| Extensions/Skills | 5 | 6 | 3 | 1 | 0 |
| Learning | 0 | 3 | 5 | 2 | 3 |
| Subagents | 3 | 3 | 3 | 1 | 1 |
| Scheduling | 0 | 2 | 3 | 2 | 3 |
| Security | 2 | 4 | 8 | 3 | 0 |
| Voice | 0 | 2 | 2 | 3 | 1 |
| Search | 0 | 1 | 1 | 5 | 0 |
| Browser | 0 | 1 | 2 | 3 | 0 |
| Channels | 2 | 15 | 5 | 16 | 0 |
| MCP | 0 | 0 | 4 | 1 | 1 |
| Export | 4 | 1 | 0 | 0 | 1 |
| Computer Use | 0 | 0 | 2 | 4 | 0 |
| Life OS Metrics | 0 | 0 | 0 | 0 | 16 |
| Brain Engine | 0 | 0 | 0 | 0 | 8 |
| Vault Intelligence | 0 | 0 | 0 | 0 | 8 |
| Interface Philosophy | 0 | 0 | 0 | 4 | 7 |

**Totals**:
- **Pi**: ~83 implemented features
- **Hermes**: ~106 implemented features
- **OpenHuman**: ~87 implemented features
- **Locus (code)**: ~73 implemented features
- **Locus (design)**: ~57 additional designed features → **130 total when built**
