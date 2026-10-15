"""sidecar/life_os/faction_balancer.py - Faction Balance Constraint Solver.

Implements Spec §25.12 (Step 4):
Faction Targets & Tolerances:
- Craft (Work / Engineering):     Target 40% (Tolerance ±5%)
- Health (Physical / Mental):     Target 25% (Tolerance ±5%)
- Leverage (Systems / Wealth):    Target 20% (Tolerance ±5%)
- Expression (Writing / Art):     Target 15% (Tolerance ±5%)

Assignment Rule:
Greedily assign highest TWS task to next open block UNLESS assigning that task causes that faction's
weekly allocated hours to exceed Target + Tolerance while an under-represented faction has eligible tasks waiting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from sidecar.life_os.factions import Faction


# Standard Spec §25.12 Step 4 targets and tolerances
SCHEDULER_FACTION_TARGETS: dict[Faction, float] = {
    Faction.CRAFT: 0.40,
    Faction.HEALTH: 0.25,
    Faction.LEVERAGE: 0.20,
    Faction.EXPRESSION: 0.15,
}

FACTION_TOLERANCE: float = 0.05  # ±5%


@dataclass
class FactionAllocationState:
    current_hours: float
    total_hours: float

    @property
    def current_pct(self) -> float:
        return (self.current_hours / self.total_hours) if self.total_hours > 0 else 0.0


class FactionBalancer:
    """Mathematical constraint solver for weekly faction balance."""

    def __init__(
        self,
        targets: Optional[dict[Faction, float]] = None,
        tolerance: float = FACTION_TOLERANCE,
    ) -> None:
        self.targets = targets or dict(SCHEDULER_FACTION_TARGETS)
        self.tolerance = tolerance

    def can_assign_task(
        self,
        faction: Faction,
        task_duration_hours: float,
        current_allocations: dict[Faction, float],
        waiting_factions: set[Faction],
    ) -> bool:
        """Check if assigning task violates faction tolerance constraint while other factions lag."""
        total_curr = sum(current_allocations.values())
        proj_total = total_curr + task_duration_hours
        if proj_total <= 0:
            return True

        curr_faction_hrs = current_allocations.get(faction, 0.0)
        proj_faction_hrs = curr_faction_hrs + task_duration_hours
        proj_pct = proj_faction_hrs / proj_total

        target_pct = self.targets.get(faction, 0.25)
        max_allowed_pct = target_pct + self.tolerance

        # If assignment would exceed max allowed tolerance
        if proj_pct > max_allowed_pct:
            # Check if any under-represented faction is waiting
            for other in waiting_factions:
                if other != faction:
                    other_hrs = current_allocations.get(other, 0.0)
                    other_pct = other_hrs / proj_total
                    other_tgt = self.targets.get(other, 0.25)
                    # If other faction is below its target - tolerance
                    if other_pct < (other_tgt - self.tolerance):
                        return False

        return True

    def get_most_starved_faction(
        self,
        current_allocations: dict[Faction, float],
        eligible_factions: set[Faction],
    ) -> Optional[Faction]:
        """Find the faction furthest below its target percentage."""
        if not eligible_factions:
            return None
        total_curr = sum(current_allocations.values())
        max_deficit = -1.0
        most_starved = None

        for faction in eligible_factions:
            curr_hrs = current_allocations.get(faction, 0.0)
            curr_pct = (curr_hrs / total_curr) if total_curr > 0 else 0.0
            tgt_pct = self.targets.get(faction, 0.25)
            deficit = tgt_pct - curr_pct
            if deficit > max_deficit:
                max_deficit = deficit
                most_starved = faction

        return most_starved
