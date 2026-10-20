VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.7s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0036
features 1 | verified avg 85.0% | old claimed avg 60.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0036", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Module implementing Subagents / AutoResearch per §11.1-11.5 and §3.7 created under sidecar/ or locus-extension/ | `sidecar/subagents.py:30`, `locus-extension/src/subagents.ts:15` | `tests/unit/test_subagents_autoresearch.py:25`, `tests/integration/test_subagents_service.py:25` | PASS |
| Registers as a provider in sidecar/providers/ with modular off-switch locus.subagents_autoresearch.enabled returning 503 | `sidecar/providers/subagents.py:120`, `sidecar/subagents.py:230`, `sidecar/service.py:1650` | `tests/unit/test_subagents_autoresearch.py:175`, `tests/integration/test_subagents_service.py:90` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/subagents.py:30-280` | `tests/unit/test_subagents_autoresearch.py:20-190` (12 tests) | PASS |
| 4 Locus faction archetypes registered (planner, curator, analyst, builder) | `sidecar/subagents.py:40-75` | `tests/unit/test_subagents_autoresearch.py:45-60` | PASS |
| 15 OpenHuman archetypes registered (orchestrator, researcher, critic, implementer, etc.) | `sidecar/subagents.py:80-220` | `tests/unit/test_subagents_autoresearch.py:65-95` | PASS |
| Depth limiting strictly enforces MAX_SPAWN_DEPTH = 3, rejecting deeper requests with 400 Bad Request | `sidecar/subagents.py:265-270`, `sidecar/service.py:1675` | `tests/unit/test_subagents_autoresearch.py:115-135`, `tests/integration/test_subagents_service.py:45-55` | PASS |
| Subagent spawning sets skip_memory=True, skip_review=True, and triggers parent memory delegation callback | `sidecar/subagents.py:285-310` | `tests/unit/test_subagents_autoresearch.py:100-112`, `tests/unit/test_subagents_autoresearch.py:145-160` | PASS |
| AutoResearch decomposes topic into multi-subagent investigation loop | `sidecar/subagents.py:315-380`, `sidecar/service.py:1720` | `tests/unit/test_subagents_autoresearch.py:165-195`, `tests/integration/test_subagents_service.py:75-90` | PASS |
| Off-switch on `locus.subagents_autoresearch.enabled` returns 503 across /subagents/* endpoints | `sidecar/service.py:1645-1730` | `tests/integration/test_subagents_service.py:90-115` | PASS |

## Test attack result
Created detached scratch worktree at `../verify-tmp`.
Mutated `sidecar/subagents.py` to bypass depth limiting checks (`if request.current_depth >= MAX_SPAWN_DEPTH:` replaced with `if False:`).
Ran pytest targeted at `test_depth_limiting_enforcement`:
```powershell
pytest tests/unit/test_subagents_autoresearch.py -k test_depth_limiting_enforcement
FAILED tests/unit/test_subagents_autoresearch.py::test_depth_limiting_enforcement
Failed: DID NOT RAISE ValueError
1 failed, 11 deselected in 0.81s
```
Mutation test confirmed that depth limiting enforcement test fails when constraints are bypassed. Scratch worktree was cleanly removed.

## Findings
1. `sidecar/subagents.py`: Fully implements the 4 Locus faction agents and 15 OpenHuman archetypes, enforces recursive depth bounding at MAX_SPAWN_DEPTH = 3, and runs AutoResearch synthesis loops.
2. `locus-extension/src/subagents.ts`: TypeScript client cleanly binds all `/subagents/*` routes with client-side depth validation and error mapping.
3. `sidecar/service.py`: Enforces modular 503 off-switch across `/subagents/spawn`, `/subagents/archetypes`, `/subagents/config`, and `/subagents/autoresearch` when disabled.

## Not checked
- External real-world LLM execution for arbitrary third-party model inference inside spawned subagents (mocked via standard prompt execution templates for deterministic test isolation).
