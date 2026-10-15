"""sidecar/life_os/lag.py - Faction Lag Score and TWS Lag Bonus.

Implements Spec §25.8:
LAG SCORE = cumulative hours a faction is behind its weekly target.
Lag Bonus Rules:
- Lag > 3h -> TWS + 2 for all that faction's tasks
- Lag > 6h -> TWS + 4 (faction in crisis)
- Ahead of target (lag < 0) -> TWS − 1
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from sidecar.life_os.factions import Faction


@dataclass
class FactionLagStatus:
    faction: Faction
    target_hours: float
    actual_hours: float
    lag_hours: float
    tws_lag_bonus: float
    is_in_crisis: bool


def calculate_lag_score(target_hours: float, actual_hours: float) -> float:
    """Calculate cumulative hours a faction is behind target."""
    return round(target_hours - actual_hours, 2)


def get_lag_tws_bonus(lag_hours: float) -> float:
    """Compute TWS bonus adjustment based on faction lag hours.

    Spec §25.8:
    - Lag > 6.0h -> +4.0 (crisis)
    - Lag > 3.0h -> +2.0
    - Lag < 0.0h -> -1.0 (ahead of schedule)
    - Otherwise -> 0.0
    """
    if lag_hours > 6.0:
        return 4.0
    elif lag_hours > 3.0:
        return 2.0
    elif lag_hours < 0.0:
        return -1.0
    return 0.0


def compute_all_faction_lags(
    weekly_targets: dict[Faction, float],
    weekly_actuals: dict[Faction, float],
) -> dict[Faction, FactionLagStatus]:
    """Compute lag statuses and TWS adjustments across all factions."""
    results = {}
    for faction in Faction:
        target = weekly_targets.get(faction, 0.0)
        actual = weekly_actuals.get(faction, 0.0)
        lag = calculate_lag_score(target, actual)
        bonus = get_lag_tws_bonus(lag)
        results[faction] = FactionLagStatus(
            faction=faction,
            target_hours=target,
            actual_hours=actual,
            lag_hours=lag,
            tws_lag_bonus=bonus,
            is_in_crisis=lag > 6.0,
        )
    return results
