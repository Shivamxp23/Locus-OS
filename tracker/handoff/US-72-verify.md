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

PASS: 0 FAIL, 8 WARN, 0 INFO  (3.8s)
```

## Verify line
```
features 1 | verified avg 85.0% | old claimed avg 70.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 8, 'INFO': 0}
{"id": "F-0040", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| # | Acceptance Criterion | Code | Test | Status |
|---|---|---|---|---|
| 1 | Module implementing Shell Blocklist per §13.7 created under `sidecar/` or `locus-extension/` | `sidecar/security/shell_policy.py:1-225`, `locus-extension/src/security/shell-policy.ts:1-120` | `tests/unit/test_shell_blocklist.py:1-180` | SATISFIED |
| 2 | Registers as a provider in `sidecar/providers/` with modular off-switch `locus.shell_blocklist.enabled` returning 503 | `sidecar/providers/shell_blocklist.py:1-115`, `sidecar/service.py:5830-5935` | `tests/unit/test_shell_blocklist.py:150-180`, `tests/integration/test_shell_blocklist_service.py:55-80` | SATISFIED |
| 3 | Unit tests in `tests/unit/` assert expected logic, boundary conditions, and error containment | `tests/unit/test_shell_blocklist.py:1-180` (12 unit tests), `tests/integration/test_shell_blocklist_service.py:1-80` (4 integration tests) | `tests/unit/test_shell_blocklist.py` + `tests/integration/test_shell_blocklist_service.py` (16 passed) | SATISFIED |

## Test attack result
Mutated `sidecar/security/shell_policy.py` by bypassing default pattern checks in `check_shell_command`.
Re-ran `pytest tests/unit/test_shell_blocklist.py::test_blocked_patterns_fork_bomb`.
The test failed immediately with:
`AssertionError: assert True is False`
Original code was restored cleanly and test passed.

## Findings
None. The implementation cleanly satisfies SPEC §13.7 requirements:
- `DEFAULT_BLOCKED_PATTERNS` catches destructive wipes (`rm -rf /`, `rm -rf ~`, `rm -rf $HOME`), fork bombs (`:(){ :|:& };:`), open chmod 777 permissions, pipe-to-shell, and dangerous sudo escalations.
- `SENSITIVE_HOME_DIRS` and `SENSITIVE_HOME_FILES` enforce strict path-level and command-level read/write blocks on user SSH credentials, AWS configs, GPG keyrings, Docker credentials, and shell startup scripts.
- Modular off-switches (`locus.shell_blocklist.enabled` and `locus.security.shell_blocklist.enabled`) return HTTP 503 with standardized error responses.
- TypeScript client contract in `locus-extension/src/security/shell-policy.ts` wraps command checking and hook integration for terminal tools.
