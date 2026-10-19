# US-22 Spec Trace (§1.3: Tool System)

Feature: `F-0003` (Tool System - 13 Canonical Tools)
Source: `packages/coding-agent/src/core/tools/index.ts`, `packages/agent/src/types.ts`
Canonical Targets: `locus-extension/src/tools/index.ts`, `sidecar/providers/tool_system.py`, `sidecar/tool_system.py`

| Spec Line | Exact Spec Sentence / Pseudocode | Verdict | Target File & Mechanism | Test Name |
| :--- | :--- | :--- | :--- | :--- |
| Line 432 | `AGENT TOOL INTERFACE: name, label, description, schema, executionMode, prepareArguments, execute` | KEEP-PI | `locus-extension/src/tools/index.ts` and `sidecar/providers/tool_system.py` define AgentTool contracts | `test_tool_system_agent_tool_contract` |
| Line 441 | `AGENT TOOL RESULT: content: (TextContent \| ImageContent)[], details: T, terminate?: boolean` | KEEP-PI | `sidecar/providers/tool_system.py:AgentToolResult` formats LLM content and execution details | `test_tool_system_agent_tool_result_format` |
| Line 446 | `TOOL LIFECYCLE: 1. prepareToolCallArguments, 2. validateToolArguments, 3. config.beforeToolCall, 4. tool.execute, 5. config.afterToolCall` | AUGMENT | `sidecar/tool_system.py:execute_tool_lifecycle` manages preparation, validation, hooks, and execution | `test_tool_system_lifecycle_stages` |
| Line 449 | `config.beforeToolCall({ assistantMessage, toolCall, args, context }) -> { block: true, reason: "..." } prevents execution` | AUGMENT | `sidecar/tool_system.py:execute_tool_lifecycle` handles beforeToolCall block decision | `test_tool_system_before_tool_call_blocking` |
| Line 453 | `config.afterToolCall({ assistantMessage, toolCall, args, result, isError, context }) -> can override content, details, isError, terminate` | AUGMENT | `sidecar/tool_system.py:execute_tool_lifecycle` applies post-execution overrides | `test_tool_system_after_tool_call_override` |
| Line 456 | `TOOL EXECUTION MODES: "parallel": prepare sequentially -> execute concurrently; "sequential": prepare, execute, finalize one at a time` | KEEP-PI | `sidecar/tool_system.py:ToolExecutionManager` supports parallel and sequential modes | `test_tool_system_execution_modes` |
| Line 464 | `Locus registers ~8 custom tools (...) via Pi's registerTool() API. Each implements the AgentTool interface.` | LOCUS-NEW | `locus-extension/src/tools/index.ts` exports 13 canonical tools: locus_checkin, locus_life, locus_goals, locus_memory, locus_vault, locus_brain, locus_research, locus_delegate_code, locus_doctor, locus_pageindex, locus_diagram, locus_capture, locus_schedule | `test_tool_system_13_canonical_tools_registered` |
| Line 466 | `Individual Locus tools can be disabled via config (locus.tools.<name>.enabled: false). Off -> that tool is unavailable to the LLM` | AUGMENT | `sidecar/tool_system.py:ToolRegistry` filters out disabled tools from available tool listing | `test_tool_system_individual_tool_toggle` |
| Accept criteria | `Registers as a provider in sidecar/providers/ with modular off-switch locus.tool_system_13_canonical_tools.enabled returning 503.` | AUGMENT | `sidecar/service.py` returns 503 on `/tools/*` when `locus.tool_system_13_canonical_tools.enabled` is false | `test_tool_system_modular_off_switch_503` |
