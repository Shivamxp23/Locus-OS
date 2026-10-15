"""sidecar/life_os.py - Locus Life OS unified package.

Implements Spec §25.1-§25.4 and Decisions D-1, D-3:
- Four Factions Framework (Health, Leverage, Craft, Expression).
- Daily Capacity Score (DCS) & 5 Operating Modes.
- Task Weight Score (TWS) formula with Faction Lag Bonus.
- Three-Layer Goal Stack multi-scale roll-up.
"""

from sidecar.life_os.dcs import calculate_dcs
from sidecar.life_os.factions import (
    FACTION_TARGET_PERCENTAGES,
    Faction,
    calculate_faction_lag,
    calculate_faction_lag_bonus,
)
from sidecar.life_os.modes import OperatingMode, resolve_operating_mode
from sidecar.life_os.tws import calculate_base_tws, calculate_tws
from sidecar.task_scoring import (
    GoalScale,
    Task,
    TaskPriorityScorer,
    TaskScorerProvider,
)

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
    "GoalScale",
    "Task",
    "TaskPriorityScorer",
    "TaskScorerProvider",
]
