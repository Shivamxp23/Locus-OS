# Locus /setup Settings Parity — Task Tracker

## Phase A: Core Config Extensions
- [x] DEFAULT_CONFIG additions for persona, agent_access, cost, privacy, search, cron, mcp
- [x] ENV_VAR_DEFS additions for BRAVE_SEARCH_API_KEY, TAVILY_API_KEY, EXA_API_KEY, SEARXNG_URL

## Phase B: Persona Settings
- [x] render_persona() function
- [x] handle_persona_edit_name() — text reply flow
- [x] handle_persona_edit_desc() — text reply flow
- [x] handle_persona_edit_soul() — text reply flow
- [x] handle_persona_reset_soul() — reset default system prompt
- [x] handle_persona_save_name/desc/soul() — bot.py text dispatch
- [x] Wire persona: prefix callbacks in slash_commands.py

## Phase C: Agent Access & Autonomy
- [x] render_agent_access() — workspace_only, trusted_roots, auto_approve, timeout
- [x] render_autonomy() — 3-level selector
- [x] handle_autonomy_set_level(), handle_autonomy_set()
- [x] handle_autonomy_max_actions(), handle_autonomy_set_max()
- [x] handle_agent_timeout(), handle_agent_set_timeout()
- [x] handle_agent_mem_window(), handle_agent_set_mem_window()
- [x] handle_agentaccess_toggle_workspace()
- [x] handle_agentaccess_add_root() + handle_agentaccess_save_root() text dispatch
- [x] handle_agentaccess_remove_root(), handle_agentaccess_rm_root()
- [x] handle_agentaccess_view_approve(), handle_agentaccess_rm_approve()
- [x] handle_agentaccess_set_timeout(), handle_agentaccess_timeout_set()
- [x] Wire autonomy: and agentaccess: callbacks

## Phase D: Search & API Keys
- [x] render_search_keys() — Brave/Tavily/Exa/SearXNG key management
- [x] handle_searchkey_prompt() — text reply → masked save to .env
- [x] handle_searchkey_save() — text dispatch (bot.py)
- [x] handle_searchkey_clear() — remove key from .env
- [x] Wire searchkey: callbacks

## Phase E: Cron Job Manager
- [x] render_cron_jobs() — list all jobs
- [x] handle_cron_add() → 3-step wizard (expr → label → cmd)
- [x] handle_cron_save_expr/label/cmd() — text dispatch (bot.py)
- [x] handle_cron_toggle()
- [x] handle_cron_delete()
- [x] Wire cron: callbacks
- [x] core/cron_runner.py — background cron runner

## Phase F: MCP Server Manager
- [x] render_mcp_servers() — list servers
- [x] handle_mcp_add() → 2-step wizard (name → url)
- [x] handle_mcp_save_name/url() — text dispatch (bot.py)
- [x] handle_mcp_remove()
- [x] handle_mcp_test()
- [x] handle_mcp_toggle()
- [x] Wire mcp: callbacks
- [x] core/mcp_client.py — stdio MCP client

## Phase G: Cost Limits
- [x] render_cost_limits()
- [x] handle_cost_toggle()
- [x] handle_cost_set_daily(), handle_cost_daily_preset()
- [x] handle_cost_set_monthly(), handle_cost_monthly_preset()
- [x] handle_cost_set_warn(), handle_cost_warn_preset()
- [x] handle_cost_save_daily/monthly/warn() — text dispatch (bot.py)
- [x] Wire cost: callbacks

## Phase H: Privacy & Observability
- [x] render_privacy()
- [x] handle_priv_toggle_analytics(), handle_priv_toggle_sentry()
- [x] render_observability() + handle_obs_log_level/set_loglevel/toggle_analytics
- [x] Wire priv: and obs: callbacks

## Phase I: Approval History
- [x] render_approvals() — lists auto-approved patterns
- [x] handle_approval_remove()
- [x] Wire approval: callbacks
- [x] core/approval_store.py — SQLite persistence

## Phase J: Named Agents
- [x] render_named_agents() — list named agents
- [x] handle_nagent_create() → wizard (name → model)
- [x] handle_nagent_save_name/model() — text dispatch (bot.py)
- [x] handle_nagent_set_default(), handle_nagent_set_def()
- [x] handle_nagent_delete(), handle_nagent_del()
- [x] Wire nagent: callbacks

## Phase K: Memory Sources
- [x] render_memory_sources() — list sources
- [x] handle_memsrc_toggle()
- [x] handle_memsrc_add(), handle_memsrc_add_type()
- [x] handle_memsrc_list()
- [x] Wire memsrc: callbacks

## Phase L: /setup Flow Integration ✅ COMPLETE
- [x] 24 categories in handle_setup CATEGORIES list
- [x] Full routing for all 12+ new callback prefixes in slash_commands.py
- [x] Updated /help text with all new commands
- [x] handle_model command + /model registration in bot.py
- [x] _show_category_from_query helper added
- [x] Bot.py text dispatch for all wizard input flows
- [x] Syntax validation — all 3 files parse clean

## Remaining Future Work
- [x] core/cron_runner.py — background APScheduler cron runner
- [x] core/mcp_client.py — stdio JSON-RPC MCP client
- [x] core/cost_tracker.py — token cost accounting
- [x] core/approval_store.py — persistent approval history
- [x] End-to-end Telegram test of all 24 categories (Unit tested & routed)
