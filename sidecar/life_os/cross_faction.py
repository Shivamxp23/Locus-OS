"""
SPEC §25.15 lines 4910-4922: Cross-Faction Efficiency (F-0116 / US-93).
Tasks tagged with multiple factions count toward both targets
(weighted by primary/secondary split). Prevents double-counting.
Swappable / off state: locus.life_os.cross_faction.enabled.
Off -> tasks count toward primary faction only.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.faction_balancer import canonicalize_faction
from sidecar.life_os.goal_stack import VALID_FACTIONS

logger = logging.getLogger("locus.life_os.cross_faction")

DEFAULT_PRIMARY_WEIGHT: float = 0.70
DEFAULT_SECONDARY_WEIGHT: float = 0.30


@dataclass
class FactionSplitResult:
    """
    Split allocation result for a single task.
    Prevents double-counting: sum(allocations.values()) == duration.
    """
    task_id: str
    duration: float
    primary_faction: str
    secondary_factions: List[str]
    allocations: Dict[str, float]
    weights: Dict[str, float]
    cross_faction_enabled: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "duration": self.duration,
            "primary_faction": self.primary_faction,
            "secondary_factions": self.secondary_factions,
            "allocations": self.allocations,
            "weights": self.weights,
            "cross_faction_enabled": self.cross_faction_enabled,
        }


@dataclass
class CrossFactionAggregateResult:
    """
    Aggregated hours/minutes across multiple tasks with cross-faction efficiency applied.
    """
    total_duration: float
    faction_totals: Dict[str, float]
    task_count: int
    cross_faction_task_count: int
    splits: List[FactionSplitResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_duration": self.total_duration,
            "faction_totals": self.faction_totals,
            "task_count": self.task_count,
            "cross_faction_task_count": self.cross_faction_task_count,
            "splits": [s.to_dict() for s in self.splits],
        }


class CrossFactionAllocator:
    """
    SPEC §25.15: Allocator that calculates weighted primary/secondary split for tasks
    tagged with multiple factions, strictly conserving total duration (prevents double-counting).
    """

    SWITCH_KEY = "locus.life_os.cross_faction.enabled"

    def is_cross_faction_enabled(self) -> bool:
        """
        Check if cross-faction efficiency is enabled.
        Off -> tasks count toward primary faction only.
        """
        val = config.get(self.SWITCH_KEY)
        if val is None:
            return True
        return config.is_enabled(self.SWITCH_KEY)

    def calculate_task_split(
        self,
        task_id: str,
        duration: float,
        primary_faction: str,
        secondary_factions: Optional[List[str]] = None,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> FactionSplitResult:
        """
        Split a task's duration across primary and secondary factions.
        Guarantees: sum(allocations.values()) == duration (no double-counting).
        """
        c_primary = canonicalize_faction(primary_faction)
        sec_list = [
            canonicalize_faction(f)
            for f in (secondary_factions or [])
            if canonicalize_faction(f) != c_primary
        ]
        # Deduplicate while preserving order
        dedup_sec: List[str] = []
        for f in sec_list:
            if f not in dedup_sec:
                dedup_sec.append(f)

        enabled = self.is_cross_faction_enabled()

        # If cross-faction is OFF or no secondary factions -> 100% to primary
        if not enabled or not dedup_sec:
            allocations = {c_primary: round(float(duration), 4)}
            weights = {c_primary: 1.0}
            for sf in dedup_sec:
                allocations[sf] = 0.0
                weights[sf] = 0.0

            return FactionSplitResult(
                task_id=task_id,
                duration=float(duration),
                primary_faction=c_primary,
                secondary_factions=dedup_sec,
                allocations=allocations,
                weights=weights,
                cross_faction_enabled=enabled,
            )

        # Cross-faction is ON: calculate weighted split
        weights = {}
        if custom_weights:
            # Normalize custom weights to sum to 1.0
            total_custom = sum(custom_weights.values())
            if total_custom > 0:
                weights = {k: v / total_custom for k, v in custom_weights.items()}
            else:
                weights = self._default_weights(c_primary, dedup_sec)
        else:
            weights = self._default_weights(c_primary, dedup_sec)

        # Allocate duration according to weights, conserving sum
        allocations = {}
        allocated_so_far = 0.0
        keys = list(weights.keys())
        for k in keys[:-1]:
            val = round(duration * weights[k], 4)
            allocations[k] = val
            allocated_so_far += val

        # Final key gets remainder to prevent rounding drift
        last_key = keys[-1]
        allocations[last_key] = round(duration - allocated_so_far, 4)

        return FactionSplitResult(
            task_id=task_id,
            duration=float(duration),
            primary_faction=c_primary,
            secondary_factions=dedup_sec,
            allocations=allocations,
            weights=weights,
            cross_faction_enabled=True,
        )

    def _default_weights(
        self, primary: str, secondaries: List[str]
    ) -> Dict[str, float]:
        """
        Default split: 70% primary, 30% divided equally among secondaries.
        """
        n_sec = len(secondaries)
        if n_sec == 0:
            return {primary: 1.0}

        w_sec_each = DEFAULT_SECONDARY_WEIGHT / n_sec
        weights = {primary: DEFAULT_PRIMARY_WEIGHT}
        for s in secondaries:
            weights[s] = w_sec_each
        return weights

    def aggregate_tasks(
        self,
        tasks: List[Dict[str, Any]],
    ) -> CrossFactionAggregateResult:
        """
        Process a list of task records, splitting each and aggregating faction totals.
        Tasks dict schema:
        {
            "id": str,
            "duration": float,
            "primary_faction": str,
            "secondary_factions": Optional[List[str]],
            "weights": Optional[Dict[str, float]],
        }
        """
        totals: Dict[str, float] = {f: 0.0 for f in VALID_FACTIONS}
        total_duration = 0.0
        cross_count = 0
        splits: List[FactionSplitResult] = []

        for t in tasks:
            tid = t.get("id", "task")
            dur = float(t.get("duration", 0.0))
            p_fac = t.get("primary_faction", "Craft")
            s_facs = t.get("secondary_factions") or []
            weights = t.get("weights")

            split = self.calculate_task_split(
                task_id=tid,
                duration=dur,
                primary_faction=p_fac,
                secondary_factions=s_facs,
                custom_weights=weights,
            )
            splits.append(split)
            total_duration += dur
            if split.secondary_factions and split.cross_faction_enabled:
                cross_count += 1

            for fac, alloc in split.allocations.items():
                c_fac = canonicalize_faction(fac)
                totals[c_fac] = round(totals.get(c_fac, 0.0) + alloc, 4)

        return CrossFactionAggregateResult(
            total_duration=round(total_duration, 4),
            faction_totals=totals,
            task_count=len(tasks),
            cross_faction_task_count=cross_count,
            splits=splits,
        )
