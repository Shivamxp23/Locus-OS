# Locus OS — Feature Scaffold Build-Out

Build hollow/stub Python modules for **every feature** borrowed from the three
reference codebases (hermes-agent, openhuman, pi), wired to the existing
`locus_cli/config.py` `DEFAULT_CONFIG` schema and SETTINGS.md.

---

## Background

Locus OS currently has a partial core (`core/`) with:
- `agent.py` — turn loop + LLM provider
- `memory.py` / `memory_manager.py` — SQLite + Neo4j + holographic backends
- `cost_tracker.py` — token budgeting
- `cron_runner.py` — cron jobs
- `mcp_client.py` — MCP stdio/HTTP servers
- `tools.py` — file/shell builtins
- `approval_store.py` — security approvals
- `deployment.py` — SSH / VPS deploy

Gaps: voice, web search, browser, screen intelligence, channels (all 12+ platforms),
heartbeat, scheduler gate, task sources, skills, subagent delegation, proxy,
observability, multimodal, computer-use, coding-agent pipeline (Pi), context
compression, streaming, dictation, integrations, TUI/display layer.

---

## Proposed File Structure

All new files land under `locus-os/core/` unless otherwise noted.  
`locus_cli/` gets new sub-packages for slash-command setup categories.

```
locus-os/
├── core/
│   ├── search/
│   │   ├── __init__.py           [NEW] Search router (brave/tavily/exa/searxng/seltz)
│   │   ├── brave.py              [NEW] Brave Search adapter
│   │   ├── tavily.py             [NEW] Tavily adapter
│   │   ├── exa.py                [NEW] Exa adapter
│   │   ├── searxng.py            [NEW] SearXNG self-hosted adapter
│   │   └── firecrawl.py          [NEW] Firecrawl web-extract adapter
│   ├── browser/
│   │   ├── __init__.py           [NEW] Browser manager (session factory)
│   │   ├── playwright_backend.py [NEW] Playwright local browser
│   │   ├── browserbase.py        [NEW] Browserbase cloud backend
│   │   └── screenshot.py         [NEW] Screenshot capture + vision encode
│   ├── voice/
│   │   ├── __init__.py           [NEW] Voice router
│   │   ├── stt/
│   │   │   ├── __init__.py       [NEW] STT provider router
│   │   │   ├── whisper.py        [NEW] Local whisper (faster-whisper)
│   │   │   ├── openai_stt.py     [NEW] OpenAI Whisper API
│   │   │   ├── groq_stt.py       [NEW] Groq STT
│   │   │   └── azure_stt.py      [NEW] Azure Cognitive STT
│   │   ├── tts/
│   │   │   ├── __init__.py       [NEW] TTS provider router
│   │   │   ├── piper.py          [NEW] Local Piper TTS
│   │   │   ├── elevenlabs.py     [NEW] ElevenLabs TTS
│   │   │   ├── openai_tts.py     [NEW] OpenAI TTS
│   │   │   └── edge_tts.py       [NEW] Edge TTS (free, local)
│   │   └── dictation.py          [NEW] Push-to-talk dictation mode
│   ├── channels/
│   │   ├── __init__.py           [NEW] Channel registry + dispatcher
│   │   ├── base.py               [NEW] Abstract channel interface
│   │   ├── telegram.py           [NEW] Telegram bot (polling + webhook)
│   │   ├── discord.py            [NEW] Discord bot
│   │   ├── slack.py              [NEW] Slack Socket Mode bot
│   │   ├── whatsapp.py           [NEW] WhatsApp Cloud API
│   │   ├── signal.py             [NEW] Signal via signal-cli HTTP
│   │   ├── matrix.py             [NEW] Matrix Synapse client
│   │   ├── email_channel.py      [NEW] IMAP/SMTP email bot
│   │   ├── lark.py               [NEW] Lark / Feishu bot
│   │   ├── dingtalk.py           [NEW] DingTalk bot
│   │   ├── imessage.py           [NEW] iMessage (macOS AppleScript)
│   │   ├── irc.py                [NEW] IRC bot
│   │   ├── mattermost.py         [NEW] Mattermost bot
│   │   ├── teams.py              [NEW] Microsoft Teams bot
│   │   ├── google_chat.py        [NEW] Google Chat bot
│   │   └── streaming.py          [NEW] Token streaming helpers (edit-based)
│   ├── heartbeat/
│   │   ├── __init__.py           [NEW] Heartbeat daemon
│   │   ├── subconscious.py       [NEW] Subconscious background loop
│   │   └── notification.py       [NEW] Heartbeat notification delivery
│   ├── scheduler/
│   │   ├── __init__.py           [NEW] Scheduler gate (battery/CPU guard)
│   │   └── task_sources.py       [NEW] Proactive task queue from external sources
│   ├── skills/
│   │   ├── __init__.py           [NEW] Skills registry
│   │   ├── loader.py             [NEW] Load/install skills from disk + hub
│   │   └── working_memory.py     [NEW] Working memory extraction from skills
│   ├── delegation/
│   │   ├── __init__.py           [NEW] Sub-agent orchestrator
│   │   ├── subagent.py           [NEW] Child agent lifecycle
│   │   └── coding_agent.py       [NEW] Pi-style coding agent pipeline
│   ├── context/
│   │   ├── __init__.py           [NEW] Context manager
│   │   ├── compactor.py          [NEW] Auto-compact + microcompact (OpenHuman pattern)
│   │   ├── compression.py        [NEW] Hermes-style context compression
│   │   └── token_counter.py      [NEW] Token counting utilities
│   ├── multimodal/
│   │   ├── __init__.py           [NEW] Multimodal attachment handler
│   │   ├── image.py              [NEW] Image encode/decode + vision
│   │   └── file_handler.py       [NEW] File upload/parse (PDF, DOCX, etc.)
│   ├── screen/
│   │   ├── __init__.py           [NEW] Screen intelligence (desktop only)
│   │   ├── capture.py            [NEW] Screen capture (hybrid/always/on-demand)
│   │   └── vision.py             [NEW] Frame analysis with vision model
│   ├── computer_use/
│   │   ├── __init__.py           [NEW] Computer-use backend router
│   │   ├── native.py             [NEW] Native OS automation (pyautogui)
│   │   └── vnc.py                [NEW] VNC-based computer use
│   ├── proxy.py                  [NEW] Proxy configuration + injection
│   ├── observability.py          [NEW] Sentry + OTEL + structured logging
│   ├── session_manager.py        [NEW] Multi-session lifecycle + reset
│   ├── learning/
│   │   ├── __init__.py           [NEW] Learning / reflection system
│   │   ├── reflector.py          [NEW] End-of-session reflection LLM call
│   │   ├── user_profile.py       [NEW] Persistent user profile (USER.md)
│   │   └── tool_tracker.py       [NEW] Tool usage tracking
│   ├── integrations/
│   │   ├── __init__.py           [NEW] Integration registry
│   │   ├── composio.py           [NEW] Composio toolkit bridge
│   │   ├── polymarket.py         [NEW] Polymarket prediction market
│   │   └── webhooks.py           [NEW] Outbound webhook server
│   ├── coding/
│   │   ├── __init__.py           [NEW] Coding agent pipeline (Pi)
│   │   ├── file_ops.py           [NEW] Read/write/patch file operations
│   │   ├── shell_exec.py         [NEW] Shell command execution
│   │   └── git_ops.py            [NEW] Git operations (status/add/commit/push)
│   └── display/
│       ├── __init__.py           [NEW] Display/UI layer
│       ├── progress.py           [NEW] Tool progress rendering
│       ├── streaming_tui.py      [NEW] Pi-style streaming terminal UI
│       └── themes.py             [NEW] Skin/theme system
├── locus_cli/
│   ├── setup_categories/         [NEW] Telegram-phase setup wizard modules
│   │   ├── __init__.py
│   │   ├── llm_providers.py
│   │   ├── memory.py
│   │   ├── channels.py
│   │   ├── tools_search.py
│   │   ├── agent_settings.py
│   │   ├── voice.py
│   │   ├── scheduling.py
│   │   ├── security.py
│   │   ├── proxy.py
│   │   ├── observability.py
│   │   └── integrations.py
│   └── slash_commands.py         [NEW] Gateway slash command dispatcher
```

---

## Proposed Changes

### Core Feature Modules (`core/`)

#### [NEW] `core/search/__init__.py`
Search router that reads `config.search.engine` and dispatches to the correct adapter.
Exposes `web_search(query, max_results)` and `web_fetch(url)` async functions.

#### [NEW] `core/search/brave.py`, `tavily.py`, `exa.py`, `searxng.py`, `firecrawl.py`
One stub per search provider. Each implements `async def search(query, max_results, api_key)`.

#### [NEW] `core/browser/__init__.py`, `playwright_backend.py`, `browserbase.py`, `screenshot.py`
Browser session factory reading `config.browser`.  
Session interface: `navigate(url)`, `screenshot()`, `click(selector)`, `type(selector, text)`, `evaluate(js)`.

#### [NEW] `core/voice/stt/`, `core/voice/tts/`, `core/voice/dictation.py`
STT and TTS provider routers (auto-select from config), plus push-to-talk dictation loop.

#### [NEW] `core/channels/` (16 platform stubs)
Each channel extends `ChannelBase` with `start()`, `stop()`, `send_message()`, `on_message()`.
The `__init__.py` exposes `get_active_channel(config)` factory.

#### [NEW] `core/heartbeat/__init__.py`, `subconscious.py`, `notification.py`
Background daemon that fires on `config.heartbeat.interval_secs`, runs optional inference,
delivers notifications through the active channel.

#### [NEW] `core/scheduler/__init__.py`, `task_sources.py`
Scheduler gate checks battery/CPU before allowing cron jobs to run.
Task sources poll external queues proactively.

#### [NEW] `core/skills/__init__.py`, `loader.py`, `working_memory.py`
Skills registry that loads Python callable files from `~/.locus/skills/` and an optional hub.

#### [NEW] `core/delegation/` — subagent orchestrator + coding agent pipeline
Orchestrator spawns child `AgentSession` instances (from `core/agent.py`) with their own
system prompt and tool set. `coding_agent.py` implements the Pi-style multi-step
coding loop (read → plan → edit → verify).

#### [NEW] `core/context/` — context compaction + compression
`compactor.py` mirrors OpenHuman's `auto_compact` with microcompact.
`compression.py` mirrors Hermes's summarisation-at-threshold approach.
`token_counter.py` provides `estimate_tokens(messages)`.

#### [NEW] `core/multimodal/`, `core/screen/`, `core/computer_use/`
Stubs for image handling, screen capture, and OS automation backends.

#### [NEW] `core/learning/` — reflection + user profile + tool tracker
Reflector runs an LLM call at end-of-session to update memory tree.
User profile (USER.md) and tool usage log are written to `~/.locus/memory/`.

#### [NEW] `core/integrations/` — Composio, Polymarket, webhooks
Stubs reading credentials from `.env` via `get_env_value()`.

#### [NEW] `core/coding/` — Pi coding agent file/shell tools
Implements `read_file`, `write_file`, `patch_file`, `run_shell`, `git_ops` as
`AgentTool`-compatible callables.

#### [NEW] `core/proxy.py`
Reads `config.proxy` and sets `os.environ` proxy vars at startup.

#### [NEW] `core/observability.py`
Initialises Sentry (if DSN set), OTEL exporter, structured logging.

#### [NEW] `core/session_manager.py`
Multi-session lifecycle: create, resume, idle-timeout reset, daily reset.

#### [NEW] `core/display/` — progress, TUI streaming, themes
Progress renderer for tool call bubbles. Streaming TUI adapted from Pi's `tui.ts`.

### Setup Categories (`locus_cli/setup_categories/`)

#### [NEW] 12 setup category modules
One module per SETTINGS category. Each exports a `run(config, state)` function
implementing the Telegram-phase interactive setup wizard for that category.

#### [NEW] `locus_cli/slash_commands.py`
Dispatcher for gateway slash commands: `/setup`, `/config`, `/help`, `/doctor`,
`/memory`, `/budget`, `/model`, `/tools`, `/cron`, `/skills`.

---

## Verification Plan

### Automated
```
cd locus-os
python -m pytest core/test_core.py -v       # existing tests still pass
python -c "from core import search, voice, channels, heartbeat"  # import smoke test
python -c "from locus_cli import setup_categories, slash_commands"
```

### Manual
- `locus` CLI starts without import errors
- `locus setup` wizard runs to completion (mock credentials)
- `locus gateway run` starts without crashing

---

## Open Questions

> [!IMPORTANT]
> **Q1: Language boundary** — Pi is TypeScript. Should `core/coding/` be a Python stub
> that shells out to the Pi binary, or a pure-Python reimplementation of the coding-agent
> pipeline patterns? (Recommended: pure-Python stub that mirrors the conceptual design.)

> [!IMPORTANT]
> **Q2: Channel priority** — All 16 channel stubs will be created. Should they all be
> minimal (skeleton with `NotImplementedError` placeholders), or should the top-3
> (Telegram, Discord, CLI) get basic working implementations?
> (Recommended: all hollow but Telegram gets a slightly fuller skeleton since it's used
> in Phase 2 of setup.)

> [!NOTE]
> **Q3: `display/streaming_tui.py`** — Pi's TUI is TypeScript/terminal-native. The Python
> equivalent will use `rich` or `curses`. The existing `locus_cli/curses_ui.py` already
> provides a base — the new file will wrap it rather than duplicate.
