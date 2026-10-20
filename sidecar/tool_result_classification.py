"""
Concrete implementation of Tool Result Classification (SPEC §3.9 / F-0101).
Classifies results as SUCCESS, FAILURE, or PARTIAL, detects landed file mutations,
and identifies whether tools may produce side-effects.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Mapping, Optional

from sidecar.providers.tool_result_classification import (
    BaseToolResultClassificationProvider,
    ResultClassificationType,
    ToolResultClassification,
    ToolResultClassificationConfig,
)

logger = logging.getLogger(__name__)

# Tools whose executions mutate files on the local filesystem
FILE_MUTATING_TOOL_NAMES: frozenset[str] = frozenset({
    "write_file",
    "write",
    "patch",
    "edit",
})

# Tools whose interrupted or completed execution is safe from side effects
NO_EFFECT_TOOL_NAMES: frozenset[str] = frozenset({
    "read_file",
    "read",
    "search_files",
    "session_search",
    "skill_view",
    "skills_list",
    "web_extract",
    "web_search",
    "vision_analyze",
    "browser_snapshot",
    "browser_get_images",
    "browser_console",
    "read_terminal",
    "find_files",
    "grep",
    "ls",
    "git_status",
    "git_diff",
    "git_log",
    "locus_memory",
})

# Regular expressions indicating clear failure in string output
_ERROR_PATTERNS = [
    re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE),
    re.compile(r"^(?:Error|Fatal|Exception|SyntaxError|TypeError|ValueError|KeyError|IndexError):", re.IGNORECASE | re.MULTILINE),
    re.compile(r"command not found", re.IGNORECASE),
    re.compile(r"Permission denied", re.IGNORECASE),
    re.compile(r"fatal: (?:not a git repository|destination path .+ already exists)", re.IGNORECASE),
]

# Patterns indicating warnings or partial outcomes
_WARNING_PATTERNS = [
    re.compile(r"warning:", re.IGNORECASE),
    re.compile(r"partial(?:ly)? (?:completed|succeeded|failed)", re.IGNORECASE),
    re.compile(r"skipped \d+ items?", re.IGNORECASE),
]


class ToolResultClassificationProvider(BaseToolResultClassificationProvider):
    """Default provider for Tool Result Classification."""

    def __init__(self, name: str = "tool_result_classification_default") -> None:
        super().__init__(name=name)
        self._config = ToolResultClassificationConfig()

    def get_config(self) -> ToolResultClassificationConfig:
        return self._config

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "provider": self.__class__.__name__,
            "name": self.name,
            "config": self._config.to_dict(),
        }

    def tool_may_have_side_effect(self, tool_name: str) -> bool:
        """Return True when tool may mutate external or session state."""
        return tool_name not in NO_EFFECT_TOOL_NAMES

    def file_mutation_result_landed(self, tool_name: str, result: Any) -> bool:
        """
        Return True when a file mutation result proves the write landed.
        Nested lint or syntax warnings do NOT invalidate landed file writes.
        """
        if tool_name not in FILE_MUTATING_TOOL_NAMES:
            return False

        data: Optional[Dict[str, Any]] = None
        if isinstance(result, dict):
            data = result
        elif isinstance(result, str):
            try:
                parsed = json.loads(result.strip())
                if isinstance(parsed, dict):
                    data = parsed
            except Exception:
                return False

        if not data or data.get("error"):
            return False

        if tool_name in ("write_file", "write"):
            # bytes_written or success or written flag
            return "bytes_written" in data or data.get("success") is True or data.get("written") is True
        if tool_name in ("patch", "edit"):
            return data.get("success") is True or data.get("applied") is True or "patched_files" in data
        return False

    def classify_result(
        self,
        tool_name: str,
        result: Any,
        error: Optional[str] = None,
        exit_code: Optional[int] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> ToolResultClassification:
        """
        Classify tool result into SUCCESS, FAILURE, or PARTIAL.
        Evaluates side effects, file mutations, exit codes, and structured payload indicators.
        """
        has_side_effect = self.tool_may_have_side_effect(tool_name)
        file_landed = self.file_mutation_result_landed(tool_name, result)
        details: Dict[str, Any] = {}

        if exit_code is not None:
            details["exit_code"] = exit_code

        # 1. Parse structured result if available
        parsed_dict: Optional[Dict[str, Any]] = None
        if isinstance(result, dict):
            parsed_dict = result
        elif isinstance(result, str):
            try:
                loaded = json.loads(result.strip())
                if isinstance(loaded, dict):
                    parsed_dict = loaded
                    details["is_json"] = True
            except Exception:
                pass

        # 2. Check explicit top-level error argument
        if error:
            details["explicit_error"] = error
            # If a file write landed despite an error (e.g. secondary hook failed), it's partial
            if file_landed:
                return ToolResultClassification(
                    status=ResultClassificationType.PARTIAL,
                    tool_name=tool_name,
                    is_success=False,
                    is_failure=False,
                    is_partial=True,
                    has_side_effect=has_side_effect,
                    file_mutation_landed=True,
                    error_message=error,
                    details=details,
                )
            return ToolResultClassification(
                status=ResultClassificationType.FAILURE,
                tool_name=tool_name,
                is_success=False,
                is_failure=True,
                is_partial=False,
                has_side_effect=has_side_effect,
                file_mutation_landed=file_landed,
                error_message=error,
                details=details,
            )

        # 3. Check explicit exit code failure
        if exit_code is not None and exit_code != 0:
            details["non_zero_exit"] = True
            # Check if stdout or result had partial useful progress
            res_str = str(result) if result is not None else ""
            has_warning = any(pat.search(res_str) for pat in _WARNING_PATTERNS)
            if file_landed or (len(res_str.strip()) > 0 and has_warning):
                return ToolResultClassification(
                    status=ResultClassificationType.PARTIAL,
                    tool_name=tool_name,
                    is_success=False,
                    is_failure=False,
                    is_partial=True,
                    has_side_effect=has_side_effect,
                    file_mutation_landed=file_landed,
                    error_message=f"Command exited with code {exit_code}",
                    details=details,
                )
            return ToolResultClassification(
                status=ResultClassificationType.FAILURE,
                tool_name=tool_name,
                is_success=False,
                is_failure=True,
                is_partial=False,
                has_side_effect=has_side_effect,
                file_mutation_landed=file_landed,
                error_message=f"Process exited with non-zero status code: {exit_code}",
                details=details,
            )

        # 4. Check structured dictionary / JSON output
        if parsed_dict is not None:
            # Check for error fields
            has_error = bool(parsed_dict.get("error") or parsed_dict.get("errors") or parsed_dict.get("status") == "error" or parsed_dict.get("failed") is True)
            err_msg = str(parsed_dict.get("error") or parsed_dict.get("errors") or "")

            # Check for lint / warnings
            lint_obj = parsed_dict.get("lint")
            has_lint_error = isinstance(lint_obj, dict) and lint_obj.get("status") == "error"
            has_warnings = bool(parsed_dict.get("warning") or parsed_dict.get("warnings") or has_lint_error)

            # Check for partial progress indicators
            has_partial_progress = (
                parsed_dict.get("partial") is True
                or parsed_dict.get("status") == "partial"
                or (parsed_dict.get("items_processed", 0) > 0 and has_error)
                or (parsed_dict.get("success_count", 0) > 0 and parsed_dict.get("failure_count", 0) > 0)
            )

            if file_landed:
                if has_lint_error or has_warnings:
                    details["lint_or_warnings"] = lint_obj or parsed_dict.get("warnings")
                    return ToolResultClassification(
                        status=ResultClassificationType.PARTIAL,
                        tool_name=tool_name,
                        is_success=False,
                        is_failure=False,
                        is_partial=True,
                        has_side_effect=has_side_effect,
                        file_mutation_landed=True,
                        error_message=err_msg or "File written with nested lint warnings/errors",
                        details=details,
                    )
                return ToolResultClassification(
                    status=ResultClassificationType.SUCCESS,
                    tool_name=tool_name,
                    is_success=True,
                    is_failure=False,
                    is_partial=False,
                    has_side_effect=has_side_effect,
                    file_mutation_landed=True,
                    details=details,
                )

            if has_partial_progress or (has_error and (parsed_dict.get("bytes_written", 0) > 0 or has_warnings)):
                return ToolResultClassification(
                    status=ResultClassificationType.PARTIAL,
                    tool_name=tool_name,
                    is_success=False,
                    is_failure=False,
                    is_partial=True,
                    has_side_effect=has_side_effect,
                    file_mutation_landed=file_landed,
                    error_message=err_msg or "Partial execution completed with errors",
                    details=details,
                )

            if has_error:
                return ToolResultClassification(
                    status=ResultClassificationType.FAILURE,
                    tool_name=tool_name,
                    is_success=False,
                    is_failure=True,
                    is_partial=False,
                    has_side_effect=has_side_effect,
                    file_mutation_landed=file_landed,
                    error_message=err_msg or "Operation returned error",
                    details=details,
                )

            if has_warnings:
                return ToolResultClassification(
                    status=ResultClassificationType.PARTIAL,
                    tool_name=tool_name,
                    is_success=False,
                    is_failure=False,
                    is_partial=True,
                    has_side_effect=has_side_effect,
                    file_mutation_landed=file_landed,
                    details=details,
                )

            return ToolResultClassification(
                status=ResultClassificationType.SUCCESS,
                tool_name=tool_name,
                is_success=True,
                is_failure=False,
                is_partial=False,
                has_side_effect=has_side_effect,
                file_mutation_landed=file_landed,
                details=details,
            )

        # 5. String result classification
        if isinstance(result, str):
            res_str = result.strip()
            # Check for error patterns
            for pat in _ERROR_PATTERNS:
                if pat.search(res_str):
                    # If warning pattern also exists, classify as partial
                    if any(w_pat.search(res_str) for w_pat in _WARNING_PATTERNS):
                        return ToolResultClassification(
                            status=ResultClassificationType.PARTIAL,
                            tool_name=tool_name,
                            is_success=False,
                            is_failure=False,
                            is_partial=True,
                            has_side_effect=has_side_effect,
                            file_mutation_landed=file_landed,
                            error_message="Error pattern detected alongside partial progress warnings",
                            details=details,
                        )
                    return ToolResultClassification(
                        status=ResultClassificationType.FAILURE,
                        tool_name=tool_name,
                        is_success=False,
                        is_failure=True,
                        is_partial=False,
                        has_side_effect=has_side_effect,
                        file_mutation_landed=file_landed,
                        error_message="Error pattern detected in tool output",
                        details=details,
                    )

            # Check for warning patterns
            if any(pat.search(res_str) for pat in _WARNING_PATTERNS):
                return ToolResultClassification(
                    status=ResultClassificationType.PARTIAL,
                    tool_name=tool_name,
                    is_success=False,
                    is_failure=False,
                    is_partial=True,
                    has_side_effect=has_side_effect,
                    file_mutation_landed=file_landed,
                    details=details,
                )

            return ToolResultClassification(
                status=ResultClassificationType.SUCCESS,
                tool_name=tool_name,
                is_success=True,
                is_failure=False,
                is_partial=False,
                has_side_effect=has_side_effect,
                file_mutation_landed=file_landed,
                details=details,
            )

        # 6. Boolean result
        if isinstance(result, bool):
            if result:
                return ToolResultClassification(
                    status=ResultClassificationType.SUCCESS,
                    tool_name=tool_name,
                    is_success=True,
                    is_failure=False,
                    is_partial=False,
                    has_side_effect=has_side_effect,
                    file_mutation_landed=file_landed,
                    details=details,
                )
            return ToolResultClassification(
                status=ResultClassificationType.FAILURE,
                tool_name=tool_name,
                is_success=False,
                is_failure=True,
                is_partial=False,
                has_side_effect=has_side_effect,
                file_mutation_landed=file_landed,
                error_message="Tool returned False",
                details=details,
            )

        # 7. Fallback clean default
        return ToolResultClassification(
            status=ResultClassificationType.SUCCESS,
            tool_name=tool_name,
            is_success=True,
            is_failure=False,
            is_partial=False,
            has_side_effect=has_side_effect,
            file_mutation_landed=file_landed,
            details=details,
        )
