"""
SPEC §25.3 line 4614: Five Operating Modes.
SURVIVAL:  DCS 0.0–2.0  — non-negotiables only; no discretionary tasks
RECOVERY:  DCS 2.1–4.0  — D ≤ 4 only; max 2 discretionary tasks
NORMAL:    DCS 4.1–6.0  — D ≤ 7; 3–4 tasks; ≥2 factions get attention
DEEP WORK: DCS 6.1–8.0  — D ≤ 9; single 2–3h uninterrupted highest-TWS block
PEAK:      DCS 8.1–10.0 — most ambitious task first; 5–6 tasks
"""
from __future__ import annotations

from typing import Dict, Tuple
from sidecar.providers.life_os import ModeConstraints, OperatingMode

OPERATING_MODE_RULES: Dict[OperatingMode, ModeConstraints] = {
    OperatingMode.SURVIVAL: ModeConstraints(
        mode=OperatingMode.SURVIVAL,
        dcs_range=(0.0, 2.0),
        max_difficulty=2,
        max_discretionary_tasks=0,
        description="non-negotiables only; no discretionary tasks",
    ),
    OperatingMode.RECOVERY: ModeConstraints(
        mode=OperatingMode.RECOVERY,
        dcs_range=(2.1, 4.0),
        max_difficulty=4,
        max_discretionary_tasks=2,
        description="D <= 4 only; max 2 discretionary tasks",
    ),
    OperatingMode.NORMAL: ModeConstraints(
        mode=OperatingMode.NORMAL,
        dcs_range=(4.1, 6.0),
        max_difficulty=7,
        max_discretionary_tasks=4,
        description="D <= 7; 3-4 tasks; >=2 factions get attention",
    ),
    OperatingMode.DEEP_WORK: ModeConstraints(
        mode=OperatingMode.DEEP_WORK,
        dcs_range=(6.1, 8.0),
        max_difficulty=9,
        max_discretionary_tasks=None,
        description="D <= 9; single 2-3h uninterrupted highest-TWS block",
    ),
    OperatingMode.PEAK: ModeConstraints(
        mode=OperatingMode.PEAK,
        dcs_range=(8.1, 10.0),
        max_difficulty=10,
        max_discretionary_tasks=6,
        description="most ambitious task first; 5-6 tasks",
    ),
}


def resolve_operating_mode(dcs: float) -> Tuple[OperatingMode, ModeConstraints]:
    """
    Map Daily Capacity Score (0.0 to 10.0) to one of Five Operating Modes.
    """
    score = max(0.0, min(10.0, float(dcs)))
    if score <= 2.0:
        mode = OperatingMode.SURVIVAL
    elif score <= 4.0:
        mode = OperatingMode.RECOVERY
    elif score <= 6.0:
        mode = OperatingMode.NORMAL
    elif score <= 8.0:
        mode = OperatingMode.DEEP_WORK
    else:
        mode = OperatingMode.PEAK

    return mode, OPERATING_MODE_RULES[mode]
