# Locus Architecture & Implementation Plan

## Overview

Locus is a **headless AI OS** — CLI installed, Telegram operated. This plan extracts ALL of OpenHuman's backend functionality but adapts it for a headless, BYO (Bring Your Own), skippable-everything model.

---

## 1. Directory Structure

```
~/.locus/
├── config.yaml              # Main YAML config (all settings)
├── .env                     # Secrets (API keys, tokens)
├── memory/
│   ├── store.db             # SQLite memory store
│   ├── tree/                # Memory tree content (.md chunks)
│   └── vault/               # Obsidian-compatible vault
├── sessions/                # Agent session transcripts
├── cron/                    # Cron job store
├── integrations/            # OAuth tokens, integration state
├── tools/                   # MCP server configs
├── skills/                  # User-installed skills
├── logs/                    # Log files
└── workspace/               # Default action directory
```

---

## 2. Complete YAML Config Schema (`~/.locus/config.yaml`)

```yaml
# Locus Configuration — v1.0
# All fields are optional/skippable.
# BYO = Bring Your Own (no default service)

version: "1.0"

# ── LLM Providers ──────────────────────────────────────────────────────
cloud_providers:
  - id: "openai"
    type: "openai"            # openai | anthropic | google | openrouter | custom
    api_key_env: "OPENAI_API_KEY"
    base_url: ""
    default_model: "gpt-4o"
  - id: "anthropic"
    type: "anthropic"
    api_key_env: "ANTHROPIC_API_KEY"
    base_url: ""
    default_model: "claude-sonnet-4-20250514"
  - id: "google"
    type: "google"
    api_key_env: "GOOGLE_API_KEY"
    default_model: "gemini-2.0-flash"
  - id: "openrouter"
    type: "openrouter"
    api_key_env: "OPENROUTER_API_KEY"
    default_model: "openrouter/auto"

primary_cloud: "openai"

chat_provider: ""
reasoning_provider: ""
coding_provider: ""
agentic_provider: ""
memory_provider: ""
embeddings_provider: ""
heartbeat_provider: ""
learning_provider: ""
subconscious_provider: ""

local_ai:
  enabled: false
  base_url: "http://localhost:11434"
  ollama_num_ctx: 8192
  usage:
    chat: false
    reasoning: false
    coding: false
    embeddings: false
    memory: false

default_model: "gpt-4o"
default_temperature: 0.7
temperature_unsupported_models: ["o1*", "o3*", "o4*", "gpt-5*"]
output_language: ""

# ── Memory System ──────────────────────────────────────────────────────
memory:
  enabled: true
  storage_backend: "sqlite"
  content_dir: ""
  sync_interval_secs: 86400
  tree:
    enabled: true
    embedding_model: ""
    llm_backend: ""
    chunk_size: 3000
  sources:
    - type: "composio"
      id: "gmail"
      enabled: true
      sync_interval_secs: 0
    - type: "folder"
      path: "~/Documents"
      enabled: false

# ── Channels ───────────────────────────────────────────────────────────
channels:
  telegram:
    enabled: false
    stream_mode: "off"
    draft_update_interval_ms: 1000
    silent_streaming: true
    mention_only: false
  discord:
    enabled: false
    guild_id: ""
    channel_id: ""
    listen_to_bots: false
    mention_only: false
  slack:
    enabled: false
    channel_id: ""
  whatsapp:
    enabled: false
    backend: "cloud"
    phone_number_id: ""
    session_path: ""
  signal:
    enabled: false
    http_url: ""
    account: ""
    group_id: ""
  matrix:
    enabled: false
    homeserver: ""
    room_id: ""
  email:
    enabled: false
    imap_host: ""
    smtp_host: ""
  irc:
    enabled: false
    server: ""
    port: 6697
    nickname: ""
    channels: []
  lark:
    enabled: false
    app_id: ""
    use_feishu: false
    receive_mode: "websocket"
  dingtalk:
    enabled: false
    app_id: ""
  cli:
    enabled: true

# ── Web Search ─────────────────────────────────────────────────────────
search:
  enabled: true
  engine: "brave"
  brave_api_key_env: "BRAVE_SEARCH_API_KEY"
  searxng:
    base_url: ""
  tavily_api_key_env: "TAVILY_API_KEY"
  exa_api_key_env: "EXA_API_KEY"

# ── Browser Tools ──────────────────────────────────────────────────────
browser:
  enabled: false
  allowlist: []
  image_quality: 85
  max_screenshots_per_turn: 10
  computer_use:
    enabled: false
    backend: "native"

# ── MCP Servers ────────────────────────────────────────────────────────
mcp_servers:
  enabled: true
  servers:
    - name: "filesystem"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem"]
      enabled: true

# ── HTTP / Network ────────────────────────────────────────────────────
http_request:
  timeout_secs: 60
  max_concurrent: 10
curl:
  enabled: true
multimodal:
  max_file_size_mb: 20
  image_quality: "high"

# ── Agent Settings ─────────────────────────────────────────────────────
agent:
  default_model: ""
  default_temperature: 0.7
  max_tool_iterations: 50
  autonomy_level: 2
  context:
    budget_tokens: 32000
    auto_compact: true
    summarization_threshold: 0.8
  delegation:
    enabled: true
    max_sub_agents: 5
  learning:
    enabled: false
    reflection_interval_hours: 24
  skills:
    enabled: true
    auto_install: false

# ── Voice ──────────────────────────────────────────────────────────────
voice:
  enabled: false
  stt_provider: "whisper"
  tts_provider: "piper"
  voice_providers:
    - id: "elevenlabs"
      type: "elevenlabs"
      api_key_env: "ELEVENLABS_API_KEY"
      default_voice: "21m00Tcm4TlvDq8ikWAM"
  server:
    host: "127.0.0.1"
    port: 8080
    activation_mode: "push_to_talk"
  dictation:
    activation_mode: "manual"
    hotkey: "ctrl+shift+d"

# ── Scheduling ─────────────────────────────────────────────────────────
cron:
  enabled: true
heartbeat:
  enabled: false
  interval_secs: 3600
  provider: ""
scheduler_gate:
  enabled: true
  mode: "battery_aware"
  agent_activity_level: 2

# ── Security ───────────────────────────────────────────────────────────
security:
  sandbox:
    enabled: false
    backend: "none"
  resource_limits:
    max_processes: 50
    max_memory_mb: 2048
    max_disk_mb: 10240
  cwd_jail:
    enabled: false
  encryption:
    enabled: true
    keyring: true

# ── Proxy ──────────────────────────────────────────────────────────────
proxy:
  enabled: false
  http_proxy: ""
  https_proxy: ""
  socks_proxy: ""
  scope: "all"
  no_proxy: ["localhost", "127.0.0.1"]

# ── Observability ──────────────────────────────────────────────────────
observability:
  logging:
    level: "info"
    format: "plain"
  sentry:
    enabled: false
    dsn_env: "SENTRY_DSN"
  opentelemetry:
    enabled: false
    endpoint: ""
  cost_tracking:
    enabled: true
    dashboard: true

# ── Updates ────────────────────────────────────────────────────────────
update:
  channel: "stable"
  restart_strategy: "prompt"
  auto_check: true

# ── Integrations ───────────────────────────────────────────────────────
integrations:
  composio:
    enabled: false
    mode: "direct"
    api_key_env: "COMPOSIO_API_KEY"
  polymarket:
    enabled: false
    clob_api_key_env: "POLYMARKET_CLOB_API_KEY"
    clob_secret_env: "POLYMARKET_CLOB_SECRET"
    polygon_api_key_env: "POLYGON_API_KEY"
  webhooks:
    enabled: false
    port: 9090
```

---

## 3. Complete Env Var Schema (`~/.locus/.env`)

```bash
# ── LLM Providers ──────────────────────────────────────────────────────
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=...
DEEPSEEK_API_KEY=...
MISTRAL_API_KEY=...
TOGETHER_API_KEY=...
GROQ_API_KEY=...
PERPLEXITY_API_KEY=...
COHERE_API_KEY=...

# ── Local AI ────────────────────────────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434

# ── Messaging Channels ──────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_ALLOWED_USERS=123456789,987654321
TELEGRAM_HOME_CHANNEL=123456789
DISCORD_BOT_TOKEN=...
DISCORD_ALLOWED_USERS=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_ALLOWED_USERS=...
WHATSAPP_ACCESS_TOKEN=...
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_VERIFY_TOKEN=...
WHATSAPP_APP_SECRET=...
SIGNAL_HTTP_URL=http://localhost:8080
SIGNAL_ACCOUNT=+1234567890
MATRIX_HOMESERVER=https://matrix.example.com
MATRIX_ACCESS_TOKEN=...
MATRIX_ROOM_ID=!...
EMAIL_ADDRESS=locus@example.com
EMAIL_PASSWORD=app-password
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_ALLOWED_USERS=user@example.com
IRC_SERVER=irc.libera.chat
IRC_NICKNAME=locus-bot
IRC_SERVER_PASSWORD=...
IRC_NICKSERV_PASSWORD=...
IRC_SASL_PASSWORD=...
LARK_APP_ID=...
LARK_APP_SECRET=...
LARK_ENCRYPT_KEY=...
LARK_VERIFICATION_TOKEN=...
DINGTALK_APP_ID=...
DINGTALK_APP_SECRET=...
QQ_BOT_TOKEN=...

# ── Web Search ──────────────────────────────────────────────────────────
BRAVE_SEARCH_API_KEY=...
TAVILY_API_KEY=...
EXA_API_KEY=...
SEARXNG_BASE_URL=...

# ── MCP ────────────────────────────────────────────────────────
MCP_GITHUB_TOKEN=...
MCP_POSTGRES_CONNECTION_STRING=...

# ── Voice ─────────────────────────────────────────────────────
ELEVENLABS_API_KEY=...
OPENAI_TTS_API_KEY=...
AZURE_STT_API_KEY=...
AZURE_STT_REGION=...

# ── Security ──────────────────────────────────────────────────
SENTRY_DSN=https://...
OTEL_EXPORTER_ENDPOINT=http://...

# ── Integrations ──────────────────────────────────────────────
COMPOSIO_API_KEY=...
POLYMARKET_CLOB_API_KEY=...
POLYMARKET_CLOB_SECRET=...
POLYGON_API_KEY=...

# ── Proxy ────────────────────────────────────────────────────
HTTP_PROXY=http://proxy:8080
HTTPS_PROXY=http://proxy:8080
SOCKS_PROXY=socks5://proxy:1080
NO_PROXY=localhost,127.0.0.1,.local
```

---

## 4. Setup Flow State Machine

```
CLI PHASE (machine):                 TELEGRAM PHASE (bot):
┌──────────────────────┐              ┌──────────────────────────────┐
│ locus setup          │              │ /setup MAIN MENU             │
│                      │              │  1. 🤖 LLM Provider         │
│ 1. ~/.locus/ created │              │  2. 💾 Memory System        │
│ 2. Default config    │  ───auto──▶  │  3. 📱 Messaging Channels   │
│ 3. Gateway wizard    │    /setup    │  4. 🔧 Tools & Search       │
│ 4. "Msg your bot"    │    message   │  5. 🧠 Agent Settings       │
└──────────────────────┘              │  6. 🎤 Voice & Audio        │
                                      │  7. ⏰ Scheduling           │
                                      │  8. 🔒 Security             │
                                      │  9. 🌐 Proxy & Network      │
                                      │ 10. 📊 Observability        │
                                      │ 11. 🔄 Updates              │
                                      │ 12. 🔌 Integrations         │
                                      │ 13. ✅ Skip All             │
                                      │ 14. 📋 Summary & Done       │
                                      └──────────────────────────────┘
```

---

## 5. Full Telegram Commands

| Command | Args | Description |
|---------|------|-------------|
| `/setup` | [category] | Setup menu or direct jump |
| `/config` | — | Show full config |
| `/config_set` | KEY VAL | Set a value |
| `/config_get` | KEY | Read a value |
| `/config_check` | — | Missing/outdated check |
| `/config_migrate` | — | Add new defaults |
| `/provider` | — | List providers |
| `/provider_add` | TYPE KEY [MODEL] | Quick-add provider |
| `/provider_remove` | ID | Remove provider |
| `/model` | MODEL [--provider] | Switch model |
| `/search` | QUERY | Web search |
| `/tool_list` | — | List tools |
| `/mcp_add` | NAME CMD... | Add MCP server |
| `/mcp_remove` | NAME | Remove MCP |
| `/memory_status` | — | Memory system status |
| `/memory_sync` | [source] | Trigger sync |
| `/cron` | — | List cron jobs |
| `/cron_add` | SCHEDULE ACTION | Add cron |
| `/cron_remove` | ID | Remove cron |
| `/status` | — | System status |
| `/doctor` | — | Diagnostics |
| `/ping` | — | Liveness check |
| `/version` | — | Version |
| `/help` | — | Help |

---

## 6. Implementation Phases

- **Phase 1** (Week 1-2): Foundation — config system, CLI wizard, gateway setup, /setup menu
- **Phase 2** (Week 2-3): LLM Providers — provider CRUD, routing, adapters
- **Phase 3** (Week 3-4): Memory System — SQLite store, embedding, sync, sources
- **Phase 4** (Week 4-5): Tools & MCP — search, fetch, MCP client, filesystem tools
- **Phase 5** (Week 5-6): Agent Engine — loop, sessions, context, sub-agents
- **Phase 6** (Week 6-8): Advanced — voice, security, proxy, observability, updates

---

## 7. Architecture Patterns

### Config Priority
```
env vars > ~/.locus/.env > ~/.locus/config.yaml > built-in defaults
```

### Provider Resolution
```
1. workload-specific config → 2. primary_cloud → 3. first provider → 4. error
```

### Telegram Flow
```
[InlineKeyboard] → tap → instructions → reply value → save → confirm → return
```

### BYO Principle
```
NO defaults, NO OpenHuman-native services. Everything Bring Your Own.
```

---

## 8. Risks

| Risk | Mitigation |
|------|-----------|
| API key leak | Masked display, never in logs |
| User fatigue | Skippable, Quick Start path, progress persists |
| Message size limits | Paginated config, text file export |
| Setup state loss | Persisted to ~/.locus/setup_state.json |
| Missing config stale | Auto-check on every /setup entry |

---

## 9. Dependencies

```
pyyaml, python-dotenv, python-telegram-bot, httpx, httpx-sse,
openai, anthropic, sqlite-utils, cryptography, keyring,
beautifulsoup4, markdownify, lxml, aiofiles
```

---

## 10. Migration Path

1. Extend `locus_cli/setup.py` → CLI wizard → delegates to Telegram
2. Enhance `gateway/slash_commands.py` → 40+ commands
3. Create `gateway/setup/` package → 13 modular setup files
4. Create `core/` → engine, providers, memory, tools, scheduler
5. Update `pyproject.toml` → dependencies
6. Existing gateway bot cod