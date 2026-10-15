"""sidecar/life_os/scheduler.py - Deterministic Six-Step Scheduling Algorithm.

Implements Spec §25.12:
- STEP 1: Operating Mode Capacity Filter
- STEP 2: Task Weight Score (TWS) Ranking
- STEP 3: Operating Mode Time-Block Grid Allocation
- STEP 4: Faction Balance Constrained Assignment
- STEP 5: Ultradian Recovery Buffer Insertion
- STEP 6: Three-Layer Goal Stack Validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from sidecar.life_os.factions import Faction
from sidecar.life_os.modes import OperatingMode, resolve_operating_mode
from sidecar.life_os.faction_balancer import FactionBalancer, SCHEDULER_FACTION_TARGETS
from sidecar.life_os.goal_stack import GoalStackManager, GoalTask, Project, Outcome


class BlockType(str, Enum):
    DEEP = "deep"
    LIGHT = "light"
    RECOVERY = "recovery"
    TRANSITION = "transition"


@dataclass
class ScheduleBlock:
    block_index: int
    block_type: BlockType
    duration_minutes: int
    assigned_task: Optional[GoalTask] = None
    faction: Optional[Faction] = None
    tws_score: float = 0.0
    notes: str = ""


@dataclass
class DailyScheduleManifest:
    operating_mode: OperatingMode
    dcs_score: float
    total_cognitive_hours: float
    blocks: list[ScheduleBlock]
    assigned_task_count: int
    unassigned_task_count: int
    faction_distribution_pct: dict[str, float]
    validation_passed: bool
    validation_errors: list[str] = field(default_factory=list)


def calculate_scheduler_tws(
    difficulty: float,
    leverage: float,
    urgency: float,
    consequence: float,
    deferral_count: int = 0,
    faction_lag_bonus: float = 0.0,
) -> float:
    """Calculate TWS according to Spec §25.12 Step 2.

    Formula: (D * 0.35) + (L * 0.25) + (U * 0.20) + (C * 0.20) + LagBonus
    where LagBonus = min(2.5, deferral_count * 0.5) + faction_lag_bonus
    """
    d = max(1.0, min(10.0, float(difficulty)))
    lev = max(1.0, min(10.0, float(leverage)))
    u = max(1.0, min(10.0, float(urgency)))
    c = max(1.0, min(10.0, float(consequence)))

    base = (d * 0.35) + (lev * 0.25) + (u * 0.20) + (c * 0.20)
    deferral_bonus = min(2.5, deferral_count * 0.5)
    total = base + deferral_bonus + faction_lag_bonus
    return round(total, 2)


class SixStepScheduler:
    """Deterministic Six-Step Schedule Generator."""

    def __init__(
        self,
        goal_manager: Optional[GoalStackManager] = None,
        balancer: Optional[FactionBalancer] = None,
    ) -> None:
        self.goal_manager = goal_manager or GoalStackManager()
        self.balancer = balancer or FactionBalancer()

    def generate_schedule(
        self,
        dcs: float,
        task_pool: list[GoalTask],
        task_factions: dict[str, Faction],
        current_weekly_hours: Optional[dict[Faction, float]] = None,
    ) -> DailyScheduleManifest:
        mode = resolve_operating_mode(dcs)
        allocations = dict(current_weekly_hours or {f: 0.0 for f in Faction})

        # --- STEP 1: Operating Mode Capacity Filter
        eligible_tasks: list[GoalTask] = []
        for task in task_pool:
            diff = task.difficulty
            faction = task_factions.get(task.id, Faction.CRAFT)

            if mode == OperatingMode.SURVIVAL:
                if diff <= 2.0 and faction == Faction.HEALTH:
                    eligible_tasks.append(task)
            elif mode == OperatingMode.RECOVERY:
                if diff <= 4.0:
                    eligible_tasks.append(task)
            elif mode == OperatingMode.NORMAL:
                if diff <= 7.0:
                    eligible_tasks.append(task)
            elif mode == OperatingMode.DEEP_WORK:
                if diff <= 9.0:
                    eligible_tasks.append(task)
            else:  # PEAK
                eligible_tasks.append(task)

        # --- STEP 2: Task Weight Score (TWS) Ranking
        scored_tasks: list[tuple[GoalTask, float]] = []
        for task in eligible_tasks:
            score = calculate_scheduler_tws(
                difficulty=task.difficulty,
                leverage=task.leverage,
                urgency=task.urgency,
                consequence=task.consequence,
                deferral_count=task.deferral_count,
            )
            scored_tasks.append((task, score))

        # Sort strictly descending by TWS
        scored_tasks.sort(key=lambda x: x[1], reverse=True)

        # --- STEP 3: Time-Block Grid Allocation by Mode
        # Grid definition: list of (block_type, duration_minutes)
        if mode == OperatingMode.PEAK:
            grid_spec = [
                (BlockType.DEEP, 90), (BlockType.DEEP, 90),
                (BlockType.DEEP, 90), (BlockType.DEEP, 90),
                (BlockType.LIGHT, 30), (BlockType.LIGHT, 30),
            ]
        elif mode == OperatingMode.DEEP_WORK:
            grid_spec = [
                (BlockType.DEEP, 90), (BlockType.DEEP, 90),
                (BlockType.DEEP, 90),
                (BlockType.LIGHT, 30), (BlockType.LIGHT, 30), (BlockType.LIGHT, 30),
            ]
        elif mode == OperatingMode.NORMAL:
            grid_spec = [
                (BlockType.DEEP, 90), (BlockType.DEEP, 90),
                (BlockType.LIGHT, 30), (BlockType.LIGHT, 30),
                (BlockType.LIGHT, 30), (BlockType.LIGHT, 30),
            ]
        elif mode == OperatingMode.RECOVERY:
            grid_spec = [
                (BlockType.DEEP, 60),
                (BlockType.LIGHT, 20), (BlockType.LIGHT, 20), (BlockType.LIGHT, 20),
            ]
        else:  # SURVIVAL
            grid_spec = [
                (BlockType.LIGHT, 15), (BlockType.LIGHT, 15),
            ]

        # --- STEP 4 & 5: Assignment + Ultradian Buffers
        final_blocks: list[ScheduleBlock] = []
        available_tasks = list(scored_tasks)
        block_idx = 1
        scheduled_task_ids: set[str] = set()

        for b_type, duration in grid_spec:
            duration_hrs = duration / 60.0
            assigned_task = None
            assigned_faction = None
            assigned_tws = 0.0

            # Find best fitting task respecting faction constraints
            waiting_factions = {task_factions.get(t.id, Faction.CRAFT) for t, _ in available_tasks}
            chosen_index = -1

            for idx, (t, score) in enumerate(available_tasks):
                f = task_factions.get(t.id, Faction.CRAFT)
                if self.balancer.can_assign_task(f, duration_hrs, allocations, waiting_factions):
                    chosen_index = idx
                    assigned_task = t
                    assigned_faction = f
                    assigned_tws = score
                    break

            if chosen_index >= 0:
                available_tasks.pop(chosen_index)
                allocations[assigned_faction] += duration_hrs
                scheduled_task_ids.add(assigned_task.id)

            # Insert work block
            final_blocks.append(
                ScheduleBlock(
                    block_index=block_idx,
                    block_type=b_type,
                    duration_minutes=duration,
                    assigned_task=assigned_task,
                    faction=assigned_faction,
                    tws_score=assigned_tws,
                )
            )
            block_idx += 1

            # STEP 5: Ultradian Buffer Insertion
            if b_type == BlockType.DEEP and duration >= 60:
                final_blocks.append(
                    ScheduleBlock(
                        block_index=block_idx,
                        block_type=BlockType.RECOVERY,
                        duration_minutes=20,
                        notes="Mandatory 20-minute Ultradian Recovery Buffer (No screens, hydration, movement)",
                    )
                )
                block_idx += 1
            elif b_type == BlockType.LIGHT:
                final_blocks.append(
                    ScheduleBlock(
                        block_index=block_idx,
                        block_type=BlockType.TRANSITION,
                        duration_minutes=5,
                        notes="Transition buffer",
                    )
                )
                block_idx += 1

        # --- STEP 6: Three-Layer Goal Stack Validation
        validation_errors: list[str] = []
        for blk in final_blocks:
            if blk.assigned_task:
                valid, err = self.goal_manager.validate_task_ancestry(blk.assigned_task.id)
                if not valid and err:
                    validation_errors.append(err)

        total_cog_hours = sum(b.duration_minutes for b in final_blocks if b.block_type in (BlockType.DEEP, BlockType.LIGHT)) / 60.0
        total_alloc_hrs = sum(allocations.values())
        dist = {
            f.value: round((allocations.get(f, 0.0) / total_alloc_hrs) * 100, 1) if total_alloc_hrs > 0 else 0.0
            for f in Faction
        }

        return DailyScheduleManifest(
            operating_mode=mode,
            dcs_score=dcs,
            total_cognitive_hours=round(total_cog_hours, 2),
            blocks=final_blocks,
            assigned_task_count=len(scheduled_task_ids),
            unassigned_task_count=len(task_pool) - len(scheduled_task_ids),
            faction_distribution_pct=dist,
            validation_passed=len(validation_errors) == 0,
            validation_errors=validation_errors,
        )


class SchedulerProvider:
    """Provider interface for Life OS deterministic scheduler."""

    def __init__(self) -> None:
        self.scheduler = SixStepScheduler()

    def plan_day(
        self,
        dcs: float,
        tasks: list[GoalTask],
        task_factions: dict[str, Faction],
    ) -> DailyScheduleManifest:
        return self.scheduler.generate_schedule(dcs, tasks, task_factions)
