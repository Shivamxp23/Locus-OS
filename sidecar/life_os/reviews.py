"""
SPEC §25.13 lines 4883-4896: Review Cadence System.
Logic:
    Daily standup (morning briefing),
    Weekly retrospective (Sunday synthesis via Gemini 2.5 Pro),
    Monthly deep review.
Off state:
    Each review cadence toggleable independently:
    - locus.life_os.reviews.daily.enabled
    - locus.life_os.reviews.weekly.enabled
    - locus.life_os.reviews.monthly.enabled
    Master off-switch: locus.review_cadence_system.enabled / locus.life_os.reviews.enabled
    Off → no automatic review prompts.
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.life_os.reviews")


class ReviewCadence(str, Enum):
    DAILY_STANDUP = "daily_standup"
    WEEKLY_RETROSPECTIVE = "weekly_retrospective"
    MONTHLY_DEEP_REVIEW = "monthly_deep_review"


CADENCE_CONFIG_SWITCHES: Dict[ReviewCadence, str] = {
    ReviewCadence.DAILY_STANDUP: "locus.life_os.reviews.daily.enabled",
    ReviewCadence.WEEKLY_RETROSPECTIVE: "locus.life_os.reviews.weekly.enabled",
    ReviewCadence.MONTHLY_DEEP_REVIEW: "locus.life_os.reviews.monthly.enabled",
}

CADENCE_SCHEDULE_DEFAULTS: Dict[ReviewCadence, Dict[str, str]] = {
    ReviewCadence.DAILY_STANDUP: {
        "schedule": "Daily 07:30 IST",
        "model": "deepseek-v4-flash",
        "title": "Morning Standup Briefing",
    },
    ReviewCadence.WEEKLY_RETROSPECTIVE: {
        "schedule": "Sunday 02:00 IST",
        "model": "gemini-2.5-pro",
        "title": "Sunday Synthesis Retrospective",
    },
    ReviewCadence.MONTHLY_DEEP_REVIEW: {
        "schedule": "Monthly 1st 09:00 IST",
        "model": "gemini-2.5-pro",
        "title": "Monthly Deep Review",
    },
}


@dataclass
class ReviewPrompt:
    cadence: ReviewCadence
    title: str
    schedule: str
    model: str
    sections: List[str]
    context_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cadence": self.cadence.value,
            "title": self.title,
            "schedule": self.schedule,
            "model": self.model,
            "sections": self.sections,
            "context_data": self.context_data,
        }


@dataclass
class ReviewResult:
    cadence: ReviewCadence
    prompt: ReviewPrompt
    content: str
    generated_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    status: str = "ready"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cadence": self.cadence.value,
            "prompt": self.prompt.to_dict(),
            "content": self.content,
            "generated_at": self.generated_at,
            "status": self.status,
        }


class ReviewCadenceEngine:
    """
    Review Cadence Engine per SPEC §25.13.
    Manages generation of prompts and execution of daily standups,
    weekly retrospectives, and monthly deep reviews.
    """

    def is_cadence_enabled(self, cadence: ReviewCadence) -> Tuple[bool, str]:
        """Check whether specific review cadence is enabled in configuration."""
        # Master switches
        for master in ("locus.review_cadence_system.enabled", "locus.life_os.reviews.enabled"):
            val = config.get(master)
            if val is not None and not config.is_enabled(master):
                return False, master

        # Specific cadence switch
        cadence_switch = CADENCE_CONFIG_SWITCHES.get(cadence)
        if cadence_switch:
            val = config.get(cadence_switch)
            if val is not None and not config.is_enabled(cadence_switch):
                return False, cadence_switch

        return True, ""

    def build_daily_standup(self, context: Optional[Dict[str, Any]] = None) -> ReviewPrompt:
        """
        Build Daily Standup morning briefing prompt (07:30 IST).
        Surfaces operating mode, DCS score, timeline blocks, and orphan tasks.
        """
        ctx = context or {}
        dcs = ctx.get("dcs", 7.0)
        mode = ctx.get("mode", "DEEP_WORK")
        timeline = ctx.get("timeline", [])
        orphans = ctx.get("orphans", [])

        sections = [
            f"1. Energy & Capacity: Operating Mode {mode} (DCS {dcs})",
            f"2. Daily Timeline: {len(timeline)} time blocks scheduled with ultradian buffers",
            f"3. Goal Stack Integrity: {len(orphans)} orphan tasks detected for reparenting",
            "4. Top Priority Focus: Highest TWS tasks assigned to morning deep work",
        ]

        defaults = CADENCE_SCHEDULE_DEFAULTS[ReviewCadence.DAILY_STANDUP]
        return ReviewPrompt(
            cadence=ReviewCadence.DAILY_STANDUP,
            title=defaults["title"],
            schedule=defaults["schedule"],
            model=defaults["model"],
            sections=sections,
            context_data=ctx,
        )

    def build_weekly_retrospective(self, context: Optional[Dict[str, Any]] = None) -> ReviewPrompt:
        """
        Build Weekly Retrospective synthesis prompt (Sunday 02:00 IST via Gemini 2.5 Pro).
        Evaluates logged faction hours, deficits, deferral escalations, and momentum.
        """
        ctx = context or {}
        faction_hours = ctx.get("faction_hours", {})
        deficits = ctx.get("deficits", {})
        deferred_tasks = ctx.get("deferred_tasks", [])

        sections = [
            f"1. Faction Distribution: Logged hours across factions {list(faction_hours.keys())}",
            f"2. Faction Deficits: Under/over-represented allocations {deficits}",
            f"3. Deferral Log: {len(deferred_tasks)} tasks deferred >= 3 times needing parking/scoping",
            "4. Gemini 2.5 Pro Synthesis: Generate strategic adjustments and next week weights",
        ]

        defaults = CADENCE_SCHEDULE_DEFAULTS[ReviewCadence.WEEKLY_RETROSPECTIVE]
        return ReviewPrompt(
            cadence=ReviewCadence.WEEKLY_RETROSPECTIVE,
            title=defaults["title"],
            schedule=defaults["schedule"],
            model=defaults["model"],
            sections=sections,
            context_data=ctx,
        )

    def build_monthly_deep_review(self, context: Optional[Dict[str, Any]] = None) -> ReviewPrompt:
        """
        Build Monthly Deep Review prompt (Monthly 1st 09:00 IST).
        Evaluates milestone progress, long-term faction drift, and vision outcome updates.
        """
        ctx = context or {}
        milestones = ctx.get("milestones", [])
        monthly_hours = ctx.get("monthly_hours", {})

        sections = [
            f"1. Vision Outcomes: Progress review across {len(milestones)} active milestones",
            f"2. Monthly Faction Balance: Cumulative 4-week totals {monthly_hours}",
            "3. Goal Stack Evolution: Archive completed projects and reparent active daily threads",
            "4. Strategic Horizon Check: Assess 30-day trajectory against core Life OS objectives",
        ]

        defaults = CADENCE_SCHEDULE_DEFAULTS[ReviewCadence.MONTHLY_DEEP_REVIEW]
        return ReviewPrompt(
            cadence=ReviewCadence.MONTHLY_DEEP_REVIEW,
            title=defaults["title"],
            schedule=defaults["schedule"],
            model=defaults["model"],
            sections=sections,
            context_data=ctx,
        )

    def generate_review(
        self,
        cadence: ReviewCadence,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReviewResult:
        """
        Generate review package for specified cadence.
        """
        enabled, switch = self.is_cadence_enabled(cadence)
        if not enabled:
            raise ValueError(f"Review cadence {cadence.value} is disabled by {switch}")

        if cadence == ReviewCadence.DAILY_STANDUP:
            prompt = self.build_daily_standup(context)
            content = f"# Morning Standup Briefing\n" + "\n".join(prompt.sections)
        elif cadence == ReviewCadence.WEEKLY_RETROSPECTIVE:
            prompt = self.build_weekly_retrospective(context)
            content = f"# Sunday Synthesis Retrospective (Gemini 2.5 Pro)\n" + "\n".join(prompt.sections)
        elif cadence == ReviewCadence.MONTHLY_DEEP_REVIEW:
            prompt = self.build_monthly_deep_review(context)
            content = f"# Monthly Deep Review\n" + "\n".join(prompt.sections)
        else:
            raise ValueError(f"Unknown cadence: {cadence}")

        return ReviewResult(
            cadence=cadence,
            prompt=prompt,
            content=content,
            status="ready",
        )

    def list_cadences(self) -> List[Dict[str, Any]]:
        """List all review cadences with active status and schedule metadata."""
        items: List[Dict[str, Any]] = []
        for cad in ReviewCadence:
            enabled, switch = self.is_cadence_enabled(cad)
            defaults = CADENCE_SCHEDULE_DEFAULTS[cad]
            items.append({
                "cadence": cad.value,
                "title": defaults["title"],
                "schedule": defaults["schedule"],
                "model": defaults["model"],
                "enabled": enabled,
                "disabled_by": switch if not enabled else None,
            })
        return items
