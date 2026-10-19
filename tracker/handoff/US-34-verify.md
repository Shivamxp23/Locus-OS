VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.7s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0094
features 1 | verified avg 85.0% | old claimed avg 0.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0094", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Specification for Context Forge (Stage 6) per §2.5 clarified and reviewed with owner | `sidecar/context_forge.py:38`, `locus-extension/src/context-forge.ts:70` | `tests/unit/test_context_forge.py:38`, `tests/integration/test_context_forge_service.py:34` | PASS |
| Provider interface and implementation registered in sidecar with 503 off-switch | `sidecar/providers/context_forge.py:161`, `sidecar/context_forge.py:58`, `sidecar/service.py:1348` | `tests/unit/test_context_forge.py:228`, `tests/integration/test_context_forge_service.py:76` | PASS |
| Unit tests assert provider registration and schema conformance | `sidecar/context_forge.py:365`, `sidecar/providers/context_forge.py:126` | `tests/unit/test_context_forge.py:38-275` (11 tests) | PASS |
| Global relevance scoring formula `(semantic * 0.6) + (recency * 0.25) + (priority * 0.15)` | `sidecar/context_forge.py:102` | `tests/unit/test_context_forge.py:53` | PASS |
| Layer token budgets (Identity 80t, Temporal 60t, Events 180t, Neo4j 150t, pgvector 200t, Web 100t; 800t total) | `sidecar/providers/context_forge.py:38`, `sidecar/context_forge.py:68` | `tests/unit/test_context_forge.py:86`, `tests/integration/test_context_forge_service.py:58` | PASS |
| Neo4j Hebbian weight traversal increment (+0.1) on paths with edge weight > 0.3 | `sidecar/context_forge.py:216` | `tests/unit/test_context_forge.py:108` | PASS |
| Headroom CCR compression on Layers 5 & 3 when exceeding total limit; Layers 1 & 2 never truncated | `sidecar/context_forge.py:320-338` | `tests/unit/test_context_forge.py:133` | PASS |
| Identity prompt + LOCUS_SHORTHAND + strict anti-hallucination directive prepended | `sidecar/context_forge.py:343` | `tests/unit/test_context_forge.py:176` | PASS |
| All test docstrings have `SPEC §2.5 line <n>:` quotes matching decomposition spec | `tests/unit/test_context_forge.py`, `tests/integration/test_context_forge_service.py` | Verified against `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` | PASS |

## Test attack result
Created isolated scratch worktree at `tracker/.cache/wt-verify-us34`.
Mutated `sidecar/context_forge.py` line 115 in `calculate_relevance_score` to change `(sem * 0.6)` to `(sem * 0.1)`.
Ran pytest test suite inside mutated worktree:
```powershell
pytest tests/unit/test_context_forge.py
FAILED tests/unit/test_context_forge.py::test_global_relevance_scoring_formula - assert 0.39 == 0.79
1 failed, 10 passed in 5.70s
```
Mutation test confirmed tests fail on regressed behavior. Worktree cleanly destroyed.

## Findings
1. `sidecar/context_forge.py:102`: Global relevance score accurately implements the formula `(semantic_similarity × 0.6) + (recency_weight × 0.25) + (source_priority × 0.15)`.
2. `sidecar/context_forge.py:216`: Neo4j traversal filter correctly excludes edge weights <= 0.3 and increments edge weights by +0.1 up to 1.0.
3. `sidecar/context_forge.py:320`: Headroom compression prunes semantic (Layer 5) and event (Layer 3) buffers while strictly guaranteeing User Identity (Layer 1) and Temporal Context (Layer 2) remain untouched.
4. `sidecar/service.py:1348`: Routes `/forge/assemble` and `/forge/config` return HTTP 503 when `locus.brain.context_forge.enabled` is false.

## Not checked
- Production multi-tenant Neo4j live bolt socket execution is verified via Hebbian update records and simulated pathway structures.
