"""
Concrete implementation of Tool Call Validation and guardrails (SPEC §3.8 / F-0100).
Integrates schema validation with Hermes loop guardrails, duplicate detection, and failure limits.
"""
from __future__ import annotations

from collections import deque
import hashlib
import json
import logging
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from sidecar import config as cfg
from sidecar.providers.tool_call_validation import (
    BaseToolCallValidationProvider,
    ToolCallGuardrailConfig,
    ToolCategory,
    ValidationAction,
    ValidationDecision,
    ValidationObservation,
)

logger = logging.getLogger(__name__)

IDEMPOTENT_TOOL_NAMES: frozenset[str] = frozenset({
    "read_file",
    "read",
    "search_files",
    "find_files",
    "grep",
    "ls",
    "web_search",
    "web_extract",
    "session_search",
    "skill_view",
    "skills_list",
    "browser_snapshot",
    "browser_console",
    "git_status",
    "git_diff",
    "git_log",
    "locus_memory",
    "mcp_filesystem_read_file",
    "mcp_filesystem_list_directory",
})

MUTATING_TOOL_NAMES: frozenset[str] = frozenset({
    "terminal",
    "bash",
    "powershell",
    "execute_code",
    "write_file",
    "write",
    "edit",
    "patch",
    "git_commit",
    "locus_checkin",
    "locus_life",
    "locus_goals",
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_scroll",
    "browser_navigate",
    "send_message",
    "cronjob_manage",
    "delegate_task",
    "subagents_spawn",
})

STALL_GUARD_REPEATABLE_TOOLS: frozenset[str] = frozenset({
    "process_manage",
    "subagent_status",
    "poll_status",
})


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def _canonical_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        return str(data)


def _detect_failure(tool_name: str, result: Optional[str], failed: Optional[bool]) -> bool:
    if failed is not None:
        return bool(failed)
    if result is None:
        return False
    lower = result[:500].lower()
    if '"exit_code":' in lower:
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and parsed.get("exit_code", 0) != 0:
                return True
        except Exception:
            pass
    return '"error"' in lower or '"failed"' in lower or result.strip().startswith("Error:")


class ToolCallValidationProvider(BaseToolCallValidationProvider):
    """Production provider enforcing tool-call schema validation and loop guardrails."""

    def __init__(self, config: Optional[ToolCallGuardrailConfig] = None) -> None:
        self._config = config or ToolCallGuardrailConfig(
            warnings_enabled=bool(cfg.get("locus.tool_call_validation.warnings_enabled", True)),
            hard_stop_enabled=bool(cfg.get("locus.tool_call_validation.hard_stop_enabled", True)),
            exact_failure_warn_after=int(cfg.get("locus.tool_call_validation.exact_failure_warn_after", 2)),
            exact_failure_block_after=int(cfg.get("locus.tool_call_validation.exact_failure_block_after", 4)),
            same_tool_failure_warn_after=int(cfg.get("locus.tool_call_validation.same_tool_failure_warn_after", 3)),
            same_tool_failure_halt_after=int(cfg.get("locus.tool_call_validation.same_tool_failure_halt_after", 6)),
            idempotent_no_progress_warn_after=int(cfg.get("locus.tool_call_validation.idempotent_no_progress_warn_after", 2)),
            idempotent_no_progress_block_after=int(cfg.get("locus.tool_call_validation.idempotent_no_progress_block_after", 4)),
            identical_call_threshold=int(cfg.get("locus.tool_call_validation.identical_call_threshold", 3)),
            max_cycle_period=int(cfg.get("locus.tool_call_validation.max_cycle_period", 4)),
            max_web_searches_per_turn=int(cfg.get("locus.tool_call_validation.max_web_searches_per_turn", 50)),
            max_subagents_per_turn=int(cfg.get("locus.tool_call_validation.max_subagents_per_turn", 50)),
        )
        # Turn-local state
        self._exact_failure_counts: Dict[Tuple[str, str], int] = {}
        self._tool_failure_counts: Dict[str, int] = {}
        self._identical_call_streaks: Dict[Tuple[str, str, str], int] = {}
        self._call_history: List[Tuple[str, str]] = []
        self._cycle_history: deque[Tuple[str, str]] = deque(maxlen=64)
        self._web_search_count: int = 0
        self._subagent_count: int = 0

    def get_config(self) -> ToolCallGuardrailConfig:
        return self._config

    def classify_tool(self, tool_name: str) -> ToolCategory:
        name = tool_name.strip().lower()
        if name in IDEMPOTENT_TOOL_NAMES:
            return ToolCategory.IDEMPOTENT
        if name in MUTATING_TOOL_NAMES:
            return ToolCategory.MUTATING
        return ToolCategory.UNKNOWN

    def validate_schema(
        self,
        tool_name: str,
        params: Mapping[str, Any],
        schema: Optional[Mapping[str, Any]] = None,
    ) -> List[str]:
        """Validate params against simplified JSON schema."""
        if not schema or not isinstance(schema, Mapping):
            return []
        errors: List[str] = []
        properties = schema.get("properties") or {}
        required = schema.get("required") or []

        # Check required fields
        for req in required:
            if req not in params or params[req] is None:
                errors.append(f"Missing required parameter: '{req}'")

        # Check property types
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": (list, tuple),
            "object": (dict, Mapping),
        }

        for param_name, param_val in params.items():
            prop_def = properties.get(param_name)
            if not prop_def or not isinstance(prop_def, Mapping):
                continue
            expected_type = prop_def.get("type")
            if expected_type in type_map:
                py_type = type_map[expected_type]
                # boolean is subclass of int in Python, special case check
                if expected_type in ("integer", "number") and isinstance(param_val, bool):
                    errors.append(f"Parameter '{param_name}' expected {expected_type}, got boolean")
                elif not isinstance(param_val, py_type):
                    errors.append(
                        f"Parameter '{param_name}' expected {expected_type}, got {type(param_val).__name__}"
                    )

            # Enum validation
            enum_vals = prop_def.get("enum")
            if enum_vals is not None and isinstance(enum_vals, (list, tuple, set)):
                if param_val not in enum_vals:
                    errors.append(f"Parameter '{param_name}' value '{param_val}' not in allowed enum {list(enum_vals)}")

        return errors

    def before_call(
        self,
        tool_name: str,
        params: Mapping[str, Any],
        schema: Optional[Mapping[str, Any]] = None,
    ) -> ValidationDecision:
        name = tool_name.strip()
        category = self.classify_tool(name)
        args_hash = _sha256(_canonical_json(params))

        # 1. Parameter schema validation
        val_errors = self.validate_schema(name, params, schema)
        if val_errors:
            return ValidationDecision(
                action=ValidationAction.BLOCK,
                code="schema_validation_failed",
                message=f"Parameter schema validation failed for {name}: {'; '.join(val_errors)}",
                tool_name=name,
                count=0,
                category=category,
                validation_errors=val_errors,
            )

        # 2. Per-turn caps
        if name in ("web_search", "web_extract"):
            if self._web_search_count >= self._config.max_web_searches_per_turn:
                return ValidationDecision(
                    action=ValidationAction.BLOCK,
                    code="cap_exceeded_web_search",
                    message=f"Turn web search cap ({self._config.max_web_searches_per_turn}) exceeded for {name}",
                    tool_name=name,
                    count=self._web_search_count,
                    category=category,
                )

        if name in ("delegate_task", "subagents_spawn"):
            if self._subagent_count >= self._config.max_subagents_per_turn:
                return ValidationDecision(
                    action=ValidationAction.BLOCK,
                    code="cap_exceeded_subagent",
                    message=f"Turn subagent spawn cap ({self._config.max_subagents_per_turn}) exceeded for {name}",
                    tool_name=name,
                    count=self._subagent_count,
                    category=category,
                )

        # 3. Repeated exact failure checks
        fail_key = (name, args_hash)
        fail_count = self._exact_failure_counts.get(fail_key, 0)
        if self._config.hard_stop_enabled and fail_count >= self._config.exact_failure_block_after:
            return ValidationDecision(
                action=ValidationAction.BLOCK,
                code="repeated_exact_failure_block",
                message=(
                    f"Blocked {name}: the same tool call failed {fail_count} times with identical arguments. "
                    "Stop retrying it unchanged; change strategy or adjust arguments."
                ),
                tool_name=name,
                count=fail_count,
                category=category,
            )
        if self._config.warnings_enabled and fail_count >= self._config.exact_failure_warn_after:
            return ValidationDecision(
                action=ValidationAction.WARN,
                code="repeated_exact_failure_warning",
                message=f"Warning: {name} with identical arguments has failed {fail_count} times this turn.",
                tool_name=name,
                count=fail_count,
                category=category,
            )

        # 4. Same tool cumulative failure halt
        tool_failures = self._tool_failure_counts.get(name, 0)
        if self._config.hard_stop_enabled and tool_failures >= self._config.same_tool_failure_halt_after:
            return ValidationDecision(
                action=ValidationAction.HALT,
                code="same_tool_failure_halt",
                message=f"Stopped {name}: it failed {tool_failures} times this turn across different arguments.",
                tool_name=name,
                count=tool_failures,
                category=category,
            )
        if self._config.warnings_enabled and tool_failures >= self._config.same_tool_failure_warn_after:
            return ValidationDecision(
                action=ValidationAction.WARN,
                code="same_tool_failure_warning",
                message=f"Warning: {name} has accumulated {tool_failures} failures this turn.",
                tool_name=name,
                count=tool_failures,
                category=category,
            )

        # 5. Cycle loop detection (e.g. A, B, A, B ...)
        cycle_detected = self._detect_cycle(name, args_hash)
        if cycle_detected and self._config.warnings_enabled:
            return ValidationDecision(
                action=ValidationAction.WARN,
                code="cycle_detected_warning",
                message=f"Warning: repeating alternating cycle detected involving {name}. Break the loop.",
                tool_name=name,
                count=cycle_detected,
                category=category,
            )

        return ValidationDecision(
            action=ValidationAction.ALLOW,
            code="allow",
            message="",
            tool_name=name,
            count=0,
            category=category,
        )

    def _detect_cycle(self, tool_name: str, args_hash: str) -> int:
        """Detect if sequence of recent calls has repeated period >= 2 up to max_cycle_period."""
        history = list(self._cycle_history) + [(tool_name, args_hash)]
        n = len(history)
        if n < 4:
            return 0
        for period in range(2, min(self._config.max_cycle_period + 1, n // 2 + 1)):
            pattern = history[-period:]
            prior = history[-2 * period : -period]
            if pattern == prior:
                # Check how many full cycles matched
                matched_cycles = 2
                pos = n - 2 * period
                while pos >= period and history[pos - period : pos] == pattern:
                    matched_cycles += 1
                    pos -= period
                if matched_cycles >= 2:
                    return matched_cycles
        return 0

    def observe_call(
        self,
        tool_name: str,
        params: Mapping[str, Any],
        result: Optional[str] = None,
        failed: Optional[bool] = None,
    ) -> ValidationObservation:
        name = tool_name.strip()
        args_hash = _sha256(_canonical_json(params))
        res_str = result or ""
        res_hash = _sha256(res_str)
        is_fail = _detect_failure(name, result, failed)

        # Update per-turn counts
        if name in ("web_search", "web_extract"):
            self._web_search_count += 1
        elif name in ("delegate_task", "subagents_spawn"):
            self._subagent_count += 1

        self._call_history.append((name, args_hash))
        self._cycle_history.append((name, args_hash))

        fail_key = (name, args_hash)
        if is_fail:
            self._exact_failure_counts[fail_key] = self._exact_failure_counts.get(fail_key, 0) + 1
            self._tool_failure_counts[name] = self._tool_failure_counts.get(name, 0) + 1
            return ValidationObservation(
                tool_name=name,
                notice=f"Call to {name} failed.",
                is_duplicate=False,
                streak_count=self._exact_failure_counts[fail_key],
            )

        # If call succeeded and is mutating, reset tool failure counters for experiments
        if self.classify_tool(name) == ToolCategory.MUTATING:
            self._exact_failure_counts.clear()

        # Idempotent stall guard: track identical (tool, args, result)
        streak_key = (name, args_hash, res_hash)
        streak = self._identical_call_streaks.get(streak_key, 0) + 1
        self._identical_call_streaks[streak_key] = streak

        notice: Optional[str] = None
        stub: Optional[str] = None
        is_dup = False

        if self.classify_tool(name) == ToolCategory.IDEMPOTENT and name not in STALL_GUARD_REPEATABLE_TOOLS:
            if streak >= self._config.identical_call_threshold:
                is_dup = True
                notice = (
                    f"NOTICE: {name} called {streak} times with identical arguments and returned identical output. "
                    "Avoid looping without state progression."
                )
                if len(res_str) >= 256:
                    stub = f"[Duplicate identical output from {name} omitted ({len(res_str)} chars)]"

        return ValidationObservation(
            tool_name=name,
            notice=notice,
            stub=stub,
            is_duplicate=is_dup,
            streak_count=streak,
        )

    def reset_for_turn(self) -> None:
        """Clear all turn-local counters."""
        self._exact_failure_counts.clear()
        self._tool_failure_counts.clear()
        self._identical_call_streaks.clear()
        self._call_history.clear()
        self._cycle_history.clear()
        self._web_search_count = 0
        self._subagent_count = 0
        logger.debug("ToolCallValidationProvider turn state reset.")

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "provider": self.__class__.__name__,
            "history_length": len(self._call_history),
            "web_searches": self._web_search_count,
            "subagents": self._subagent_count,
            "config": self._config.to_dict(),
        }


# Auto-register with global provider registry
from sidecar.registry import get_registry

get_registry().register("tool_call_validation", "default", ToolCallValidationProvider)
get_registry().register("tool_validation", "default", ToolCallValidationProvider)
get_registry().register("guardrails", "default", ToolCallValidationProvider)
