"""
SPEC §25.13 lines 4883-4896: Unit tests for Review Cadence System (F-0114 / US-91).
Tests:
- Daily standup (morning briefing 07:30 IST)
- Weekly retrospective (Sunday synthesis via Gemini 2.5 Pro)
- Monthly deep review (monthly 1st 09:00 IST)
- Independent cadence toggleability (daily, weekly, monthly)
- Master modular off-switch returning HTTP 503
- Provider swappability
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

import sidecar.config as config
from sidecar.life_os.reviews import (
    ReviewCadence,
    ReviewCadenceEngine,
)
from sidecar.providers.reviews import (
    BaseReviewCadenceProvider,
    DefaultReviewCadenceProvider,
)


def test_daily_standup_generation() -> None:
    """SPEC §25.13 line 4889: "daily standup (morning briefing)" """
    engine = ReviewCadenceEngine()

    context = {
        "dcs": 6.5,
        "mode": "NORMAL",
        "timeline": [{"block": "deep", "task": "Write Review Tests"}],
        "orphans": [{"id": "t-1", "title": "Orphan"}],
    }

    res = engine.generate_review(ReviewCadence.DAILY_STANDUP, context)
    assert res.status == "ready"
    assert res.cadence == ReviewCadence.DAILY_STANDUP
    assert res.prompt.schedule == "Daily 07:30 IST"
    assert "DCS 6.5" in res.content
    assert "1 orphan tasks detected" in res.content


def test_weekly_retrospective_generation_gemini_pro() -> None:
    """SPEC §25.13 line 4889: "weekly retrospective (Sunday synthesis via Gemini 2.5 Pro)" """
    engine = ReviewCadenceEngine()

    context = {
        "faction_hours": {"Craft": 30.0, "Health": 10.0},
        "deficits": {"Health": 0.15, "Craft": -0.10},
        "deferred_tasks": [{"id": "t-def", "deferrals": 4}],
    }

    res = engine.generate_review(ReviewCadence.WEEKLY_RETROSPECTIVE, context)
    assert res.status == "ready"
    assert res.cadence == ReviewCadence.WEEKLY_RETROSPECTIVE
    assert res.prompt.schedule == "Sunday 02:00 IST"
    assert res.prompt.model == "gemini-2.5-pro"
    assert "Sunday Synthesis Retrospective" in res.content
    assert "Gemini 2.5 Pro" in res.content


def test_monthly_deep_review_generation() -> None:
    """SPEC §25.13 line 4889: "monthly deep review." """
    engine = ReviewCadenceEngine()

    context = {
        "milestones": [{"id": "m1", "title": "Framework Complete"}],
        "monthly_hours": {"Craft": 120.0, "Health": 80.0},
    }

    res = engine.generate_review(ReviewCadence.MONTHLY_DEEP_REVIEW, context)
    assert res.status == "ready"
    assert res.cadence == ReviewCadence.MONTHLY_DEEP_REVIEW
    assert res.prompt.schedule == "Monthly 1st 09:00 IST"
    assert "Monthly Deep Review" in res.content


def test_independent_cadence_toggles() -> None:
    """SPEC §25.13 line 4893: "Swappable / off state: each review cadence toggleable independently. Off → no automatic review prompts." """
    provider = DefaultReviewCadenceProvider()

    # Disable daily standup specifically
    config.set("locus.life_os.reviews.daily.enabled", False)
    res_daily = provider.generate_review("daily_standup")
    assert res_daily.get("status_code") == 503
    assert res_daily.get("disabled") == "locus.life_os.reviews.daily.enabled"

    # Weekly and monthly must remain enabled
    res_weekly = provider.generate_review("weekly_retrospective")
    assert res_weekly.get("status") == "ok"

    res_monthly = provider.generate_review("monthly_deep_review")
    assert res_monthly.get("status") == "ok"
    config.set("locus.life_os.reviews.daily.enabled", True)

    # Disable weekly retrospective specifically
    config.set("locus.life_os.reviews.weekly.enabled", False)
    res_weekly_off = provider.generate_review("weekly_retrospective")
    assert res_weekly_off.get("status_code") == 503
    assert res_weekly_off.get("disabled") == "locus.life_os.reviews.weekly.enabled"

    # Daily must remain enabled
    res_daily_ok = provider.generate_review("daily_standup")
    assert res_daily_ok.get("status") == "ok"
    config.set("locus.life_os.reviews.weekly.enabled", True)


def test_master_modular_off_switches() -> None:
    """SPEC §25.13 line 4893: Master modular off-switches returning HTTP 503."""
    provider = DefaultReviewCadenceProvider()

    # Master switch locus.review_cadence_system.enabled
    config.set("locus.review_cadence_system.enabled", False)
    res = provider.generate_review("daily_standup")
    assert res.get("status_code") == 503
    assert res.get("disabled") == "locus.review_cadence_system.enabled"

    assert provider.list_cadences().get("status_code") == 503
    config.set("locus.review_cadence_system.enabled", True)

    # Master switch locus.life_os.reviews.enabled
    config.set("locus.life_os.reviews.enabled", False)
    res2 = provider.generate_review("weekly_retrospective")
    assert res2.get("status_code") == 503
    assert res2.get("disabled") == "locus.life_os.reviews.enabled"
    config.set("locus.life_os.reviews.enabled", True)


def test_swappable_reviews_provider_contract() -> None:
    """SPEC §25.13: Swappable Review Cadence Provider contract."""
    class CustomReviewsProvider(BaseReviewCadenceProvider):
        @property
        def name(self) -> str:
            return "custom_reviews"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def generate_review(self, cadence: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def list_cadences(self) -> dict[str, Any]:
            return {"status": "ok", "custom_cadences": []}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "provider": self.name}

    custom = CustomReviewsProvider()
    assert custom.name == "custom_reviews"
    assert custom.generate_review("daily_standup")["custom"] is True
