"""sidecar/life_os/deferral.py - Deferral Detection (3/5/8+).

Implements Spec §25.7:
DEFERRAL THRESHOLDS:
- 3x defer -> warn: "Consider dropping or delegating"
- 5x defer -> escalate: surfaced at weekly review
- 8x defer -> flag as phantom task: auto-parked with review note
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class DeferralAction(str, Enum):
    NONE = "none"
    WARN = "warn"
    ESCALATE = "escalate"
    PARK_PHANTOM = "park_phantom"


@dataclass
class DeferralResult:
    task_id: str
    task_title: str
    deferral_count: int
    action: DeferralAction
    message: str
    is_parked: bool = False


def evaluate_deferral_thresholds(deferral_count: int) -> tuple[DeferralAction, str]:
    """Evaluate task deferral count against 3/5/8+ thresholds."""
    if deferral_count >= 8:
        return (
            DeferralAction.PARK_PHANTOM,
            f"Deferred {deferral_count} times: flagged as phantom task. Automatically parked with review note.",
        )
    elif deferral_count >= 5:
        return (
            DeferralAction.ESCALATE,
            f"Deferred {deferral_count} times: escalated for mandatory weekly review triage.",
        )
    elif deferral_count >= 3:
        return (
            DeferralAction.WARN,
            f"Deferred {deferral_count} times: consider dropping, scoping down, or delegating.",
        )
    return DeferralAction.NONE, f"Deferred {deferral_count} times: normal status."


class DeferralTracker:
    """Tracks task deferrals, applies thresholds, and auto-parks phantom tasks."""

    def __init__(self) -> None:
        self.deferral_counts: dict[str, int] = {}
        self.parked_tasks: set[str] = set()

    def record_deferral(self, task_id: str, task_title: str) -> DeferralResult:
        """Increment deferral count for a task and evaluate action."""
        count = self.deferral_counts.get(task_id, 0) + 1
        self.deferral_counts[task_id] = count
        action, msg = evaluate_deferral_thresholds(count)
        is_parked = False
        if action == DeferralAction.PARK_PHANTOM:
            self.parked_tasks.add(task_id)
            is_parked = True

        return DeferralResult(
            task_id=task_id,
            task_title=task_title,
            deferral_count=count,
            action=action,
            message=msg,
            is_parked=is_parked,
        )

    def is_task_parked(self, task_id: str) -> bool:
        return task_id in self.parked_tasks

    def get_weekly_review_escalations(self) -> list[str]:
        """Return list of task IDs deferred 5 or more times."""
        return [tid for tid, cnt in self.deferral_counts.items() if cnt >= 5]
