"""sidecar/life_os/__init__.py - Locus Life OS core modules."""

from sidecar.life_os.dcs import calculate_dcs
from sidecar.life_os.factions import (
    FACTION_TARGET_PERCENTAGES,
    Faction,
    calculate_faction_lag,
    calculate_faction_lag_bonus,
)
from sidecar.life_os.modes import OperatingMode, resolve_operating_mode
from sidecar.life_os.tws import calculate_base_tws, calculate_tws

__all__ = [
    "Faction",
    "FACTION_TARGET_PERCENTAGES",
    "calculate_faction_lag",
    "calculate_faction_lag_bonus",
    "calculate_dcs",
    "OperatingMode",
    "resolve_operating_mode",
    "calculate_base_tws",
    "calculate_tws",
]
