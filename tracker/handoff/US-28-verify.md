VERDICT: ACCEPT
Verifier: Claude 3.7 Sonnet

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

PASS: 0 FAIL, 9 WARN, 0 INFO  (3.2s)
```

## Verify line
```
features 1 | verified avg 85.0% | old claimed avg 80.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0009", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| Criterion | Code file:line | Test file:line | Status |
|-----------|----------------|----------------|--------|
| Module implementing Rate Limit Tracking per §1.9: Rate Limit Tracking created under sidecar/ or locus-extension/ | `sidecar/rate_limiter.py:117`, `locus-extension/src/rate-limiter.ts:161` | `tests/unit/test_rate_limiter.py:80`, `tests/integration/test_rate_limiter_service.py:20` | SATISFIED |
| Registers as a provider in sidecar/providers/ with modular off-switch locus.rate_limit_tracking.enabled returning 503 | `sidecar/rate_limiter.py:283`, `sidecar/service.py:920` | `tests/unit/test_rate_limiter.py:188`, `tests/integration/test_rate_limiter_service.py:97` | SATISFIED |
| Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `sidecar/rate_limiter.py:23-280`, `sidecar/providers/rate_limit.py:17-172` | `tests/unit/test_rate_limiter.py:27-215` (14 unit tests passed) | SATISFIED |

## Test attack result
Created isolated scratch worktree at `tracker/.cache/wt-verify-us28`. Mutated `RateLimitBucket.used` property to return `self.remaining` instead of `max(0, self.limit - self.remaining)`.
Running `pytest tests/unit/test_rate_limiter.py` in the scratch worktree immediately failed with 5 test failures:
- `FAILED tests/unit/test_rate_limiter.py::test_rate_limit_bucket_used_computation`
- `FAILED tests/unit/test_rate_limiter.py::test_rate_limit_bucket_usage_pct_computation`
- `FAILED tests/unit/test_rate_limiter.py::test_rate_limit_state_structure_and_has_data`
- `FAILED tests/unit/test_rate_limiter.py::test_format_rate_limit_display_populated`
- `FAILED tests/unit/test_rate_limiter.py::test_rate_limit_tracker_provider_lifecycle`
Confirmed the tests reliably catch defects. Removed scratch worktree cleanly.

## Findings
1. `sidecar/providers/rate_limit.py:17-128`: Dataclasses `RateLimitBucket` and `RateLimitState` implement exact formulas from spec §1.9 (`used = max(0, limit - remaining)`, `usage_pct = (used / limit) * 100`, `remaining_seconds_now = max(0, reset_seconds - (now - captured_at))`) with complete dictionary serialization roundtrip.
2. `sidecar/rate_limiter.py:117-185`: `parse_rate_limit_headers` cleanly normalizes 12 canonical headers (`x-ratelimit-limit-*`, `x-ratelimit-remaining-*`, `x-ratelimit-reset-*`) for requests and tokens across 1-minute and 1-hour windows, parsing suffixes ("100k", "1M") and durations ("30s", "1m30s", epoch timestamps).
3. `sidecar/rate_limiter.py:205-250`: Pre-call rate guard `should_throttle` enforces the spec criteria, checking RPM remaining against safety margin threshold and tokens remaining < 1000.
4. `sidecar/service.py:920-995`: Routes `/ratelimit/parse`, `/ratelimit/state`, `/ratelimit/throttle/check`, and `/ratelimit/display` strictly enforce the 503 off-switch when disabled.
5. `tests/unit/test_rate_limiter.py`: Every unit test begins with an exact `SPEC §1.9 line <n>:` docstring reference verifying spec conformance.

## Not checked
- Physical network responses from remote third-party LLM providers (e.g. Nous Portal, Anthropic, OpenAI) were not called over the wire to avoid requiring live paid API credits and secrets during automated testing. Verified end-to-end via mocked and simulated headers in unit and FastAPI integration tests.
