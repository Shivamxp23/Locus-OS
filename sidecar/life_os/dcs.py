"""
SPEC §25.2 line 4592: Daily Capacity Score (DCS).
DCS = ((E + M + S) / 3) × (1 − ST/20)
    E = Energy (1-10), M = Mood (1-10), S = Sleep quality (1-10), ST = Stress (1-10)
    Output: 0.0–10.0 float.
    If no check-in today (1 day since): apply staleness penalty (score × 0.9).
    If no check-in in 3+ days: default to baseline (5,5,5,7) & queue STALE_CHECKIN alert.
"""
from __future__ import annotations

from typing import Optional
from sidecar.life_os.modes import resolve_operating_mode
from sidecar.providers.life_os import CheckInInput, DCSResult


def calculate_dcs(
    energy: int = 5,
    mood: int = 5,
    sleep: int = 5,
    stress: int = 5,
    days_since_last_checkin: int = 0,
) -> DCSResult:
    """
    Compute Daily Capacity Score according to SPEC §25.2.
    """
    staleness_applied = False
    alert: Optional[str] = None

    if days_since_last_checkin >= 3:
        # Default to baseline (5, 5, 5, 7) and queue alert
        e, m, s, st = 5, 5, 5, 7
        staleness_applied = True
        alert = "STALE_CHECKIN"
    else:
        # Clamp inputs 1 to 10
        e = max(1, min(10, int(energy)))
        m = max(1, min(10, int(mood)))
        s = max(1, min(10, int(sleep)))
        st = max(1, min(10, int(stress)))

    # Base formula: ((E + M + S) / 3) * (1 - ST / 20)
    raw = ((e + m + s) / 3.0) * (1.0 - (st / 20.0))

    if days_since_last_checkin == 1 or days_since_last_checkin == 2:
        raw *= 0.9
        staleness_applied = True

    dcs = round(max(0.0, min(10.0, raw)), 2)
    mode, mode_constraints = resolve_operating_mode(dcs)

    return DCSResult(
        dcs=dcs,
        mode=mode,
        staleness_applied=staleness_applied,
        alert=alert,
        mode_constraints={
            "max_difficulty": mode_constraints.max_difficulty,
            "max_discretionary_tasks": mode_constraints.max_discretionary_tasks,
            "description": mode_constraints.description,
        },
    )


def calculate_dcs_from_input(checkin: CheckInInput) -> DCSResult:
    """Helper accepting CheckInInput data class."""
    return calculate_dcs(
        energy=checkin.energy,
        mood=checkin.mood,
        sleep=checkin.sleep,
        stress=checkin.stress,
        days_since_last_checkin=checkin.days_since_last_checkin,
    )
