"""sidecar/life_os/goal_enforcement.py - Goal Stack Strict Enforcement.

Implements Spec §25.14:
- Every task MUST parent to a project; every project MUST parent to an outcome.
- Orphan tasks surfaced during morning briefing.
- Validates structural completeness and blocks unanchored tasks when enforcement is enabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sidecar.life_os.goal_stack import GoalStackManager, GoalTask, Project, Outcome


@dataclass
class EnforcementReport:
    enforcement_enabled: bool
    is_valid: bool
    orphan_tasks: list[GoalTask]
    orphan_projects: list[Project]
    summary_message: str


class GoalStackEnforcer:
    """Enforces 3-layer ancestry on task creation, scheduling, and morning review."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def enforce_task(
        self,
        task: GoalTask,
        goal_manager: GoalStackManager,
    ) -> tuple[bool, Optional[str]]:
        """Validate an individual task prior to execution or scheduling."""
        if not self.enabled:
            return True, None

        valid, err = goal_manager.validate_task_ancestry(task.id)
        if not valid:
            return False, f"GoalStackEnforcement Violation: {err}"
        return True, None

    def audit_all(self, goal_manager: GoalStackManager) -> EnforcementReport:
        """Audit entire hierarchy for orphan tasks and orphan projects."""
        if not self.enabled:
            return EnforcementReport(
                enforcement_enabled=False,
                is_valid=True,
                orphan_tasks=[],
                orphan_projects=[],
                summary_message="Goal stack enforcement is disabled.",
            )

        orphan_tasks = goal_manager.get_orphan_tasks()
        orphan_projs = goal_manager.get_orphan_projects()
        is_valid = len(orphan_tasks) == 0 and len(orphan_projs) == 0

        if is_valid:
            msg = "Goal stack integrity 100%: All tasks and projects cleanly anchored."
        else:
            msg = f"Goal stack violations: {len(orphan_tasks)} orphan task(s), {len(orphan_projs)} orphan project(s)."

        return EnforcementReport(
            enforcement_enabled=True,
            is_valid=is_valid,
            orphan_tasks=orphan_tasks,
            orphan_projects=orphan_projs,
            summary_message=msg,
        )
