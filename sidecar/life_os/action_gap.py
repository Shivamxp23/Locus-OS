"""sidecar/life_os/action_gap.py - Action Gap Tracking.

Implements Spec §25.6:
ACTION GAP = declared_priority − (actual_hrs / target_hrs × 10)
Where:
- declared_priority: 1.0 to 10.0 scale reflecting relative importance of faction
- actual_hrs: hours logged in this faction during the period
- target_hrs: expected allocation hours
- Action Gap > 5.0 -> Alert: faction is being neglected relative to declared priority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sidecar.life_os.factions import Faction


@dataclass
class ActionGapAlert:
    faction: Faction
    declared_priority: float
    actual_hours: float
    target_hours: float
    action_gap: float
    severity: str  # "warning" (>5.0) or "critical" (>7.5)
    message: str


def calculate_action_gap(
    declared_priority: float,
    actual_hours: float,
    target_hours: float,
) -> float:
    """Calculate the Action Gap score.

    Formula: declared_priority - (actual_hrs / target_hrs * 10)
    """
    if target_hours <= 0:
        ratio = 0.0
    else:
        ratio = actual_hours / target_hours
    gap = declared_priority - (ratio * 10.0)
    return round(gap, 2)


def evaluate_faction_action_gaps(
    faction_metrics: dict[Faction, tuple[float, float, float]],
    threshold: float = 5.0,
) -> list[ActionGapAlert]:
    """Evaluate action gaps across factions.

    faction_metrics: map of Faction -> (declared_priority, actual_hours, target_hours)
    """
    alerts = []
    for faction, (priority, actual, target) in faction_metrics.items():
        gap = calculate_action_gap(priority, actual, target)
        if gap > threshold:
            sev = "critical" if gap > 7.5 else "warning"
            msg = (
                f"Action Gap alert for {faction.value}: gap={gap:.1f} (declared priority {priority:.1f}, "
                f"delivered {actual:.1f}h of {target:.1f}h target). Faction is severely neglected."
            )
            alerts.append(
                ActionGapAlert(
                    faction=faction,
                    declared_priority=priority,
                    actual_hours=actual,
                    target_hours=target,
                    action_gap=gap,
                    severity=sev,
                    message=msg,
                )
            )
    return alerts
