# US-58 Spec Trace — §5.1-5.8: Session Management & Telegram Bridge

Feature: F-0027 | Verdict: AUGMENT | Author model: Claude Opus 4.6

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `SESSION FORMAT (JSONL v3): Entry types: message, tool_call, tool_result, compaction_summary, branch_summary, metadata, system_event, checkpoint, marker` | AUGMENT | sidecar/sessions/session_manager.py:20-56 | test_session_format_and_entry_types, test_session_invalid_entry_type |
| 2 | `Structure: tree-based (sessions can fork into branches)` | AUGMENT | sidecar/sessions/session_manager.py:59-130 | test_session_tree_and_forking |
| 3 | `Storage: one .jsonl file per session, named by session_id` | AUGMENT | sidecar/sessions/session_manager.py:60-100, 133-145 | test_session_format_and_entry_types |
| 4 | `FUNCTION fork_session(parent_session_id, fork_point): new_session = create_session(); new_session.parent = parent_session_id; new_session.fork_point = fork_point; copy_entries(parent_session_id, new_session.id, up_to=fork_point); new_session.append(BranchSummaryEntry { parent: parent_session_id, fork_point: fork_point, summary: generate_branch_summary(entries_before_fork) }); RETURN new_session` | AUGMENT | sidecar/sessions/session_manager.py:183-238 | test_session_tree_and_forking, test_service_session_lifecycle_and_forking |
| 5 | `FUNCTION resume_session(session_id): session = load_session(session_id); messages = session.replay_entries(); compactions = session.get_compaction_entries(); context = rebuild_context(compactions, messages); RETURN context` | AUGMENT | sidecar/sessions/session_manager.py:240-256 | test_session_resume_rebuild_context, test_service_session_lifecycle_and_forking |
| 6 | `TELEGRAM SESSION BRIDGE (Locus-unique): FUNCTION bridge_telegram_to_session(telegram_chat_id, user_message): session_id = session_map.get(telegram_chat_id); IF session_id is None: session_id = create_new_session(); session_map.set(telegram_chat_id, session_id); session = load_session(session_id); session.append(MessageEntry { role: "user", content: user_message }); response = run_reactive_loop(session, user_message); channel_provider.send_message(telegram_chat_id, response); session.append(MessageEntry { role: "assistant", content: response }); session.flush()` | AUGMENT | sidecar/sessions/session_manager.py:259-354 | test_telegram_session_bridge, test_service_telegram_bridge |
| 7 | `Component: locus/core/session-bridge.ts -> locus-extension/src/session-bridge.ts` | AUGMENT | locus-extension/src/session-bridge.ts:1-170 | test_service_session_lifecycle_and_forking |
| 8 | `KEEP: All Pi session formats, branching, resume, export. Zero changes.` | AUGMENT | sidecar/session_export.py:1-120 | test_session_exports, test_service_session_lifecycle_and_forking |
| 9 | `ADD: Telegram↔Session bridge maps Telegram chat IDs to Pi session IDs. State stored in PostgreSQL telegram_sessions table.` | AUGMENT | sidecar/sessions/session_manager.py:270-310 | test_telegram_session_bridge |
| 10 | `Swappable / off state: locus.session_management.enabled and locus.sessions.enabled returning 503` | AUGMENT | sidecar/service.py:4289-4460 | test_session_management_provider_off_switch, test_service_sessions_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/sessions/__init__.py` — package re-exports for session module
- `sidecar/sessions/session_manager.py` — §5.1-5.8 SessionManager, Session, SessionEntry, and TelegramSessionBridge
- `sidecar/session_export.py` — §5.1-5.8 export to markdown, json, jsonl
- `sidecar/providers/session_management.py` — BaseSessionManagementProvider & DefaultSessionManagementProvider
- `sidecar/providers/__init__.py` — provider module re-exports
- `locus-extension/src/session-bridge.ts` — TypeScript contract
- `sidecar/service.py` — REST endpoints for sessions & telegram bridge with 503 off-switch
- `tests/unit/test_session_management.py` — unit tests for rows 1-6, 8, 9, 10
- `tests/integration/test_session_management_service.py` — integration tests for rows 4, 5, 6, 7, 8, 10
- `tracker/features.yaml` — updated evidence for F-0027

No file or behaviour outside the spec trace.
