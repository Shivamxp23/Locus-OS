# US-37 Spec Trace: Intelligent Model Routing + Quality-Based Fallback (§2.7-2.8)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 1859 | `## Feature §2.7-2.8: Intelligent Model Routing + Quality-Based Fallback` | AUGMENT | `sidecar/providers/model_routing.py:1` | `tests/unit/test_model_routing.py:25` |
| 1862 | `**Verdict**: 🔄 AUGMENT (steal OpenHuman's routing module, adapt for Locus' model strategy)` | AUGMENT | `sidecar/model_routing.py:1`, `locus-extension/src/routing/router.ts:1` | `tests/unit/test_model_routing.py:40` |
| 1879 | `FUNCTION classify(model_string) → TaskCategory:` | STEAL VERBATIM | `sidecar/model_routing.py:60`, `locus-extension/src/routing/policy.ts:35` | `tests/unit/test_model_routing.py:55` |
| 1896 | `FUNCTION decide(category, local_healthy, hints) → (primary, fallback):` | STEAL VERBATIM | `sidecar/model_routing.py:85`, `locus-extension/src/routing/policy.ts:60` | `tests/unit/test_model_routing.py:75` |
| 1906 | `PRIVACY_REQUIRED: Forces local routing for ALL categories (even Heavy)` | STEAL VERBATIM | `sidecar/model_routing.py:110`, `locus-extension/src/routing/policy.ts:80` | `tests/unit/test_model_routing.py:95` |
| 1911 | `TOOLS FORCE REMOTE: If request carries tools and policy chose local → override to remote` | STEAL VERBATIM | `sidecar/model_routing.py:125`, `locus-extension/src/routing/policy.ts:95` | `tests/unit/test_model_routing.py:115` |
| 1925 | `LocalHealthChecker: Cached probe with 30-second TTL and 3-second timeout` | STEAL VERBATIM | `sidecar/model_routing.py:145`, `locus-extension/src/routing/health.ts:20` | `tests/unit/test_model_routing.py:135` |
| 1942 | `FUNCTION is_low_quality(response_text) → bool:` | STEAL VERBATIM | `sidecar/model_routing.py:195`, `locus-extension/src/routing/quality.ts:25` | `tests/unit/test_model_routing.py:160` |
| 1968 | `FUNCTION chat(request):` | STEAL VERBATIM | `sidecar/model_routing.py:240`, `locus-extension/src/routing/router.ts:70` | `tests/unit/test_model_routing.py:190` |
| 1997 | `RoutingRecord { category, target (Local|Remote), resolved_model, health_status, used_fallback: bool, latency_ms, tokens_in, tokens_out, estimated_cost }` | STEAL VERBATIM | `sidecar/providers/model_routing.py:45`, `locus-extension/src/routing/types.ts:50` | `tests/unit/test_model_routing.py:215` |
| Criteria 1 | `Module implementing Intelligent Model Routing + Quality-Based Fallback per §2.7-2.8: Intelligent Model Routing + Quality-Based Fallback created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/model_routing.py`, `locus-extension/src/routing/` | `tests/unit/test_model_routing.py:25` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.intelligent_model_routing_quality_based_fallback.enabled returning 503.` | LOCUS-NEW | `sidecar/model_routing.py:280`, `sidecar/service.py:1475` | `tests/unit/test_model_routing.py:230`, `tests/integration/test_model_routing_service.py:50` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_model_routing.py` | `tests/unit/test_model_routing.py:25-260` |
