"""sidecar/task_scoring.py - Task Priority Scoring & Multi-Scale Goal Roll-Up.

Implements Spec §25.4 and Errata Decisions D-1 and D-3:
- Formula: TWS = Priority * 0.4 + Urgency * 0.4 + Difficulty * 0.2 + FactionLagBonus.
- FactionLagBonus against targets (Health 25%, Leverage 25%, Craft 30%, Expression 20%):
  +2 if lag >3h, +4 if >6h, -1 if ahead.
- Three-Layer Goal Stack (D-3: vision, milestone, daily):
  Multi-scale roll-up where parent goals blend intrinsic scores and child averages.
- Modular switch: locus.task_scoring.enabled (True | False).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple, runtime_checkable

from sidecar.config import get as config_get
from sidecar.life_os.factions import (
    FACTION_TARGET_PERCENTAGES,
    Faction,
    calculate_faction_lag,
    calculate_faction_lag_bonus,
)
from sidecar.life_os.tws import calculate_base_tws, calculate_tws

logger = logging.getLogger("sidecar.task_scoring")


class GoalScale(str, Enum):
    """Three-Layer Goal Stack levels (Decision D-3)."""

    VISION = "vision"
    MILESTONE = "milestone"
    DAILY = "daily"


@dataclass
class Task:
    """A task, project, or goal at any scale within Locus OS."""

    task_id: str
    title: str
    faction: Faction | str = Faction.CRAFT
    scale: GoalScale | str = GoalScale.DAILY
    priority: float = 5.0
    urgency: float = 5.0
    difficulty: float = 5.0
    actual_hours: float = 0.0
    target_hours: float = 0.0
    children: list[Task] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def faction_enum(self) -> Faction:
        if isinstance(self.faction, Faction):
            return self.faction
        for f in Faction:
            if f.value.lower() == str(self.faction).lower():
                return f
        return Faction.CRAFT

    @property
    def scale_enum(self) -> GoalScale:
        if isinstance(self.scale, GoalScale):
            return self.scale
        for s in GoalScale:
            if s.value.lower() == str(self.scale).lower():
                return s
        return GoalScale.DAILY


@runtime_checkable
class TaskScorerProvider(Protocol):
    """Protocol for task priority and TWS scoring engines."""

    def score_task(
        self,
        task: Task,
        faction_hours: dict[Faction, tuple[float, float]] | None = None,
    ) -> float:
        """Calculate TWS score for a task."""
        return 0.0

    def rank_tasks(
        self,
        tasks: Sequence[Task],
        faction_hours: dict[Faction, tuple[float, float]] | None = None,
    ) -> list[tuple[Task, float]]:
        """Sort tasks descending by priority score."""
        return []


class TaskPriorityScorer:
    """Scorer calculating TWS with multi-scale roll-up and faction lag bonuses."""

    def __init__(self, enabled: Optional[bool] = None):
        self._enabled_override = enabled

    @property
    def is_enabled(self) -> bool:
        if self._enabled_override is not None:
            return self._enabled_override
        return bool(config_get("locus.task_scoring.enabled", default=True))

    def compute_lag_bonus(
        self,
        task: Task,
        faction_hours: dict[Faction, tuple[float, float]] | None = None,
    ) -> float:
        """Compute faction lag bonus using either passed faction hours or task direct targets."""
        faction = task.faction_enum
        if faction_hours and faction in faction_hours:
            target_h, actual_h = faction_hours[faction]
        else:
            target_h = task.target_hours
            actual_h = task.actual_hours

        lag = calculate_faction_lag(target_h, actual_h)
        return calculate_faction_lag_bonus(lag)

    def score_task(
        self,
        task: Task,
        faction_hours: dict[Faction, tuple[float, float]] | None = None,
    ) -> float:
        """Calculate Task Weight Score (TWS) for a task at any scale.

        If disabled: returns raw priority (1.0 - 10.0).
        If enabled:
          base = (P * 0.4) + (U * 0.4) + (D * 0.2)
          if task has children:
            effective_base = (base * 0.5) + (avg(child_base_scores) * 0.5)
          TWS = effective_base + FactionLagBonus
        """
        if not self.is_enabled:
            return float(task.priority)

        intrinsic_base = calculate_base_tws(task.priority, task.urgency, task.difficulty)

        # Multi-scale roll-up (D-3)
        if task.children:
            child_scores = [self.score_task(c, faction_hours=faction_hours) for c in task.children]
            child_avg = sum(child_scores) / len(child_scores)
            effective_base = round((intrinsic_base * 0.5) + (child_avg * 0.5), 2)
        else:
            effective_base = intrinsic_base

        lag_bonus = self.compute_lag_bonus(task, faction_hours=faction_hours)
        total_tws = round(effective_base + lag_bonus, 2)
        return total_tws

    def rank_tasks(
        self,
        tasks: Sequence[Task],
        faction_hours: dict[Faction, tuple[float, float]] | None = None,
    ) -> list[tuple[Task, float]]:
        """Rank tasks in descending order of TWS."""
        scored = [(t, self.score_task(t, faction_hours=faction_hours)) for t in tasks]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)


def get_task_suite() -> list[Task]:
    """Create a demonstration task suite covering all 3 scales and 4 factions."""
    # Daily tasks under a Milestone
    daily1 = Task(
        task_id="D-1",
        title="Morning HIIT Cardio",
        faction=Faction.HEALTH,
        scale=GoalScale.DAILY,
        priority=8.0,
        urgency=7.0,
        difficulty=6.0,
        target_hours=5.0,
        actual_hours=1.0,  # 4h lag -> +2 bonus
    )
    daily2 = Task(
        task_id="D-2",
        title="Refactor Life OS TWS Engine",
        faction=Faction.CRAFT,
        scale=GoalScale.DAILY,
        priority=9.0,
        urgency=8.0,
        difficulty=5.0,
        target_hours=10.0,
        actual_hours=2.0,  # 8h lag -> +4 crisis bonus
    )
    daily3 = Task(
        task_id="D-3",
        title="Read Philosophy Chapter",
        faction=Faction.EXPRESSION,
        scale=GoalScale.DAILY,
        priority=4.0,
        urgency=3.0,
        difficulty=2.0,
        target_hours=2.0,
        actual_hours=4.0,  # ahead -> -1 penalty
    )

    # Milestone goal containing daily children
    milestone1 = Task(
        task_id="M-1",
        title="Sprint S16 Delivery",
        faction=Faction.CRAFT,
        scale=GoalScale.MILESTONE,
        priority=8.0,
        urgency=8.0,
        difficulty=7.0,
        target_hours=20.0,
        actual_hours=12.0,  # 8h lag -> +4 bonus
        children=[daily2],
    )

    # Top-level Vision goal containing milestone child
    vision1 = Task(
        task_id="V-1",
        title="Master Autonomous Intelligent Software",
        faction=Faction.CRAFT,
        scale=GoalScale.VISION,
        priority=10.0,
        urgency=7.0,
        difficulty=9.0,
        target_hours=50.0,
        actual_hours=45.0,  # 5h lag -> +2 bonus
        children=[milestone1],
    )

    return [daily1, daily2, daily3, milestone1, vision1]


def main() -> int:
    """CLI runner executing evaluation on standard task suite."""
    scorer = TaskPriorityScorer()
    tasks = get_task_suite()
    ranked = scorer.rank_tasks(tasks)

    print("=" * 75)
    print("LOCUS OS — TASK PRIORITY SCORING (TWS) EVALUATION (D-1 / D-3 / Spec §25.4)")
    print("=" * 75)
    print(f"{'ID':<6} | {'Scale':<10} | {'Faction':<11} | {'P':<3} {'U':<3} {'D':<3} | {'Lag Bonus':<10} | {'TWS Score'}")
    print("-" * 75)
    for t, score in ranked:
        bonus = scorer.compute_lag_bonus(t)
        bonus_str = f"{bonus:+.1f}" if bonus != 0 else " 0.0"
        print(f"{t.task_id:<6} | {t.scale_enum.value:<10} | {t.faction_enum.value:<11} | {t.priority:<3.0f} {t.urgency:<3.0f} {t.difficulty:<3.0f} | {bonus_str:<10} | {score:.2f}")
    print("=" * 75)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
