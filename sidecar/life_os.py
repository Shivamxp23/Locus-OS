"""
SPEC §25.1-§25.4 / §03 line 15 / F-0055: Concrete Life OS Provider.
Implements LifeOSProvider adhering to BaseLifeOSProvider for Task Weight Score (TWS),
Daily Capacity Score (DCS), Operating Modes, and Faction balance.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.dcs import calculate_dcs_from_input
from sidecar.life_os.factions import (
    DEFAULT_FACTION_TARGETS,
    FACTION_CRISIS_HIERARCHY,
    compute_faction_lag,
)
from sidecar.life_os.modes import resolve_operating_mode
from sidecar.life_os.tws import calculate_tws_from_input
from sidecar.providers.life_os import (
    BaseLifeOSProvider,
    CheckInInput,
    DCSResult,
    FactionType,
    GoalStackLevel,
    ModeConstraints,
    OperatingMode,
    TaskScoreInput,
    TaskScoreResult,
)


class LifeOSProvider(BaseLifeOSProvider):
    """
    Default Life OS provider implementing TWS, DCS, Operating Modes, and Factions.
    Swappable and switchable via locus.life_os.enabled.
    """

    def __init__(self, name: str = "default_life_os") -> None:
        super().__init__(name=name)
        self._initialized: bool = False
        self._last_active: float = time.time()

    def is_enabled(self) -> bool:
        """Check whether Life OS features are enabled in configuration."""
        return config.get("locus.life_os.enabled", True) is not False

    def initialize(self) -> None:
        """Initialize Life OS caches and configurations."""
        self._initialized = True
        self._last_active = time.time()

    def health_check(self) -> Dict[str, Any]:
        """Return provider health status, latency, and registered submodules."""
        start = time.time()
        is_up = self.is_enabled()
        latency = (time.time() - start) * 1000.0

        return {
            "status": "healthy" if is_up else "disabled",
            "latency_ms": round(latency, 2),
            "initialized": self._initialized,
            "provider": self.name,
            "factions": list(DEFAULT_FACTION_TARGETS.keys()),
            "crisis_hierarchy": FACTION_CRISIS_HIERARCHY,
        }

    def shutdown(self) -> None:
        """Gracefully release Life OS resources."""
        self._initialized = False

    def calculate_tws(self, task_input: TaskScoreInput) -> TaskScoreResult:
        """Calculate Task Weight Score according to D-1 Option A."""
        self._last_active = time.time()
        return calculate_tws_from_input(task_input)

    def calculate_dcs(self, checkin: CheckInInput) -> DCSResult:
        """Calculate Daily Capacity Score and map to operating mode."""
        self._last_active = time.time()
        return calculate_dcs_from_input(checkin)

    def resolve_mode(self, dcs: float) -> Tuple[OperatingMode, ModeConstraints]:
        """Resolve operating mode given Daily Capacity Score."""
        return resolve_operating_mode(dcs)

    def compute_faction_lag(
        self, faction: str, target_pct: float, actual_hours: float, total_hours: float
    ) -> float:
        """Compute lag hours for a faction against total logged hours."""
        target_hours = float(total_hours) * float(target_pct)
        return compute_faction_lag(target_hours, actual_hours)

    def score_task_at_scale(
        self,
        priority: int,
        urgency: int,
        difficulty: int,
        faction: Optional[str] = None,
        faction_lag_hours: float = 0.0,
        scale: GoalStackLevel = GoalStackLevel.DAILY,
        child_scores: Optional[List[float]] = None,
    ) -> TaskScoreResult:
        """Convenience method for calculating TWS directly from primitive parameters."""
        task_input = TaskScoreInput(
            priority=priority,
            urgency=urgency,
            difficulty=difficulty,
            faction=faction,
            faction_lag_hours=faction_lag_hours,
            scale=scale,
            child_scores=child_scores,
        )
        return self.calculate_tws(task_input)
