"""
Concrete implementation of Tool Timeout / Budget (SPEC §3.11 / F-0103).
Enforces configurable per-tool execution timeouts and per-turn elapsed time budgets,
derived from OpenHuman's tool_timeout architecture.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from sidecar.providers.tool_timeout_budget import (
    BaseToolTimeoutBudgetProvider,
    ExecutionBudgetRecord,
    TimeoutAction,
    TimeoutResolution,
    ToolTimeoutConfig,
)

logger = logging.getLogger(__name__)


class ToolTimeoutBudgetProvider(BaseToolTimeoutBudgetProvider):
    """Default provider for Tool Timeout and Turn Budgeting."""

    def __init__(self, name: str = "tool_timeout_budget_default") -> None:
        super().__init__(name=name)
        self._config = ToolTimeoutConfig()
        self._lock = threading.Lock()
        self._elapsed_turn_secs: float = 0.0
        self._turn_budget_secs: Optional[float] = None
        self._history: List[ExecutionBudgetRecord] = []

    def get_config(self) -> ToolTimeoutConfig:
        return self._config

    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            elapsed = self._elapsed_turn_secs
            budget = self._turn_budget_secs
            records_count = len(self._history)
        return {
            "status": "healthy",
            "provider": self.__class__.__name__,
            "elapsed_turn_secs": elapsed,
            "turn_budget_secs": budget,
            "executions_count": records_count,
            "config": self._config.to_dict(),
        }

    def resolve_timeout(
        self,
        tool_name: str,
        requested_timeout: Optional[float] = None,
    ) -> TimeoutResolution:
        """
        Resolve effective timeout for tool execution, clamping to configured
        maximum and any remaining per-turn budget.
        """
        with self._lock:
            max_limit = self._config.max_timeout_secs
            base_timeout: float

            if requested_timeout is not None:
                base_timeout = max(0.1, min(float(requested_timeout), max_limit))
            elif tool_name in self._config.per_tool_timeouts:
                base_timeout = self._config.per_tool_timeouts[tool_name]
            else:
                base_timeout = self._config.default_timeout_secs

            # Evaluate against turn budget if set
            active_turn_budget = self._turn_budget_secs or self._config.turn_budget_secs
            if active_turn_budget is not None:
                remaining = max(0.0, active_turn_budget - self._elapsed_turn_secs)
                if remaining <= 0.0:
                    return TimeoutResolution(
                        tool_name=tool_name,
                        timeout_secs=0.0,
                        remaining_turn_budget_secs=0.0,
                        action=TimeoutAction.ENFORCE,
                        is_over_budget=True,
                    )
                effective_timeout = min(base_timeout, remaining)
                return TimeoutResolution(
                    tool_name=tool_name,
                    timeout_secs=effective_timeout,
                    remaining_turn_budget_secs=remaining,
                    action=TimeoutAction.ENFORCE,
                    is_over_budget=False,
                )

            return TimeoutResolution(
                tool_name=tool_name,
                timeout_secs=base_timeout,
                remaining_turn_budget_secs=None,
                action=TimeoutAction.ENFORCE,
                is_over_budget=False,
            )

    def record_execution(
        self,
        tool_name: str,
        elapsed_secs: float,
        timed_out: bool = False,
    ) -> None:
        """Record completed tool invocation duration and update turn totals."""
        with self._lock:
            self._elapsed_turn_secs += max(0.0, float(elapsed_secs))
            self._history.append(
                ExecutionBudgetRecord(
                    tool_name=tool_name,
                    elapsed_secs=max(0.0, float(elapsed_secs)),
                    timed_out=timed_out,
                )
            )

    def get_remaining_turn_budget(self) -> Optional[float]:
        """Return remaining seconds in current turn budget."""
        with self._lock:
            active_budget = self._turn_budget_secs or self._config.turn_budget_secs
            if active_budget is None:
                return None
            return max(0.0, active_budget - self._elapsed_turn_secs)

    def reset_turn_budget(self, total_budget_secs: Optional[float] = None) -> None:
        """Reset elapsed time and optionally configure turn budget."""
        with self._lock:
            self._elapsed_turn_secs = 0.0
            if total_budget_secs is not None:
                self._turn_budget_secs = max(0.0, float(total_budget_secs))
            else:
                self._turn_budget_secs = None
            self._history.clear()
