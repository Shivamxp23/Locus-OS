# US-43 Spec Trace: Tool Output Accumulator (§3.10)

| Spec Line | Spec Sentence (Verbatim) | Verdict | Implementation File:Line | Test / Status |
|---|---|---|---|---|
| 2697 | `## Feature §3.10: Tool Output Accumulator` | KEEP-PI / AUGMENT | `sidecar/providers/tool_output_accumulator.py:1` | `tests/unit/test_tool_output_accumulator.py:25` |
| 2698 | `- **Verdict**: 📦 KEEP-PI · **Source**: pi/output-accumulator.ts · **Repo vs .locus**: locus-os (inherited)` | AUGMENT | `sidecar/tool_output_accumulator.py:30`, `packages/coding-agent/src/core/tools/output-accumulator.ts:35`, `locus-extension/src/tool-output-accumulator.ts:35` | `tests/unit/test_tool_output_accumulator.py:80`, `tests/integration/test_tool_output_accumulator_service.py:25` |
| 2699 | `- **Off state**: N/A (core Pi infrastructure)` | AUGMENT | `sidecar/tool_output_accumulator.py:200`, `sidecar/service.py:2080` | `tests/unit/test_tool_output_accumulator.py:150`, `tests/integration/test_tool_output_accumulator_service.py:80` |
| 2700 | `- **Scope**: Built-in truncation. Inherited unchanged.` | AUGMENT | `sidecar/tool_output_accumulator.py:90-210` | `tests/unit/test_tool_output_accumulator.py:25-140` |
| Criteria 1 | `Module implementing Tool Output Accumulator per §3.10: Tool Output Accumulator created under sidecar/ or locus-extension/.` | LOCUS-NEW | `sidecar/tool_output_accumulator.py`, `locus-extension/src/tool-output-accumulator.ts` | `tests/unit/test_tool_output_accumulator.py:25` |
| Criteria 2 | `Registers as a provider in sidecar/providers/ with modular off-switch locus.tool_output_accumulator.enabled returning 503.` | LOCUS-NEW | `sidecar/providers/tool_output_accumulator.py:1`, `sidecar/service.py:2065` | `tests/unit/test_tool_output_accumulator.py:150`, `tests/integration/test_tool_output_accumulator_service.py:80` |
| Criteria 3 | `Unit tests in tests/unit/ assert expected logic, boundary conditions, and error containment.` | LOCUS-NEW | `tests/unit/test_tool_output_accumulator.py` | `tests/unit/test_tool_output_accumulator.py:20-175` |
