# US-44 Spec Trace: Tool Timeout / Budget (§3.11)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 2702 | `## Feature §3.11: Tool Timeout / Budget` | LOCUS-NEW / AUGMENT | `sidecar/providers/tool_timeout_budget.py:1` | `tests/unit/test_tool_timeout_budget.py:25` |
| 2703 | `- **Verdict**: 🆕 LOCUS-NEW · **Source**: OpenHuman tool_timeout · **Repo vs .locus**: locus-os` | AUGMENT | `sidecar/tool_timeout_budget.py:30`, `locus-extension/src/tool-timeout-budget.ts:35` | `tests/unit/test_tool_timeout_budget.py:35`, `tests/integration/test_tool_timeout_budget_service.py:25` |
| 2704 | `- **Swappable / off state**: locus.tools.timeout.enabled. Off → no per-tool timeout enforcement.` | AUGMENT | `sidecar/tool_timeout_budget.py:45`, `sidecar/service.py:2240` | `tests/unit/test_tool_timeout_budget.py:140`, `tests/integration/test_tool_timeout_budget_service.py:90` |
| Criteria 1 | `Module implementing Tool Timeout / Budget per §3.11: Tool Timeout / Budget created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/tool_timeout_budget.py`, `locus-extension/src/tool-timeout-budget.ts` | `tests/unit/test_tool_timeout_budget.py:25` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.tool_timeout_budget.enabled returning 503.` | LOCUS-NEW | `sidecar/providers/tool_timeout_budget.py:1`, `sidecar/service.py:2226` | `tests/unit/test_tool_timeout_budget.py:140`, `tests/integration/test_tool_timeout_budget_service.py:90` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_tool_timeout_budget.py` | `tests/unit/test_tool_timeout_budget.py:20-160` |
