VERDICT: ACCEPT
Verifier: Claude Opus

## Guard output
```
LOCUS GUARD  mode=full  root=C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os
[WARN] segment-size: docs/agent/11-agile-workflow.md is 8806 bytes (limit 7500). Segments must stay concentrated: split it.  (docs/agent/11-agile-workflow.md)
[WARN] spec-lint: 26 KNOWN spec defects still open (docs/agent/09-spec-errata.md). Agents must stop and ask when a task touches one.
[WARN] stale-locus-core: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:13)
[WARN] stale-locus-core: 40 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:415)
[WARN] stale-locus-extensions: 2 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:544)
[WARN] stale-locus-os-src-core: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:13)
[WARN] stale-locus-os-src-core: 11 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:1179)
[WARN] stale-src-extensions: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (AGENTS.md:14)
[WARN] stale-src-extensions: 1 reference(s) to a non-canonical path; canonical is `locus-extension/src/`.  (.keysndocs/Documentation/Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md:7095)

PASS: 0 FAIL, 9 WARN, 0 INFO  (4.1s)
```

## Verify line
```
features 1 | verified avg 85.0% | old claimed avg 50.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0047", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| # | Acceptance Criterion | Code | Test | Status |
|---|---|---|---|---|
| 1 | Module implementing Graceful Restart per §17.10: Graceful Gateway Restart & State Snapshotting created under sidecar/ or locus-extension/ | `sidecar/gateway/lifecycle.py:1-265`, `locus-extension/src/gateway/lifecycle.ts:1-125` | `tests/unit/test_graceful_restart.py:1-125` | SATISFIED |
| 2 | Registers as a provider in sidecar/providers/ with modular off-switch `locus.graceful_restart.enabled` and `locus.gateway.graceful_restart.enabled` returning 503 | `sidecar/providers/graceful_restart.py:1-95`, `sidecar/service.py` | `tests/unit/test_graceful_restart.py:100-125`, `tests/integration/test_graceful_restart_service.py:75-105` | SATISFIED |
| 3 | Unit and integration tests in `tests/unit/` and `tests/integration/` assert expected logic, boundary conditions, and error containment | `tests/unit/test_graceful_restart.py` (6 unit tests), `tests/integration/test_graceful_restart_service.py` (6 integration tests) | `tests/unit/test_graceful_restart.py` + `tests/integration/test_graceful_restart_service.py` (12 passed) | SATISFIED |

## Test attack result
Mutated `sidecar/gateway/lifecycle.py` by changing `MockChannelAdapter.name` to return `"mutated_channel"`.
Re-ran `pytest tests/unit/test_graceful_restart.py::test_swappable_channel_adapters`.
The test failed immediately with:
`AssertionError: assert 'telegram' in ['mutated_channel', 'mutated_channel']`
Original code was restored cleanly and test passed.

## Findings
None. The implementation cleanly satisfies SPEC §17.10 requirements:
- `GatewayLifecycleManager` handles 30s connection draining, ingress adapter deregistration, session snapshotting to `.locus/sessions/recovery/{id}.json`, and forensic logging.
- Crash-resilient session recovery recovers active sessions from disk on startup.
- Modular off-switches (`locus.graceful_restart.enabled` and `locus.gateway.graceful_restart.enabled`) return HTTP 503 with standardized status payloads.
- TypeScript contract in `locus-extension/src/gateway/lifecycle.ts` provides `GatewayLifecycleClient`, `SessionSnapshot`, `ForensicRecord`, and `LifecycleStatus` interfaces.
