"""sidecar/life_os/factions.py - Four Factions Framework & Lag Bonus.

Implements Spec §25.1 and Errata Decision D-1:
- Four Factions: Health, Leverage, Craft, Expression.
- Weekly target allocations: Health 25%, Leverage 25%, Craft 30%, Expression 20%.
- Faction Lag Bonus: +2 if lag >3h, +4 if lag >6h, -1 if ahead of target.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class Faction(str, Enum):
    """The Four Factions of Locus Life OS."""

    HEALTH = "Health"
    LEVERAGE = "Leverage"
    CRAFT = "Craft"
    EXPRESSION = "Expression"


# Target weekly allocation ratios (Spec §25.1 / Appendix C)
FACTION_TARGET_PERCENTAGES: dict[Faction, float] = {
    Faction.HEALTH: 0.25,
    Faction.LEVERAGE: 0.25,
    Faction.CRAFT: 0.30,
    Faction.EXPRESSION: 0.20,
}


def calculate_faction_lag(target_hours: float, actual_hours: float) -> float:
    """Calculate the lag hours behind target allocation.

    Positive means behind target (lagging). Negative means ahead of target.
    """
    return target_hours - actual_hours


def calculate_faction_lag_bonus(lag_hours: float) -> float:
    """Compute the TWS lag adjustment bonus based on lag hours.

    Spec §25.4 & D-1:
    - lag > 6h -> +4.0 (crisis)
    - lag > 3h -> +2.0
    - lag < 0h -> -1.0 (ahead of target)
    - otherwise -> 0.0
    """
    if lag_hours > 6.0:
        return 4.0
    elif lag_hours > 3.0:
        return 2.0
    elif lag_hours < 0.0:
        return -1.0
    return 0.0
