"""sidecar/tools/classifier.py - Tool Result Classification Engine.

Implements Spec §3.9:
- Classifies tool execution outcomes into:
  SUCCESS, RETRIABLE_ERROR, FATAL_ERROR, TIMEOUT, PARTIAL_SUCCESS.
- Distinguishes transient network/resource failures from syntax/permission errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ToolResultClass(str, Enum):
    SUCCESS = "success"
    RETRIABLE_ERROR = "retriable_error"
    FATAL_ERROR = "fatal_error"
    TIMEOUT = "timeout"
    PARTIAL = "partial"


@dataclass
class ClassifiedResult:
    classification: ToolResultClass
    is_success: bool
    should_retry: bool
    diagnostics: str
    cleaned_output: Any


class ToolResultClassifier:
    """Classifies raw tool execution output into deterministic outcome categories."""

    RETRIABLE_ERRORS = [
        "rate limit", "timeout", "timed out", "econnreset", "econnrefused",
        "temporary failure", "429", "503", "504", "try again", "resource locked"
    ]

    FATAL_ERRORS = [
        "permission denied", "not found", "no such file", "command not found",
        "invalid syntax", "unauthorized", "401", "403", "cannot find module"
    ]

    def classify(
        self,
        tool_name: str,
        output: Any,
        error: Optional[Exception | str] = None,
        duration_ms: Optional[float] = None,
    ) -> ClassifiedResult:
        if error is not None:
            err_str = str(error).lower()
            if any(term in err_str for term in ["timeout", "timed out"]):
                return ClassifiedResult(
                    classification=ToolResultClass.TIMEOUT,
                    is_success=False,
                    should_retry=True,
                    diagnostics=f"Tool '{tool_name}' timed out: {error}",
                    cleaned_output=None,
                )
            if any(term in err_str for term in self.RETRIABLE_ERRORS):
                return ClassifiedResult(
                    classification=ToolResultClass.RETRIABLE_ERROR,
                    is_success=False,
                    should_retry=True,
                    diagnostics=f"Tool '{tool_name}' transient error: {error}",
                    cleaned_output=None,
                )
            return ClassifiedResult(
                classification=ToolResultClass.FATAL_ERROR,
                is_success=False,
                should_retry=False,
                diagnostics=f"Tool '{tool_name}' fatal failure: {error}",
                cleaned_output=None,
            )

        # Check output structure for error hints
        if isinstance(output, dict) and output.get("status") == "error":
            msg = str(output.get("message", "")).lower()
            if any(term in msg for term in self.RETRIABLE_ERRORS):
                return ClassifiedResult(
                    classification=ToolResultClass.RETRIABLE_ERROR,
                    is_success=False,
                    should_retry=True,
                    diagnostics=f"Tool '{tool_name}' reported retriable error: {output.get('message')}",
                    cleaned_output=output,
                )
            return ClassifiedResult(
                classification=ToolResultClass.FATAL_ERROR,
                is_success=False,
                should_retry=False,
                diagnostics=f"Tool '{tool_name}' failed: {output.get('message')}",
                cleaned_output=output,
            )

        return ClassifiedResult(
            classification=ToolResultClass.SUCCESS,
            is_success=True,
            should_retry=False,
            diagnostics=f"Tool '{tool_name}' executed successfully.",
            cleaned_output=output,
        )
