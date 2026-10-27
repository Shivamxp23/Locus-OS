"""
SPEC §25.8 lines 4719-4739: Lag Score + TWS Lag Bonus.
Logic:
    LAG SCORE = cumulative hours a faction is behind its weekly target.
    Lag > 3h -> TWS + 2 for all that faction's tasks
    Lag > 6h -> TWS + 4 (faction in crisis)
    Ahead of target -> TWS - 1
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger("locus.life_os.lag")


@dataclass
class FactionLagReport:
    faction: str
    target_hours: float
    actual_hours: float
    lag_hours: float
    tws_lag_bonus: float
    is_crisis: bool
    is_ahead: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "faction": self.faction,
            "target_hours": self.target_hours,
            "actual_hours": self.actual_hours,
            "lag_hours": round(self.lag_hours, 2),
            "tws_lag_bonus": self.tws_lag_bonus,
            "is_crisis": self.is_crisis,
            "is_ahead": self.is_ahead,
        }


def calculate_lag_score(target_hours: float, actual_hours: float) -> float:
    """
    Cumulative hours a faction is behind target:
    lag = target_hours - actual_hours.
    Positive indicates behind target; negative indicates ahead of target.
    """
    return float(target_hours) - float(actual_hours)


def calculate_tws_lag_bonus(lag_hours: float) -> float:
    """
    Calculate TWS bonus according to §25.8:
    - Lag > 6h -> +4.0 (crisis)
    - Lag > 3h -> +2.0
    - Ahead of target (lag < 0) -> -1.0
    - Otherwise (0 <= lag <= 3) -> 0.0
    """
    if lag_hours > 6.0:
        return 4.0
    if lag_hours > 3.0:
        return 2.0
    if lag_hours < 0.0:
        return -1.0
    return 0.0


def compute_faction_lag_report(
    faction: str,
    target_hours: float,
    actual_hours: float,
) -> FactionLagReport:
    lag = calculate_lag_score(target_hours, actual_hours)
    bonus = calculate_tws_lag_bonus(lag)
    return FactionLagReport(
        faction=faction,
        target_hours=target_hours,
        actual_hours=actual_hours,
        lag_hours=lag,
        tws_lag_bonus=bonus,
        is_crisis=lag > 6.0,
        is_ahead=lag < 0.0,
    )
