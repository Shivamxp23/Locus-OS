"""
SPEC §25.13 lines 4883-4896: Integration tests for Review Cadence System endpoints (F-0114 / US-91).
Tests FastAPI endpoints under /reviews/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.reviews import ReviewCadenceEngine
from sidecar.providers.reviews import DefaultReviewCadenceProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    engine = ReviewCadenceEngine()
    provider = DefaultReviewCadenceProvider(engine=engine)
    app.state.reviews_provider = provider
    return TestClient(app)


def test_reviews_service_generate_daily_standup_endpoint(client: TestClient) -> None:
    """SPEC §25.13: POST /reviews/generate endpoint for daily standup."""
    payload = {
        "cadence": "daily_standup",
        "context": {
            "dcs": 8.5,
            "mode": "PEAK",
            "timeline": [{"block": "deep", "duration": 90}],
            "orphans": [],
        },
    }
    res = client.post("/reviews/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    review = data["review"]
    assert review["cadence"] == "daily_standup"
    assert "Morning Standup Briefing" in review["content"]
    assert "DCS 8.5" in review["content"]


def test_reviews_service_generate_weekly_retrospective_endpoint(client: TestClient) -> None:
    """SPEC §25.13: POST /reviews/generate endpoint for weekly retrospective."""
    payload = {
        "cadence": "weekly_retrospective",
        "context": {
            "faction_hours": {"Craft": 45.0, "Health": 20.0},
            "deficits": {"Craft": -0.15, "Health": 0.05},
        },
    }
    res = client.post("/reviews/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    review = data["review"]
    assert review["cadence"] == "weekly_retrospective"
    assert review["prompt"]["model"] == "gemini-2.5-pro"
    assert "Sunday Synthesis Retrospective" in review["content"]


def test_reviews_service_scheduled_endpoint(client: TestClient) -> None:
    """SPEC §25.13: GET /reviews/scheduled endpoint listing cadences."""
    res = client.get("/reviews/scheduled")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    cadences = data["cadences"]
    cad_names = [c["cadence"] for c in cadences]
    assert "daily_standup" in cad_names
    assert "weekly_retrospective" in cad_names
    assert "monthly_deep_review" in cad_names


def test_reviews_service_status_endpoint(client: TestClient) -> None:
    """SPEC §25.13: GET /reviews/status diagnostic endpoint."""
    res = client.get("/reviews/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "default_review_cadence_provider"
    assert data["enabled"] is True


def test_reviews_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §25.13: Modular off-switches returning HTTP 503."""
    # Master switch
    config.set("locus.review_cadence_system.enabled", False)
    try:
        res = client.post("/reviews/generate", json={"cadence": "daily_standup"})
        assert res.status_code == 503
        data = res.json()
        assert "disabled" in data

        res_sched = client.get("/reviews/scheduled")
        assert res_sched.status_code == 503

        res_status = client.get("/reviews/status")
        assert res_status.status_code == 503
    finally:
        config.set("locus.review_cadence_system.enabled", True)

    # Specific cadence switch
    config.set("locus.life_os.reviews.daily.enabled", False)
    try:
        res_daily = client.post("/reviews/generate", json={"cadence": "daily_standup"})
        assert res_daily.status_code == 503
        assert res_daily.json()["disabled"] == "locus.life_os.reviews.daily.enabled"

        # Weekly remains accessible
        res_weekly = client.post("/reviews/generate", json={"cadence": "weekly_retrospective"})
        assert res_weekly.status_code == 200
    finally:
        config.set("locus.life_os.reviews.daily.enabled", True)
