# US-41 Spec Trace: Tool Call Validation (§3.8)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 2687 | `## Feature §3.8: Tool Call Validation` | AUGMENT | `sidecar/providers/tool_call_validation.py:1` | `tests/unit/test_tool_call_validation.py:25` |
| 2688 | `- **Verdict**: 🔄 AUGMENT · **Source**: Pi tool-definition-wrapper.ts + Hermes tool_guardrails.py · **Repo vs .locus**: locus-os` | AUGMENT | `sidecar/tool_call_validation.py:35`, `locus-extension/src/tool-call-validation.ts:15` | `tests/unit/test_tool_call_validation.py:70`, `tests/integration/test_tool_call_validation_service.py:25` |
| 2689 | `- **Swappable / off state**: Always on (safety critical)` | AUGMENT | `sidecar/tool_call_validation.py:80`, `sidecar/service.py:1890` | `tests/unit/test_tool_call_validation.py:175`, `tests/integration/test_tool_call_validation_service.py:120` |
| 2690 | `- **Scope**: Keep Pi's wrapper. Steal Hermes' guardrails.` | AUGMENT | `sidecar/tool_call_validation.py:90-250` | `tests/unit/test_tool_call_validation.py:35-150` |
| Criteria 1 | `Module implementing Tool Call Validation per §3.8: Tool Call Validation created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/tool_call_validation.py`, `locus-extension/src/tool-call-validation.ts` | `tests/unit/test_tool_call_validation.py:25` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.tool_call_validation.enabled returning 503.` | LOCUS-NEW | `sidecar/providers/tool_call_validation.py:1`, `sidecar/service.py:1885` | `tests/unit/test_tool_call_validation.py:175`, `tests/integration/test_tool_call_validation_service.py:120` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_tool_call_validation.py` | `tests/unit/test_tool_call_validation.py:20-180` |
