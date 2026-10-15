"""sidecar/life_os/modes.py - Five Operating Modes of Locus OS.

Implements Spec §25.3:
SURVIVAL:  DCS 0.0–2.0  — non-negotiables only
RECOVERY:  DCS 2.1–4.0  — D <= 4 only; max 2 discretionary tasks
NORMAL:    DCS 4.1–6.0  — D <= 7; 3–4 tasks; >=2 factions get attention
DEEP WORK: DCS 6.1–8.0  — D <= 9; single 2–3h uninterrupted highest-TWS block
PEAK:      DCS 8.1–10.0 — most ambitious task first; 5–6 tasks
"""

from __future__ import annotations

from enum import Enum


class OperatingMode(str, Enum):
    """The 5 Operating Modes mapped to Daily Capacity Score."""

    SURVIVAL = "SURVIVAL"
    RECOVERY = "RECOVERY"
    NORMAL = "NORMAL"
    DEEP_WORK = "DEEP_WORK"
    PEAK = "PEAK"


def resolve_operating_mode(dcs: float) -> OperatingMode:
    """Map a Daily Capacity Score (0.0 - 10.0) to its OperatingMode."""
    score = float(dcs)
    if score <= 2.0:
        return OperatingMode.SURVIVAL
    elif score <= 4.0:
        return OperatingMode.RECOVERY
    elif score <= 6.0:
        return OperatingMode.NORMAL
    elif score <= 8.0:
        return OperatingMode.DEEP_WORK
    else:
        return OperatingMode.PEAK
