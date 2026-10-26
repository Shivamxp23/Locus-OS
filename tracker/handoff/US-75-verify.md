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

PASS: 0 FAIL, 9 WARN, 0 INFO  (3.8s)
```

## Verify line
```
features 1 | verified avg 85.0% | old claimed avg 75.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0043", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| # | Acceptance Criterion | Code | Test | Status |
|---|---|---|---|---|
| 1 | Module implementing Message Sanitization per §13.10 created under `sidecar/` or `locus-extension/` | `sidecar/security/sanitizer.py:1-140`, `locus-extension/src/security/message-sanitize.ts:1-145` | `tests/unit/test_message_sanitizer.py:1-125` | SATISFIED |
| 2 | Registers as a provider in `sidecar/providers/` with modular off-switch `locus.message_sanitization.enabled` returning 503 | `sidecar/providers/message_sanitizer.py:1-75`, `sidecar/service.py:6160-6240` | `tests/unit/test_message_sanitizer.py:90-120`, `tests/integration/test_message_sanitizer_service.py:65-90` | SATISFIED |
| 3 | Unit tests in `tests/unit/` assert expected logic, boundary conditions, and error containment | `tests/unit/test_message_sanitizer.py:1-120` (7 unit tests), `tests/integration/test_message_sanitizer_service.py:1-90` (4 integration tests) | `tests/unit/test_message_sanitizer.py` + `tests/integration/test_message_sanitizer_service.py` (11 passed) | SATISFIED |

## Test attack result
Mutated `sidecar/security/sanitizer.py` by removing regex replacement in `sanitize_surrogates` to return input text untouched.
Re-ran `pytest tests/unit/test_message_sanitizer.py::test_sanitize_surrogate_replacement`.
The test failed immediately with:
`AssertionError: assert '\ud800' not in 'Invalid\ud800high\udbffsurrogates\udc00and\udffflow'`
Original code was restored cleanly and test passed.

## Findings
None. The implementation cleanly satisfies SPEC §13.10 requirements:
- `SURROGATE_RE` identifies lone surrogate code points (`[\ud800-\udfff]`) and swaps them with `\ufffd`, preventing JSON serialization and UTF-8 encoding failures.
- `sanitize_structure_surrogates` recursively traverses complex nested dictionary and list trees, cleaning keys and values while preserving clean nodes.
- `sanitize_messages` cleans full conversation lists, tool call parameters, and metadata objects prior to model dispatch.
- Modular off-switches (`locus.message_sanitization.enabled` and `locus.security.message_sanitization.enabled`) return HTTP 503 with standardized error responses.
- TypeScript contract in `locus-extension/src/security/message-sanitize.ts` exports `MessageSanitizerClient` and pure helper functions `sanitizeSurrogates`, `sanitizeStructureSurrogates`, and `sanitizeMessages`.
