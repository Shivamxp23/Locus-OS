# Locus /setup Command — Complete OpenHuman Settings Parity

## Overview

Map every OpenHuman settings panel to Locus's `/setup` Telegram wizard with full backend logic. The coding philosophy is: **Locus is a modular intelligence framework** — every setting is a config key, every category is a replaceable module, every toggle writes to a live config file.

---

## Step 1 — Complete OpenHuman Settings Map (N-Depth)

All 50+ settings panels from `Settings.tsx` and their backend logic:

### 🏠 ACCOUNT GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **TeamPanel** | `/settings/team` — list/create/leave teams, roles, invites | Team membership, shared agent access |
| **TeamManagementPanel** | `/settings/team/manage/:id` — rename, delete, member management | Per-team admin controls |
| **TeamMembersPanel** | Fetch members, promote/demote/remove | Role-based access to agent |
| **TeamInvitesPanel** | Send invite links, revoke pending invites | Invite management |
| **PrivacyPanel** | `privacy` config — telemetry opt-in/out, data sharing | Data collection consent |
| **SecurityPanel** | `keyring` config — encryption key type, PIN lock | Credential store security |
| **MigrationPanel** | Import/export data (SQLite dump, config, memories) | Account portability |
| **BillingPanel** | Credits API — balance, top-up, plan info | Token spend tracking |
| **RecoveryPhrasePanel** | Wallet seed phrase — show/hide/export | Crypto wallet backup |
| **WalletBalancesPanel** | EVM/Solana/BTC/Tron balances, send, receive | Multi-chain wallet UI |

### 🤖 AI GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **AIPanel (LLM)** | `cloud_providers[]` + `routing{}` — 8-workload routing matrix | Provider/model assignment per workload: chat, reasoning, agentic, coding, memory, heartbeat, learning, subconscious |
| **EmbeddingsPanel** | `embeddings{}` — model, dimensions, re-embed trigger | Vector embedding for memory search |
| **VoicePanel** | `voice{}` — STT provider (Whisper/Cloud/Deepgram), TTS (ElevenLabs/Piper/Cloud), hotkey, always-on | Full voice pipeline config |
| **HeartbeatPanel** | `heartbeat{}` — interval, enabled, model assignment | Background reasoning cadence |
| **LedgerUsagePanel** | Token ledger — per-provider spend, session costs | Usage accounting |
| **CostDashboardPanel** | `cost{}` — daily/monthly limits, warn %, charts | Budget enforcement |

### ✨ FEATURES GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **ScreenIntelligencePanel** | `screen_intelligence{}` — enabled, OCR provider, active apps | Screen-aware context injection |
| **ToolsPanel** | `tool_registry{}` — enabled/disabled tools, per-tool config | Tool availability |
| **CompanionPanel** | `desktop_companion{}` — floating window, always-on-top, transparency | Desktop mascot/overlay window |

### 🧠 AGENTS GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **AgentsPanel** | `agent_registry[]` — list/create/edit named agents | Named agent definitions |
| **AgentEditorPage** | Per-agent: name, system prompt, model, tools, channels | Agent persona editor |
| **AutonomyPanel** | `autonomy.max_actions_per_hour` — u32, presets: unlimited/100/500/1000 | Rate limit for autonomous actions |
| **AgentAccessPanel** | `autonomy{}` — workspace_only, trusted_roots[], auto_approve[], agent_timeout_secs, require_task_plan_approval | Filesystem access, always-allow tools, action timeout |
| **AgentActivityPanel** | `agent_activity_level` 0-4 — Off/Minimal/Moderate/Active/Always-On | Background activity intensity |
| **SandboxSettingsPanel** | `sandbox{}` — backend (landlock/bubblewrap/docker), allowed syscalls | Process isolation |

### 🔌 COMPOSIO/INTEGRATIONS GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **ComposioPanel** | `composio{}` — API key, routing (which events trigger agent) | 118+ third-party integrations |
| **ComposioTriagePanel** | Composio trigger rules — keyword filters, channel routing | Event → agent routing rules |
| **TaskSourcesPanel** | `task_sources[]` — GitHub issues, Notion tasks, Linear, ClickUp | Proactive task inbox |
| **WebhooksPanel/Debug** | `webhooks{}` — endpoints, secret, payload format | Incoming webhook triggers |

### 🔔 NOTIFICATIONS GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **NotificationsTabbedPanel** | Alerts inbox + routing rules | Alert history + channel routing |
| **NotificationsPanel** | Per-channel notification preferences | Where notifications are delivered |
| **NotificationRoutingPanel** | Rule-based routing: severity → channel | Smart notification dispatch |

### ⏰ SCHEDULING GROUP  

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **CronJobsPanel** | `cron_jobs[]` — schedule (interval/cron/once), action (agent/shell), enabled, run history | Full cron job manager |
| **HeartbeatPanel** | `heartbeat.interval_secs`, `enabled`, model | Background reasoning heartbeat |

### 🔍 SEARCH GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **SearchPanel** | `search{}` — engine (disabled/managed/parallel/brave/querit), API keys, web_access_mode (all/custom/block), allowed_domains[] | Web search provider + site allowlist |

### 🔐 SECURITY GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **SecurityPanel** | `keyring{}` + `encryption{}` — storage mode (local_encrypted/os_keyring), PIN, master key rotation | Credential encryption |
| **SandboxSettingsPanel** | `sandbox{}` — backend, allowed paths, syscall policy | Code execution sandbox |
| **PermissionsPanel** | `autonomy.level` (supervised/informed/autonomous) | Agent permission tier |
| **ApprovalHistoryPanel** | Approval log — view/revoke past tool approvals | Tool consent audit log |

### 🎨 APPEARANCE/PERSONA GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **PersonaPanel** | `persona{}` — display_name, description, SOUL.md system prompt | Agent identity and personality |
| **AppearancePanel** | `theme{}` — light/dark/system, accent color, font size | UI theme |
| **MascotPanel** | `mascot{}` — Rive animation, visibility, position, audio enabled | Desktop mascot settings |

### 🛠️ DEVELOPER GROUP

| Panel | OpenHuman Backend | What it controls |
|---|---|---|
| **DeveloperOptionsPanel** | Debug flags, feature flags, experimental settings | Power user controls |
| **McpServerPanel** | `mcp_servers[]` — list/add/remove MCP servers, health status | MCP server registry |
| **AgentChatPanel** | Debug agent chat with raw model output | Agent conversation debugger |
| **LocalModelDebugPanel** | Ollama status, installed models, pull/delete | Local AI runtime debug |
| **EventLogPanel** | Internal event bus log — stream live events | System event viewer |
| **ModelHealthPanel** | Provider health checks — ping each configured model | Provider connectivity status |
| **MemorySyncPanel** | Memory sync status, last sync time, force sync | Memory source sync control |
| **MemoryDataPanel** | Browse/search memory docs, delete entries | Memory browser |
| **MemoryDebugPanel** | Memory tree structure, embedding stats | Memory system diagnostics |
| **AnalysisViewsPanel** | Brain activity charts, thought summaries | Agent introspection UI |
| **DevWorkflowPanel** | Workflow run history, skill runner | Developer workflow tools |
| **ScreenAwarenessDebugPanel** | Screen capture test, OCR output preview | Screen intelligence debug |
| **AutocompleteDebugPanel** | Autocomplete provider test, token counts | Autocomplete diagnostics |
| **VoiceDebugPanel** | STT/TTS test, audio device list | Voice pipeline debug |
| **WebhooksDebugPanel** | Webhook event log, test POST | Webhook debug |
| **ToolPolicyDiagnosticsPanel** | Tool policy decisions log | Tool access audit |

---

## Step 2 — What Locus Already Has

### ✅ Already Implemented (in `/setup` wizard)

| Setting | Status | Location |
|---|---|---|
| LLM Providers — add/list | ✅ Working | `handlers.py:render_llm`, `handle_llm_add` |
| Primary provider selection | ✅ Working | `handle_llm_primary`, `handle_llm_set_primary` |
| Workload routing (10 routes) | ✅ Working | `handle_llm_routes`, `handle_llm_route_set` |
| Local AI (Ollama) toggle | ✅ Working | `handle_llm_toggle_local` |
| Memory enabled toggle | ✅ Working | `handle_mem_toggle` |
| Memory tree toggle | ✅ Partial | `handle_mem_tree_toggle` (not wired to `/setup`) |
| Memory embedding dimensions | ✅ Partial | `handle_mem_dims` (not wired to `/setup`) |
| Channel toggles (7 channels) | ✅ Working | `handle_ch_toggle` |
| Search engine select | ✅ Working | `handle_tools_search_engine` |
| Browser toggle | ✅ Working | `handle_tools_toggle_browser` |
| Computer use toggle | ✅ Partial | `handle_tools_toggle_computer` (not wired) |
| Web access mode | ✅ Working | `handle_tools_web_access` |
| Agent auto-compact | ✅ Working | `handle_agent_toggle_compact` |
| Agent delegation | ✅ Working | `handle_agent_toggle_delegation` |
| Agent learning | ✅ Working | `handle_agent_toggle_learning` |
| Agent memory window | ✅ Working | `handle_agent_mem_window` |
| Voice STT/TTS select | ✅ Working | `handle_voice_select_stt/tts` |
| Voice always-on | ✅ Working | `handle_voice_toggle_always` |
| Cron toggle | ✅ Working | `handle_sched_toggle_cron` |
| Heartbeat toggle + interval | ✅ Working | `handle_sched_toggle_hb`, `handle_sched_hb_interval` |
| Scheduler gate mode | ✅ Working | `handle_sched_gate_mode` |
| Activity level 0-4 | ✅ Working | `handle_sched_activity` |
| Sandbox toggle + backend | ✅ Working | `handle_sec_toggle_sandbox`, `handle_sec_sandbox_backend` |
| CWD jail toggle | ✅ Working | `handle_sec_toggle_jail` |
| Storage mode | ✅ Working | `handle_sec_storage_mode` |
| Proxy toggle | ✅ Working | `handle_proxy_toggle` |
| Log level | ✅ Working | `handle_obs_log_level` |
| Cost tracking toggle | ✅ Working | `handle_obs_toggle_cost` |
| Analytics toggle | ✅ Working | `handle_obs_toggle_analytics` |
| Composio toggle | ✅ Working | `handle_int_toggle_composio` |
| Webhooks toggle | ✅ Working | `handle_int_toggle_webhooks` |
| Deployment (VPS) | ✅ Working | Full SSH deploy pipeline |

### ❌ Missing / Not Implemented Yet

| Setting | Priority | Notes |
|---|---|---|
| **Persona** — name, description, SOUL.md | 🔴 HIGH | Core identity, used in every agent turn |
| **Agent timeout (per-action)** | 🔴 HIGH | `agent_timeout_secs` setting |
| **Workspace confinement** | 🔴 HIGH | `workspace_only` + trusted roots |
| **Auto-approve tool allowlist** | 🔴 HIGH | `auto_approve[]` — view/remove |
| **Cron job management** | 🔴 HIGH | Add/list/run/remove named cron jobs |
| **MCP server management** | 🔴 HIGH | Add/list/remove MCP servers |
| **Search API key management** | 🔴 HIGH | Brave, Tavily, Exa key storage |
| **Autonomy level** (supervised/informed/autonomous) | 🔴 HIGH | Permission tier selector |
| **Max actions per hour** | 🔴 HIGH | Rate limit for autonomous mode |
| **Approval history** | 🟡 MED | View/revoke past tool approvals |
| **Memory sources** | 🟡 MED | Gmail, Notion, GitHub sync config |
| **Agent definitions** | 🟡 MED | Named agents with system prompts |
| **Notification routing** | 🟡 MED | Alert routing rules |
| **Task sources** | 🟡 MED | GitHub issues, Notion, Linear |
| **Composio routing** | 🟡 MED | Event → agent trigger rules |
| **Cost limits** | 🟡 MED | Daily/monthly spend caps |
| **Model health check** | 🟡 MED | Ping all configured providers |
| **Privacy settings** | 🟡 MED | Telemetry, data sharing consent |
| **Security — encryption mode** | 🟡 MED | local_encrypted vs OS keyring |
| **Voice hotkey config** | 🟡 MED | Push-to-talk / dictation hotkey |
| **Screen intelligence** | 🟠 LOW | Desktop-only feature |
| **Desktop companion** | 🟠 LOW | Desktop-only feature |
| **Mascot/Appearance** | 🟠 LOW | Desktop-only feature |
| **Wallet/Crypto** | 🟠 LOW | Web3 (future) |
| **Team management** | 🟠 LOW | Multi-user (future) |
| **Billing/Credits** | 🟠 LOW | Managed plans (future) |

---

## Step 3 — Logic for Each Missing Setting (N-Depth)

### S1: Persona (name, description, SOUL.md)
- **Config path**: `config.json → persona.display_name`, `persona.description`, `persona.soul_md` (file path or inline)
- **Agent effect**: Display name injected into system prompt; SOUL.md replaces/augments the default system prompt
- **Telegram flow**: Show current name/description → "Edit Name" prompts text reply → save to config
- **SOUL.md**: Store at `~/.locus/soul.md`; agent reads on every turn startup

### S2: Agent Timeout
- **Config path**: `config.json → agent.action_timeout_secs` (default: 120)
- **Agent effect**: Tool calls killed after N seconds; passed to `subprocess.run(timeout=...)`  
- **Telegram flow**: Show current value → preset buttons (30s/60s/120s/300s) → or type custom value

### S3: Workspace Confinement
- **Config path**: `config.json → agent.workspace_only` (bool) + `agent.trusted_roots[]`
- **Agent effect**: Tool registry intercepts `read`/`write`/`bash` — checks path against trusted roots
- **Telegram flow**: Toggle workspace_only → then list/add/remove trusted root paths via text reply

### S4: Auto-Approve Tool Allowlist
- **Config path**: `config.json → agent.auto_approve[]` (list of tool names)
- **Agent effect**: Tools in this list skip the approval gate and run silently
- **Telegram flow**: List current auto-approved tools → Remove button per tool → no Add (added via chat "Always allow" intent)

### S5: Cron Job Management
- **Config path**: `memory/store.db → cron_jobs` table (already exists in `core/memory.py`)
- **Agent effect**: A background cron thread checks due jobs and runs agent turns or shell commands
- **Telegram flow**: List jobs → Add (schedule + action text) → Toggle enable/disable → Delete → Run now

### S6: MCP Server Management
- **Config path**: `config.json → mcp_servers[]` — each with `{name, command, env}`
- **Agent effect**: MCP client spawns each server as subprocess, registers tools into ToolRegistry
- **Telegram flow**: List servers → Add (name + command) → Remove → Test (ping)

### S7: Search API Keys (Brave, Tavily, Exa)
- **Config path**: `.env → BRAVE_SEARCH_API_KEY`, `TAVILY_API_KEY`, `EXA_API_KEY`
- **Agent effect**: `web_search` tool selects provider based on available keys
- **Telegram flow**: Show configured/unconfigured → prompt to send API key via text → save to .env (masked)

### S8: Autonomy Level
- **Config path**: `config.json → agent.autonomy_level` = "supervised" | "informed" | "autonomous"
- **supervised**: Every tool call asks for approval
- **informed**: External-effect tools ask, read-only tools are silent
- **autonomous**: All tools run silently
- **Telegram flow**: 3-button selector → save immediately

### S9: Max Actions Per Hour
- **Config path**: `config.json → agent.max_actions_per_hour` (u32, default 1000)
- **Agent effect**: Counter resets every hour; agent pauses if exceeded
- **Telegram flow**: Preset buttons (100/500/1000/Unlimited) or custom number input

### S10: Approval History
- **Config path**: SQLite table `tool_approvals(id, tool_name, approved, ts, context)`
- **Telegram flow**: `/approvals` command → paginated list → Revoke button per entry

### S11: Memory Sources
- **Config path**: `config.json → memory.sources[]` = [{name, type (gmail/notion/github/slack), enabled, credentials}]
- **Agent effect**: Background sync thread pulls data from enabled sources into memory store
- **Telegram flow**: List sources → Toggle enable/disable → Add (type selection → API key prompt)

### S12: Named Agent Definitions
- **Config path**: `config.json → agents[]` = [{id, name, system_prompt, model, tools[], channels[]}]
- **Agent effect**: `locus agent --id <id>` selects named agent; different system prompt/model per agent
- **Telegram flow**: List agents → Create (name + system prompt) → Edit → Delete → Set as default

### S13: Notification Routing
- **Config path**: `config.json → notifications.routing[]` = [{severity, channel, keywords[]}]
- **Agent effect**: Alert dispatcher checks rules before sending
- **Telegram flow**: List rules → Add (severity selector + channel + keyword filter) → Remove

### S14: Task Sources
- **Config path**: `config.json → task_sources[]` = [{type (github/notion/linear), enabled, config}]
- **Agent effect**: Heartbeat checks sources, adds new items to agent's task queue
- **Telegram flow**: List sources → Toggle enable → Configure (repo URL, API key)

### S15: Cost Limits
- **Config path**: `config.json → cost.daily_limit_usd`, `cost.monthly_limit_usd`, `cost.warn_at_percent`
- **Agent effect**: Usage tracker compares running total; warns at threshold; blocks at limit
- **Telegram flow**: Show current spend → Set daily/monthly limit → set warning threshold

### S16: Model Health Check
- **Logic**: Ping each configured provider with a minimal test completion ("Say OK")
- **Telegram flow**: Button → runs health check in background → reports status per provider

### S17: Privacy Settings
- **Config path**: `config.json → privacy.telemetry_enabled`, `privacy.crash_reporting`
- **Telegram flow**: Toggles for each privacy dimension

### S18: Voice Hotkey
- **Config path**: `config.json → voice.dictation.hotkey` (e.g. "ctrl+shift+d")
- **Telegram flow**: Show current → Type new hotkey combo

---

## Step 4 — Execution Plan

### Architecture Principles (Locus Philosophy)
1. Every setting = a config key path (dot notation, e.g. `agent.autonomy_level`)
2. Every handler = a pure `async def handle_*(update, context)` function
3. Every category = a `render_*` function returning `(lines, actions)` for inline keyboard
4. All config persisted to `~/.locus/config.json` (atomic write via `save_config`)
5. All secrets in `~/.locus/.env` (never in config.json)
6. Every new handler registered in `CATEGORY_RENDERERS` dict OR as standalone callback
7. New categories are drop-in additions to the `CATEGORIES` list in `handle_setup`

### Files to Create/Modify

#### MODIFY: `setup_categories/handlers.py`
- Add handlers for: persona, agent_timeout, workspace_confinement, auto_approve, cron, mcp, search_keys, autonomy_level, max_actions, approval_history, memory_sources, named_agents, notification_routing, task_sources, cost_limits, model_health, privacy

#### MODIFY: `gateway/slash_commands.py`  
- Wire new callback prefixes: `persona:`, `cron:`, `mcp:`, `search:`, `autonomy:`, `approval:`, `memsrc:`, `nagent:`, `notif:`, `tsrc:`, `cost:`, `health:`, `priv:`
- Add new slash commands: `/approvals`, `/agents`, `/cron`, `/health`

#### MODIFY: `gateway/bot.py`
- Register new command handlers

#### MODIFY: `locus_cli/config.py`
- Add new config keys to `DEFAULT_CONFIG`
- Add new ENV_VAR_DEFS entries

#### CREATE: `core/cron_runner.py`
- Background thread that polls cron_jobs table and executes due jobs

#### CREATE: `core/mcp_client.py`  
- Spawn MCP server subprocesses, register their tools into ToolRegistry

#### CREATE: `core/approval_store.py`
- SQLite table for tool approval history

#### CREATE: `core/cost_tracker.py`
- Token usage counting, daily/monthly accumulation, limit enforcement

---

## Step 5 — Checklist (Loop Until Done)

### Phase A: Core Config Extensions
- [ ] `DEFAULT_CONFIG` additions for all new settings
- [ ] `ENV_VAR_DEFS` additions for new secrets (search keys, etc.)

### Phase B: Persona Settings
- [ ] `render_persona()` — show current name/description/soul.md status  
- [ ] `handle_persona_edit_name()` — text reply flow to update name
- [ ] `handle_persona_edit_desc()` — text reply flow to update description
- [ ] `handle_persona_reset_soul()` — reset to default system prompt
- [ ] Wire `persona:` prefix callbacks in `slash_commands.py`

### Phase C: Agent Access & Autonomy
- [ ] `render_agent_access()` — show workspace_only, trusted_roots, auto_approve, timeout
- [ ] `handle_autonomy_level()` — 3-button selector (supervised/informed/autonomous)
- [ ] `handle_max_actions()` — preset + custom input
- [ ] `handle_agent_timeout()` — preset + custom input
- [ ] `handle_workspace_toggle()` — boolean toggle
- [ ] `handle_trusted_root_add()` — text reply → path validation → save
- [ ] `handle_trusted_root_remove()` — per-root remove button
- [ ] `handle_auto_approve_remove()` — per-tool remove button
- [ ] Wire `autonomy:` and `agentaccess:` callbacks

### Phase D: Search & API Keys
- [ ] `render_search()` — show engine + configured keys + access mode
- [ ] `handle_search_set_engine()` — engine selector (disabled/brave/tavily/exa/searxng)
- [ ] `handle_search_set_key()` — text reply for API key → save to .env (masked)
- [ ] `handle_search_access_mode()` — all/custom/block selector
- [ ] Wire `search:` callbacks

### Phase E: Cron Job Manager
- [ ] `render_cron()` — list all jobs with next_run, status, enable toggle
- [ ] `handle_cron_add()` — schedule input (cron expr or natural language) + action
- [ ] `handle_cron_toggle()` — enable/disable per job
- [ ] `handle_cron_run()` — run job immediately
- [ ] `handle_cron_delete()` — remove job
- [ ] `core/cron_runner.py` — background thread with schedule checking
- [ ] Wire `cron:` callbacks + `/cron` command

### Phase F: MCP Server Manager
- [ ] `render_mcp()` — list servers, health status, tool count
- [ ] `handle_mcp_add()` — name + command input flow
- [ ] `handle_mcp_remove()` — per-server remove
- [ ] `handle_mcp_test()` — ping server, count tools
- [ ] `core/mcp_client.py` — stdio MCP client
- [ ] Wire `mcp:` callbacks

### Phase G: Cost Limits & Observability
- [ ] `render_cost()` — show current spend + limits
- [ ] `handle_cost_set_daily()` — number input
- [ ] `handle_cost_set_monthly()` — number input
- [ ] `handle_cost_set_warn()` — percentage selector
- [ ] `core/cost_tracker.py` — usage accumulation
- [ ] Wire `cost:` callbacks

### Phase H: Model Health & Privacy
- [ ] `handle_model_health()` — async ping all providers, report per-provider
- [ ] `render_privacy()` — show telemetry/crash toggles
- [ ] `handle_privacy_toggle_telemetry()` — boolean toggle
- [ ] Wire `health:` and `priv:` callbacks + `/health` command

### Phase I: Approval History
- [ ] `core/approval_store.py` — SQLite table
- [ ] `render_approvals()` — paginated approval log
- [ ] `handle_approval_revoke()` — remove from auto_approve list
- [ ] Wire `approval:` callbacks + `/approvals` command

### Phase J: Named Agents
- [ ] `render_agents()` — list all named agents
- [ ] `handle_agent_create()` — name + system prompt flow
- [ ] `handle_agent_set_default()` — set active agent
- [ ] `handle_agent_delete()` — remove agent
- [ ] Wire `nagent:` callbacks + `/agents` command

### Phase K: Memory Sources
- [ ] `render_memory_sources()` — list sources with enable toggle
- [ ] `handle_memsrc_toggle()` — enable/disable per source
- [ ] `handle_memsrc_add()` — type selector + credential flow
- [ ] Wire `memsrc:` callbacks

### Phase L: Integration into /setup flow
- [ ] Add new categories to `CATEGORIES` list: `persona`, `agent_access`, `search_keys`, `cron_jobs`, `mcp_servers`, `cost_limits`, `privacy`, `named_agents`, `memory_sources`
- [ ] Update `/setup` menu to show 20+ categories
- [ ] Update `/help` text

---

## Verification Plan

### Automated
- Run each handler with a mock Telegram update object
- Verify config file is updated correctly after each toggle
- Verify .env is updated correctly after API key save

### Manual
1. `/setup` → all categories visible
2. Navigate to each category → data shows correctly
3. Toggle each setting → verify config.json changes
4. Enter API key → verify .env masked correctly
5. Add cron job → verify it runs
6. Add MCP server → verify tools visible in agent

---

> [!NOTE]
> **Locus Modular Philosophy**: Every new category/handler is self-contained. Adding a new integration = add one `render_*` function + one `handle_*` function + one entry in `CATEGORY_RENDERERS` + one entry in `CATEGORIES`. Zero changes to other files required.
