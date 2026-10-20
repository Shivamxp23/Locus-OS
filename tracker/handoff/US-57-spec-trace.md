# US-57 Spec Trace — §4.18: Memory Provider Interface

Feature: F-0118 | Verdict: AUGMENT | Author model: Gemini Flash

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `ABSTRACT CLASS MemoryProvider:` | AUGMENT | sidecar/memory/provider_interface.py:22-120 | test_memory_provider_lifecycle |
| 2 | `name: str` | AUGMENT | sidecar/memory/provider_interface.py:29 | test_memory_provider_lifecycle |
| 3 | `is_available() → bool          // check config + deps, no network calls` | AUGMENT | sidecar/memory/provider_interface.py:34-39, 137-142 | test_memory_provider_lifecycle |
| 4 | `initialize(session_id, **kwargs)  // connect, create resources` | AUGMENT | sidecar/memory/provider_interface.py:41-47, 144-148 | test_memory_provider_lifecycle |
| 5 | `system_prompt_block() → str    // static text for system prompt` | AUGMENT | sidecar/memory/provider_interface.py:49-52, 150-152 | test_system_prompt_block |
| 6 | `prefetch(query, session_id) → str // Recall context BEFORE each LLM call` | AUGMENT | sidecar/memory/provider_interface.py:54-60, 154-173 | test_prefetch_and_sync_turn, test_service_memory_provider_prefetch_and_sync_turn |
| 7 | `queue_prefetch(query, session_id) // Queue background recall for NEXT turn` | AUGMENT | sidecar/memory/provider_interface.py:62-65, 175-178 | test_prefetch_and_sync_turn |
| 8 | `sync_turn(user_content, assistant_content, session_id, messages) // Persist completed turn. Non-blocking` | AUGMENT | sidecar/memory/provider_interface.py:67-78, 180-192 | test_prefetch_and_sync_turn, test_service_memory_provider_prefetch_and_sync_turn |
| 9 | `get_tool_schemas() → [tool_schema]  // tools to expose to model` | AUGMENT | sidecar/memory/provider_interface.py:80-83, 194-210 | test_tool_schemas_and_execution, test_service_memory_provider_tools_and_call |
| 10 | `handle_tool_call(tool_name, args) → json_string` | AUGMENT | sidecar/memory/provider_interface.py:85-88, 212-217 | test_tool_schemas_and_execution, test_service_memory_provider_tools_and_call |
| 11 | `shutdown()` | AUGMENT | sidecar/memory/provider_interface.py:90-93, 219-224 | test_memory_provider_lifecycle |
| 12 | `Optional hooks: on_turn_start, on_session_end, on_session_switch, on_pre_compress, on_memory_write, on_delegation` | AUGMENT | sidecar/memory/provider_interface.py:95-125 | test_optional_hooks |
| 13 | `MEMORY MANAGER — One-provider limit: Locus RELAXES this: allows stackable providers (primary + secondary)` | AUGMENT | sidecar/memory/provider_interface.py:227-240 | test_stackable_memory_manager, test_service_memory_provider_config |
| 14 | `register_provider(provider): IF provider.is_available(): provider.initialize(session_id, **runtime_kwargs); active_providers.append(provider)` | AUGMENT | sidecar/memory/provider_interface.py:242-266 | test_stackable_memory_manager |
| 15 | `prefetch_all(query): FOR EACH provider IN active_providers: results.append(provider.prefetch(query)); RETURN merge_results(results)` | AUGMENT | sidecar/memory/provider_interface.py:276-297 | test_stackable_memory_manager, test_service_memory_provider_prefetch_and_sync_turn |
| 16 | `sync_turn_all(user, assistant): FOR EACH provider IN active_providers: provider.sync_turn(user, assistant)` | AUGMENT | sidecar/memory/provider_interface.py:308-330 | test_stackable_memory_manager, test_service_memory_provider_prefetch_and_sync_turn |
| 17 | `Swappable / off state: locus.memory_provider.enabled and locus.memory.enabled returning 503` | AUGMENT | sidecar/service.py:4178-4280 | test_service_memory_provider_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/memory/provider_interface.py` — new, §4.18 MemoryProvider ABC & Stackable MemoryManager
- `sidecar/memory/__init__.py` — package re-exports
- `sidecar/providers/memory_provider.py` — new, §4.18 provider re-exports
- `sidecar/providers/__init__.py` — provider module re-exports
- `sidecar/service.py` — REST endpoints for memory provider & manager with 503 off-switch
- `locus-extension/src/memory/interface.ts` — TypeScript contract
- `tests/unit/test_memory_provider.py` — unit tests for rows 1-16
- `tests/integration/test_memory_provider_service.py` — integration tests for rows 6, 8, 9, 10, 13, 15, 16, 17
- `tracker/features.yaml` — updated evidence for F-0118

No file or behaviour outside the spec trace.
