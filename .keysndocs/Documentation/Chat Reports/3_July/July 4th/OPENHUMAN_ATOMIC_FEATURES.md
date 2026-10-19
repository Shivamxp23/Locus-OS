# OPENHUMAN — COMPLETE ATOMIC FEATURE SPECIFICATION (v2 — CORRECTED)

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
- All data canonicalized into &#x2264;3k-token Markdown chunks
- Stored in SQLite on user's machine
- Obsidian-compatible Markdown vault (`wiki/`)

### Pipeline Stages
1. **Canonicalize** — source adapters &#x2192; normalized Markdown + provenance metadata
2. **Chunker** — deterministic IDs, &#x2264;3k-token bounded segments
3. **Content Store** — atomic .md files on disk (body + tags)
4. **Store** — persistence (chunks, scores, summaries, jobs)
5. **Score** — signals + embeddings + entity extraction
6. **Trees** — source / topic / global summary trees
7. **Retrieval** — search / drill_down / topic / global / fetch

### Three Trees, Three Scopes
- **Source trees** — per-source rolling buffer (L0 &#x2192; L1 &#x2192; L2 cascading). One per Gmail label, Slack channel, uploaded doc
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
- Orchestrator &#x2192; leaf agent delegation
- Per-agent model pins (orchestrator gets strong model, leaf gets fast)
- Isolated context per sub-agent
- Team-level config in `config.toml`:
  - `[orchestrator]` — lead model
  - `[teams.research]` — lead_model + agent_model
  - `[teams.code]` — agent_model

### 14 Built-in Archetypes (`.claude/agents/`)
| Archetype | Role |
|-----------|------|
| `architectobot` | Architecture design |
| `build-agent` | Build/deployment |
| `codecrusher` | Intensive coding |
| `deploy-agent` | Deployment |
| `designguru` | UI/UX design |
| `dev-agent` | General development |
| `memory-keeper` | Memory management |
| `mobile-agent` | Mobile development |
| `pr-manager` / `pr-manager-lite` | PR management |
| `pr-reviewer` | Code review |
| `qualityqueen` | Quality assurance |
| `taskmaster` | Task management |
| `test-agent` | Testing |
| `ship-and-babysit` | Release + monitor |

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
- `resolve(model)` &#x2192; `(provider_index, model_name)`
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
| Channel | Key Features |
|---------|-------------|
| **Telegram** | Primary channel, two-way, 80+ actions, encrypted credentials, group topics, emoji reactions |
| **Discord** | Send/receive, channel management, skills as native slash commands, `/approve`/`/deny` |
| **Slack** | Thread engagement, strict_mention, channel skill bindings, approval buttons, mrkdwn |
| **Signal** | Native formatting (markdown&#x2192;bodyRanges), reply quotes, reactions, full MEDIA tag delivery |
| **Matrix** | E2E encryption, reactions, read receipts, rich formatting, room management, Synapse compat, CJK input |
| **WhatsApp** | WhatsApp Web via WhatsApp-Rust v0.5, SQLiteStore, group sender-key, LID-addressed contacts |
| **Email** | IMAP/SMTP (Himalaya-backed), Gmail native ingest path, Outlook support |
| **Mattermost** | File attachments, multi-image sending |
| **iMessage** | Via BlueBubbles on macOS |
| **Lark/Feishu** | Interactive card approval buttons, reconnect, multi-image, ACL fixes |
| **DingTalk** | Messaging |
| **WeCom** | Messaging |
| **IRC** | IRC channel |
| **QQ** | QQ bot |
| **Yuanbao** | Tencent Yuanbao groups (COS HMAC-SHA1 signing) |
| **Microsoft Teams** | Graph-backed transcripts, operator CLI, meetings (plugin) |
| **Web** | Browser-based chat within desktop app, messages stay local |

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
- `[autonomy]` config block &#x2192; `SecurityPolicy`
- Tiers: `readonly` / `supervised` / `full`
- `workspace_only` flag, `trusted_roots`, `allow_tool_install` gate
- Configurable via Settings &#x2192; Agent access or `config.update_autonomy_settings`

### Path Security
- **`action_dir`** — agent's read/write root (default: `~/OpenHuman/projects`)
- **`workspace_dir`** — internal state (`~/.openhuman/users/<id>/workspace`), agent tools CANNOT write here
- `is_workspace_internal_path` fail-closed regardless of tier/trusted_roots
- `is_always_forbidden` — system/credential dirs unconditionally blocked

### Command Permission Model
- `classify_command` &#x2192; `CommandClass` (Read/Write/Network/Install/Destructive)
- Unrecognized commands &#x2192; `Write`
- `gate_decision(class, tier)` &#x2192; Allow/Prompt/Block

### Approval Gate
- ON by default (opt out: `OPENHUMAN_APPROVAL_GATE=0`)
- Parks interactive chat turns only; background/cron allowed through
- Frontend: `ApprovalRequestCard`
- 10-min TTL &#x2192; Auto-Deny

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
- BIP-39 mnemonic &#x2192; seed (via `coins-bip39`)
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
- **TokenJuice** (`tokenjuice/`) — smart compression pipeline (classify &#x2192; match rule &#x2192; reduce)
- Three-layer rule overlay: Builtin, User (`~/.config/tokenjuice/rules/`), Project (`.tokenjuice/rules/`)
- Reduction strategies: truncate, dedup lines, fold whitespace, drop matching regexes, summarize sections
- HTML &#x2192; Markdown with CJK/emoji grapheme preservation, multi-byte never stripped
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
| Path | Purpose |
|------|---------|
| `~/.openhuman/` | Workspace root |
| `~/.openhuman/memory_tree/chunks.db` | Memory chunks |
| `~/.openhuman/wiki/` | Obsidian vault |
| `~/OpenHuman/projects/` | action_dir |
| `~/.config/tokenjuice/rules/` | TokenJuice rules |
| `.tokenjuice/rules/` | Project TokenJuice rules |
| `config.toml` | Rust config |
| `app/.env.local` | Vite env |

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

| Feature | Hermes | OpenHuman | Pi |
|---------|--------|-----------|-----|
| Bundled Skills | **73** | **1** (marketplace) | **1** (`add-llm-provider`) |
| Optional Skills | **97** | 0 | 0 (user installs) |
| Managed Integrations | 0 | **118+** via Composio | 0 |
| Native MCP Client | &#x2705; | &#x2705; | &#x274c; |
| Native MCP Server | &#x2705; | &#x2705; | &#x274c; |
| MCP OAuth/Catalog/Circuit Breaker | &#x2705; | &#x274c; | &#x274c; |
| MCP Registry/Audit | &#x274c; | &#x2705; | &#x274c; |
| Agent Skills Standard | &#x274c; (custom) | &#x274c; (custom) | &#x2705; |
| Extension/Package System | Plugins | None | Extensions + Packages |
| Memory System | 8 providers | Memory Tree + 16 domains | None |
| Voice/STT/TTS | &#x2705; | &#x2705; | &#x274c; |
| Desktop Mascot | &#x274c; | &#x2705; | &#x274c; |
| Messaging Gateway | 25 platforms | 17 platforms | None (separate pi-chat) |
| Wallet/Web3 | &#x274c; | &#x2705; | &#x274c; |
| Subconscious Loop | &#x274c; | &#x2705; | &#x274c; |
| Cron/Scheduling | &#x2705; | &#x2705; | &#x274c; |
| Browser/Computer Use | CDP + macOS CUA | CEF + mouse/kb | None |
| SDK | None | None | &#x2705; `AgentSession` |
| Supply-chain Hardening | No | No | &#x2705; shrinkwrap + audit |

---

End of atomic specification.