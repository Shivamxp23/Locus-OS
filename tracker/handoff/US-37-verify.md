VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.9s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0096
features 1 | verified avg 85.0% | old claimed avg 0.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0096", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Module implementing Intelligent Model Routing + Quality-Based Fallback per §2.7-2.8 created under sidecar/ or locus-extension/ | `sidecar/model_routing.py:45`, `locus-extension/src/routing/router.ts:20` | `tests/unit/test_model_routing.py:25`, `tests/integration/test_model_routing_service.py:20` | PASS |
| Registers as a provider in sidecar/providers/ with modular off-switch locus.intelligent_model_routing_quality_based_fallback.enabled returning 503 | `sidecar/providers/model_routing.py:120`, `sidecar/model_routing.py:380`, `sidecar/service.py:1475` | `tests/unit/test_model_routing.py:220`, `tests/integration/test_model_routing_service.py:48` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/model_routing.py:50-375` | `tests/unit/test_model_routing.py:25-235` (16 tests) | PASS |
| Task classification (Lightweight for quick/fast hints; Medium for medium hints; Heavy for reasoning/coding/agentic/chat/explicit/unknown) | `sidecar/model_routing.py:65-90`, `locus-extension/src/routing/policy.ts:35-55` | `tests/unit/test_model_routing.py:25-50` | PASS |
| Routing decision matrix with LatencyBudget::Low and CostSensitivity::High local overrides for Medium category | `sidecar/model_routing.py:110-185`, `locus-extension/src/routing/policy.ts:70-135` | `tests/unit/test_model_routing.py:60-100` | PASS |
| Privacy-required fail-closed local enforcement (no remote fallback, streaming disabled) | `sidecar/model_routing.py:125-140`, `locus-extension/src/routing/policy.ts:90-105` | `tests/unit/test_model_routing.py:102-114` | PASS |
| Tools presence forces remote override | `sidecar/model_routing.py:175-180`, `locus-extension/src/routing/policy.ts:130-135` | `tests/unit/test_model_routing.py:116-125` | PASS |
| Local health check probe caching with 30-second TTL and non-blocking lock discipline | `sidecar/model_routing.py:190-230`, `locus-extension/src/routing/health.ts:25-55` | `tests/unit/test_model_routing.py:145-160` | PASS |
| Quality-based fallback detecting length floor (< 10 bytes), empty-noise tokens, and refusal DFA patterns | `sidecar/model_routing.py:240-270`, `locus-extension/src/routing/quality.ts:25-55` | `tests/unit/test_model_routing.py:128-142` | PASS |
| Dispatch execution flow with remote fallback on local error and on low quality / refusal | `sidecar/model_routing.py:275-350`, `locus-extension/src/routing/router.ts:75-125` | `tests/unit/test_model_routing.py:165-215` | PASS |
| Off switch on `locus.intelligent_model_routing_quality_based_fallback.enabled` returns 503 | `sidecar/service.py:1475-1550` | `tests/integration/test_model_routing_service.py:48-75` | PASS |

## Test attack result
Created detached scratch worktree at `../verify-tmp`.
Mutated `sidecar/model_routing.py` in `is_low_quality()` method to invert return value: `return False` -> `return True`.
Ran pytest targeted at `test_valid_response_not_low_quality`:
```powershell
pytest tests/unit/test_model_routing.py -k test_valid_response_not_low_quality
FAILED tests/unit/test_model_routing.py::TestQualityBasedFallback::test_valid_response_not_low_quality
AssertionError: assert True is False
1 failed, 15 deselected in 1.15s
```
Mutation test confirmed that quality-based validation fails immediately when heuristics are compromised. Worktree was cleanly removed.

## Findings
1. `sidecar/model_routing.py`: Faithfully implements OpenHuman routing logic, properly classifying "hint:chat" as Heavy to avoid slow local TTFT while allowing privacy mode to override all categories to local.
2. `locus-extension/src/routing/`: Full TypeScript counterpart provides synchronous policy evaluation, cached health probes, refusal regex matching, and dispatch abstraction.
3. `sidecar/service.py`: Enforces modular 503 off-switch across all `/routing/*` endpoints when `locus.intelligent_model_routing_quality_based_fallback.enabled` is false.

## Not checked
- Physical invocation of an external running Ollama server instance on port 11434 was simulated via mock invokers and test health injection in unit/integration suites.
