VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.6s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0095
features 1 | verified avg 85.0% | old claimed avg 0.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0095", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Specification for Anti-Hallucination Guard (Stage 10) per §2.6 clarified and reviewed with owner | `sidecar/anti_hallucination.py:32`, `locus-extension/src/anti-hallucination.ts:38` | `tests/unit/test_anti_hallucination.py:27`, `tests/integration/test_anti_hallucination_service.py:32` | PASS |
| Provider interface and implementation registered in sidecar with 503 off-switch | `sidecar/providers/anti_hallucination.py:108`, `sidecar/anti_hallucination.py:262`, `sidecar/service.py:1396` | `tests/unit/test_anti_hallucination.py:151`, `tests/integration/test_anti_hallucination_service.py:87` | PASS |
| Unit tests assert provider registration and schema conformance | `sidecar/anti_hallucination.py:262`, `sidecar/providers/anti_hallucination.py:108` | `tests/unit/test_anti_hallucination.py:27-179` (10 tests) | PASS |
| Factual claims extracted from LLM responses about user data, completed actions, and vault | `sidecar/anti_hallucination.py:64` | `tests/unit/test_anti_hallucination.py:32` | PASS |
| Grounding verification checks claims against Context Forge content with numerical strictness | `sidecar/anti_hallucination.py:102` | `tests/unit/test_anti_hallucination.py:53`, `tests/unit/test_anti_hallucination.py:73` | PASS |
| Strict mode blocks output and logs severity 2 brain error | `sidecar/anti_hallucination.py:186` | `tests/unit/test_anti_hallucination.py:91`, `tests/integration/test_anti_hallucination_service.py:53` | PASS |
| Warn mode appends standard caveat and logs severity 1 brain error | `sidecar/anti_hallucination.py:218` | `tests/unit/test_anti_hallucination.py:113`, `tests/integration/test_anti_hallucination_service.py:32` | PASS |
| Off switch on `locus.brain.anti_hallucination.enabled` returns 503 | `sidecar/service.py:1396-1430` | `tests/integration/test_anti_hallucination_service.py:87` | PASS |
| All test docstrings have `SPEC §2.6 line <n>:` quotes matching decomposition spec | `tests/unit/test_anti_hallucination.py`, `tests/integration/test_anti_hallucination_service.py` | Verified against `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` | PASS |

## Test attack result
Created isolated scratch worktree at `tracker/.cache/wt-verify`.
Mutated `sidecar/anti_hallucination.py` in `check` method to disable strict mode branch (`active_mode == GuardMode.STRICT` -> `False`).
Ran pytest test suite inside mutated worktree:
```powershell
pytest tests/unit/test_anti_hallucination.py
FAILED tests/unit/test_anti_hallucination.py::test_strict_mode_rejects_and_logs - assert False is True
1 failed, 9 passed in 0.34s
```
Mutation test confirmed tests fail immediately on regressed behavior. Reverted and worktree cleanly destroyed.

## Findings
1. `sidecar/anti_hallucination.py`: Claim extraction properly isolates claims about user activity/vault while ignoring opinion and advice prefixes.
2. `sidecar/anti_hallucination.py`: Number grounding ensures that statements with quantitative claims cannot pass as grounded if the target numbers are absent from Context Forge.
3. `sidecar/service.py`: `/guard/check` and `/guard/config` adhere to the modular 503 off-switch standard.

## Not checked
- Production PostgreSQL live connection for `brain_errors` table write is tested via in-memory error log collector.
