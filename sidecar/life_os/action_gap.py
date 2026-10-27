"""
SPEC §25.6 lines 4679-4697: Action Gap Tracking.
Formula:
    ACTION GAP = declared_priority - (actual_hrs / target_hrs * 10)
Alert condition:
    Action Gap > 5.0 -> alert: faction is being neglected relative to its declared importance.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger("locus.life_os.action_gap")

ALERT_THRESHOLD = 5.0


@dataclass
class FactionActionGap:
    faction: str
    declared_priority: float
    actual_hours: float
    target_hours: float
    action_gap: float
    alert: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "faction": self.faction,
            "declared_priority": self.declared_priority,
            "actual_hours": self.actual_hours,
            "target_hours": self.target_hours,
            "action_gap": round(self.action_gap, 2),
            "alert": self.alert,
            "message": self.message,
        }


def calculate_action_gap(declared_priority: float, actual_hours: float, target_hours: float) -> float:
    """
    Calculate single action gap score.
    If target_hours <= 0, return declared_priority.
    """
    if target_hours <= 0:
        return float(declared_priority)
    ratio = float(actual_hours) / float(target_hours)
    return float(declared_priority) - (ratio * 10.0)


def evaluate_faction_action_gaps(
    factions_data: Dict[str, Dict[str, float]],
    alert_threshold: float = ALERT_THRESHOLD,
) -> List[FactionActionGap]:
    """
    Evaluate action gaps across factions data:
    factions_data = {
        "Craft": {"declared_priority": 8.0, "actual_hours": 10.0, "target_hours": 20.0},
        ...
    }
    """
    results: List[FactionActionGap] = []
    for faction, data in factions_data.items():
        declared = float(data.get("declared_priority", 5.0))
        actual = float(data.get("actual_hours", 0.0))
        target = float(data.get("target_hours", 10.0))

        gap = calculate_action_gap(declared, actual, target)
        is_alert = gap > alert_threshold
        msg = (
            f"ALERT: {faction} is being neglected relative to its declared importance (Action Gap {gap:.1f} > {alert_threshold})"
            if is_alert
            else f"{faction} action gap normal ({gap:.1f})"
        )
        results.append(
            FactionActionGap(
                faction=faction,
                declared_priority=declared,
                actual_hours=actual,
                target_hours=target,
                action_gap=gap,
                alert=is_alert,
                message=msg,
            )
        )
    return results
