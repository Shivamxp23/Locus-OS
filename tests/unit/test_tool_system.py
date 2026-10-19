"""
Unit tests for Locus Tool System (SPEC §1.3, F-0003, US-22).
Verifies 13 canonical tools, AgentTool contract, 5-step lifecycle, execution modes, and modular off-switches.
"""
from __future__ import annotations

import pytest

from sidecar.providers.tool_system import (
    AgentTool,
    AgentToolResult,
    BeforeToolCallResult,
    ExecutionMode,
)
from sidecar.tool_system import ToolSystemProvider, _create_canonical_tools


def test_tool_system_agent_tool_contract():
    """SPEC §1.3 line 432: "AGENT TOOL INTERFACE: name: string, label: string, description: string, schema: TSchema, executionMode?: 'sequential' | 'parallel'"."""
    tool = AgentTool(
        name="test_tool",
        label="Test Tool",
        description="A test tool",
        schema={"type": "object", "properties": {"val": {"type": "string"}}, "required": ["val"]},
        execution_mode=ExecutionMode.SEQUENTIAL,
    )
    assert tool.name == "test_tool"
    assert tool.label == "Test Tool"
    assert tool.description == "A test tool"
    assert tool.schema["type"] == "object"
    assert tool.execution_mode == ExecutionMode.SEQUENTIAL


def test_tool_system_agent_tool_result_format():
    """SPEC §1.3 line 441: "AGENT TOOL RESULT: content: (TextContent | ImageContent)[], details: T, terminate?: boolean"."""
    result = AgentToolResult(
        content=[{"type": "text", "text": "result output"}],
        details={"key": "value"},
        terminate=False,
        is_error=False,
    )
    d = result.to_dict()
    assert d["content"] == [{"type": "text", "text": "result output"}]
    assert d["details"] == {"key": "value"}
    assert d["terminate"] is False
    assert d["isError"] is False


def test_tool_system_13_canonical_tools_registered():
    """SPEC §1.3 line 464: "Locus registers ~8 custom tools (locus_checkin, locus_memory, locus_goals, locus_life, locus_vault, locus_brain, locus_research, locus_delegate_code) via Pi's registerTool() API."."""
    tools = _create_canonical_tools()
    expected_13 = [
        "locus_checkin",
        "locus_life",
        "locus_goals",
        "locus_memory",
        "locus_vault",
        "locus_brain",
        "locus_research",
        "locus_delegate_code",
        "locus_doctor",
        "locus_pageindex",
        "locus_diagram",
        "locus_capture",
        "locus_schedule",
    ]
    assert len(tools) == 13
    for name in expected_13:
        assert name in tools, f"Missing canonical tool {name}"
        tool = tools[name]
        assert tool.name == name
        assert tool.label
        assert tool.description
        assert "type" in tool.schema


def test_tool_system_lifecycle_stages():
    """SPEC §1.3 line 446: "TOOL LIFECYCLE: 1. prepareToolCallArguments, 2. validateToolArguments, 3. config.beforeToolCall, 4. tool.execute, 5. config.afterToolCall"."""
    provider = ToolSystemProvider(config={"locus.tool_system_13_canonical_tools.enabled": True})

    custom_tool = AgentTool(
        name="custom_math",
        label="Math",
        description="Double a number",
        schema={"type": "object", "properties": {"x": {"type": "number"}}, "required": ["x"]},
        prepare_arguments=lambda raw: {"x": raw.get("x", 0) * 2},
        execute_handler=lambda tool_call_id, params, signal: AgentToolResult(
            content=[{"type": "text", "text": f"Computed: {params['x']}"}],
            details={"computed": params["x"]},
        ),
    )
    provider.register_tool(custom_tool)

    res = provider.execute_tool("custom_math", "call-1", {"x": 5})
    assert not res.is_error
    assert res.details["computed"] == 10
    assert res.content[0]["text"] == "Computed: 10"


def test_tool_system_validation_error():
    """SPEC §1.3 line 448: "2. validateToolArguments(tool, preparedToolCall) // schema validation"."""
    provider = ToolSystemProvider(config={"locus.tool_system_13_canonical_tools.enabled": True})
    # locus_checkin requires 'energy' and 'mood'
    res = provider.execute_tool("locus_checkin", "call-2", {"energy": 7})
    assert res.is_error
    assert "Schema validation error" in res.content[0]["text"]
    assert "mood" in res.content[0]["text"]


def test_tool_system_before_tool_call_blocking():
    """SPEC §1.3 line 449: "3. config.beforeToolCall({ assistantMessage, toolCall, args, context }) -> { block: true, reason: '...' } prevents execution"."""
    provider = ToolSystemProvider(config={"locus.tool_system_13_canonical_tools.enabled": True})

    def security_guard(ctx):
        if ctx.get("tool") == "locus_delegate_code":
            return BeforeToolCallResult(block=True, reason="Delegate code blocked by security policy")
        return BeforeToolCallResult(block=False)

    provider.add_before_hook(security_guard)

    res = provider.execute_tool("locus_delegate_code", "call-sec", {"harness": "pi", "prompt": "rm -rf"})
    assert res.is_error
    assert res.details.get("blocked") is True
    assert "Delegate code blocked by security policy" in res.content[0]["text"]


def test_tool_system_after_tool_call_override():
    """SPEC §1.3 line 453: "5. config.afterToolCall({ assistantMessage, toolCall, args, result, isError, context }) -> can override content, details, isError, terminate"."""
    provider = ToolSystemProvider(config={"locus.tool_system_13_canonical_tools.enabled": True})

    def audit_override(ctx):
        return {
            "content": [{"type": "text", "text": "Overridden by audit hook"}],
            "terminate": True,
        }

    provider.add_after_hook(audit_override)

    res = provider.execute_tool("locus_doctor", "call-audit", {})
    assert res.content[0]["text"] == "Overridden by audit hook"
    assert res.terminate is True


def test_tool_system_execution_modes():
    """SPEC §1.3 line 456: "TOOL EXECUTION MODES: 'parallel': prepare sequentially -> execute concurrently; 'sequential': prepare, execute, finalize one at a time"."""
    tools = _create_canonical_tools()
    # Memory, brain, research, doctor, pageindex, diagram should allow parallel mode
    assert tools["locus_memory"].execution_mode == ExecutionMode.PARALLEL
    assert tools["locus_brain"].execution_mode == ExecutionMode.PARALLEL
    assert tools["locus_research"].execution_mode == ExecutionMode.PARALLEL
    # Vault, checkin, life, goals, delegate_code, capture, schedule are sequential
    assert tools["locus_vault"].execution_mode == ExecutionMode.SEQUENTIAL
    assert tools["locus_checkin"].execution_mode == ExecutionMode.SEQUENTIAL
    assert tools["locus_delegate_code"].execution_mode == ExecutionMode.SEQUENTIAL


def test_tool_system_individual_tool_toggle():
    """SPEC §1.3 line 466: "Individual Locus tools can be disabled via config (locus.tools.<name>.enabled: false). Off -> that tool is unavailable to the LLM"."""
    cfg = {
        "locus.tool_system_13_canonical_tools.enabled": True,
        "locus.tools.locus_doctor.enabled": False,
    }
    provider = ToolSystemProvider(config=cfg)
    assert not provider.is_tool_enabled("locus_doctor")
    assert provider.is_tool_enabled("locus_vault")

    tool_names = [t.name for t in provider.list_tools()]
    assert "locus_doctor" not in tool_names
    assert "locus_vault" in tool_names

    res = provider.execute_tool("locus_doctor", "call-off", {})
    assert res.is_error
    assert "disabled" in res.content[0]["text"] or "not registered" in res.content[0]["text"]
