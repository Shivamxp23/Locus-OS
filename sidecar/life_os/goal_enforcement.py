"""
SPEC §25.14 lines 4897-4909: Goal Stack Enforcement (F-0115 / US-92).
Enforces hierarchy rules:
- Every task MUST parent to a project (milestone).
- Every project MUST parent to an outcome (vision).
- Orphan tasks surfaced during morning briefing.
Swappable / off state: locus.life_os.goal_enforcement.enabled.
Off -> orphan tasks are allowed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
    VALID_FACTIONS,
)

logger = logging.getLogger("locus.life_os.goal_enforcement")


@dataclass
class EnforcementResult:
    """
    Result of a goal stack enforcement check.
    """
    allowed: bool
    enforced: bool
    valid: bool
    reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "enforced": self.enforced,
            "valid": self.valid,
            "reasons": self.reasons,
            "details": self.details,
        }


@dataclass
class BriefingOrphanReport:
    """
    Orphans surfaced specifically for morning briefing.
    """
    orphan_count: int
    orphans: List[Dict[str, Any]]
    briefing_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "orphan_count": self.orphan_count,
            "orphans": self.orphans,
            "briefing_text": self.briefing_text,
        }


class GoalStackEnforcer:
    """
    SPEC §25.14: Enforces 3-layer goal stack hierarchy (Outcome -> Project -> Task).
    When locus.life_os.goal_enforcement.enabled is False, orphan tasks are allowed.
    """

    SWITCH_KEY = "locus.life_os.goal_enforcement.enabled"

    def is_enforcement_enabled(self) -> bool:
        """
        Check if goal enforcement is enabled.
        Off -> orphan tasks are allowed.
        """
        val = config.get(self.SWITCH_KEY)
        if val is None:
            return True
        return config.is_enabled(self.SWITCH_KEY)

    def enforce_task(
        self,
        task_id: str,
        stack: ThreeLayerGoalStack,
    ) -> EnforcementResult:
        """
        Enforce that task_id parents to a project, and the project parents to an outcome.
        If enforcement is OFF, orphan tasks are allowed (allowed=True, enforced=False).
        """
        if not self.is_enforcement_enabled():
            return EnforcementResult(
                allowed=True,
                enforced=False,
                valid=True,
                reasons=["Goal stack enforcement disabled: orphan tasks allowed"],
                details={"task_id": task_id, "bypass": True},
            )

        task = stack.get_node(task_id)
        if not task:
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Task '{task_id}' not found in goal stack"],
                details={"task_id": task_id},
            )

        if task.level != GoalStackLevel.DAILY:
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Node '{task_id}' has level '{task.level.value}', expected daily task"],
                details={"task_id": task_id, "actual_level": task.level.value},
            )

        # 1. Task MUST parent to a project (milestone)
        if not task.parent_id or task.parent_id not in stack._nodes:
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Orphan task detected: task '{task_id}' has no valid project parent"],
                details={"task_id": task_id, "parent_id": task.parent_id, "issue": "missing_project_parent"},
            )

        project = stack.get_node(task.parent_id)
        if not project or project.level != GoalStackLevel.MILESTONE:
            actual_level = project.level.value if project else "missing"
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Task '{task_id}' parent '{task.parent_id}' is {actual_level}, expected project milestone"],
                details={"task_id": task_id, "parent_id": task.parent_id, "issue": "invalid_project_parent"},
            )

        # 2. Project MUST parent to an outcome (vision)
        if not project.parent_id or project.parent_id not in stack._nodes:
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Orphan project detected: project '{project.id}' has no valid outcome parent"],
                details={"task_id": task_id, "project_id": project.id, "issue": "missing_outcome_parent"},
            )

        outcome = stack.get_node(project.parent_id)
        if not outcome or outcome.level != GoalStackLevel.VISION:
            actual_level = outcome.level.value if outcome else "missing"
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Project '{project.id}' parent '{project.parent_id}' is {actual_level}, expected outcome vision"],
                details={"task_id": task_id, "project_id": project.id, "issue": "invalid_outcome_parent"},
            )

        # Valid lineage
        faction = outcome.faction or task.faction or project.faction
        return EnforcementResult(
            allowed=True,
            enforced=True,
            valid=True,
            reasons=["Valid goal stack lineage: Task -> Project -> Outcome"],
            details={
                "task_id": task.id,
                "project_id": project.id,
                "outcome_id": outcome.id,
                "faction": faction,
            },
        )

    def enforce_project(
        self,
        project_id: str,
        stack: ThreeLayerGoalStack,
    ) -> EnforcementResult:
        """
        Enforce that project_id parents to an outcome (vision).
        If enforcement is OFF, orphan projects are allowed (allowed=True, enforced=False).
        """
        if not self.is_enforcement_enabled():
            return EnforcementResult(
                allowed=True,
                enforced=False,
                valid=True,
                reasons=["Goal stack enforcement disabled: orphan projects allowed"],
                details={"project_id": project_id, "bypass": True},
            )

        project = stack.get_node(project_id)
        if not project:
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Project '{project_id}' not found in goal stack"],
                details={"project_id": project_id},
            )

        if project.level != GoalStackLevel.MILESTONE:
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Node '{project_id}' has level '{project.level.value}', expected project milestone"],
                details={"project_id": project_id, "actual_level": project.level.value},
            )

        # Project MUST parent to an outcome
        if not project.parent_id or project.parent_id not in stack._nodes:
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Orphan project detected: project '{project_id}' has no valid outcome parent"],
                details={"project_id": project_id, "issue": "missing_outcome_parent"},
            )

        outcome = stack.get_node(project.parent_id)
        if not outcome or outcome.level != GoalStackLevel.VISION:
            actual_level = outcome.level.value if outcome else "missing"
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=[f"Project '{project_id}' parent '{project.parent_id}' is {actual_level}, expected outcome vision"],
                details={"project_id": project_id, "issue": "invalid_outcome_parent"},
            )

        return EnforcementResult(
            allowed=True,
            enforced=True,
            valid=True,
            reasons=["Valid goal stack lineage: Project -> Outcome"],
            details={
                "project_id": project.id,
                "outcome_id": outcome.id,
                "faction": outcome.faction or project.faction,
            },
        )

    def surface_orphans_for_briefing(
        self,
        stack: ThreeLayerGoalStack,
    ) -> BriefingOrphanReport:
        """
        SPEC §25.14: Surface orphan tasks during morning briefing.
        Identifies orphan tasks and projects and generates formatted briefing alert.
        """
        orphans = stack.detect_orphan_tasks()
        task_orphans = [o for o in orphans if o.get("level") == GoalStackLevel.DAILY.value]
        project_orphans = [o for o in orphans if o.get("level") == GoalStackLevel.MILESTONE.value]

        if not orphans:
            text = "Morning Briefing: Goal stack clean — 0 orphan tasks detected. All tasks advance verified outcomes."
        else:
            lines = [
                f"Morning Briefing Alert: {len(task_orphans)} orphan task(s) and {len(project_orphans)} orphan project(s) detected.",
                "The following items lack parent linkage in the 3-Layer Goal Stack:",
            ]
            for item in orphans:
                lines.append(f"- [{item.get('level', 'item').upper()}] {item.get('title')} (ID: {item.get('node_id')}) -> {item.get('issue')}")
            lines.append("Recommendation: Reparent or prune orphan tasks before deep work scheduling.")
            text = "\n".join(lines)

        return BriefingOrphanReport(
            orphan_count=len(orphans),
            orphans=orphans,
            briefing_text=text,
        )

    def audit_stack(
        self,
        stack: ThreeLayerGoalStack,
    ) -> EnforcementResult:
        """
        Run full enforcement audit across all nodes in the goal stack.
        """
        if not self.is_enforcement_enabled():
            return EnforcementResult(
                allowed=True,
                enforced=False,
                valid=True,
                reasons=["Goal stack enforcement disabled: all nodes permitted without parentage"],
                details={"total_nodes": len(stack._nodes), "bypass": True},
            )

        orphans = stack.detect_orphan_tasks()
        if orphans:
            reasons = [f"Found {len(orphans)} orphan node(s) in goal stack"]
            return EnforcementResult(
                allowed=False,
                enforced=True,
                valid=False,
                reasons=reasons,
                details={
                    "total_nodes": len(stack._nodes),
                    "orphan_count": len(orphans),
                    "orphans": orphans,
                },
            )

        return EnforcementResult(
            allowed=True,
            enforced=True,
            valid=True,
            reasons=["All nodes satisfy 3-layer goal stack enforcement rules"],
            details={"total_nodes": len(stack._nodes), "orphan_count": 0},
        )
