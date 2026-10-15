"""sidecar/life_os/dcs.py - Daily Capacity Score (DCS) calculation.

Implements Spec §25.2:
DCS = ((E + M + S) / 3) * (1 - ST / 20)
Where E=Energy, M=Mood, S=Sleep, ST=Stress (each 1-10 scale).
Clamped to [0.0, 10.0].
"""

from __future__ import annotations


def calculate_dcs(
    energy: float,
    mood: float,
    sleep: float,
    stress: float,
    stale_checkin: bool = False,
) -> float:
    """Calculate Daily Capacity Score (0.0 to 10.0 float).

    Parameters:
    - energy: 1-10
    - mood: 1-10
    - sleep: 1-10
    - stress: 1-10
    - stale_checkin: apply 0.9 staleness penalty if no check-in today
    """
    e = max(1.0, min(10.0, float(energy)))
    m = max(1.0, min(10.0, float(mood)))
    s = max(1.0, min(10.0, float(sleep)))
    st = max(1.0, min(10.0, float(stress)))

    base = (e + m + s) / 3.0
    factor = 1.0 - (st / 20.0)
    score = base * factor

    if stale_checkin:
        score *= 0.9

    return max(0.0, min(10.0, round(score, 2)))
