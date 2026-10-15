"""sidecar/life_os/reviews.py - Review Cadence System.

Implements Spec §25.13:
Review Cadence System:
- Daily Standup (Morning Briefing at 07:30 IST): Check-in, DCS assessment, daily schedule dispatch, orphan task triage.
- Weekly Retrospective (Sunday 02:00 IST): Weekly faction rebalance, deferral escalation (5x+ tasks), capacity synthesis.
- Monthly Deep Review: Outcome milestone audit, long-term vision realignment, quarterly strategic adjustments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ReviewCadenceType(str, Enum):
    DAILY_STANDUP = "daily_standup"
    WEEKLY_RETROSPECTIVE = "weekly_retrospective"
    MONTHLY_DEEP_REVIEW = "monthly_deep_review"


@dataclass
class ReviewPrompt:
    cadence: ReviewCadenceType
    title: str
    scheduled_time_ist: str
    check_items: list[str]
    action_items: list[str] = field(default_factory=list)


class ReviewCadenceManager:
    """Manages review cadences, triggers, and scheduled briefing synthesis."""

    def __init__(
        self,
        daily_enabled: bool = True,
        weekly_enabled: bool = True,
        monthly_enabled: bool = True,
    ) -> None:
        self.daily_enabled = daily_enabled
        self.weekly_enabled = weekly_enabled
        self.monthly_enabled = monthly_enabled

    def get_morning_briefing_prompt(self, orphan_task_count: int = 0) -> Optional[ReviewPrompt]:
        """Generate 07:30 IST Daily Morning Briefing."""
        if not self.daily_enabled:
            return None
        checks = [
            "Log sleep, energy, mood, and stress for DCS calculation",
            "Review automatically generated Six-Step Daily Schedule",
            "Commit to Deep Work blocks",
        ]
        if orphan_task_count > 0:
            checks.append(f"Triage {orphan_task_count} orphan tasks (assign to project or discard)")

        return ReviewPrompt(
            cadence=ReviewCadenceType.DAILY_STANDUP,
            title="Morning Briefing & Daily Standup",
            scheduled_time_ist="07:30 IST",
            check_items=checks,
        )

    def get_weekly_retro_prompt(self, escalated_tasks: list[str]) -> Optional[ReviewPrompt]:
        """Generate Sunday 02:00 IST Weekly Retrospective."""
        if not self.weekly_enabled:
            return None
        checks = [
            "Audit weekly hours logged across Craft, Health, Leverage, Expression",
            "Execute Weekly Faction Rebalance algorithm",
            "Review Action Gap alerts",
        ]
        actions = []
        if escalated_tasks:
            actions.append(f"Triage {len(escalated_tasks)} tasks deferred >= 5 times")

        return ReviewPrompt(
            cadence=ReviewCadenceType.WEEKLY_RETROSPECTIVE,
            title="Weekly Retrospective & Synthesis",
            scheduled_time_ist="Sunday 02:00 IST",
            check_items=checks,
            action_items=actions,
        )

    def get_monthly_review_prompt(self) -> Optional[ReviewPrompt]:
        """Generate Monthly Deep Review."""
        if not self.monthly_enabled:
            return None
        return ReviewPrompt(
            cadence=ReviewCadenceType.MONTHLY_DEEP_REVIEW,
            title="Monthly Deep Strategic Review",
            scheduled_time_ist="1st of month 10:00 IST",
            check_items=[
                "Review Level 1 Vision / Outcome progress",
                "Prune dead projects and spin up new milestones",
                "Evaluate long-term faction balance trajectory",
            ],
        )
