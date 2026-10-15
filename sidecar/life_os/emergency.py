"""sidecar/life_os/emergency.py - Emergency Task Injection.

Implements Spec §25.9:
EMERGENCY INJECTION:
- Tasks tagged EMERGENCY bypass standard TWS ordering.
- Inserted at the top of the schedule.
- Respects only faction crisis hierarchy: Health > Leverage > Craft > Expression.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sidecar.life_os.factions import Faction
from sidecar.life_os.goal_stack import GoalTask


# Crisis hierarchy priority weights
CRISIS_HIERARCHY: dict[Faction, int] = {
    Faction.HEALTH: 4,
    Faction.LEVERAGE: 3,
    Faction.CRAFT: 2,
    Faction.EXPRESSION: 1,
}


@dataclass
class ScheduledTaskEntry:
    task: GoalTask
    faction: Faction
    tws: float
    is_emergency: bool = False


class EmergencyInjector:
    """Manages emergency task injection and priority queue ordering."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def order_schedule(
        self,
        normal_entries: list[ScheduledTaskEntry],
        emergency_entries: list[ScheduledTaskEntry],
    ) -> list[ScheduledTaskEntry]:
        """Order tasks into dispatch schedule.

        If enabled, emergency tasks are sorted by crisis hierarchy
        (Health > Leverage > Craft > Expression) then TWS, and placed at top.
        Normal tasks follow, sorted strictly by descending TWS.
        """
        if not self.enabled:
            # If disabled, treat all tasks identically by TWS
            combined = normal_entries + emergency_entries
            return sorted(combined, key=lambda x: x.tws, reverse=True)

        sorted_emergencies = sorted(
            emergency_entries,
            key=lambda x: (CRISIS_HIERARCHY.get(x.faction, 0), x.tws),
            reverse=True,
        )

        sorted_normals = sorted(
            normal_entries,
            key=lambda x: x.tws,
            reverse=True,
        )

        return sorted_emergencies + sorted_normals
