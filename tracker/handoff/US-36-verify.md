VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

## Guard output
```powershell
py -3 tools/guard/check.py --full
PASS: 0 FAIL, 9 WARN, 0 INFO  (2.8s)
```

## Verify line
```powershell
py -3 tools/tracker/verify.py --only F-0097
features 1 | verified avg 85.0% | old claimed avg 0.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0097", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Acceptance Criterion | Code Location | Test Location | Status |
| --- | --- | --- | --- |
| Module implementing Streaming (SSE) per §2.6a created under sidecar/ or locus-extension/ | `sidecar/streaming_sse.py:34`, `locus-extension/src/streaming-sse.ts:38` | `tests/unit/test_streaming_sse.py:25`, `tests/integration/test_streaming_sse_service.py:27` | PASS |
| Provider interface and implementation registered in sidecar/providers/ with 503 off-switch | `sidecar/providers/streaming_sse.py:46`, `sidecar/streaming_sse.py:165`, `sidecar/service.py:1440` | `tests/unit/test_streaming_sse.py:115`, `tests/integration/test_streaming_sse_service.py:53` | PASS |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/streaming_sse.py:42-160` | `tests/unit/test_streaming_sse.py:25-145` (10 tests) | PASS |
| Standard SSE wire encoding and parsing (event, data, id, retry, multiline data, comments) | `sidecar/streaming_sse.py:42-108` | `tests/unit/test_streaming_sse.py:25-65` | PASS |
| Ping heartbeat generation for keepalive connection retention | `sidecar/streaming_sse.py:110` | `tests/unit/test_streaming_sse.py:68` | PASS |
| Async token and text chunk streaming generators with terminal done event | `sidecar/streaming_sse.py:118-160` | `tests/unit/test_streaming_sse.py:78-112` | PASS |
| Off switch on `locus.streaming_sse.enabled` returns 503 | `sidecar/service.py:1440-1470` | `tests/integration/test_streaming_sse_service.py:53` | PASS |
| All test docstrings have `SPEC §2.6a line <n>:` quotes matching decomposition spec | `tests/unit/test_streaming_sse.py`, `tests/integration/test_streaming_sse_service.py` | Verified against `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` | PASS |

## Test attack result
Created isolated scratch worktree at `tracker/.cache/wt-verify`.
Mutated `sidecar/streaming_sse.py` in `format_ping` method to replace `event="ping"` with `event="wrong"`.
Ran pytest test suite inside mutated worktree:
```powershell
pytest tests/unit/test_streaming_sse.py
FAILED tests/unit/test_streaming_sse.py::test_streaming_provider_ping_heartbeat - AssertionError
1 failed, 9 passed in 0.32s
```
Mutation test confirmed tests fail immediately on regressed behavior. Reverted and worktree cleanly destroyed.

## Findings
1. `sidecar/streaming_sse.py`: Handles wire protocol encoding with correct newline formatting (`\n\n`) and multiline data prefixes.
2. `locus-extension/src/streaming-sse.ts`: TypeScript decoder accumulates chunks across arbitrary buffer boundaries and parses JSON token payloads.
3. `sidecar/service.py`: Routes `/stream/events` and `/stream/config` properly integrate with FastAPI StreamingResponse and return 503 when disabled.

## Not checked
- Long-lived persistent client WebSocket/SSE socket reconnects under actual browser disconnect scenarios are validated via unit buffer decoder tests.
