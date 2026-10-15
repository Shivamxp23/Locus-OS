"""sidecar/tools/validation.py - Tool Call Validation Engine.

Implements Spec §3.8:
- Validates parameter schemas, required fields, and type bounds prior to tool execution.
- Sanitizes dangerous values and produces detailed validation rejection diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type


@dataclass
class ValidationRule:
    param_name: str
    expected_type: type
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[list[Any]] = None


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    sanitized_params: dict[str, Any] = field(default_factory=dict)


class ToolCallValidator:
    """Validates and sanitizes tool arguments against formal schemas."""

    def __init__(self) -> None:
        self.schemas: dict[str, list[ValidationRule]] = {}

    def register_schema(self, tool_name: str, rules: list[ValidationRule]) -> None:
        self.schemas[tool_name] = rules

    def validate_call(self, tool_name: str, params: dict[str, Any]) -> ValidationResult:
        rules = self.schemas.get(tool_name)
        if not rules:
            # If no schema registered, pass through safely
            return ValidationResult(is_valid=True, sanitized_params=dict(params))

        errors = []
        sanitized = dict(params)

        for rule in rules:
            val = params.get(rule.param_name)
            if val is None:
                if rule.required:
                    errors.append(f"Missing required parameter '{rule.param_name}' for tool '{tool_name}'")
                continue

            if not isinstance(val, rule.expected_type):
                # Try soft type coercion for floats and ints
                if rule.expected_type is float and isinstance(val, (int, float)):
                    sanitized[rule.param_name] = float(val)
                elif rule.expected_type is int and isinstance(val, int):
                    sanitized[rule.param_name] = val
                else:
                    errors.append(
                        f"Parameter '{rule.param_name}' expected {rule.expected_type.__name__}, got {type(val).__name__}"
                    )
                    continue

            # Bounds check
            num_val = sanitized[rule.param_name]
            if isinstance(num_val, (int, float)):
                if rule.min_value is not None and num_val < rule.min_value:
                    errors.append(f"Parameter '{rule.param_name}' value {num_val} < min {rule.min_value}")
                if rule.max_value is not None and num_val > rule.max_value:
                    errors.append(f"Parameter '{rule.param_name}' value {num_val} > max {rule.max_value}")

            # Enum check
            if rule.allowed_values is not None and num_val not in rule.allowed_values:
                errors.append(f"Parameter '{rule.param_name}' value '{num_val}' not in allowed set {rule.allowed_values}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized,
        )
