"""
Unit tests for Tool Call Validation and loop guardrails (SPEC §3.8 / F-0100).
Asserts parameter schema validation, loop detection, stall guard duplicate stubbing,
failure streak thresholds, and modular provider swapping.
"""
from typing import Any, Dict, List, Mapping, Optional
import pytest

from sidecar.providers.tool_call_validation import (
    BaseToolCallValidationProvider,
    ToolCallGuardrailConfig,
    ToolCategory,
    ValidationAction,
    ValidationDecision,
    ValidationObservation,
)
from sidecar.tool_call_validation import ToolCallValidationProvider
from sidecar.registry import ProviderRegistry


def test_schema_validation_valid_parameters():
    """SPEC §3.8 line 2690: "Keep Pi's wrapper. Steal Hermes' guardrails."."""
    provider = ToolCallValidationProvider()
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
            "enabled": {"type": "boolean"},
        },
        "required": ["query"],
    }
    errors = provider.validate_schema("test_tool", {"query": "search query", "limit": 10, "enabled": True}, schema)
    assert errors == []


def test_schema_validation_missing_required():
    """SPEC §3.8 line 2690: "Keep Pi's wrapper. Steal Hermes' guardrails."."""
    provider = ToolCallValidationProvider()
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }
    errors = provider.validate_schema("write_file", {"path": "test.txt"}, schema)
    assert len(errors) == 1
    assert "Missing required parameter: 'content'" in errors[0]


def test_schema_validation_type_mismatch():
    """SPEC §3.8 line 2690: "Keep Pi's wrapper. Steal Hermes' guardrails."."""
    provider = ToolCallValidationProvider()
    schema = {
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "action": {"type": "string", "enum": ["start", "stop"]},
        },
        "required": ["count", "action"],
    }
    # Pass boolean for integer
    err1 = provider.validate_schema("test_tool", {"count": True, "action": "start"}, schema)
    assert any("expected integer, got boolean" in e for e in err1)

    # Pass invalid enum
    err2 = provider.validate_schema("test_tool", {"count": 5, "action": "restart"}, schema)
    assert any("not in allowed enum" in e for e in err2)


def test_repeated_exact_failure_warning_and_block():
    """SPEC §3.8 line 2688: "Verdict: AUGMENT · Source: Pi tool-definition-wrapper.ts + Hermes tool_guardrails.py"."""
    config = ToolCallGuardrailConfig(
        exact_failure_warn_after=2,
        exact_failure_block_after=4,
    )
    provider = ToolCallValidationProvider(config=config)
    tool_name = "terminal"
    params = {"cmd": "invalid_command_that_fails"}

    # Run 1: Allow
    d1 = provider.before_call(tool_name, params)
    assert d1.action == ValidationAction.ALLOW
    provider.observe_call(tool_name, params, result="Error: command not found", failed=True)

    # Run 2: Allow
    d2 = provider.before_call(tool_name, params)
    assert d2.action == ValidationAction.ALLOW
    provider.observe_call(tool_name, params, result="Error: command not found", failed=True)

    # Run 3: Warn (streak == 2)
    d3 = provider.before_call(tool_name, params)
    assert d3.action == ValidationAction.WARN
    assert d3.code == "repeated_exact_failure_warning"
    assert d3.allows_execution is True
    provider.observe_call(tool_name, params, result="Error: command not found", failed=True)

    # Run 4: Warn (streak == 3)
    d4 = provider.before_call(tool_name, params)
    assert d4.action == ValidationAction.WARN
    provider.observe_call(tool_name, params, result="Error: command not found", failed=True)

    # Run 5: Block (streak == 4 >= exact_failure_block_after)
    d5 = provider.before_call(tool_name, params)
    assert d5.action == ValidationAction.BLOCK
    assert d5.code == "repeated_exact_failure_block"
    assert d5.allows_execution is False
    assert d5.should_halt is True


def test_same_tool_failure_halt():
    """SPEC §3.8 line 2688: "Verdict: AUGMENT · Source: Pi tool-definition-wrapper.ts + Hermes tool_guardrails.py"."""
    config = ToolCallGuardrailConfig(
        same_tool_failure_warn_after=2,
        same_tool_failure_halt_after=4,
    )
    provider = ToolCallValidationProvider(config=config)
    tool_name = "terminal"

    for i in range(4):
        params = {"cmd": f"run_failing_script_{i}.py"}
        provider.before_call(tool_name, params)
        provider.observe_call(tool_name, params, result="Error: script crashed", failed=True)

    # 5th attempt across any args should halt
    decision = provider.before_call(tool_name, {"cmd": "another_one.py"})
    assert decision.action == ValidationAction.HALT
    assert decision.code == "same_tool_failure_halt"
    assert decision.should_halt is True


def test_idempotent_stall_guard_notice_and_stub():
    """SPEC §3.8 line 2690: "Keep Pi's wrapper. Steal Hermes' guardrails."."""
    config = ToolCallGuardrailConfig(identical_call_threshold=3)
    provider = ToolCallValidationProvider(config=config)
    tool_name = "read_file"
    params = {"path": "src/index.ts"}
    large_result = "A" * 600

    # 1st call
    obs1 = provider.observe_call(tool_name, params, result=large_result, failed=False)
    assert obs1.is_duplicate is False
    assert obs1.notice is None

    # 2nd call
    obs2 = provider.observe_call(tool_name, params, result=large_result, failed=False)
    assert obs2.is_duplicate is False

    # 3rd identical call: stall guard fires!
    obs3 = provider.observe_call(tool_name, params, result=large_result, failed=False)
    assert obs3.is_duplicate is True
    assert obs3.notice is not None
    assert "called 3 times with identical arguments" in obs3.notice
    assert obs3.stub is not None
    assert "Duplicate identical output" in obs3.stub


def test_cycle_detection_loop():
    """SPEC §3.8 line 2690: "Keep Pi's wrapper. Steal Hermes' guardrails."."""
    config = ToolCallGuardrailConfig(max_cycle_period=4)
    provider = ToolCallValidationProvider(config=config)

    # Simulate alternating cycle: tool_a -> tool_b -> tool_a -> tool_b
    provider.observe_call("read_file", {"path": "a.txt"}, result="content a", failed=False)
    provider.observe_call("read_file", {"path": "b.txt"}, result="content b", failed=False)
    provider.observe_call("read_file", {"path": "a.txt"}, result="content a", failed=False)
    provider.observe_call("read_file", {"path": "b.txt"}, result="content b", failed=False)

    # Next attempt of tool_a should detect cycle
    decision = provider.before_call("read_file", {"path": "a.txt"})
    assert decision.action == ValidationAction.WARN
    assert decision.code == "cycle_detected_warning"


def test_per_turn_caps_web_search_and_subagents():
    """SPEC §3.8 line 2688: "Verdict: AUGMENT · Source: Pi tool-definition-wrapper.ts + Hermes tool_guardrails.py"."""
    config = ToolCallGuardrailConfig(max_web_searches_per_turn=2, max_subagents_per_turn=1)
    provider = ToolCallValidationProvider(config=config)

    # 2 web searches allowed
    provider.observe_call("web_search", {"q": "query 1"}, result="ok", failed=False)
    provider.observe_call("web_search", {"q": "query 2"}, result="ok", failed=False)

    # 3rd search blocked
    d = provider.before_call("web_search", {"q": "query 3"})
    assert d.action == ValidationAction.BLOCK
    assert d.code == "cap_exceeded_web_search"

    # Subagent cap
    provider.observe_call("delegate_task", {"task": "sub 1"}, result="ok", failed=False)
    d_sub = provider.before_call("delegate_task", {"task": "sub 2"})
    assert d_sub.action == ValidationAction.BLOCK
    assert d_sub.code == "cap_exceeded_subagent"


def test_reset_for_turn_clears_counters():
    """SPEC §3.8 line 2689: "Swappable / off state: Always on (safety critical)"."""
    config = ToolCallGuardrailConfig(exact_failure_block_after=2)
    provider = ToolCallValidationProvider(config=config)
    provider.observe_call("terminal", {"cmd": "fail"}, result="Error", failed=True)
    provider.observe_call("terminal", {"cmd": "fail"}, result="Error", failed=True)

    d_before = provider.before_call("terminal", {"cmd": "fail"})
    assert d_before.action == ValidationAction.BLOCK

    # Reset
    provider.reset_for_turn()
    d_after = provider.before_call("terminal", {"cmd": "fail"})
    assert d_after.action == ValidationAction.ALLOW


def test_mutating_success_resets_exact_failures():
    """SPEC §3.8 line 2690: "Keep Pi's wrapper. Steal Hermes' guardrails."."""
    config = ToolCallGuardrailConfig(exact_failure_warn_after=2)
    provider = ToolCallValidationProvider(config=config)
    provider.observe_call("read_file", {"path": "err.txt"}, result="Error", failed=True)
    provider.observe_call("read_file", {"path": "err.txt"}, result="Error", failed=True)

    assert provider.before_call("read_file", {"path": "err.txt"}).action == ValidationAction.WARN

    # Mutating tool succeeds (e.g. edit / write_file fixed the issue)
    provider.observe_call("write_file", {"path": "err.txt", "content": "fixed"}, result="Success", failed=False)

    # Exact failure streak cleared for new experiment
    assert provider.before_call("read_file", {"path": "err.txt"}).action == ValidationAction.ALLOW


def test_modular_provider_swap():
    """SPEC §3.8 line 2689: "Swappable / off state: Always on (safety critical)"."""
    class CustomValidationProvider(BaseToolCallValidationProvider):
        def validate_schema(self, tool_name, params, schema=None):
            return []

        def before_call(self, tool_name, params, schema=None):
            return ValidationDecision(
                action=ValidationAction.WARN,
                code="custom_warn",
                message="custom implementation",
                tool_name=tool_name,
            )

        def observe_call(self, tool_name, params, result=None, failed=None):
            return ValidationObservation(tool_name=tool_name, notice="custom notice")

        def reset_for_turn(self):
            pass

        def classify_tool(self, tool_name):
            return ToolCategory.UNKNOWN

        def get_config(self):
            return ToolCallGuardrailConfig()

        def health_check(self):
            return {"status": "custom"}

    registry = ProviderRegistry()
    registry.register("tool_call_validation", "custom", CustomValidationProvider)
    active_cls = registry.get_active_provider("tool_call_validation", default_name="custom")
    assert active_cls is CustomValidationProvider
    inst = active_cls()
    dec = inst.before_call("any_tool", {})
    assert dec.code == "custom_warn"
