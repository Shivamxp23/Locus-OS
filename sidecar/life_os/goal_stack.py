"""sidecar/life_os/goal_stack.py - Three-Layer Goal Stack (Outcome -> Project -> Task).

Implements Spec §25.5 & §25.14:
- Level 1: Outcome/Vision (long-term desired results, tied to a Faction)
- Level 2: Project/Milestone (measurable sub-goals advancing an outcome)
- Level 3: Task (concrete actions advancing a project)
- Goal stack enforcement: every task must parent to a project; every project must parent to an outcome.
- Orphan detection surfaces disconnected tasks/projects for triage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from sidecar.life_os.factions import Faction


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class Outcome:
    """Level 1: Vision / Outcome."""
    id: str
    title: str
    faction: Faction
    status: GoalStatus = GoalStatus.ACTIVE
    description: str = ""
    target_date: Optional[str] = None


@dataclass
class Project:
    """Level 2: Project / Milestone."""
    id: str
    outcome_id: Optional[str]
    title: str
    status: GoalStatus = GoalStatus.ACTIVE
    description: str = ""
    target_date: Optional[str] = None


@dataclass
class GoalTask:
    """Level 3: Daily Task."""
    id: str
    project_id: Optional[str]
    title: str
    difficulty: float = 5.0
    urgency: float = 5.0
    leverage: float = 5.0
    consequence: float = 5.0
    status: GoalStatus = GoalStatus.ACTIVE
    deferral_count: int = 0
    estimated_minutes: int = 30


class GoalStackManager:
    """Manages the 3-Layer Goal Stack hierarchy and integrity validation."""

    def __init__(self) -> None:
        self.outcomes: dict[str, Outcome] = {}
        self.projects: dict[str, Project] = {}
        self.tasks: dict[str, GoalTask] = {}

    def add_outcome(self, title: str, faction: Faction, description: str = "", outcome_id: Optional[str] = None) -> Outcome:
        oid = outcome_id or str(uuid4())
        outcome = Outcome(id=oid, title=title, faction=faction, description=description)
        self.outcomes[oid] = outcome
        return outcome

    def add_project(self, title: str, outcome_id: Optional[str] = None, description: str = "", project_id: Optional[str] = None) -> Project:
        pid = project_id or str(uuid4())
        project = Project(id=pid, outcome_id=outcome_id, title=title, description=description)
        self.projects[pid] = project
        return project

    def add_task(
        self,
        title: str,
        project_id: Optional[str] = None,
        difficulty: float = 5.0,
        urgency: float = 5.0,
        leverage: float = 5.0,
        consequence: float = 5.0,
        task_id: Optional[str] = None,
    ) -> GoalTask:
        tid = task_id or str(uuid4())
        task = GoalTask(
            id=tid,
            project_id=project_id,
            title=title,
            difficulty=difficulty,
            urgency=urgency,
            leverage=leverage,
            consequence=consequence,
        )
        self.tasks[tid] = task
        return task

    def validate_task_ancestry(self, task_id: str) -> tuple[bool, Optional[str]]:
        """Validate that a task has valid project -> outcome ancestry."""
        task = self.tasks.get(task_id)
        if not task:
            return False, f"Task {task_id} not found"
        if not task.project_id:
            return False, f"Task '{task.title}' has no parent project (orphan task)"
        project = self.projects.get(task.project_id)
        if not project:
            return False, f"Parent project {task.project_id} not found"
        if not project.outcome_id:
            return False, f"Project '{project.title}' has no parent outcome (orphan project)"
        outcome = self.outcomes.get(project.outcome_id)
        if not outcome:
            return False, f"Grandparent outcome {project.outcome_id} not found"
        if outcome.faction not in Faction:
            return False, f"Outcome '{outcome.title}' has invalid faction {outcome.faction}"
        return True, None

    def get_orphan_tasks(self) -> list[GoalTask]:
        """Return tasks missing a valid parent project."""
        orphans = []
        for task in self.tasks.values():
            if not task.project_id or task.project_id not in self.projects:
                orphans.append(task)
        return orphans

    def get_orphan_projects(self) -> list[Project]:
        """Return projects missing a valid parent outcome."""
        orphans = []
        for proj in self.projects.values():
            if not proj.outcome_id or proj.outcome_id not in self.outcomes:
                orphans.append(proj)
        return orphans

    def reparent_task(self, task_id: str, new_project_id: str) -> bool:
        if task_id in self.tasks and new_project_id in self.projects:
            self.tasks[task_id].project_id = new_project_id
            return True
        return False

    def reparent_project(self, project_id: str, new_outcome_id: str) -> bool:
        if project_id in self.projects and new_outcome_id in self.outcomes:
            self.projects[project_id].outcome_id = new_outcome_id
            return True
        return False
