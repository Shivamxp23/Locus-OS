# US-25 Spec Trace (F-0006: Context Window Management)

## Covered Spec Sentences (§1.6: Context Window Management, lines 551-583)
1. Line 560: `estimateContextTokens(messages) → rough count` -> Implemented in `HeadroomCCRAdapter.estimate_tokens` and tested in `test_estimate_context_tokens` and `test_estimate_endpoint`.
2. Line 561: `shouldCompact(promptTokens, threshold) → bool` -> Implemented in `HeadroomCCRAdapter.should_compact` and tested in `test_should_compact_threshold_evaluation`.
3. Line 562: `compact(messages, options) → CompactionResult` -> Implemented in `HeadroomCCRAdapter.compact` and tested in `test_compaction_preservation_bounds` and `test_compact_endpoint`.
4. Line 564-567: `Compaction preserves: - protect_first_n = 3 (first 3 non-system messages), - protect_last_n = 6 (last 6 messages), - Everything between is summarized by auxiliary LLM call` -> Implemented in `HeadroomCCRAdapter.compact` preserving `[:3]` and `[-6:]` with middle compressed into CCR summary entry.
5. Line 577: `Locus replaces Pi's default compaction with Headroom CCR (§4.17) + its own 800-token budget enforcement in transformContext. Pi's compaction remains available as a CompactionProvider option.` -> Implemented in `sidecar/context/headroom_adapter.py` and `locus-extension/src/context-manager.ts` and tested in `test_ccr_reversible_retrieval` and `test_inflation_guard_protection`.
6. Line 579: `Swappable / off state: locus.compaction.provider (headroom-ccr | pi-default | simple-summarize). Off → raw message history grows unbounded until the LLM's context limit is hit.` -> Implemented and tested in `test_context_compression_disabled_passthrough` and `test_context_compression_service_off_switch_503`.
