# OpenHuman Settings → Locus Port: Complete Analysis

## A. What Locus Has vs What's Missing (Complete Diff)

### Locus Categories (12) — Current Coverage

| # | Category | Status | Coverage |
|---|----------|--------|----------|
| 1 | **LLM Providers** | 🟡 Partial | Providers list ✓, routing ✓, local AI ✓. Missing: per-workload temperature/vision, test model, background loop controls, usage ledger, provider chip UI for 10+ providers |
| 2 | **Memory** | 🟡 Partial | SQLite backend ✓, basic doc CRUD ✓, FTS-like search ✓. Missing: embedding config, memory tree (chunking, LLM extractor/summarizer), sync interval, memory sources, agentmemory, agent activity level |
| 3 | **Channels** | 🟡 Partial | Platform registry ✓, CLI setup for Telegram/Discord/Slack/Email ✓. Missing: actual adapters for 12+ channel types, stream mode, message timeout, channel permissions |
| 4 | **Tools & Search** | 🟡 Partial | Web search ✓, web fetch ✓, bash/filesystem tools ✓. Missing: browser/computer_use config, screen intelligence, MCP server UI, tool permissions, multimodal config |
| 5 | **Agent Settings** | 🟡 Partial | Max iterations ✓, context budget ✓, auto-compact ✓, delegation ✓, learning ✓. Missing: memory context window, parallel tools, tool dispatcher, agent timeout, channel permissions, orchestrator model config |
| 6 | **Voice** | 🔴 Stub | Toggle only. Missing: STT/TTS provider selection, Whisper/Piper/ElevenLabs, dictation, push-to-talk, VAD, wake word |
| 7 | **Scheduling** | 🔴 Stub | Cron/heartbeat/gate toggles. Missing: heartbeat interval, inference toggle, meeting/reminder lookahead, subconscious mode, cron CRUD, scheduler gate battery/cpu thresholds |
| 8 | **Security** | 🔴 Stub | Sandbox/jail/encryption toggles. Missing: auto_approve, trusted roots, forbidden paths, storage mode (keyring), consent flow, resource limits config |
| 9 | **Proxy** | 🔴 Stub | Toggle + scope only. Missing: URL configs, no_proxy, per-service proxy |
| 10 | **Observability** | 🔴 Stub | Logging/sentry/OTEL/cost toggles. Missing: event stream, model health dashboard, cost dashboard, usage ledger |
| 11 | **Updates** | 🟢 Minimal | Channel/strategy/auto-check ✓ — adequate for headless |
| 12 | **Integrations** | 🔴 Stub | Composio/webhooks/polymarket/gitbooks toggles. Missing: composio routing mode, task sources, capability providers, webhook triggers |

### Entire Sections Missing from Locus

These OpenHuman sections have **no Locus equivalent at all**:

1. **Persona** — Display name, description, SOUL.md personality editor, reset/default badge
2. **Mascot / Appearance** — Face, avatar, character selection
3. **Account** — Profile, team, privacy (telemetry), security (keychain), migration (import/export)
4. **Screen Intelligence** — Capture policy, vision model, baseline FPS, allowlist/denylist, panic hotkey
5. **Autocomplete** — Enable, debounce, max chars, style preset, disabled apps
6. **Heartbeat Panel** (standalone) — Background loop controls + loop map
7. **Agent Chat Panel** — Model override, temperature override, test message UI
8. **Cron Jobs CRUD** — List/create/edit/delete/enable/disable/run jobs
9. **Search Engine Panel** — Engine radio, per-engine API keys, web access mode, allowed domains
10. **Tools Panel** — Per-category tool toggles (Core, File, Dev, Integrations)
11. **Voice Panel** — Full provider chip grid, routing selectors, test buttons
12. **Privacy Panel** — Capability catalog, analytics toggle, auto-handoff meeting toggle
13. **Security Panel** — Storage mode badge, consent grant/revoke
14. **Cost Dashboard** — Daily/monthly limits, warning thresholds, model pricing registry
15. **Crypto** — Recovery phrase, wallet balances
16. **Developer Options** — 17 debug/management panels (devOnly in OH)
17. **Billing** — Web-only deep link

---

## B. Expanded DEFAULT_CONFIG — Complete Schema (355 fields)

Full schema at: `locus-os/locus_cli/config.py` → replace `DEFAULT_CONFIG` with expanded v2.

**Key new top-level sections** (see inline comments for field details):
- `profile` — display_name, description, soul_md
- `context` — microcompact, autocompact, summarizer, session_memory_window
- `orchestrator` — model
- `teams` — {team_name: {lead_model, agent_model}}
- `model_routes` — [{provider, model, task, temperature, vision}]
- `embedding_routes` — [{provider, model, dimensions}]
- `autonomy` — level, allowed_commands, forbidden_paths, auto_approve, trusted_roots, max_cost
- `sandbox` — backend, firejail_args
- `runtime` — kind, docker {image, network, memory_limit_mb, cpu_limit}
- `cost` — daily_limit_usd, monthly_limit_usd, prices, dashboard
- `model_registry` — [{id, provider, cost_per_1m_output, vision}]
- `scheduler_gate` — battery_floor, cpu thresholds, require_ac_power
- `task_sources` — enabled, default_interval_secs, max_tasks_per_fetch
- `meet` — auto_join/summarize policies
- `node`, `runtime_python` — versioned runtime configs
- `capability_providers` — [{id, display_name, trust_state, enabled}]
- `agent_registry` — agents map

**Expanded existing sections:**
- `memory` → +embedding config, +tree config (extractor, summarizer, chunk_size), +agentmemory
- `channels` → +15 platform configs (full OH surface), +stream_mode per channel
- `search` → +brave/tavily/exa API key fields, +web_access_mode, +allowed_domains
- `voice` → +full server config, +dictation, +VAD, +wake_word
- `agent.learning` → +full ReflectionConfig (source, stability, episodic, STM, compaction)
- `agent` → +parallel_tools, +tool_dispatcher, +memory_context_window, +channel_permissions, +timeout
- `security` → +storage_mode, +resource_limits (processes/memory/disk)
- `observability` → +cost_tracking dashboard, +analytics_enabled
- `proxy` → +http_proxy, https_proxy, all_proxy, services list
- `integrations` → +composio mode, api_key
- `heartbeat` → +inference_enabled, context_budget, notification toggles, subconscious_mode

**Existing Locus fields preserved**: 75 keys kept intact.
**New fields added**: ~280.
**Excluded**: OH-native managed service URLs, billing/payments, dev-only debug panels.

---

## C. Per-Category Sub-Settings with Callback Data Schema

### 1. LLM Providers (`scat:llm_providers`)
Current: `llm:add`, `llm:primary`, `llm:routes`, `llm:toggle_local`

| New Callback | UI Element |
|---|---|
| `llm:provider:openai` .. `llm:provider:xai` | Provider auth chip toggle |
| `llm:apikey:PROVIDER` | API key text input |
| `llm:model:PROVIDER` | Model name text input |
| `llm:test:PROVIDER` | Test model button |
| `llm:routing_mode:managed/own/advanced` | Routing mode selector cards |
| `llm:route:chat/reasoning/coding/agentic/memory/heartbeat/learning/subconscious` | Per-workload model picker |
| `llm:route:temp:PROVIDER` | Temperature slider (0-2, step 0.05) |
| `llm:route:vision:PROVIDER` | Vision checkbox |
| `llm:bg:heartbeat/subconscious/calendar/cron/notifications/external_delivery` | Background loop toggles |
| `llm:bg:interval:VALUE` | Heartbeat interval selector |
| `llm:bg:meeting_lookahead:VALUE` | Meeting lookahead selector |
| `llm:bg:tick_now` | Immediate planner tick |

### 2. Memory (`scat:memory`)
Current: `mem:toggle`

| New Callback | UI Element |
|---|---|
| `mem:backend:sqlite/agentmemory` | Backend radio |
| `mem:embeddings:auto` | Toggle embeddings |
| `mem:embed:dimensions:VALUE` | Embedding dimensions num input |
| `mem:sync:VALUE` | Sync interval secs num input |
| `mem:tree:chunk_size:VALUE` | Chunk size num input |
| `mem:score:VALUE` | Min relevance score (0.0-1.0) |

### 3. Channels (`scat:channels`)
Current: `ch:toggle:NAME`

| New Callback | UI Element |
|---|---|
| `ch:token:NAME` | Bot token password input |
| `ch:users:NAME` | Allowed users CSV input |
| `ch:channel:NAME` | Channel ID text input |
| `ch:stream:NAME:off/partial` | Stream mode selector |
| `ch:timeout:VALUE` | Message timeout num input |

### 4. Tools & Search (`scat:tools_search`)
Current: `tools:toggle_search`, `tools:toggle_browser`, `tools:mcp` (stub)

| New Callback | UI Element |
|---|---|
| `tools:search:engine:brave/tavily/exa/searxng/none` | Engine radio |
| `tools:search:key:VAR` | Per-engine API key input |
| `tools:search:access:all/custom/block` | Web access mode radio |
| `tools:browser:quality:VALUE` | Image quality (0-100) |
| `tools:browser:max_ss:VALUE` | Max screenshots/turn |
| `tools:mcp:add` | MCP server form |
| `tools:mcp:remove:ID` | Remove MCP |
| `tools:mcp:toggle:ID` | Toggle MCP server |

### 5. Agent Settings (`scat:agent`)
Current: `agent:toggle_compact`, `agent:toggle_delegation`, `agent:toggle_learning`

| New Callback | UI Element |
|---|---|
| `agent:iterations:VALUE` | Max iterations num input |
| `agent:timeout:VALUE` | Agent timeout secs |
| `agent:parallel` | Toggle parallel tools |
| `agent:parallel:max:VALUE` | Max parallel count |
| `agent:context:budget:VALUE` | Context budget tokens |
| `agent:mem_window:balanced` | Memory window selector |
| `agent:learning:reflection` | Toggle reflection |
| `agent:learning:source:local/cloud` | Reflection source |

### 6. Voice (`scat:voice`)
Current: `voice:toggle`

| New Callback | UI Element |
|---|---|
| `voice:stt:cloud/whisper/deepgram` | STT provider select |
| `voice:stt:whisper_model:VALUE` | Whisper model selector |
| `voice:tts:cloud/piper/elevenlabs` | TTS provider select |
| `voice:tts:piper_voice:VALUE` | Piper voice selector |
| `voice:tts:test` | Test TTS button |
| `voice:always_on` | Toggle always-on listening |
| `voice:wake_word:VALUE` | Wake word text input |
| `voice:activation:tap/push` | Activation mode radio |
| `voice:hotkey:VALUE` | Hotkey text input |
| `voice:dictation` | Toggle dictation |
| `voice:dictation:mode:toggle/push` | Dictation activation |

### 7. Scheduling (`scat:scheduling`)
Current: `sched:toggle_cron`, `sched:toggle_hb`

| New Callback | UI Element |
|---|---|
| `sched:hb:interval:VALUE` | Heartbeat interval mins |
| `sched:gate:mode:auto/always/off` | Gate mode radio |
| `sched:gate:battery:VALUE` | Battery floor % |
| `sched:activity:0/1/2/3/4` | Activity level radio |
| `sched:cron:add` | Create cron job form |
| `sched:cron:edit:ID` | Edit cron job |
| `sched:cron:delete:ID` | Delete cron job |
| `sched:cron:run:ID` | Run cron job now |
| `sched:cron:toggle:ID` | Enable/disable cron |

### 8. Security (`scat:security`)
Current: `sec:toggle_sandbox`, `sec:toggle_jail`

| New Callback | UI Element |
|---|---|
| `sec:sandbox:backend:firejail/docker/none` | Sandbox backend select |
| `sec:storage:os_keyring/local_encrypted` | Storage mode select |
| `sec:consent:grant` | Grant consent button |
| `sec:consent:revoke` | Revoke consent button |
| `sec:limits:processes:VALUE` | Max processes num |
| `sec:limits:memory:VALUE` | Max memory MB num |
| `sec:auto_approve:add:NAME` | Add auto-approve tool |
| `sec:auto_approve:remove:NAME` | Remove auto-approve |

### 9. Proxy (`scat:proxy`)
Current: `proxy:toggle`

| New Callback | UI Element |
|---|---|
| `proxy:http:VALUE` | HTTP proxy URL input |
| `proxy:https:VALUE` | HTTPS proxy URL input |
| `proxy:all:VALUE` | ALL proxy URL input |
| `proxy:no_add:HOST` | Add no_proxy entry |
| `proxy:no_remove:HOST` | Remove no_proxy entry |
| `proxy:scope:environment/locus/services` | Scope radio |

### 10. Observability (`scat:observability`)
Current: `obs:toggle_cost`

| New Callback | UI Element |
|---|---|
| `obs:log:level:debug/info/warning/error` | Log level radio |
| `obs:log:format:plain/json` | Log format radio |
| `obs:sentry:dsn:VALUE` | Sentry DSN input |
| `obs:analytics` | Toggle analytics |
| `obs:daily_limit:VALUE` | Daily cost limit $ |
| `obs:monthly_limit:VALUE` | Monthly cost limit $ |

### 11. Updates (`scat:updates`)
Current: `upd:channel`

| New Callback | UI Element |
|---|---|
| `upd:channel:stable/beta/nightly` | Channel radio |
| `upd:restart:prompt/auto/never` | Restart strategy radio |
| `upd:auto_check` | Toggle auto-check |

### 12. Integrations (`scat:integrations`)
Current: `int:toggle_composio`, `int:toggle_webhooks`

| New Callback | UI Element |
|---|---|
| `int:composio:mode:managed/direct` | Composio routing mode radio |
| `int:composio:key:VALUE` | Composio API key input |
| `int:webhooks:port:VALUE` | Webhook port num input |

---

## D. Priority Order — Maximum Functional Impact

### Tier 1 — Core Functionality (Build First)
*Without these, Locus cannot function meaningfully.*

1. **LLM Providers — Per-workload routing** (`llm:route:*`, `llm:route:temp:*`, `llm:route:vision:*`)
   - Why: Every user needs to differentiate model quality per task (cheap for chat, expensive for coding)
   - Files: `locus_cli/config.py` → DEFAULT_CONFIG, `core/agent.py` → resolve_provider(), `setup_categories/handlers.py` → render_llm() + new handler functions, `gateway/slash_commands.py` → new callback routing

2. **Agent Settings — Full config surface** (`agent:*` callbacks)
   - Why: max_tool_iterations, timeout, parallel tools, context budget directly impact agent behavior quality
   - Files: `setup_categories/handlers.py` → render_agent() expanded, `config.py` → defaults update

3. **Tools & Search — Engine selection + API keys** (`tools:search:engine:*`, `tools:search:key:*`)
   - Why: Web search is the most-used tool. Currently hardcoded to Brave with no UI to change.
   - Files: `setup_categories/handlers.py` → render_tools(), `core/tools.py` → web_search()

### Tier 2 — Daily Usability (Build Second)
*These significantly improve the user experience.*

4. **Scheduling — Heartbeat config + cron CRUD** (`sched:hb:*`, `sched:cron:*`)
   - Why: Background agent loop enables proactive behaviors (digests, reminders)

5. **Channels — Full per-platform config** (`ch:token:*`,`ch:users:*`, `ch:stream:*`)
   - Why: Users need to configure tokens, allowlists, and stream modes per platform
   - Files: `gateway/setup_gateway.py` → _PLATFORMS expanded, `setup_categories/handlers.py` → render_channels()

6. **Memory — Embeddings + tree config** (`mem:embed:*`, `mem:tree:*`, `mem:sync:*`)
   - Why: Embedding quality directly impacts memory search relevance
   - Files: `core/memory.py` → config integration, `setup_categories/handlers.py` → render_memory()

7. **Voice — Provider selection** (`voice:stt:*`, `voice:tts:*`)
   - Why: Voice is a flagship feature; provider selection is the minimum viable config
   - Files: `config.py` → expand voice config, `setup_categories/handlers.py` → render_voice()

### Tier 3 — Polish & Security (Build Third)
*Important for safety and completeness but non-blocking.*

8. **Security — Sandbox backend, storage mode, consent** (`sec:*`)
9. **Proxy — Full URL config** (`proxy:*`)
10. **Observability — Cost limits, log level** (`obs:*`)
11. **Integrations — Composio routing** (`int:composio:mode:*`)
12. **Updates — Channel/strategy** (`upd:channel:*`)
13. **Background Loop Controls** (`llm:bg:*`) — tied to LLM Providers UI

### Tier 4 — Nice-to-Have (Build Last)
*Lowest functional impact for headless BYO.*

14. Persona / SOUL.md editor
15. Mascot / Appearance settings
16. Screen Intelligence config
17. Autocomplete config
18. Agent Chat panel
19. Privacy panel / capability catalog
20. Developer options (all 17 debug panels)
21. Crypto / wallet

---

## Key Architectural Dependencies

### Config Migration Path
```python
# 1. Expand DEFAULT_CONFIG in config.py → add all ~280 new fields
# 2. Update load_config() deep_merge to handle v1→v2 schema migration
# 3. Add schema migration version check:
#    if config["schema_version"] == 0:
#        config = migrate_v1_to_v2(config)
#        config["schema_version"] = 1
#        save_config(config)
```

### Handler Pattern for Each New Callback
```python
# Template in setup_categories/handlers.py
async def handle_sched_hb_interval(update, context) -> None:
    """Handle sched:hb:interval:<minutes> callback."""
    query = update.callback_query
    await query.answer()
    minutes = int(query.data.split(":")[-1])
    config = load_config()
    config["heartbeat"]["interval_minutes"] = minutes
    config["heartbeat"]["interval_secs"] = minutes * 60
    save_config(config)
    await query.edit_message_text(
        f"💓 Heartbeat interval set to *{minutes} min*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀ Back", callback_data="scat:scheduling")
        ]])
    )
```

### Expected File Changes Summary
| File | Changes |
|------|---------|
| `locus_cli/config.py` | Expand DEFAULT_CONFIG (~280 new keys), add migration helper |
| `setup_categories/handlers.py` | Expand all 12 render functions, ~80 new async handle_* functions |
| `gateway/slash_commands.py` | Add ~100 new callback routes in handle_setup_callback() |
| `core/agent.py` | Update resolve_provider() to use model_routes |
| `core/tools.py` | Dynamic search engine selection from config |
| `core/memory.py` | Integrate embedding dimensions, tree config |
| `locus_cli/setup.py` | Update SETUP_CATEGORIES to match new callback schema |
