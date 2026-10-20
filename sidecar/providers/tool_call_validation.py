"""
Abstract base provider and data models for Tool Call Validation (SPEC §3.8 / F-0100).
Integrates Pi tool-definition-wrapper schema validation with Hermes tool_guardrails primitives.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Set


class ValidationAction(str, Enum):
    """Action dictated by the guardrails controller."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    HALT = "halt"


class ToolCategory(str, Enum):
    """Classification of tool mutation effects."""
    IDEMPOTENT = "idempotent"
    MUTATING = "mutating"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ToolCallGuardrailConfig:
    """Thresholds for per-turn tool-call loop and safety guardrails."""
    warnings_enabled: bool = True
    hard_stop_enabled: bool = True
    exact_failure_warn_after: int = 2
    exact_failure_block_after: int = 4
    same_tool_failure_warn_after: int = 3
    same_tool_failure_halt_after: int = 6
    idempotent_no_progress_warn_after: int = 2
    idempotent_no_progress_block_after: int = 4
    identical_call_threshold: int = 3
    max_cycle_period: int = 4
    max_web_searches_per_turn: int = 50
    max_subagents_per_turn: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationDecision:
    """Decision returned prior to tool execution."""
    action: ValidationAction = ValidationAction.ALLOW
    code: str = "allow"
    message: str = ""
    tool_name: str = ""
    count: int = 0
    category: ToolCategory = ToolCategory.UNKNOWN
    validation_errors: List[str] = field(default_factory=list)

    @property
    def allows_execution(self) -> bool:
        return self.action in (ValidationAction.ALLOW, ValidationAction.WARN)

    @property
    def should_halt(self) -> bool:
        return self.action in (ValidationAction.BLOCK, ValidationAction.HALT)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "code": self.code,
            "message": self.message,
            "tool_name": self.tool_name,
            "count": self.count,
            "category": self.category.value,
            "allows_execution": self.allows_execution,
            "should_halt": self.should_halt,
            "validation_errors": self.validation_errors,
        }


@dataclass(frozen=True)
class ValidationObservation:
    """Observation recorded after tool execution."""
    tool_name: str
    notice: Optional[str] = None
    stub: Optional[str] = None
    is_duplicate: bool = False
    streak_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "notice": self.notice,
            "stub": self.stub,
            "is_duplicate": self.is_duplicate,
            "streak_count": self.streak_count,
        }


class BaseToolCallValidationProvider(ABC):
    """Interface for Tool Call Validation and safety guardrail providers."""

    def __init__(self, name: str = "tool_call_validation") -> None:
        self.name = name

    @abstractmethod
    def validate_schema(
        self,
        tool_name: str,
        params: Mapping[str, Any],
        schema: Optional[Mapping[str, Any]] = None,
    ) -> List[str]:
        """Validate parameters against JSON Schema, returning list of validation error strings."""
        pass

    @abstractmethod
    def before_call(
        self,
        tool_name: str,
        params: Mapping[str, Any],
        schema: Optional[Mapping[str, Any]] = None,
    ) -> ValidationDecision:
        """
        Evaluate tool parameters and per-turn history before invocation.
        Returns ValidationDecision indicating allow, warn, block, or halt.
        """
        pass

    @abstractmethod
    def observe_call(
        self,
        tool_name: str,
        params: Mapping[str, Any],
        result: Optional[str] = None,
        failed: Optional[bool] = None,
    ) -> ValidationObservation:
        """
        Record tool invocation result, updating failure streaks and duplicate detectors.
        Returns ValidationObservation with potential notice or duplicate stub.
        """
        pass

    @abstractmethod
    def reset_for_turn(self) -> None:
        """Reset turn-local streak counters, loop detectors, and per-turn invocation counts."""
        pass

    @abstractmethod
    def classify_tool(self, tool_name: str) -> ToolCategory:
        """Classify tool as IDEMPOTENT, MUTATING, or UNKNOWN."""
        pass

    @abstractmethod
    def get_config(self) -> ToolCallGuardrailConfig:
        """Retrieve current guardrail configuration."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return diagnostic health check dict."""
        pass
