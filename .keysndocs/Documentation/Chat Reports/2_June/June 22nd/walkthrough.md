# Walkthrough — Locus Setup Command and Core Backend Integration

This walkthrough details the implementation of Locus's `/setup` Telegram wizard parity features and all the core backend modules that support these settings.

## Summary of Changes

### 1. Cost Tracker (`core/cost_tracker.py`)
- Created a database-backed component to track token usage, input/output cost, and daily/monthly limits.
- Supports fine-grained cost estimations for Anthropic, OpenAI, Gemini, and DeepSeek models.
- Integrated spending check rules configured inside `config.yaml` to enforce strict limits before tool iterations.

### 2. Approval Store (`core/approval_store.py`)
- Created a database-backed history log for always-allowed and blocked tools.
- Tracks tool names, timestamps, approval status, and context reason.

### 3. MCP Client (`core/mcp_client.py`)
- Created a lightweight stdio-based JSON-RPC Model Context Protocol client.
- Initiates connection, registers tools, and executes calls over stdio.
- Integrated into the agent session instantiation in `gateway/agent.py` to auto-discover and map tools from configured servers.

### 4. Cron Runner (`core/cron_runner.py`)
- Implemented a zero-dependency background cron scheduler supporting 5-field cron syntax and shorthand aliases (`@hourly`, `@daily`, etc.).
- Wired into python-telegram-bot's asynchronous event loop in `gateway/bot.py`.
- Triggers background agent turns and posts results back to the user's home Telegram channel or allowed user ID.

### 5. Setup Text Replier & Bot Routing Fixes (`gateway/bot.py`, `setup_categories/handlers.py`)
- Standardized text-reply setup variables (such as `"cron_add"`, `"mcp_add"`, `"persona_name"`, `"voice_hotkey"`) between the wizard pages and Telegram text dispatch.
- Implemented custom text entry handlers for `handle_cost_daily_reply`, `handle_cost_monthly_reply`, and `handle_voice_hotkey_reply`.

---

## Verification Results

### Automated Tests
Successfully validated cost calculation, threshold alerts, cron match patterns, and approval logging by running unit tests on Locus Core:

```powershell
python core/test_core.py
```

Output:
```
Running unit tests...
Matches schedule: PASSED
Approval store: PASSED
Cost tracker: PASSED
All tests PASSED!
```
