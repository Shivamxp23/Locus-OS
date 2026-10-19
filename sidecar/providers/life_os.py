"""
SPEC §25.1-§25.4 / §03 line 15: Base Life OS Provider Interface.
Declares abstract contracts for Task Weight Score (TWS), Daily Capacity Score (DCS),
Operating Mode resolution, and Faction balance tracking.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class GoalStackLevel(str, Enum):
    """SPEC §25.5 line 4664: Three-Layer Goal Stack (Outcome -> Project -> Task)."""
    VISION = "vision"
    MILESTONE = "milestone"
    DAILY = "daily"


class FactionType(str, Enum):
    """SPEC §25.1 line 4566: Four Factions Framework."""
    HEALTH = "Health/Stability"
    LEVERAGE = "Leverage/Money"
    CRAFT = "Craft/Skills"
    EXPRESSION = "Expression/Explore"


class OperatingMode(str, Enum):
    """SPEC §25.3 line 4614: Five Operating Modes."""
    SURVIVAL = "SURVIVAL"
    RECOVERY = "RECOVERY"
    NORMAL = "NORMAL"
    DEEP_WORK = "DEEP WORK"
    PEAK = "PEAK"


@dataclass
class ModeConstraints:
    """Operating mode capacity thresholds and scheduling constraints."""
    mode: OperatingMode
    dcs_range: Tuple[float, float]
    max_difficulty: int
    max_discretionary_tasks: Optional[int]
    description: str


@dataclass
class TaskScoreInput:
    """Input parameters for calculating Task Weight Score (TWS)."""
    priority: int
    urgency: int
    difficulty: int
    faction: Optional[str] = None
    faction_lag_hours: float = 0.0
    scale: GoalStackLevel = GoalStackLevel.DAILY
    child_scores: Optional[List[float]] = None


@dataclass
class TaskScoreResult:
    """Calculated Task Weight Score and associated component breakdown."""
    base_tws: float
    lag_bonus: float
    final_tws: float
    scale: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_tws": self.base_tws,
            "lag_bonus": self.lag_bonus,
            "final_tws": self.final_tws,
            "scale": self.scale,
            "metadata": self.metadata,
        }


@dataclass
class CheckInInput:
    """Daily morning check-in inputs for energy, mood, sleep quality, and stress."""
    energy: int
    mood: int
    sleep: int
    stress: int
    days_since_last_checkin: int = 0


@dataclass
class DCSResult:
    """Daily Capacity Score computation result, resolved mode, and alert status."""
    dcs: float
    mode: OperatingMode
    staleness_applied: bool
    alert: Optional[str] = None
    mode_constraints: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dcs": self.dcs,
            "mode": self.mode.value,
            "staleness_applied": self.staleness_applied,
            "alert": self.alert,
            "mode_constraints": self.mode_constraints or {},
        }


@dataclass
class PostTaskLog:
    """SPEC §25.4 line 4646: Post-task log record."""
    actual_time_minutes: int
    estimated_time_minutes: int
    quality: int
    reason: Optional[str] = None


class BaseLifeOSProvider(ABC):
    """Abstract interface for Life OS task scoring, capacity estimation, and faction balance."""

    def __init__(self, name: str = "life_os_provider") -> None:
        self.name = name
        self._enabled: bool = True

    def is_enabled(self) -> bool:
        """Return whether Life OS provider features are currently enabled."""
        return self._enabled

    @abstractmethod
    def initialize(self) -> None:
        """Initialize provider resources, caches, or persistent connections."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform provider health check returning status, latency, and diagnostics."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully release provider resources on system shutdown."""
        pass

    @abstractmethod
    def calculate_tws(self, task_input: TaskScoreInput) -> TaskScoreResult:
        """Compute Task Weight Score according to D-1 Option A formula with lag bonus and scale roll-up."""
        pass

    @abstractmethod
    def calculate_dcs(self, checkin: CheckInInput) -> DCSResult:
        """Compute Daily Capacity Score and resolve operating mode with staleness handling."""
        pass

    @abstractmethod
    def resolve_mode(self, dcs: float) -> Tuple[OperatingMode, ModeConstraints]:
        """Resolve one of 5 Operating Modes given a Daily Capacity Score."""
        pass

    @abstractmethod
    def compute_faction_lag(
        self, faction: str, target_pct: float, actual_hours: float, total_hours: float
    ) -> float:
        """Compute lag hours for a faction against weekly allocation targets."""
        pass
