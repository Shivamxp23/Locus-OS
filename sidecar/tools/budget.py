"""sidecar/tools/budget.py - Tool Execution Timeout and Invocation Budget.

Implements Spec §3.11:
- Per-tool timeout limits (e.g. 5s for fast lookup, 60s for browser/research).
- Per-turn invocation budget to prevent infinite loops.
- Cumulative execution time budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ToolBudgetLimits:
    max_invocations_per_turn: int = 25
    max_total_seconds_per_turn: float = 120.0
    default_tool_timeout_seconds: float = 15.0
    per_tool_timeouts: dict[str, float] = field(default_factory=dict)


@dataclass
class BudgetUsage:
    invocation_count: int = 0
    total_duration_seconds: float = 0.0
    is_exhausted: bool = False
    exhaustion_reason: Optional[str] = None


class ToolBudgetManager:
    """Tracks and enforces tool execution timeouts and turn budgets."""

    def __init__(self, limits: Optional[ToolBudgetLimits] = None) -> None:
        self.limits = limits or ToolBudgetLimits()
        self.usage = BudgetUsage()

    def get_timeout_for_tool(self, tool_name: str) -> float:
        return self.limits.per_tool_timeouts.get(
            tool_name, self.limits.default_tool_timeout_seconds
        )

    def can_invoke(self, tool_name: str) -> tuple[bool, Optional[str]]:
        if self.usage.invocation_count >= self.limits.max_invocations_per_turn:
            reason = f"Max invocation budget ({self.limits.max_invocations_per_turn}) reached this turn."
            self.usage.is_exhausted = True
            self.usage.exhaustion_reason = reason
            return False, reason

        if self.usage.total_duration_seconds >= self.limits.max_total_seconds_per_turn:
            reason = f"Max total duration ({self.limits.max_total_seconds_per_turn}s) exhausted this turn."
            self.usage.is_exhausted = True
            self.usage.exhaustion_reason = reason
            return False, reason

        return True, None

    def record_invocation(self, tool_name: str, duration_seconds: float) -> None:
        self.usage.invocation_count += 1
        self.usage.total_duration_seconds += duration_seconds
        if (
            self.usage.invocation_count >= self.limits.max_invocations_per_turn
            or self.usage.total_duration_seconds >= self.limits.max_total_seconds_per_turn
        ):
            self.usage.is_exhausted = True

    def reset_turn(self) -> None:
        self.usage = BudgetUsage()
