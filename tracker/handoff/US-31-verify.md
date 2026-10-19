VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.6s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0012
features 1 | verified avg 85.0% | old claimed avg 100.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0012", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Module implementing Onboarding Flow per §1.12 created under sidecar/ and locus-extension/ | `sidecar/onboarding.py:41`, `sidecar/providers/onboarding.py:42`, `locus-extension/src/ui/setup-wizard.ts:85`, `locus_cli/setup.py:53` | `tests/unit/test_onboarding.py:28`, `tests/integration/test_onboarding_service.py:27` | PASS |
| Registers as a provider in sidecar/providers/ with modular off-switch `locus.onboarding_flow.enabled` returning 503 | `sidecar/onboarding.py:476`, `sidecar/service.py:1145` | `tests/unit/test_onboarding.py:240`, `tests/integration/test_onboarding_service.py:133` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/onboarding.py:68-410` | `tests/unit/test_onboarding.py:28-251` (12 tests) | PASS |
| Integration tests assert HTTP endpoints `/onboarding/start`, `/onboarding/step`, `/onboarding/diagnostics`, `/onboarding/status`, `/onboarding/reset` | `sidecar/service.py:1152-1260` | `tests/integration/test_onboarding_service.py:27-148` (6 tests) | PASS |
| All test docstrings have `SPEC §1.12 line <n>:` quotes matching decomposition spec | `tests/unit/test_onboarding.py`, `tests/integration/test_onboarding_service.py` | Verified against `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` | PASS |

## Test attack result
Created isolated scratch worktree at `tracker/.cache/wt-verify-us31`.
Mutated `sidecar/onboarding.py` line 86 to return `status="error_mutated"` instead of `"ok"` in `set_topology`.
Ran pytest test suite inside mutated worktree:
```powershell
pytest tests/unit/test_onboarding.py tests/integration/test_onboarding_service.py
FAILED tests/unit/test_onboarding.py::test_topology_selection_and_defaults - AssertionError: assert 'error_mutated' == 'ok'
1 failed, 17 passed in 6.89s
```
Mutation test confirmed tests fail on regressed behavior. Worktree cleanly destroyed.

## Findings
1. `sidecar/onboarding.py:68`: Multi-topology setup supports `local`, `vm`, and `hybrid` deployments, falling back gracefully to `local` on invalid input.
2. `sidecar/onboarding.py:314`: Live diagnostic probes run across LLM providers, graph memory (Neo4j), vault storage, Telegram bots, and cron schedulers with non-blocking error containment.
3. `sidecar/service.py:1145`: HTTP 503 modular off-switch is verified across all `/onboarding/*` routes when `locus.onboarding_flow.enabled` or `locus.onboarding.enabled` is false.
4. `locus_cli/setup.py:198`: Headless CLI setup provides full non-interactive batch automation via `--non-interactive --env-file <path>`.

## Not checked
- Physical hardware connections to live cloud VMs and remote Neo4j instances during diagnostics are mocked/stubbed with socket probes in local sandbox tests.
