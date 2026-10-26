# US-70 Spec Traceability Matrix

## Feature
- ID: F-0108
- Title: Autonomy Tiers
- Spec Reference: §13.4 lines 3308-3332

## Traceability Mapping

| Spec Requirement | Spec Line | Implementation | Test Coverage |
|------------------|-----------|----------------|---------------|
| `AUTONOMY TIERS`: READONLY, SUPERVISED, FULL | 3320-3323 | `sidecar/security/autonomy_tiers.py:AutonomyTier`, `AutonomyTierManager` | `tests/unit/test_autonomy_tiers.py:test_tier_initialization_and_parsing`, `test_service_autonomy_tiers_list` |
| `READONLY`: read tools only, no writes, no terminal | 3321 | `sidecar/security/autonomy_tiers.py:AutonomyTierManager.evaluate` | `tests/unit/test_autonomy_tiers.py:test_readonly_tier_allows_read_tools`, `test_readonly_tier_blocks_write_tools`, `test_readonly_tier_blocks_terminal_tools` |
| `SUPERVISED`: write tools require explicit user approval (10-min TTL) | 3322 | `sidecar/security/autonomy_tiers.py:AutonomyTierManager.evaluate` | `tests/unit/test_autonomy_tiers.py:test_supervised_tier_allows_read_tools`, `test_supervised_tier_requires_approval_for_write_tools`, `test_supervised_tier_allows_write_with_approval`, `test_supervised_tier_requires_approval_for_terminal_tools` |
| `FULL`: all tools allowed (trusted mode) | 3323 | `sidecar/security/autonomy_tiers.py:AutonomyTierManager.evaluate` | `tests/unit/test_autonomy_tiers.py:test_full_tier_allows_all_tools` |
| Tool classification & overrides | 3327 | `sidecar/security/autonomy_tiers.py:ToolCategory`, `classify_tool` | `tests/unit/test_autonomy_tiers.py:test_tool_classification_heuristics`, `test_tool_override_registration`, `tests/integration/test_autonomy_tiers_service.py:test_service_autonomy_classify` |
| Pi hook integration (`beforeToolCall`) | 3327 | `locus-extension/src/security/autonomy-tiers.ts:createBeforeToolCallHook` | Extension contract integration |
| Modular Off-switches (`locus.autonomy_tiers.enabled`, `locus.security.autonomy_tiers.enabled`) | 3329 | `sidecar/providers/autonomy_tiers.py:DefaultAutonomyTiersProvider`, `sidecar/service.py` | `tests/unit/test_autonomy_tiers.py:test_provider_modular_off_switches`, `tests/integration/test_autonomy_tiers_service.py:test_service_autonomy_tiers_off_switches` |
| Service Routes (`/security/autonomy/tier`, `/evaluate`, `/classify`, `/tiers`) | 3327-3330 | `sidecar/service.py` | `tests/integration/test_autonomy_tiers_service.py` |
| Extension Client Contract | 3327 | `locus-extension/src/security/autonomy-tiers.ts:AutonomyTiersClient` | TypeScript contract |
