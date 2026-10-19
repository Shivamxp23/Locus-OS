# US-23 Spec Trace (§1.4: Model Management & Escalation)

Feature: `F-0004` (Model Management & Escalation)
Source: `packages/coding-agent/src/core/model-resolver.ts`, `packages/ai/src/models.ts`
Canonical Targets: `locus-extension/src/model-escalation.ts`, `sidecar/providers/model_manager.py`, `sidecar/model_escalation.py`

| Spec Line | Exact Spec Sentence / Pseudocode | Verdict | Target File & Mechanism | Test Name |
| :--- | :--- | :--- | :--- | :--- |
| Line 485 | `1. User selects model via config or CLI flag` | KEEP-PI | `sidecar/model_escalation.py` respects user configured default model | `test_model_resolution_default_selection` |
| Line 486 | `2. ModelRegistry resolves provider + model name` | KEEP-PI | `sidecar/providers/model_manager.py:ModelRegistry` resolves model catalog and provider attributes | `test_model_registry_resolution` |
| Line 487 | `3. API key resolved dynamically per call (for expiring tokens)` | KEEP-PI | `sidecar/model_escalation.py:resolve_model_credentials` resolves API keys dynamically from config accessor | `test_dynamic_api_key_resolution` |
| Line 488 | `4. Thinking level clamped to model's supported levels` | KEEP-PI | `sidecar/model_escalation.py:clamp_thinking_level` clamps thinking budget to provider maximums | `test_thinking_level_clamping` |
| Line 489 | `5. prepareNextTurn() can swap model mid-conversation` | AUGMENT | `locus-extension/src/model-escalation.ts` and `sidecar/model_escalation.py:evaluate_turn_escalation` suggest next turn model | `test_prepare_next_turn_model_swap` |
| Line 492 | `Standard turns: DeepSeek V4 Flash (cheapest available, ~$0.012/day)` | LOCUS-NEW | `sidecar/model_escalation.py:resolve_turn_model` selects standard tier for routine conversational turns | `test_escalation_tier_standard_turn` |
| Line 493 | `Complex reasoning / Sunday synthesis: Gemini 2.5 Pro (1M context)` | LOCUS-NEW | `sidecar/model_escalation.py:resolve_turn_model` escalates to reasoning tier for synthesis or high complexity | `test_escalation_tier_complex_reasoning` |
| Line 494 | `Background tasks: auxiliary client (separate API key, cheapest model)` | LOCUS-NEW | `sidecar/model_escalation.py:resolve_turn_model` selects background auxiliary tier with separate key config | `test_escalation_tier_background_tasks` |
| Line 500 | `Off -> Locus uses a single model for all turns; no automatic escalation.` | AUGMENT | `sidecar/model_escalation.py:ModelEscalator` returns base model without escalation when disabled | `test_model_escalation_disabled_passthrough` |
| Accept criteria | `Registers as a provider in sidecar/providers/ with modular off-switch locus.model_management_escalation.enabled returning 503.` | AUGMENT | `sidecar/service.py` returns 503 on `/models/*` when `locus.model_management_escalation.enabled` is false | `test_model_escalation_modular_off_switch_503` |
