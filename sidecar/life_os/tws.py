"""sidecar/life_os/tws.py - Task Weight Score (TWS) formula.

Implements Spec §25.4 and Decision D-1:
TWS = (Priority * 0.4) + (Urgency * 0.4) + (Difficulty * 0.2) + FactionLagBonus
Priority, Urgency, Difficulty: 1.0 to 10.0 scale.
"""

from __future__ import annotations


def calculate_base_tws(priority: float, urgency: float, difficulty: float) -> float:
    """Calculate base TWS before faction lag bonus.

    Formula: (P * 0.4) + (U * 0.4) + (D * 0.2)
    """
    p = max(1.0, min(10.0, float(priority)))
    u = max(1.0, min(10.0, float(urgency)))
    d = max(1.0, min(10.0, float(difficulty)))
    return round((p * 0.4) + (u * 0.4) + (d * 0.2), 2)


def calculate_tws(
    priority: float,
    urgency: float,
    difficulty: float,
    faction_lag_bonus: float = 0.0,
) -> float:
    """Calculate total TWS including faction lag bonus (D-1)."""
    base = calculate_base_tws(priority, urgency, difficulty)
    return round(base + float(faction_lag_bonus), 2)
