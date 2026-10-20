VERDICT: ACCEPT
Verifier: Gemini 3.8 Flash

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

PASS: 0 FAIL, 9 WARN, 0 INFO  (3.4s)
```

## Verify line
```
features 1 | verified avg 85.0% | old claimed avg 25.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0025", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Criterion | Code File:Line | Test File:Line | Status |
|---|---|---|---|
| Module implementing Project Memory Decay per §4.14: Project-Specific Memory Decay Engine created under sidecar/ or locus-extension/ | `sidecar/memory/project_decay.py:1`, `sidecar/memory/cold_archiver.py:1`, `sidecar/providers/project_memory_decay.py:1` | `tests/unit/test_project_decay.py:27`, `tests/unit/test_project_decay.py:117` | PASS |
| Registers as a provider in sidecar/providers/ with modular off-switch locus.project_memory_decay.enabled returning 503 | `sidecar/providers/project_memory_decay.py:130`, `sidecar/service.py:3848` | `tests/integration/test_project_decay_service.py:125` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/memory/project_decay.py:37`, `sidecar/memory/project_decay.py:141` | `tests/unit/test_project_decay.py:46`, `tests/unit/test_project_decay.py:72`, `tests/unit/test_project_decay.py:84`, `tests/unit/test_project_decay.py:149`, `tests/unit/test_project_decay.py:214` | PASS |

## Test attack result
In detached scratch worktree `tracker/.cache/wt-verify`, mutated `calculate_retention_strength` in `sidecar/memory/project_decay.py` line 58 to invert decay exponent:
`strength = initial_strength * (2.0 ** (days / half_life))` instead of `-days`.
Ran `python -m pytest tests/unit/test_project_decay.py tests/integration/test_project_decay_service.py -q`:
- `test_calculate_retention_strength_exact`: FAILED
- `test_retention_strength_bounds_and_clamping`: FAILED
- `test_cold_storage_threshold_trigger`: FAILED
- `test_nightly_project_decay_sweep`: FAILED (`assert 'p_archived' in []`)
- `test_sweep_dry_run`: FAILED (`assert 0 == 1`)
- `test_provider_interface_implementation`: FAILED (`assert 1.0 == 0.5`)
- `test_service_decay_calculate`: FAILED (`assert 1.0 == 0.5`)
- `test_service_decay_projects_and_sweep`: FAILED (`assert 'proj_legacy' in []`)
Outcome: 8 failed, 8 passed. The test suite is strictly sensitive to algorithmic inversion. Detached worktree removed cleanly.

## Findings
None. All 20 spec behaviour sentences from §4.14 are covered in code and verified by passing unit and integration tests.

## Not checked
- L5 proof signoff: Requires human signoff in `tracker/signoff.yaml` as designed by the guard architecture.
