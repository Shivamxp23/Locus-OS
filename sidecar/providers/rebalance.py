"""
SPEC §25.11 lines 4778-4800: Weekly Faction Rebalance Provider (F-0113 / US-89).
Modular off-switches returning HTTP 503:
- locus.weekly_faction_rebalance.enabled
- locus.life_os.rebalance.enabled
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from sidecar import config
from sidecar.life_os.rebalance import (
    RebalanceResult,
    STANDARD_FACTION_TARGETS,
    WeeklyFactionRebalancer,
)

logger = logging.getLogger("locus.providers.rebalance")


class BaseWeeklyFactionRebalanceProvider(ABC):
    """Abstract contract for weekly faction rebalance provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check modular off-switches."""

    @abstractmethod
    def calculate_rebalance(
        self,
        actual_hours: Optional[Dict[str, float]] = None,
        base_weights: Optional[Dict[str, float]] = None,
        target_percentages: Optional[Dict[str, float]] = None,
        correction_factor: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Calculate weekly rebalance and update next week weights."""

    @abstractmethod
    def get_active_weights(self) -> Dict[str, Any]:
        """Return currently active faction scheduling weights."""

    @abstractmethod
    def record_duration(self, faction: str, duration_hours: float) -> Dict[str, Any]:
        """Record task duration for a faction."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status."""


class DefaultWeeklyFactionRebalanceProvider(BaseWeeklyFactionRebalanceProvider):
    """
    Default provider wrapping WeeklyFactionRebalancer with modular off-switch enforcement.
    """

    def __init__(self, rebalancer: Optional[WeeklyFactionRebalancer] = None) -> None:
        self.rebalancer = rebalancer or WeeklyFactionRebalancer()

    @property
    def name(self) -> str:
        return "default_weekly_faction_rebalance_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        for switch in (
            "locus.weekly_faction_rebalance.enabled",
            "locus.life_os.rebalance.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def calculate_rebalance(
        self,
        actual_hours: Optional[Dict[str, float]] = None,
        base_weights: Optional[Dict[str, float]] = None,
        target_percentages: Optional[Dict[str, float]] = None,
        correction_factor: Optional[float] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Weekly faction rebalance is disabled",
                "disabled": switch,
            }

        result = self.rebalancer.calculate_rebalance(
            actual_hours=actual_hours,
            base_weights=base_weights,
            target_percentages=target_percentages,
            correction_factor=correction_factor,
        )
        return {
            "status": "ok",
            "rebalance": result.to_dict(),
        }

    def get_active_weights(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Weekly faction rebalance is disabled",
                "disabled": switch,
            }
        return {
            "status": "ok",
            "weights": self.rebalancer.get_active_weights(),
        }

    def record_duration(self, faction: str, duration_hours: float) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Weekly faction rebalance is disabled",
                "disabled": switch,
            }
        self.rebalancer.record_duration(faction, duration_hours)
        return {
            "status": "ok",
            "durations": self.rebalancer.get_logged_durations(),
        }

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Weekly faction rebalance is disabled",
                "disabled": switch,
            }
        return {
            "status": "ok",
            "provider": self.name,
            "enabled": True,
            "active_weights": self.rebalancer.get_active_weights(),
            "logged_durations": self.rebalancer.get_logged_durations(),
            "default_targets": dict(STANDARD_FACTION_TARGETS),
        }


# Canonical alias
WeeklyFactionRebalanceProvider = DefaultWeeklyFactionRebalanceProvider
