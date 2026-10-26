# US-66 Spec Trace — §10.8: Self-Evolving Architect Bot

Feature: F-0120 | Verdict: LOCUS-ORIGINAL DESIGN | Author model: Gemini Flash

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `1. Scan reward signals: read the §10.5 reward model (per-turn reward) + §10.6 Hebbian pattern weights + §10.9 agent-experience outcomes + §25 Life OS metrics (deferral, DCS, action-gap). Aggregate into candidate improvement targets.` | LOCUS-ORIGINAL | sidecar/architect/engine.py:120-145, 175-245 | test_architect_gather_signals_and_propose_improvements, test_service_architect_scan |
| 2 | `2. Classify the target of each candidate patch — this is the crucial fork: Config/prompt/rules (SOUL.md, config.yaml, system-prompt sections, pattern weights, blocklists) -> Locus edits them itself (these are non-code artifacts Locus owns).` | LOCUS-ORIGINAL | sidecar/architect/engine.py:147-160 | test_architect_classify_target_crucial_fork |
| 3 | `Code (an actual bug, a provider needing new logic) -> Locus delegates to a coding harness via §3.7 — it never writes its own code. This is philosophy point 7, applied to self-modification.` | LOCUS-ORIGINAL | sidecar/architect/engine.py:220-245, 255-270 | test_architect_code_delegation_philosophy_pt_7 |
| 4 | `3. Generate the patch as a draft diff, not a live edit: for config, a proposed key-value change; for code, a harness prompt with the failing signal as evidence.` | LOCUS-ORIGINAL | sidecar/architect/engine.py:180-245 | test_architect_gather_signals_and_propose_improvements |
| 5 | `4. Risk-gate the deploy: each candidate carries a risk class. low (config value, reversible) -> apply immediately; medium (SOUL.md/prompt change) -> stage + require approval-gate confirmation (§13.5); high (code, schema, or anything touching the loop itself) -> require approval + a rollback point + a canary (apply to a staging copy first).` | LOCUS-ORIGINAL | sidecar/architect/engine.py:162-173, 272-300 | test_architect_risk_gated_deploy, test_service_architect_candidates_and_apply |
| 6 | `5. Close the loop: record the patch + its effect in the trajectory/experience store (§19.2, §10.9) so the next scan can see whether the change actually improved the reward signal.` | LOCUS-ORIGINAL | sidecar/architect/engine.py:302-315 | test_architect_close_the_loop_history, test_service_architect_history |
| 7 | `Component: locus/core/architect/ -> locus-extension/src/architect/ and sidecar/architect/` | LOCUS-ORIGINAL | locus-extension/src/architect/client.ts:1-110, sidecar/architect/engine.py:1-325 | test_service_architect_scan |
| 8 | `Provider Interface: ArchitectProvider` | LOCUS-ORIGINAL | sidecar/providers/architect.py:25-60 | test_architect_provider_swappable |
| 9 | `Swappable / off state: locus.architect.enabled. Off -> Locus stops proposing self-changes entirely (it remains static, still fully functional). locus.architect.risk_gate (off|approval|canary) tunes how aggressively it deploys.` | LOCUS-ORIGINAL | sidecar/providers/architect.py:65-90, sidecar/service.py:5150-5175 | test_architect_provider_off_switch, test_service_architect_disabled_returns_503 |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/architect/engine.py` — §10.8 ArchitectEngine, ArchitectCandidate, SignalBundle, TargetClass, RiskClass
- `sidecar/architect/__init__.py` — re-exports
- `sidecar/providers/architect.py` — BaseArchitectProvider & DefaultArchitectProvider
- `sidecar/providers/__init__.py` — provider module re-exports
- `locus-extension/src/architect/client.ts` — TypeScript ArchitectClient contract
- `sidecar/service.py` — REST endpoints (`/architect/scan`, `/candidates`, `/apply`, `/history`) with 503 off-switch
- `tests/unit/test_architect.py` — unit tests for rows 1-6, 8, 9
- `tests/integration/test_architect_service.py` — integration tests for rows 1, 5, 6, 7, 9
- `tracker/features.yaml` — updated evidence for F-0120

No file or behaviour outside the spec trace.
