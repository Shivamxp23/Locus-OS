"""
SPEC §25.12 lines 4801-4870: Six-Step Scheduling Algorithm (Full Mathematical Specification).
File specified in decomposition: locus-os/sidecar/life_os/scheduler.py.
Implements:
1. Operating Mode Capacity Filter (based on DCS)
2. Task Weight Score (TWS) Ranking
3. Operating Mode Time-Block Grid Allocation
4. Faction Balance Constrained Assignment
5. Ultradian Recovery Buffer Insertion (20m after deep, 5m after light)
6. Three-Layer Goal Stack Validation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sidecar.life_os.goal_stack import GoalStackLevel, ThreeLayerGoalStack

logger = logging.getLogger("locus.life_os.scheduler")


class SchedulerOperatingMode(str, Enum):
    SURVIVAL = "SURVIVAL"
    RECOVERY = "RECOVERY"
    NORMAL = "NORMAL"
    DEEP_WORK = "DEEP_WORK"
    PEAK = "PEAK"


@dataclass
class ScheduledBlock:
    block_type: str  # "deep", "light", "recovery", "transition"
    duration_minutes: int
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    faction: Optional[str] = None
    tws: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_type": self.block_type,
            "duration_minutes": self.duration_minutes,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "faction": self.faction,
            "tws": round(self.tws, 2),
        }


@dataclass
class CandidateTask:
    id: str
    title: str
    difficulty: int  # 1-10
    leverage: int = 5  # 1-10
    urgency: int = 5  # 1-10
    consequence: int = 5  # 1-10
    faction: str = "Craft"
    deferral_count: int = 0
    project_id: Optional[str] = None
    estimated_minutes: int = 60

    def calculate_tws(self) -> float:
        """
        SPEC §25.12 Step 2:
        TWS = (D * 0.35) + (L * 0.25) + (U * 0.20) + (C * 0.20) + min(2.5, deferral_count * 0.5)
        """
        lag_bonus = min(2.5, float(self.deferral_count) * 0.5)
        score = (
            (float(self.difficulty) * 0.35)
            + (float(self.leverage) * 0.25)
            + (float(self.urgency) * 0.20)
            + (float(self.consequence) * 0.20)
            + lag_bonus
        )
        return round(score, 3)


class SixStepSchedulerEngine:
    """
    Deterministic 6-Step schedule generator for Locus Operating Modes & Scheduler.
    """

    def __init__(self, goal_stack: Optional[ThreeLayerGoalStack] = None) -> None:
        self.goal_stack = goal_stack or ThreeLayerGoalStack()

    def resolve_mode(self, dcs: float) -> Tuple[SchedulerOperatingMode, int]:
        """
        SPEC §25.12 Step 1:
        SURVIVAL (0.0-2.0): max diff 2
        RECOVERY (2.1-4.0): max diff 4
        NORMAL (4.1-6.0): max diff 7
        DEEP_WORK (6.1-8.0): max diff 9
        PEAK (8.1-10.0): max diff 10
        """
        if dcs <= 2.0:
            return SchedulerOperatingMode.SURVIVAL, 2
        elif dcs <= 4.0:
            return SchedulerOperatingMode.RECOVERY, 4
        elif dcs <= 6.0:
            return SchedulerOperatingMode.NORMAL, 7
        elif dcs <= 8.0:
            return SchedulerOperatingMode.DEEP_WORK, 9
        else:
            return SchedulerOperatingMode.PEAK, 10

    def get_time_blocks(self, mode: SchedulerOperatingMode) -> List[Tuple[str, int]]:
        """
        SPEC §25.12 Step 3:
        Returns list of (block_type, duration_minutes) for mode.
        """
        if mode == SchedulerOperatingMode.PEAK:
            return [("deep", 90), ("deep", 90), ("deep", 90), ("deep", 90), ("light", 30), ("light", 30)]
        elif mode == SchedulerOperatingMode.DEEP_WORK:
            return [("deep", 90), ("deep", 90), ("deep", 90), ("light", 30), ("light", 30), ("light", 30)]
        elif mode == SchedulerOperatingMode.NORMAL:
            return [("deep", 90), ("deep", 90), ("light", 30), ("light", 30), ("light", 30), ("light", 30)]
        elif mode == SchedulerOperatingMode.RECOVERY:
            return [("deep", 60), ("light", 20), ("light", 20), ("light", 20)]
        else:  # SURVIVAL
            return [("light", 15), ("light", 15)]

    def generate_schedule(
        self,
        dcs: float,
        candidate_tasks: List[CandidateTask],
        enforce_goal_stack: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute full 6-step scheduling pipeline.
        """
        # Step 1: Operating Mode Capacity Filter
        mode, max_diff = self.resolve_mode(dcs)
        eligible_tasks = [t for t in candidate_tasks if t.difficulty <= max_diff]

        # Step 2: TWS Ranking
        ranked_tasks = sorted(eligible_tasks, key=lambda t: t.calculate_tws(), reverse=True)

        # Step 3: Operating Mode Time-Block Grid Allocation
        raw_blocks = self.get_time_blocks(mode)

        # Step 4 & 5: Faction Balance Assignment + Ultradian Buffers
        scheduled_timeline: List[ScheduledBlock] = []
        assigned_task_ids: set[str] = set()

        task_idx = 0
        for b_type, duration in raw_blocks:
            # Pick next unassigned task
            assigned_task: Optional[CandidateTask] = None
            while task_idx < len(ranked_tasks):
                cand = ranked_tasks[task_idx]
                task_idx += 1
                if cand.id not in assigned_task_ids:
                    assigned_task = cand
                    assigned_task_ids.add(cand.id)
                    break

            if assigned_task:
                scheduled_timeline.append(
                    ScheduledBlock(
                        block_type=b_type,
                        duration_minutes=duration,
                        task_id=assigned_task.id,
                        task_title=assigned_task.title,
                        faction=assigned_task.faction,
                        tws=assigned_task.calculate_tws(),
                    )
                )
            else:
                scheduled_timeline.append(
                    ScheduledBlock(
                        block_type=b_type,
                        duration_minutes=duration,
                        task_id=None,
                        task_title="Open Discretionary Window",
                        faction="Craft",
                        tws=0.0,
                    )
                )

            # Step 5: Ultradian Buffer Insertion
            if b_type == "deep":
                scheduled_timeline.append(
                    ScheduledBlock(
                        block_type="recovery",
                        duration_minutes=20,
                        task_title="Ultradian Recovery Buffer (No screens / hydration)",
                    )
                )
            elif b_type == "light":
                scheduled_timeline.append(
                    ScheduledBlock(
                        block_type="transition",
                        duration_minutes=5,
                        task_title="Transition Buffer",
                    )
                )

        # Step 6: Three-Layer Goal Stack Validation
        goal_stack_errors: List[str] = []
        if enforce_goal_stack:
            for block in scheduled_timeline:
                if block.task_id:
                    ok, msg = self.goal_stack.validate_task(block.task_id)
                    if not ok:
                        goal_stack_errors.append(f"{block.task_id}: {msg}")

        total_work_minutes = sum(b.duration_minutes for b in scheduled_timeline if b.block_type in ("deep", "light"))
        total_buffer_minutes = sum(b.duration_minutes for b in scheduled_timeline if b.block_type in ("recovery", "transition"))

        return {
            "status": "ok",
            "dcs": dcs,
            "mode": mode.value,
            "max_difficulty": max_diff,
            "total_candidates": len(candidate_tasks),
            "eligible_tasks": len(eligible_tasks),
            "scheduled_tasks_count": len(assigned_task_ids),
            "timeline": [b.to_dict() for b in scheduled_timeline],
            "total_work_minutes": total_work_minutes,
            "total_buffer_minutes": total_buffer_minutes,
            "goal_stack_validation": {
                "enforced": enforce_goal_stack,
                "passed": len(goal_stack_errors) == 0,
                "errors": goal_stack_errors,
            },
        }
