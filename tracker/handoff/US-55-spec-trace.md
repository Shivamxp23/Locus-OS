# US-55 Spec Trace — §4.16: Context Compression

Feature: F-0110 | Verdict: AUGMENT | Author model: Gemini Flash

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `ABSTRACT CLASS ContextEngine:` | AUGMENT | sidecar/providers/compaction.py:46-121, sidecar/compaction/context_engine.py:180-248 | test_context_engine_initialization_and_thresholds |
| 2 | `threshold_percent: float = 0.75   // compress at 75% usage` | AUGMENT | sidecar/providers/compaction.py:27, 56 | test_context_engine_initialization_and_thresholds, test_service_compaction_config |
| 3 | `protect_first_n: int = 3          // keep first 3 non-system messages` | AUGMENT | sidecar/providers/compaction.py:28, 57 | test_context_engine_initialization_and_thresholds, test_compression_flow_identifies_compressible_range_and_preserves_head_tail |
| 4 | `protect_last_n: int = 6           // keep last 6 messages` | AUGMENT | sidecar/providers/compaction.py:29, 58 | test_context_engine_initialization_and_thresholds, test_compression_flow_identifies_compressible_range_and_preserves_head_tail |
| 5 | `update_from_response(usage)      // called after every LLM call` | AUGMENT | sidecar/compaction/context_engine.py:199-204 | test_update_from_response_and_should_compress |
| 6 | `should_compress(prompt_tokens)   // check if compaction needed` | AUGMENT | sidecar/compaction/context_engine.py:206-208 | test_update_from_response_and_should_compress, test_service_should_compress_endpoint |
| 7 | `compress(messages, current_tokens, focus_topic) // do the compaction` | AUGMENT | sidecar/compaction/context_engine.py:210-224 | test_compression_flow_identifies_compressible_range_and_preserves_head_tail |
| 8 | `on_session_start(session_id), on_session_end(session_id, messages), on_session_reset()` | AUGMENT | sidecar/compaction/context_engine.py:226-241 | test_context_engine_initialization_and_thresholds |
| 9 | `update_model(model, context_length, ...) // recalculate thresholds` | AUGMENT | sidecar/providers/compaction.py:113-121 | test_update_model_recalculates_thresholds, test_service_update_model_endpoint |
| 10 | `// Step 1: Acquire compression lock (prevent concurrent compressions)` | AUGMENT | sidecar/compaction/context_engine.py:29-57, 107-118 | test_compaction_lock_concurrency_guard |
| 11 | `head = messages[:protect_first_n + 1]  // system + first N` | AUGMENT | sidecar/compaction/context_engine.py:121, 131 | test_compression_flow_identifies_compressible_range_and_preserves_head_tail |
| 12 | `tail = messages[-protect_last_n:]      // last N` | AUGMENT | sidecar/compaction/context_engine.py:132 | test_compression_flow_identifies_compressible_range_and_preserves_head_tail |
| 13 | `middle = messages[protect_first_n + 1 : -protect_last_n]` | AUGMENT | sidecar/compaction/context_engine.py:133 | test_compression_flow_identifies_compressible_range_and_preserves_head_tail |
| 14 | `IF middle.length == 0: RETURN messages  // nothing to compress` | AUGMENT | sidecar/compaction/context_engine.py:123-130, 135-143 | test_compaction_short_conversation_noop |
| 15 | `// Step 3: Notify memory providers before compression` | AUGMENT | sidecar/compaction/context_engine.py:145-154 | test_compression_flow_notifies_memory_providers_and_splits_session |
| 16 | `summary_prompt = Summarize the following conversation, preserving key decisions, facts, preferences, tool results, focus_topic` | AUGMENT | sidecar/compaction/context_engine.py:68-96, 156-160 | test_compression_flow_identifies_compressible_range_and_preserves_head_tail |
| 17 | `// Step 5: Build new message list: head + [system_message(summary)] + tail` | AUGMENT | sidecar/compaction/context_engine.py:162-171 | test_compression_flow_identifies_compressible_range_and_preserves_head_tail |
| 18 | `new_session_id = generate_session_id(); session_db.split(...)` | AUGMENT | sidecar/compaction/context_engine.py:173-174 | test_compression_flow_notifies_memory_providers_and_splits_session |
| 19 | `// Step 7: Notify memory providers of session switch: provider.on_session_switch(...)` | AUGMENT | sidecar/compaction/context_engine.py:176-180 | test_compression_flow_notifies_memory_providers_and_splits_session |
| 20 | `Provider Interface: CompactionProvider (wraps both Pi's compaction AND Hermes's ContextEngine ABC)` | AUGMENT | sidecar/providers/compaction.py:139-178, sidecar/compaction/context_engine.py:250-295 | test_compaction_provider_interface_and_health_check, test_service_compaction_config |
| 21 | `Swappable / off state: locus.context_compression.enabled returning 503` | AUGMENT | sidecar/service.py:3990-4050 | test_service_compaction_off_switch_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/compaction/context_engine.py` — new, §4.16 rows 1-20
- `sidecar/compaction/__init__.py` — new, §4.16 re-exports
- `sidecar/providers/compaction.py` — new, §4.16 rows 1-9, 20
- `sidecar/providers/__init__.py` — provider re-exports
- `sidecar/service.py` — mounts §4.16 endpoints with 503 off-switch
- `locus-extension/src/compaction.ts` — TypeScript contract
- `tests/unit/test_context_compression.py` — tests rows 1-19
- `tests/integration/test_context_compression_service.py` — tests rows 2, 6, 9, 20, 21
- `tracker/features.yaml` — evidence updates for F-0110

No file or behaviour outside the spec trace.
