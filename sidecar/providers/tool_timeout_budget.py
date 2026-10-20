"""
Abstract base provider and data models for Tool Timeout / Budget (SPEC §3.11 / F-0103).
Enforces configurable per-tool execution timeouts and per-turn elapsed time budgets,
derived from OpenHuman's tool_timeout architecture.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class TimeoutAction(str, Enum):
    """Enforcement action for tool execution timeout."""
    ALLOW = "allow"
    ENFORCE = "enforce"
    BYPASS = "bypass"


@dataclass(frozen=True)
class ToolTimeoutConfig:
    """Configuration for Tool Timeout and Budgeting."""
    enabled: bool = True
    default_timeout_secs: float = 120.0
    max_timeout_secs: float = 3600.0
    turn_budget_secs: Optional[float] = None
    per_tool_timeouts: Dict[str, float] = field(default_factory=lambda: {
        "terminal": 300.0,
        "bash": 300.0,
        "powershell": 300.0,
        "execute_code": 180.0,
        "web_search": 60.0,
        "web_extract": 60.0,
        "read_file": 30.0,
        "write_file": 60.0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "default_timeout_secs": self.default_timeout_secs,
            "max_timeout_secs": self.max_timeout_secs,
            "turn_budget_secs": self.turn_budget_secs,
            "per_tool_timeouts": dict(self.per_tool_timeouts),
        }


@dataclass(frozen=True)
class TimeoutResolution:
    """Calculated timeout limit and budget status for a tool invocation."""
    tool_name: str
    timeout_secs: float
    remaining_turn_budget_secs: Optional[float] = None
    action: TimeoutAction = TimeoutAction.ENFORCE
    is_over_budget: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "timeout_secs": self.timeout_secs,
            "remaining_turn_budget_secs": self.remaining_turn_budget_secs,
            "action": self.action.value,
            "is_over_budget": self.is_over_budget,
        }


@dataclass(frozen=True)
class ExecutionBudgetRecord:
    """Record of completed tool execution duration and timeout flag."""
    tool_name: str
    elapsed_secs: float
    timed_out: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseToolTimeoutBudgetProvider(ABC):
    """Interface for Tool Timeout and Budget providers."""

    def __init__(self, name: str = "tool_timeout_budget") -> None:
        self.name = name

    @abstractmethod
    def resolve_timeout(
        self,
        tool_name: str,
        requested_timeout: Optional[float] = None,
    ) -> TimeoutResolution:
        """Resolve effective timeout limit in seconds for a specific tool execution."""
        pass

    @abstractmethod
    def record_execution(
        self,
        tool_name: str,
        elapsed_secs: float,
        timed_out: bool = False,
    ) -> None:
        """Record completed tool execution duration and update turn budget."""
        pass

    @abstractmethod
    def get_remaining_turn_budget(self) -> Optional[float]:
        """Return remaining seconds in current turn budget, or None if unconstrained."""
        pass

    @abstractmethod
    def reset_turn_budget(self, total_budget_secs: Optional[float] = None) -> None:
        """Reset elapsed turn time and optionally update turn budget limit."""
        pass

    @abstractmethod
    def get_config(self) -> ToolTimeoutConfig:
        """Retrieve current timeout and budget configuration."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return diagnostic health check dict."""
        pass
