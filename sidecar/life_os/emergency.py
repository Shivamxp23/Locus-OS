"""
SPEC §25.9 lines 4740-4758: Emergency Task Injection.
Rule:
    EMERGENCY INJECTION: tasks tagged EMERGENCY bypass TWS ordering and are inserted at
    the top of the schedule, respecting only faction crisis hierarchy.
Faction Crisis Hierarchy:
    Health/Stability > Leverage/Money > Craft/Skills > Expression/Explore.
Off state:
    When disabled (locus.life_os.emergency.enabled=false), emergency-tagged tasks sort
    strictly by TWS like everything else.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("locus.life_os.emergency")

CRISIS_FACTION_ORDER = [
    "Health/Stability",
    "Leverage/Money",
    "Craft/Skills",
    "Expression/Explore",
]

FACTION_ALIASES: Dict[str, str] = {
    "health": "Health/Stability",
    "health/stability": "Health/Stability",
    "stability": "Health/Stability",
    "leverage": "Leverage/Money",
    "leverage/money": "Leverage/Money",
    "money": "Leverage/Money",
    "craft": "Craft/Skills",
    "craft/skills": "Craft/Skills",
    "skills": "Craft/Skills",
    "expression": "Expression/Explore",
    "expression/explore": "Expression/Explore",
    "explore": "Expression/Explore",
}


@dataclass
class EmergencyTask:
    id: str
    title: str
    faction: str
    difficulty: int = 5
    tws: float = 0.0
    is_emergency: bool = False
    estimated_minutes: int = 60
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "faction": self.faction,
            "difficulty": self.difficulty,
            "tws": round(self.tws, 2),
            "is_emergency": self.is_emergency,
            "estimated_minutes": self.estimated_minutes,
            "metadata": self.metadata,
        }


class EmergencyTaskInjector:
    """
    SPEC §25.9: Schedule injector ordering emergency tasks via faction crisis hierarchy.
    """

    def normalize_faction(self, faction: str) -> str:
        key = (faction or "").strip().lower()
        return FACTION_ALIASES.get(key, "Craft/Skills")

    def get_crisis_rank(self, faction: str) -> int:
        canonical = self.normalize_faction(faction)
        try:
            return CRISIS_FACTION_ORDER.index(canonical)
        except ValueError:
            return 99

    def prioritize_tasks(
        self,
        tasks: List[EmergencyTask],
        bypass_tws: bool = True,
    ) -> List[EmergencyTask]:
        """
        Prioritize tasks:
        - If bypass_tws is True: emergency tasks bypass TWS and appear first, sorted by
          faction crisis rank (Health > Leverage > Craft > Expression), breaking ties by TWS.
          Non-emergency tasks follow, sorted by TWS.
        - If bypass_tws is False: all tasks sort strictly by TWS descending.
        """
        if not bypass_tws:
            return sorted(tasks, key=lambda t: t.tws, reverse=True)

        emergencies: List[EmergencyTask] = []
        standard: List[EmergencyTask] = []

        for t in tasks:
            if t.is_emergency:
                emergencies.append(t)
            else:
                standard.append(t)

        # Sort emergency tasks: primary key = crisis rank ascending (0 is Health), secondary = TWS descending
        emergencies_sorted = sorted(
            emergencies,
            key=lambda t: (self.get_crisis_rank(t.faction), -t.tws),
        )

        # Sort standard tasks by TWS descending
        standard_sorted = sorted(standard, key=lambda t: t.tws, reverse=True)

        return emergencies_sorted + standard_sorted

    def inject_into_schedule(
        self,
        timeline: List[Dict[str, Any]],
        task: EmergencyTask,
        at_index: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Inject emergency task into scheduled blocks timeline.
        """
        new_block = {
            "block_type": "deep" if task.estimated_minutes > 45 else "light",
            "duration_minutes": task.estimated_minutes,
            "task_id": task.id,
            "task_title": f"[EMERGENCY] {task.title}",
            "faction": self.normalize_faction(task.faction),
            "tws": task.tws,
            "is_emergency": True,
        }
        res = list(timeline)
        idx = max(0, min(at_index, len(res)))
        res.insert(idx, new_block)
        return res
