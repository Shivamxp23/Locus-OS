# Locus OS — Gap Closure Task Tracker

## Wave 1: Foundation Wiring (T0.6 → T0.1 → T0.4)

- [X] **T0.6** PG Migration Execution & Seed Data
  - [X] Create `scripts/init_database.py`
  - [X] Seed data verification
- [X] **T0.1** System Prompt Builder Extraction
  - [X] Create `core/prompt_builder.py` (7-section dynamic builder)
  - [X] Modify `core/agent.py` to use PromptBuilder
- [X] **T0.4** Conductor ↔ Context Forge Full Integration
  - [X] Wire all 6 layers via `prompt_builder.build_context_forge()`

## Wave 2: Event System & Scheduling (T0.5 → T0.3 → T0.2)

- [X] **T0.5** Event Bus Emitters Throughout Codebase
  - [X] Create `core/event_emitters.py` (25+ fire-and-forget emitter functions)
- [X] **T0.3** Agent Loop ↔ Learning Integration
  - [X] Wire trajectory recording in agent loop
  - [X] Wire reflector post-turn review
  - [X] Wire tool tracker logging
- [X] **T0.2** APScheduler Cron Wiring
  - [X] Create `core/scheduler_wiring.py` (18+ jobs)

## Wave 3: Check-ins, Reviews, Notifications (T1.1, T1.2, T1.7, T1.8)

- [X] **T1.1** 4-Daily Structured Check-ins
  - [X] Create `gateway/checkin_flow.py` (interactive inline keyboards, DCS calculation)
  - [X] Add `send_checkin_prompt(cadence)` to `core/life_os_persistent.py`
  - [X] Wire `/checkin` command and callback handler in `gateway/bot.py`
- [X] **T1.2** Review Cadence System
  - [X] Implement `generate_review`, `save_review_to_vault`, `trigger_review` in `core/life_os_persistent.py`
  - [X] Wire review cadence jobs (daily, weekly, monthly, quarterly) in `core/scheduler_wiring.py`
- [X] **T1.7** Nightly Vault Diff Cron
  - [X] Add `run_nightly_diff()` to `core/ingestion/collector.py`
  - [X] MD5 vault crawl, chunk extraction, pgvector sync, and event emission
- [X] **T1.8** Notification Dispatch
  - [X] Priority router (HIGH→Telegram, MEDIUM→Morning brief queue, LOW→Log) in `core/heartbeat/notification.py`

## Wave 4: TUI, Telegram, Model Escalation (T1.3, T1.4, T1.5, T1.9)

- [X] **T1.3** TUI Dashboard Interactive Keybindings
  - [X] Implement `run_interactive()` in `core/display/dashboard.py` (Space, D, N, C, R, Q, Arrow keys)
  - [X] Wire `locus dashboard` command in `locus_cli/main.py`
- [X] **T1.4** Telegram Gateway Deep Patterns
  - [X] Create `gateway/deep_patterns.py` (AdaptiveBatcher, MessageDeduplicator, TypingContext, TelegramChatLogger)
  - [X] Wire into `gateway/agent.py` and `gateway/bot.py` with exponential backoff polling
- [X] **T1.5** Model Escalation
  - [X] Create `core/model_escalation.py` (STANDARD, REASONING, BACKGROUND routing)
- [X] **T1.9** Deduplicate Desktop/Screen/Computer-Use
  - [X] Consolidate `screen_capture.py`, `vnc_client.py`, `vision.py` under `core/computer_use/`
  - [X] Provide backwards-compatibility shims in `core/desktop/` and `core/screen/`

## Wave 5: Calendar, FastAPI, Local Models (T1.6, T2.1, T2.7)

- [X] **T1.6** Google Calendar Real OAuth
  - [X] Real Google Calendar API OAuth2 flow, token refresh, and event synchronization in `core/integrations/calendar_sync.py`
  - [X] Faction-blocked deep work event creation and schedule fragmentation calculation
- [X] **T2.1** FastAPI REST Layer
  - [X] Create `core/api/app.py` (FastAPI factory + middleware)
  - [X] Create 6 routers: `checkins.py`, `tasks.py`, `factions.py`, `schedule.py`, `brain.py`, `events.py` (+ WebSocket stream)
- [X] **T2.7** Local Model Support
  - [X] Add Ollama, LM Studio, and vLLM endpoint resolution to `core/agent.py` with cloud fallback

## Wave 6: Remaining Medium (T2.2-T2.10)

- [X] **T2.2** Title Generation → `core/title_generator.py`
- [X] **T2.3** Rate Limit Tracking → `core/rate_limiter.py`
- [X] **T2.4** Obsidian Dashboard.md Template → `core/vault/dashboard_template.py`, `vault/Dashboard.md`
- [X] **T2.5** Daily Session Export → `core/session_export.py`
- [X] **T2.6** Gmail Integration → `core/integrations/gmail.py` (OAuth, inbox scan, classification, task capture)
- [X] **T2.8** Self-Maintenance pip-audit → `core/maintenance.py:security_audit`
- [X] **T2.9** Progress Visualization → `core/display/stats_publisher.py`
- [X] **T2.10** Shell Sandbox Multi-Backend → `core/security.py` (SubprocessSandbox, BubblewrapSandbox, FirejailSandbox)

## Wave 7: Polish & Deferred (T3.x)

- [ ] **T3.1** Polymarket & Webhooks
- [ ] **T3.2** ACP Protocol
- [ ] **T3.3** Dynamic MCP Tool Calling
- [ ] **T3.4** Inter-Harness Communication
- [ ] **T3.5** Achievements System
- [ ] **T3.6** LLM Council
- [ ] **T3.7** NotebookLM Integration

---

## Summary

| Category                     | Done            | Total | %              |
| ---------------------------- | --------------- | ----- | -------------- |
| **T0 (Critical)**      | **6/6**   | 6     | **100%** |
| **T1 (High)**          | **9/9**   | 9     | **100%** |
| **T2 (Medium)**        | **10/10** | 10    | **100%** |
| **T3 (Low/Deferred)**  | 0/7             | 7     | 0%             |
| **Total Core System**  | **25/25** | 25    | **100%** |
| **Overall (incl. T3)** | **25/32** | 32    | **78%**  |
