VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.6s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0011
features 1 | verified avg 85.0% | old claimed avg 75.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0011", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Module implementing Title Generation per §1.11 created under sidecar/ and locus-extension/ | `sidecar/title_generator.py:108`, `sidecar/providers/title_generator.py:46`, `locus-extension/src/sessions/title-gen.ts:107` | `tests/unit/test_title_generator.py:129`, `tests/integration/test_title_generator_service.py:18` | PASS |
| Registers as a provider in sidecar/providers/ with modular off-switch `locus.title_generation.enabled` returning 503 | `sidecar/title_generator.py:237`, `sidecar/service.py:1101` | `tests/unit/test_title_generator.py:186`, `tests/integration/test_title_generator_service.py:65` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/title_generator.py:31`, `sidecar/title_generator.py:73` | `tests/unit/test_title_generator.py:28-202` (12 tests) | PASS |
| Integration tests assert HTTP endpoints `/title/generate`, `/title/clean`, `/title/prompt` | `sidecar/service.py:1106-1144` | `tests/integration/test_title_generator_service.py:18-80` (4 tests) | PASS |
| All test docstrings have `SPEC §1.11 line <n>:` quotes matching decomposition spec | `tests/unit/test_title_generator.py`, `tests/integration/test_title_generator_service.py` | Verified against `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` | PASS |

## Test attack result
Created isolated scratch worktree at `tracker/.cache/wt-verify-us30`.
Mutated `sidecar/title_generator.py` line 47 to disable quote stripping (`quote_chars = ""`).
Ran pytest test suite:
```powershell
pytest tests/unit/test_title_generator.py tests/integration/test_title_generator_service.py
FAILED tests/unit/test_title_generator.py::test_clean_title_strip_quotes - assert '"FastAPI Architecture Design"' == 'FastAPI Architecture Design'
FAILED tests/unit/test_title_generator.py::test_clean_title_remove_prefix - assert '"Optimizing SQLite Queries"' == 'Optimizing SQLite Queries'
FAILED tests/unit/test_title_generator.py::test_title_generator_provider_synchronous_generation - assert '"Kubernetes Pod Lifecycle Management."' == 'Kubernetes Pod Lifecycle Management'
FAILED tests/integration/test_title_generator_service.py::test_title_clean_endpoint - assert '"Building a Distributed SQLite Database Engine..."' == 'Building a Distributed SQLite Database Engine'
4 failed, 12 passed in 2.02s
```
Mutation test confirmed tests fail on regressed behavior. Worktree cleanly destroyed.

## Findings
1. `sidecar/title_generator.py:31`: Cleaning pipeline thoroughly strips multiple varieties of Unicode quotes (« », “ ”, „ ”), handles case-insensitive "Title:" prefixes, trailing punctuation, and enforces the 80 character length cap.
2. `sidecar/title_generator.py:73`: Input snippets are safely clamped to 500 characters, keeping background prompt overhead minimal.
3. `sidecar/service.py:1106`: HTTP 503 off-switch is enforced across all `/title/*` endpoints when `locus.title_generation.enabled` is disabled.
4. `locus-extension/src/sessions/title-gen.ts:107`: TypeScript module exports `cleanTitle`, `formatTitlePrompt`, and `TitleGenerator` for client-side Pi session usage.

## Not checked
- Integration with external LLM endpoints in production involves API keys and network access outside the local offline sandbox; verified using mock LLM callers and heuristic fallback.
