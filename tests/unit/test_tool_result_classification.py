"""
Unit tests for Tool Result Classification (SPEC §3.9 / F-0101).
Asserts classification into SUCCESS, FAILURE, PARTIAL, side-effect detection,
file mutation landing verification, and modular provider interchangeability.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional

import pytest

from sidecar.providers.tool_result_classification import (
    BaseToolResultClassificationProvider,
    ResultClassificationType,
    ToolResultClassification,
    ToolResultClassificationConfig,
)
from sidecar.registry import ProviderRegistry
from sidecar.tool_result_classification import (
    FILE_MUTATING_TOOL_NAMES,
    NO_EFFECT_TOOL_NAMES,
    ToolResultClassificationProvider,
)


def test_classify_result_clean_success():
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    provider = ToolResultClassificationProvider()

    # Plain clean string
    res = provider.classify_result("read_file", "File contents here")
    assert res.status == ResultClassificationType.SUCCESS
    assert res.is_success is True
    assert res.is_failure is False
    assert res.is_partial is False
    assert res.has_side_effect is False
    assert res.file_mutation_landed is False

    # Clean JSON dict
    res_json = provider.classify_result(
        "read_file",
        {"status": "ok", "lines": 42},
    )
    assert res_json.status == ResultClassificationType.SUCCESS
    assert res_json.is_success is True


def test_classify_result_explicit_error_failure():
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    provider = ToolResultClassificationProvider()
    res = provider.classify_result(
        "bash",
        "Some partial output",
        error="Command timed out after 30 seconds",
    )
    assert res.status == ResultClassificationType.FAILURE
    assert res.is_failure is True
    assert res.is_success is False
    assert res.is_partial is False
    assert res.error_message == "Command timed out after 30 seconds"
    assert res.has_side_effect is True


def test_classify_result_non_zero_exit_code_failure():
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    provider = ToolResultClassificationProvider()
    res = provider.classify_result(
        "terminal",
        "rm: cannot remove 'missing.txt': No such file or directory",
        exit_code=1,
    )
    assert res.status == ResultClassificationType.FAILURE
    assert res.is_failure is True
    assert res.details.get("exit_code") == 1


def test_classify_result_string_traceback_failure():
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    provider = ToolResultClassificationProvider()
    tb_output = (
        "Traceback (most recent call last):\n"
        "  File \"script.py\", line 4, in <module>\n"
        "ZeroDivisionError: division by zero"
    )
    res = provider.classify_result("execute_code", tb_output)
    assert res.status == ResultClassificationType.FAILURE
    assert res.is_failure is True


def test_classify_result_json_error_failure():
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    provider = ToolResultClassificationProvider()
    res = provider.classify_result(
        "search_files",
        json.dumps({"error": "Directory does not exist", "status": "error"}),
    )
    assert res.status == ResultClassificationType.FAILURE
    assert res.is_failure is True
    assert "Directory does not exist" in (res.error_message or "")


def test_classify_result_partial_progress_with_errors():
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    provider = ToolResultClassificationProvider()
    payload = {
        "items_processed": 5,
        "error": "Item 6 could not be reached",
        "success_count": 5,
        "failure_count": 1,
    }
    res = provider.classify_result("batch_sync", payload)
    assert res.status == ResultClassificationType.PARTIAL
    assert res.is_partial is True
    assert res.is_success is False
    assert res.is_failure is False


def test_classify_result_warnings_partial():
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    provider = ToolResultClassificationProvider()
    warning_output = "Compiled successfully.\nWarning: unused variable 'temp' at line 12."
    res = provider.classify_result("build", warning_output)
    assert res.status == ResultClassificationType.PARTIAL
    assert res.is_partial is True


def test_write_file_with_nested_lint_error_counts_as_landed():
    """SPEC §3.9 line 2693: "Source: Hermes tool_result_classification.py" """
    provider = ToolResultClassificationProvider()
    raw = json.dumps({
        "bytes_written": 12,
        "lint": {"status": "error", "output": "SyntaxError: invalid syntax"},
    })

    assert provider.file_mutation_result_landed("write_file", raw) is True

    # When classified, a landed file mutation with nested lint errors yields PARTIAL
    res = provider.classify_result("write_file", raw)
    assert res.status == ResultClassificationType.PARTIAL
    assert res.file_mutation_landed is True
    assert res.has_side_effect is True


def test_file_mutation_result_landed_patch():
    """SPEC §3.9 line 2693: "Source: Hermes tool_result_classification.py" """
    provider = ToolResultClassificationProvider()

    clean_patch = json.dumps({"success": True, "applied": True})
    assert provider.file_mutation_result_landed("patch", clean_patch) is True

    failed_patch = json.dumps({"error": "Hunk #1 failed", "success": False})
    assert provider.file_mutation_result_landed("patch", failed_patch) is False

    res = provider.classify_result("patch", clean_patch)
    assert res.status == ResultClassificationType.SUCCESS
    assert res.file_mutation_landed is True


def test_side_effect_classification_keeps_session_mutations():
    """SPEC §3.9 line 2693: "Source: Hermes tool_result_classification.py" """
    provider = ToolResultClassificationProvider()

    # Mutating / stateful tools have side effects
    assert provider.tool_may_have_side_effect("todo") is True
    assert provider.tool_may_have_side_effect("memory") is True
    assert provider.tool_may_have_side_effect("write_file") is True
    assert provider.tool_may_have_side_effect("mcp_unknown") is True
    assert provider.tool_may_have_side_effect("terminal") is True

    # Read-only tools have no side effects
    assert provider.tool_may_have_side_effect("read_file") is False
    assert provider.tool_may_have_side_effect("web_search") is False
    assert provider.tool_may_have_side_effect("browser_snapshot") is False
    assert provider.tool_may_have_side_effect("git_diff") is False


def test_modular_provider_swap():
    """SPEC §3.9 line 2694: "Swappable / off state: locus.tools.result_classification.enabled. Off → results not classified." """
    registry = ProviderRegistry()

    class CustomClassificationProvider(BaseToolResultClassificationProvider):
        def classify_result(
            self,
            tool_name: str,
            result: Any,
            error: Optional[str] = None,
            exit_code: Optional[int] = None,
            params: Optional[Mapping[str, Any]] = None,
        ) -> ToolResultClassification:
            return ToolResultClassification(
                status=ResultClassificationType.SUCCESS,
                tool_name=tool_name,
                is_success=True,
                is_failure=False,
                is_partial=False,
                has_side_effect=False,
                file_mutation_landed=False,
                details={"custom": True},
            )

        def tool_may_have_side_effect(self, tool_name: str) -> bool:
            return False

        def file_mutation_result_landed(self, tool_name: str, result: Any) -> bool:
            return False

        def get_config(self) -> ToolResultClassificationConfig:
            return ToolResultClassificationConfig()

        def health_check(self) -> Dict[str, Any]:
            return {"status": "custom"}

    registry.register("tool_result_classification", "custom", CustomClassificationProvider)
    active_cls = registry.get_active_provider("tool_result_classification", default_name="custom")
    assert active_cls is CustomClassificationProvider

    inst = active_cls()
    classified = inst.classify_result("any_tool", "any_payload")
    assert classified.details.get("custom") is True
