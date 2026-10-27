"""
SPEC §25.5 lines 4655-4678: Three-Layer Goal Stack (Outcome -> Project -> Task).
Enforces hierarchy:
- Level 1: Vision / Outcome (long-term desired results, associated with a Faction)
- Level 2: Milestone / Project (measurable sub-goals within an outcome)
- Level 3: Daily Task (concrete actions advancing a milestone)
Enforces: every task MUST parent to a project; every project MUST parent to an outcome.
Orphan tasks are surfaced for pruning / reparenting.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("locus.life_os.goal_stack")

VALID_FACTIONS = {"Craft", "Health", "Leverage", "Expression"}


class GoalStackLevel(str, Enum):
    VISION = "vision"
    MILESTONE = "milestone"
    DAILY = "daily"


@dataclass
class GoalNode:
    id: str
    title: str
    level: GoalStackLevel
    parent_id: Optional[str] = None
    faction: Optional[str] = None
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level.value,
            "parent_id": self.parent_id,
            "faction": self.faction,
            "status": self.status,
            "metadata": self.metadata,
        }


class ThreeLayerGoalStack:
    """
    SPEC §25.5: Three-Layer Goal Stack container and validator.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, GoalNode] = {}

    def add_node(self, node: GoalNode) -> None:
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[GoalNode]:
        return self._nodes.get(node_id)

    def reparent(self, node_id: str, new_parent_id: str) -> bool:
        node = self.get_node(node_id)
        if not node:
            return False
        parent = self.get_node(new_parent_id)
        if not parent:
            return False
        node.parent_id = new_parent_id
        return True

    def validate_task(self, task_id: str) -> Tuple[bool, str]:
        """
        Validate task hierarchy:
        t -> project (milestone) -> outcome (vision) -> faction.
        """
        task = self.get_node(task_id)
        if not task:
            return False, f"Task {task_id} not found in goal stack"
        if task.level != GoalStackLevel.DAILY:
            return False, f"Node {task_id} is level {task.level.value}, expected daily task"

        if not task.parent_id or task.parent_id not in self._nodes:
            return False, f"Orphan task detected: {task_id} has no valid milestone parent"

        project = self._nodes[task.parent_id]
        if project.level != GoalStackLevel.MILESTONE:
            return False, f"Parent {task.parent_id} is level {project.level.value}, expected milestone"

        if not project.parent_id or project.parent_id not in self._nodes:
            return False, f"Orphan project detected: {project.id} has no valid vision outcome parent"

        outcome = self._nodes[project.parent_id]
        if outcome.level != GoalStackLevel.VISION:
            return False, f"Parent {project.parent_id} is level {outcome.level.value}, expected vision"

        faction = outcome.faction or task.faction or project.faction
        if not faction or faction not in VALID_FACTIONS:
            return False, f"Outcome {outcome.id} faction '{faction}' not in valid factions {VALID_FACTIONS}"

        return True, "Valid goal stack hierarchy"

    def detect_orphan_tasks(self) -> List[Dict[str, Any]]:
        """
        Identify tasks or milestones without valid parents for morning briefing.
        """
        orphans: List[Dict[str, Any]] = []
        for node in self._nodes.values():
            if node.level == GoalStackLevel.DAILY:
                if not node.parent_id or node.parent_id not in self._nodes:
                    orphans.append({
                        "node_id": node.id,
                        "title": node.title,
                        "level": node.level.value,
                        "issue": "missing_milestone_parent",
                    })
                else:
                    parent = self._nodes[node.parent_id]
                    if parent.level != GoalStackLevel.MILESTONE:
                        orphans.append({
                            "node_id": node.id,
                            "title": node.title,
                            "level": node.level.value,
                            "issue": f"parent_is_{parent.level.value}_not_milestone",
                        })
            elif node.level == GoalStackLevel.MILESTONE:
                if not node.parent_id or node.parent_id not in self._nodes:
                    orphans.append({
                        "node_id": node.id,
                        "title": node.title,
                        "level": node.level.value,
                        "issue": "missing_vision_parent",
                    })
                else:
                    parent = self._nodes[node.parent_id]
                    if parent.level != GoalStackLevel.VISION:
                        orphans.append({
                            "node_id": node.id,
                            "title": node.title,
                            "level": node.level.value,
                            "issue": f"parent_is_{parent.level.value}_not_vision",
                        })
        return orphans

    def validate_hierarchy(self) -> Dict[str, Any]:
        """
        Validate all nodes in stack and report integrity.
        """
        orphans = self.detect_orphan_tasks()
        return {
            "valid": len(orphans) == 0,
            "total_nodes": len(self._nodes),
            "orphan_count": len(orphans),
            "orphans": orphans,
        }
