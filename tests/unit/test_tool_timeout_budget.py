"""
Unit tests for Tool Timeout / Budget (SPEC §3.11 / F-0103).
Asserts default timeouts, per-tool overrides, max clamping, per-turn budget
tracking, over-budget detection, and modular provider interchangeability.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from sidecar.providers.tool_timeout_budget import (
    BaseToolTimeoutBudgetProvider,
    ExecutionBudgetRecord,
    TimeoutAction,
    TimeoutResolution,
    ToolTimeoutConfig,
)
from sidecar.registry import ProviderRegistry
from sidecar.tool_timeout_budget import ToolTimeoutBudgetProvider


def test_resolve_default_timeout():
    """SPEC §3.11 line 2703: "Verdict: 🆕 LOCUS-NEW · Source: OpenHuman tool_timeout · Repo vs .locus: locus-os" """
    provider = ToolTimeoutBudgetProvider()
    res = provider.resolve_timeout("unknown_tool")

    assert res.tool_name == "unknown_tool"
    assert res.timeout_secs == 120.0
    assert res.action == TimeoutAction.ENFORCE
    assert res.is_over_budget is False
    assert res.remaining_turn_budget_secs is None


def test_resolve_per_tool_override():
    """SPEC §3.11 line 2703: "Verdict: 🆕 LOCUS-NEW · Source: OpenHuman tool_timeout · Repo vs .locus: locus-os" """
    provider = ToolTimeoutBudgetProvider()

    # bash / terminal has 300s override
    res_bash = provider.resolve_timeout("bash")
    assert res_bash.timeout_secs == 300.0

    # web_search has 60s override
    res_search = provider.resolve_timeout("web_search")
    assert res_search.timeout_secs == 60.0

    # read_file has 30s override
    res_read = provider.resolve_timeout("read_file")
    assert res_read.timeout_secs == 30.0


def test_resolve_requested_timeout_clamped():
    """SPEC §3.11 line 2703: "Verdict: 🆕 LOCUS-NEW · Source: OpenHuman tool_timeout · Repo vs .locus: locus-os" """
    provider = ToolTimeoutBudgetProvider()

    # Valid custom request
    res = provider.resolve_timeout("any_tool", requested_timeout=45.0)
    assert res.timeout_secs == 45.0

    # Request exceeding max (3600s)
    res_max = provider.resolve_timeout("any_tool", requested_timeout=99999.0)
    assert res_max.timeout_secs == 3600.0

    # Minimum threshold clamp (0.1s)
    res_min = provider.resolve_timeout("any_tool", requested_timeout=-10.0)
    assert res_min.timeout_secs == 0.1


def test_turn_budget_clamping():
    """SPEC §3.11 line 2703: "Verdict: 🆕 LOCUS-NEW · Source: OpenHuman tool_timeout · Repo vs .locus: locus-os" """
    provider = ToolTimeoutBudgetProvider()
    # Configure 100s turn budget
    provider.reset_turn_budget(total_budget_secs=100.0)

    # bash default is 300s, but should be clamped to remaining turn budget 100s
    res = provider.resolve_timeout("bash")
    assert res.timeout_secs == 100.0
    assert res.remaining_turn_budget_secs == 100.0
    assert res.is_over_budget is False

    # Record 40s execution
    provider.record_execution("bash", elapsed_secs=40.0)
    assert provider.get_remaining_turn_budget() == 60.0

    # Next execution should clamp to remaining 60s
    res2 = provider.resolve_timeout("bash")
    assert res2.timeout_secs == 60.0
    assert res2.remaining_turn_budget_secs == 60.0


def test_turn_budget_exhaustion_over_budget():
    """SPEC §3.11 line 2703: "Verdict: 🆕 LOCUS-NEW · Source: OpenHuman tool_timeout · Repo vs .locus: locus-os" """
    provider = ToolTimeoutBudgetProvider()
    provider.reset_turn_budget(total_budget_secs=50.0)

    # Consume entire budget
    provider.record_execution("terminal", elapsed_secs=55.0)
    assert provider.get_remaining_turn_budget() == 0.0

    res = provider.resolve_timeout("any_tool")
    assert res.is_over_budget is True
    assert res.timeout_secs == 0.0
    assert res.remaining_turn_budget_secs == 0.0


def test_record_execution_and_reset():
    """SPEC §3.11 line 2704: "Swappable / off state: locus.tools.timeout.enabled. Off → no per-tool timeout enforcement." """
    provider = ToolTimeoutBudgetProvider()
    provider.reset_turn_budget(total_budget_secs=200.0)

    provider.record_execution("read_file", elapsed_secs=5.0)
    provider.record_execution("write_file", elapsed_secs=10.0, timed_out=True)

    health = provider.health_check()
    assert health["executions_count"] == 2
    assert health["elapsed_turn_secs"] == 15.0

    # Reset
    provider.reset_turn_budget(total_budget_secs=300.0)
    health_reset = provider.health_check()
    assert health_reset["executions_count"] == 0
    assert health_reset["elapsed_turn_secs"] == 0.0
    assert health_reset["turn_budget_secs"] == 300.0


def test_modular_timeout_provider_swap():
    """SPEC §3.11 line 2704: "Swappable / off state: locus.tools.timeout.enabled. Off → no per-tool timeout enforcement." """
    registry = ProviderRegistry()

    class CustomTimeoutProvider(BaseToolTimeoutBudgetProvider):
        def resolve_timeout(self, tool_name: str, requested_timeout: Optional[float] = None) -> TimeoutResolution:
            return TimeoutResolution(
                tool_name=tool_name,
                timeout_secs=999.0,
                action=TimeoutAction.BYPASS,
                is_over_budget=False,
            )

        def record_execution(self, tool_name: str, elapsed_secs: float, timed_out: bool = False) -> None:
            pass

        def get_remaining_turn_budget(self) -> Optional[float]:
            return 999.0

        def reset_turn_budget(self, total_budget_secs: Optional[float] = None) -> None:
            pass

        def get_config(self) -> ToolTimeoutConfig:
            return ToolTimeoutConfig()

        def health_check(self) -> Dict[str, Any]:
            return {"status": "custom"}

    registry.register("tool_timeout_budget", "custom", CustomTimeoutProvider)
    active_cls = registry.get_active_provider("tool_timeout_budget", default_name="custom")
    assert active_cls is CustomTimeoutProvider

    inst = active_cls()
    res = inst.resolve_timeout("bash")
    assert res.timeout_secs == 999.0
    assert res.action == TimeoutAction.BYPASS
