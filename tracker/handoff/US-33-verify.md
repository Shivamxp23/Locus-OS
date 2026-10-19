VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.6s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0093
features 1 | verified avg 85.0% | old claimed avg 0.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0093", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Specification for State Engine (Stage 3) per §2.4 clarified and reviewed with owner | `sidecar/state_engine.py:27`, `locus-extension/src/state-engine.ts:8` | `tests/unit/test_state_engine.py:24`, `tests/integration/test_state_engine_service.py:24` | PASS |
| Provider interface and implementation registered in sidecar with 503 off-switch | `sidecar/providers/state_engine.py:100`, `sidecar/state_engine.py:59`, `sidecar/service.py:1296` | `tests/unit/test_state_engine.py:168`, `tests/integration/test_state_engine_service.py:68` | PASS |
| Unit tests assert provider registration and schema conformance | `sidecar/state_engine.py:236`, `sidecar/providers/state_engine.py:48` | `tests/unit/test_state_engine.py:24-174` (8 tests) | PASS |
| Canonical DCS calculation formula: `((E + M + S) / 3) * (1 - ST / 20)` | `sidecar/state_engine.py:68` | `tests/unit/test_state_engine.py:53`, `tests/integration/test_state_engine_service.py:38` | PASS |
| Operating mode determination across all 5 tiers (SURVIVAL -> PEAK) | `sidecar/state_engine.py:99` | `tests/unit/test_state_engine.py:72` | PASS |
| Staleness penalties applied when no check-in today (scores * 0.9) or >=3 days (baseline fallback + STALE_CHECKIN) | `sidecar/state_engine.py:180-218` | `tests/unit/test_state_engine.py:114-158` | PASS |
| All test docstrings have `SPEC §2.4 line <n>:` quotes matching decomposition spec | `tests/unit/test_state_engine.py`, `tests/integration/test_state_engine_service.py` | Verified against `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` | PASS |

## Test attack result
Created isolated scratch worktree at `tracker/.cache/wt-verify-us33`.
Mutated `sidecar/state_engine.py` line 99 in `calculate_dcs` to add `+ 2.0` offset to DCS computation.
Ran pytest test suite inside mutated worktree:
```powershell
pytest tests/unit/test_state_engine.py tests/integration/test_state_engine_service.py
FAILED tests/unit/test_state_engine.py::test_canonical_dcs_formula_calculation - assert 2.0 == 0.0
FAILED tests/unit/test_state_engine.py::test_process_checkin_and_state_snapshot - AssertionError: assert 10.0 == 8.1
FAILED tests/integration/test_state_engine_service.py::test_state_calculate_endpoint - assert 10.0 == 8.1
3 failed, 9 passed in 1.89s
```
Mutation test confirmed tests fail on regressed behavior. Worktree cleanly destroyed.

## Findings
1. `sidecar/state_engine.py:68`: Canonical DCS calculation formula strictly bounds inputs and computes `((E + M + S) / 3) * (1 - ST / 20)` with 0.0-10.0 clamping.
2. `sidecar/state_engine.py:99`: 5-tier operating mode classification accurately implements LOCUS_SYSTEM_v1.md §4 boundaries (`SURVIVAL` <= 2.0, `RECOVERY` <= 4.0, `NORMAL` <= 6.0, `DEEP_WORK` <= 8.0, `PEAK` > 8.0).
3. `sidecar/state_engine.py:180`: Staleness decay correctly degrades scores by 10% after 24h and falls back to baseline with `STALE_CHECKIN` alert after 72h.
4. `sidecar/service.py:1296`: Endpoints `/state/current` and `/state/calculate` enforce HTTP 503 off-switch when `locus.state_engine.enabled` is false.

## Not checked
- Production multi-user PostgreSQL LISTEN/NOTIFY socket bridge is simulated via thread-safe in-memory cache for sidecar unit testing.
