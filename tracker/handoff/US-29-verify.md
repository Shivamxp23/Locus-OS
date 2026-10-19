VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.5s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0010
features 1 | verified avg 85.0% | old claimed avg 75.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0010", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Module implementing Usage/Cost Tracking per §1.10 created under sidecar/ and locus-extension/ | `sidecar/cost_tracker.py:289`, `sidecar/providers/cost_tracker.py:17`, `locus-extension/src/tracking/usage.ts:162`, `locus-extension/src/tracking/pricing.ts:34` | `tests/unit/test_cost_tracker.py:16`, `tests/integration/test_cost_tracker_service.py:18` | PASS |
| Registers as a provider in sidecar/providers/ with modular off-switch `locus.usage_cost_tracking.enabled` returning 503 | `sidecar/cost_tracker.py:408`, `sidecar/service.py:1010` | `tests/unit/test_cost_tracker.py:291`, `tests/integration/test_cost_tracker_service.py:101` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/cost_tracker.py:190`, `sidecar/cost_tracker.py:241` | `tests/unit/test_cost_tracker.py:16-309` (13 tests) | PASS |
| Integration tests assert HTTP endpoints `/cost/calculate`, `/cost/record`, `/cost/session`, `/cost/pricing`, `/cost/pricing/override` | `sidecar/service.py:1017-1094` | `tests/integration/test_cost_tracker_service.py:18-119` (4 tests) | PASS |
| All test docstrings have `SPEC §1.10 line <n>:` quotes matching decomposition spec | `tests/unit/test_cost_tracker.py`, `tests/integration/test_cost_tracker_service.py` | Verified against `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` | PASS |

## Test attack result
An isolated temporary git worktree was created at `tracker/.cache/wt-verify-us29`.
Mutated `sidecar/cost_tracker.py` line 265 to hardcode `amount = 0.0` in `calculate_cost`.
Ran pytest test suite:
```powershell
pytest tests/unit/test_cost_tracker.py tests/integration/test_cost_tracker_service.py
FAILED tests/unit/test_cost_tracker.py::test_calculate_cost_exact_formula - AssertionError: assert 0.0 == 10.7275
FAILED tests/unit/test_cost_tracker.py::test_cost_tracker_session_accumulator - AssertionError: assert 0.0 == 0.35
FAILED tests/unit/test_cost_tracker.py::test_cost_tracker_provider_lifecycle_and_registry - AssertionError: assert 0.0 > 0
FAILED tests/integration/test_cost_tracker_service.py::test_cost_calculate_endpoint - assert 0.0 > 0
FAILED tests/integration/test_cost_tracker_service.py::test_cost_record_and_session_endpoints - assert 0.0 > 0
5 failed, 12 passed in 2.30s
```
Mutation test confirmed tests are sensitive, specific, and catch behavioral regressions. Scratch worktree cleanly removed.

## Findings
1. `sidecar/cost_tracker.py:25`: Official pricing snapshot includes standard Claude 3.5/3.7/Opus, GPT-4o/o1/o3-mini, and Gemini 1.5/2.0 families in USD per million tokens. Cleanly structured.
2. `sidecar/cost_tracker.py:294`: Thread-safe session accumulation across multi-threaded or multi-instance calls using class-level state and `threading.RLock()`.
3. `sidecar/service.py:1010`: Sidecar cost endpoints properly enforce HTTP 503 off-switch when `locus.usage_cost_tracking.enabled` is false.
4. `locus-extension/src/tracking/usage.ts:162`: TypeScript `UsageTracker` singleton properly exports modular logic for Pi extension integration.

## Not checked
- External network egress to remote provider live pricing APIs is intentionally stubbed/snapshotted in line with offline-first self-hosted design principles.
