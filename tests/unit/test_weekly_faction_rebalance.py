"""
SPEC §25.11 lines 4778-4800: Unit tests for Weekly Faction Rebalance (F-0113 / US-89).
Tests:
- Calculation of weekly actual faction percentages from logged hours
- Deficit computation (target_pct - actual_pct) per faction
- Next week weight adjustment: base_weight + (deficit * correction_factor)
- Clamping to minimum weight floor
- Zero logged duration handling
- Provider modular off-switch returning HTTP 503
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

import sidecar.config as config
from sidecar.life_os.rebalance import (
    STANDARD_FACTION_TARGETS,
    WeeklyFactionRebalancer,
    normalize_faction_name,
)
from sidecar.providers.rebalance import (
    BaseWeeklyFactionRebalanceProvider,
    DefaultWeeklyFactionRebalanceProvider,
)


def test_rebalance_deficit_calculation() -> None:
    """SPEC §25.11 line 4790: "deficit = target_pct − actual_pct" """
    rebalancer = WeeklyFactionRebalancer()

    # Targets: Health 0.25, Leverage 0.25, Craft 0.30, Expression 0.20
    # Actual hours logged: Health 10h, Leverage 10h, Craft 80h, Expression 0h -> Total 100h
    # Actual pcts: Health 0.10, Leverage 0.10, Craft 0.80, Expression 0.00
    actual_hours = {
        "Health/Stability": 10.0,
        "Leverage/Money": 10.0,
        "Craft/Skills": 80.0,
        "Expression/Explore": 0.0,
    }

    res = rebalancer.calculate_rebalance(actual_hours=actual_hours, correction_factor=1.0)

    # Health deficit: 0.25 - 0.10 = +0.15
    assert round(res.deficits["Health/Stability"], 4) == 0.15
    # Leverage deficit: 0.25 - 0.10 = +0.15
    assert round(res.deficits["Leverage/Money"], 4) == 0.15
    # Craft deficit: 0.30 - 0.80 = -0.50
    assert round(res.deficits["Craft/Skills"], 4) == -0.50
    # Expression deficit: 0.20 - 0.00 = +0.20
    assert round(res.deficits["Expression/Explore"], 4) == 0.20


def test_rebalance_next_week_weight_adjustment() -> None:
    """SPEC §25.11 line 4791: "next_week_weight = base_weight + (deficit × correction_factor)" """
    rebalancer = WeeklyFactionRebalancer(min_weight_floor=0.01)

    # Targets: Health 0.25, Leverage 0.25, Craft 0.30, Expression 0.20
    # Actual: Health 20h, Leverage 20h, Craft 40h, Expression 20h -> Total 100h
    # Actual pcts: Health 0.20, Leverage 0.20, Craft 0.40, Expression 0.20
    # Deficits: Health +0.05, Leverage +0.05, Craft -0.10, Expression 0.00
    actual_hours = {
        "health": 20.0,
        "leverage": 20.0,
        "craft": 40.0,
        "expression": 20.0,
    }

    res = rebalancer.calculate_rebalance(actual_hours=actual_hours, correction_factor=1.0)

    # Base weights default to targets
    # Next weights:
    # Health: 0.25 + 0.05 = 0.30
    # Leverage: 0.25 + 0.05 = 0.30
    # Craft: 0.30 - 0.10 = 0.20
    # Expression: 0.20 + 0.00 = 0.20
    assert round(res.adjusted_weights["Health/Stability"], 2) == 0.30
    assert round(res.adjusted_weights["Leverage/Money"], 2) == 0.30
    assert round(res.adjusted_weights["Craft/Skills"], 2) == 0.20
    assert round(res.adjusted_weights["Expression/Explore"], 2) == 0.20

    # Normalized weights sum to 1.0
    assert round(sum(res.normalized_weights.values()), 4) == 1.0000


def test_rebalance_zero_hours_edge_case() -> None:
    """SPEC §25.11 line 4788: "actual = PG query: SUM(duration) per faction for current week" """
    rebalancer = WeeklyFactionRebalancer()

    # Zero hours logged
    res = rebalancer.calculate_rebalance(actual_hours={})

    assert res.total_hours == 0.0
    for f in STANDARD_FACTION_TARGETS:
        assert round(res.deficits[f], 4) == 0.0
        assert round(res.adjusted_weights[f], 4) == STANDARD_FACTION_TARGETS[f]


def test_rebalance_clamping_and_correction_factor() -> None:
    """SPEC §25.11 line 4791: "next_week_weight = base_weight + (deficit × correction_factor)" """
    rebalancer = WeeklyFactionRebalancer(min_weight_floor=0.05)

    # Massive over-allocation on Craft (100h out of 100h)
    actual_hours = {
        "Craft/Skills": 100.0,
        "Health/Stability": 0.0,
        "Leverage/Money": 0.0,
        "Expression/Explore": 0.0,
    }

    # High correction factor 2.0 -> Craft raw: 0.30 + (-0.70 * 2.0) = 0.30 - 1.40 = -1.10
    # Floor must clamp to min_weight_floor 0.05
    res = rebalancer.calculate_rebalance(actual_hours=actual_hours, correction_factor=2.0)

    assert res.adjusted_weights["Craft/Skills"] == 0.05
    assert res.adjusted_weights["Health/Stability"] > 0.25
    assert res.adjusted_weights["Leverage/Money"] > 0.25
    assert res.adjusted_weights["Expression/Explore"] > 0.20


def test_rebalance_provider_modular_off_switches() -> None:
    """SPEC §25.11 line 4797: "Swappable / off state: locus.life_os.rebalance.enabled. Off → faction weights remain static." """
    provider = DefaultWeeklyFactionRebalanceProvider()

    # Default is enabled
    status = provider.get_status()
    assert status["status"] == "ok"

    # Test locus.weekly_faction_rebalance.enabled off-switch
    config.set("locus.weekly_faction_rebalance.enabled", False)
    off_res = provider.calculate_rebalance()
    assert off_res.get("status_code") == 503
    assert off_res.get("disabled") == "locus.weekly_faction_rebalance.enabled"
    config.set("locus.weekly_faction_rebalance.enabled", True)

    # Test locus.life_os.rebalance.enabled off-switch
    config.set("locus.life_os.rebalance.enabled", False)
    off_res2 = provider.calculate_rebalance()
    assert off_res2.get("status_code") == 503
    assert off_res2.get("disabled") == "locus.life_os.rebalance.enabled"
    config.set("locus.life_os.rebalance.enabled", True)


def test_swappable_rebalance_provider_contract() -> None:
    """SPEC §25.11 line 4796: "Repo vs .locus: rebalance in locus-os/sidecar/life_os/rebalance.py." """
    class CustomRebalanceProvider(BaseWeeklyFactionRebalanceProvider):
        @property
        def name(self) -> str:
            return "custom_rebalancer"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def calculate_rebalance(
            self,
            actual_hours: dict[str, float] | None = None,
            base_weights: dict[str, float] | None = None,
            target_percentages: dict[str, float] | None = None,
            correction_factor: float | None = None,
        ) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_active_weights(self) -> dict[str, Any]:
            return {"status": "ok", "custom_weights": True}

        def record_duration(self, faction: str, duration_hours: float) -> dict[str, Any]:
            return {"status": "ok"}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "provider": self.name}

    custom = CustomRebalanceProvider()
    assert custom.name == "custom_rebalancer"
    assert custom.calculate_rebalance()["custom"] is True
