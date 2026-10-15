"""sidecar/life_os/cross_faction.py - Cross-Faction Efficiency & Multi-Tag Accounting.

Implements Spec §25.15:
- Tasks tagged with multiple factions count toward both targets (weighted by primary/secondary split).
- Prevents double-counting by strictly partitioning total logged duration.
- Default split: Primary 70%, Secondary 30% (customizable per task).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from sidecar.life_os.factions import Faction


@dataclass
class CrossFactionAllocation:
    task_id: str
    total_hours: float
    primary_faction: Faction
    secondary_faction: Optional[Faction]
    primary_hours: float
    secondary_hours: float


class CrossFactionAllocator:
    """Calculates weighted hour allocations for multi-faction tasks."""

    def __init__(self, enabled: bool = True, default_primary_ratio: float = 0.7) -> None:
        self.enabled = enabled
        self.default_primary_ratio = default_primary_ratio

    def allocate(
        self,
        task_id: str,
        total_hours: float,
        primary_faction: Faction,
        secondary_faction: Optional[Faction] = None,
        primary_ratio: Optional[float] = None,
    ) -> CrossFactionAllocation:
        """Partition task duration across primary and secondary factions."""
        if not self.enabled or not secondary_faction or primary_faction == secondary_faction:
            return CrossFactionAllocation(
                task_id=task_id,
                total_hours=total_hours,
                primary_faction=primary_faction,
                secondary_faction=None,
                primary_hours=total_hours,
                secondary_hours=0.0,
            )

        ratio = primary_ratio if primary_ratio is not None else self.default_primary_ratio
        ratio = max(0.5, min(0.95, ratio))

        prim_hrs = round(total_hours * ratio, 2)
        sec_hrs = round(total_hours - prim_hrs, 2)

        return CrossFactionAllocation(
            task_id=task_id,
            total_hours=total_hours,
            primary_faction=primary_faction,
            secondary_faction=secondary_faction,
            primary_hours=prim_hrs,
            secondary_hours=sec_hrs,
        )

    def accumulate_allocations(
        self,
        allocations: list[CrossFactionAllocation],
    ) -> dict[Faction, float]:
        """Aggregate total hours across factions from multiple cross-faction tasks."""
        totals: dict[Faction, float] = {f: 0.0 for f in Faction}
        for alloc in allocations:
            totals[alloc.primary_faction] = round(totals[alloc.primary_faction] + alloc.primary_hours, 2)
            if alloc.secondary_faction:
                totals[alloc.secondary_faction] = round(totals[alloc.secondary_faction] + alloc.secondary_hours, 2)
        return totals
