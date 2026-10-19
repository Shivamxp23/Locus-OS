"""
Life OS core modules: TWS, DCS, Operating Modes, Factions, and Provider.
"""
from __future__ import annotations

from sidecar.life_os.dcs import calculate_dcs
from sidecar.life_os.factions import (
    DEFAULT_FACTION_TARGETS,
    FACTION_CRISIS_HIERARCHY,
    compute_faction_lag,
)
from sidecar.life_os.modes import OPERATING_MODE_RULES, resolve_operating_mode
from sidecar.life_os.provider import LifeOSProvider
from sidecar.life_os.tws import calculate_tws, log_post_task

__all__ = [
    "DEFAULT_FACTION_TARGETS",
    "FACTION_CRISIS_HIERARCHY",
    "LifeOSProvider",
    "OPERATING_MODE_RULES",
    "calculate_dcs",
    "calculate_tws",
    "compute_faction_lag",
    "log_post_task",
    "resolve_operating_mode",
]
