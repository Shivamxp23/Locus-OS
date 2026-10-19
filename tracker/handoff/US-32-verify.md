VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.6s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0092
features 1 | verified avg 85.0% | old claimed avg 0.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0092", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Specification for Query Router / Intent Classifier (Stage 2) per §2.1-2.3 clarified and reviewed with owner | `sidecar/router/classifier.py:32`, `locus-extension/src/intent-classifier.ts:7` | `tests/unit/test_query_router.py:27`, `tests/integration/test_query_router_service.py:25` | PASS |
| Provider interface and stub implementation registered in sidecar with 503 off-switch | `sidecar/providers/query_router.py:72`, `sidecar/router/classifier.py:84`, `sidecar/service.py:1268` | `tests/unit/test_query_router.py:126`, `tests/integration/test_query_router_service.py:53` | PASS |
| Unit tests assert provider registration and schema conformance | `sidecar/router/classifier.py:229`, `sidecar/providers/query_router.py:38` | `tests/unit/test_query_router.py:27-140` (9 tests) | PASS |
| Anti-hallucination confidence gate (<0.7 forces querying all 4 data sources) | `sidecar/router/classifier.py:198`, `locus-extension/src/intent-classifier.ts:50` | `tests/unit/test_query_router.py:79`, `tests/integration/test_query_router_service.py:42` | PASS |
| Temporal scope resolution (TODAY, WEEK, MONTH, ALLTIME) to start_ts and end_ts Unix timestamps | `sidecar/router/classifier.py:94-142` | `tests/unit/test_query_router.py:94-124` | PASS |
| All test docstrings have `SPEC §2.1-2.3 line <n>:` quotes matching decomposition spec | `tests/unit/test_query_router.py`, `tests/integration/test_query_router_service.py` | Verified against `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` | PASS |

## Test attack result
Created isolated scratch worktree at `tracker/.cache/wt-verify-us32`.
Mutated `sidecar/router/classifier.py` lines 116-123 in `resolve_temporal_scope` to set `start_dt.replace(hour=12)` instead of `hour=0`.
Ran pytest test suite inside mutated worktree:
```powershell
pytest tests/unit/test_query_router.py tests/integration/test_query_router_service.py
FAILED tests/unit/test_query_router.py::test_temporal_scope_resolution_today - AssertionError: assert (1770056999.999999 - 1770013800.0) >= 86399.0
1 failed, 11 passed in 1.50s
```
Mutation test confirmed tests fail on regressed behavior. Worktree cleanly destroyed.

## Findings
1. `sidecar/router/classifier.py:44`: Robust regex intent mapping supports all 8 canonical intent categories: `FACTUAL_PERSONAL`, `BEHAVIORAL_PATTERN`, `KNOWLEDGE_RETRIEVAL`, `TASK_PLANNING`, `EMOTIONAL_STATE`, `EXTERNAL_KNOWLEDGE`, `SYNTHESIS`, `INFERENCE_REQUEST`.
2. `sidecar/router/classifier.py:198`: Anti-hallucination confidence gate strictly enforces `sources_required = ["pg", "neo4j", "pgvector", "pageindex"]` whenever confidence drops below 0.70.
3. `sidecar/router/classifier.py:94`: Timezone-aware date replacement correctly bounds `TODAY` to the user's localized 24-hour day interval (defaulting to IST `Asia/Kolkata`).
4. `sidecar/service.py:1268`: Endpoint `POST /router/classify` returns HTTP 503 `{"disabled": "locus.query_router.enabled"}` when disabled.

## Not checked
- Production multi-modal voice/attachment intake (Stage 0) and Telegram keyboard dispatch (Stage 11) are out of scope for Stage 2 Query Router.
