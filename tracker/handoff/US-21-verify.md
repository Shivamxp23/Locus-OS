VERDICT: ACCEPT
Verifier: Gemini 2.5 Pro

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.6s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0002
features 1 | verified avg 85.0% | old claimed avg 100.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
{"id": "F-0002", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Name | Result |
| :--- | :--- | :--- | :--- |
| Module implementing System Prompt Construction created under sidecar/ or locus-extension/ | `sidecar/prompt_builder.py`, `locus-extension/src/prompt-builder.ts` | `test_prompt_builder_provider_interface` | PASS |
| Registers as a provider in sidecar/providers/ with modular off-switch returning 503 | `sidecar/service.py:383-433` | `test_prompt_builder_off_switch_503` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `tests/unit/test_prompt_builder.py` | 13 unit tests | PASS |

## Test attack result
- Scratch worktree `tracker/.cache/wt-verify-21` created at commit `9e0ed7079`.
- Mutated `sidecar/prompt_builder.py` to disable backward slash normalization (`prompt_cwd = options.cwd`).
- Executed `py -3 -m pytest -k test_system_prompt_cwd_normalization`.
- Test FAILED with `AssertionError: assert 'Current working directory: C:/Users/soni8/Desktop/locus-os' in ... Current working directory: C:\Users\soni8\Desktop\locus-os`.
- Scratch worktree cleanly removed.

## Findings
none. Implementation matches SPEC §1.2 exactly.

## Not checked
- Physical Pi CLI process launch with `--approve --no-context-files` loading `locus-extension/src/prompt-builder.ts` (tested at unit and service integration boundaries).
