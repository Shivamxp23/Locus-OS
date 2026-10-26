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

PASS: 0 FAIL, 9 WARN, 0 INFO  (3.9s)
```

## Verify line
```
features 1 | verified avg 85.0% | old claimed avg 10.0% | integrated+ 1 | proven 0 | overclaims 0 | no-evidence 0
by level: {'INTEGRATED': 1}
guard: PASS {'FAIL': 0, 'WARN': 9, 'INFO': 0}
{"id": "F-0034", "label": "INTEGRATED", "pct": 85, "flags": [], "reasons": ["no recorded proof"], "next": "Run tools/tracker/record_proof.py, then the human adds the printed line to tracker/signoff.yaml."}
```

## Criteria table
| # | Acceptance Criterion | Code | Test | Status |
|---|---|---|---|---|
| 1 | Module implementing Plugin LLM per §9.9 created under sidecar/ or locus-extension/ | `sidecar/plugins/llm_bridge.py:1-270`, `sidecar/providers/plugin_llm.py:1-120`, `locus-extension/src/plugins/llm-bridge.ts:1-125` | `tests/unit/test_plugin_llm.py:1-140` | SATISFIED |
| 2 | Registers as a provider in sidecar/providers/ with modular off-switch locus.plugin_llm.enabled returning 503 | `sidecar/providers/plugin_llm.py:65-120`, `sidecar/service.py:5030-5120` | `tests/unit/test_plugin_llm.py:115-135`, `tests/integration/test_plugin_llm_service.py:50-70` | SATISFIED |
| 3 | Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment | `tests/unit/test_plugin_llm.py:1-140` (8 unit tests), `tests/integration/test_plugin_llm_service.py:1-70` (4 integration tests) | `tests/unit/test_plugin_llm.py` + `tests/integration/test_plugin_llm_service.py` (12 passed) | SATISFIED |

## Test attack result
Inverted the quota threshold check in `sidecar/plugins/llm_bridge.py` (`if self.tokens_used_today + max_tokens > self.token_quota_daily:` changed to `<`).
Re-ran `pytest tests/unit/test_plugin_llm.py::test_plugin_llm_within_quota`.
The test failed immediately with:
`sidecar.plugins.llm_bridge.QuotaExceededError: Plugin excalidraw-skill exceeded daily token limit (0/1000).`
Original code was restored cleanly.

## Findings
None. The implementation cleanly satisfies SPEC §9.9 requirements:
- `PluginLLMBridge` enforces per-plugin daily token quota (`token_quota_daily: 50000`), roll-over on new dates, and isolated auxiliary client invocation.
- `AuxiliaryClientPool` and `DefaultAuxiliaryClient` ensure secondary LLM execution does not collide with the main conversation prompt cache.
- Fail-fast 15s timeout is enforced (`AuxiliaryTimeoutError`).
- Per-plugin daily token usage is recorded in `~/.locus/usage/plugins.json` without creating repository-root pollution.
- `DefaultPluginLLMProvider` and FastAPI endpoints enforce modular off-switches (`locus.plugin_llm.enabled` and `locus.plugins.auxiliary_llm.enabled`) returning HTTP 503.
- `locus-extension` TypeScript contract provides client wrapper `PluginLLMBridgeClient` with abort signal timeout and 503 error handling.

## Not checked
Level 5 proven signoff (`tracker/signoff.yaml`) is human-owned and out of scope for automated sprint completion. Level 4 (INTEGRATED, 85%) is verified and accepted.
