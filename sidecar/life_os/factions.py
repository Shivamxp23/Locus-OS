"""
SPEC §25.1 line 4566: Four Factions Framework.
Health/Stability (25%), Leverage/Money (25%), Craft/Skills (30%), Expression/Explore (20%).
Crisis priority hierarchy: Health > Leverage > Craft > Expression.
"""
from __future__ import annotations

from typing import Dict, List
from sidecar.providers.life_os import FactionType

DEFAULT_FACTION_TARGETS: Dict[str, float] = {
    FactionType.HEALTH.value: 0.25,
    FactionType.LEVERAGE.value: 0.25,
    FactionType.CRAFT.value: 0.30,
    FactionType.EXPRESSION.value: 0.20,
}

FACTION_CRISIS_HIERARCHY: List[str] = [
    FactionType.HEALTH.value,
    FactionType.LEVERAGE.value,
    FactionType.CRAFT.value,
    FactionType.EXPRESSION.value,
]


def compute_faction_lag(target_hours: float, actual_hours: float) -> float:
    """
    Compute lag score in hours for a faction against target hours.
    Lag > 0 means behind target; lag < 0 means ahead of target.
    """
    return round(float(target_hours) - float(actual_hours), 2)


def compute_faction_lag_from_total(
    faction: str, actual_hours: float, total_hours: float, custom_targets: Dict[str, float] | None = None
) -> float:
    """
    Compute faction lag given total logged hours across all factions.
    """
    targets = custom_targets or DEFAULT_FACTION_TARGETS
    target_pct = targets.get(faction, 0.25)
    target_hours = float(total_hours) * target_pct
    return compute_faction_lag(target_hours, actual_hours)
