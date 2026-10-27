"""
SPEC §25.15 lines 4910-4922: Cross-Faction Efficiency Provider (F-0116 / US-93).
Modular off-switches:
- locus.cross_faction_efficiency.enabled (returns HTTP 503 when off)
- locus.life_os.cross_faction.enabled (when off, tasks count toward primary faction only)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.cross_faction import (
    CrossFactionAggregateResult,
    CrossFactionAllocator,
    FactionSplitResult,
)

logger = logging.getLogger("locus.providers.cross_faction")


class BaseCrossFactionEfficiencyProvider(ABC):
    """
    Abstract contract for Cross-Faction Efficiency Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def calculate_task_split(
        self,
        task_id: str,
        duration: float,
        primary_faction: str,
        secondary_factions: Optional[List[str]] = None,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Split a task's duration across multiple factions without double-counting."""

    @abstractmethod
    def aggregate_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Aggregate durations across tasks applying cross-faction efficiency."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultCrossFactionEfficiencyProvider(BaseCrossFactionEfficiencyProvider):
    """
    Default provider wrapping CrossFactionAllocator with modular off-switch enforcement.
    """

    def __init__(
        self,
        allocator: Optional[CrossFactionAllocator] = None,
    ) -> None:
        self.allocator = allocator or CrossFactionAllocator()

    @property
    def name(self) -> str:
        return "default_cross_faction_efficiency_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        switch = "locus.cross_faction_efficiency.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def calculate_task_split(
        self,
        task_id: str,
        duration: float,
        primary_faction: str,
        secondary_factions: Optional[List[str]] = None,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Cross-faction efficiency is disabled",
                "disabled": switch,
            }

        res = self.allocator.calculate_task_split(
            task_id=task_id,
            duration=duration,
            primary_faction=primary_faction,
            secondary_factions=secondary_factions,
            custom_weights=custom_weights,
        )
        return res.to_dict()

    def aggregate_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Cross-faction efficiency is disabled",
                "disabled": switch,
            }

        res = self.allocator.aggregate_tasks(tasks=tasks)
        return res.to_dict()

    def get_status(self) -> Dict[str, Any]:
        master_enabled, master_switch = self.is_feature_enabled()
        subsystem_enabled = self.allocator.is_cross_faction_enabled()
        return {
            "provider": self.name,
            "master_enabled": master_enabled,
            "master_switch": master_switch,
            "subsystem_enabled": subsystem_enabled,
            "subsystem_switch": self.allocator.SWITCH_KEY,
        }
