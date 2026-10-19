# US-24 Spec Trace (F-0005: Extension Lifecycle)

## Covered Spec Sentences (§1.5: Extension Lifecycle (25+ Events), lines 506-550)
1. Line 514: `EXTENSION LIFECYCLE (25+ events):` -> Implemented in `sidecar/providers/extension_lifecycle.py` and tested in `test_canonical_lifecycle_events_catalog`.
2. Line 515-517: `session_start → turn_start → message_start → message_update → message_end → tool_execution_start → tool_execution_update → tool_execution_end → turn_end → agent_end → session_shutdown` -> Implemented and tested in `test_priority_ordered_dispatch`.
3. Line 519-520: `PLUS: before_compact, after_compact, before_tree, session_switch, replaced_session, context_usage_update` -> Implemented in `CANONICAL_LIFECYCLE_EVENTS`.
4. Line 528-534: `Key Locus hooks into this: session_start: initialize all providers, load state; turn_start: Query Router, State Injection; tool_execution_start: tool guardrails check; tool_execution_end: tool tracking (idempotent vs mutating); turn_end: post-turn learning, background review; session_shutdown: flush all providers, persist state` -> Implemented in `ExtensionLifecycleProvider._register_default_locus_hooks` and `locus-extension/src/lifecycle.ts`.
5. Line 538: `Component: locus/extensions/ directory for all Locus extensions. Each extension registers via Pi's onEvent() API.` -> Implemented via `LocusLifecycleDispatcher` in `locus-extension/src/lifecycle.ts`.
6. Line 540: `Swappable / off state: each Locus extension can be disabled individually via config. Off → that extension's hooks don't fire; Pi's core event loop continues unchanged.` -> Implemented and tested in `test_extension_individual_swappable_off_state` and `test_global_off_switch_behavior`.
7. Line 541: `KEEP: Pi's entire extension system, all 25+ lifecycle events, event payload structure.` -> Verified via error containment and non-interfering hook dispatch.
