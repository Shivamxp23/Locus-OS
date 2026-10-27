"""
SPEC §25.12 lines 4801-4882: Integration tests for Goal Tracker & Faction Balancer endpoints (F-0057 / US-90).
Tests FastAPI endpoints under /goal-tracker/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.faction_balancer import FactionBalancer
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)
from sidecar.providers.goal_tracker import DefaultGoalTrackerProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    stack = ThreeLayerGoalStack()
    # Populate a test tree
    vis = GoalNode(id="v1", title="Career Mastery", level=GoalStackLevel.VISION, faction="Craft")
    proj = GoalNode(id="p1", title="Deliver Engine", level=GoalStackLevel.MILESTONE, parent_id="v1")
    task = GoalNode(id="t1", title="Write Tests", level=GoalStackLevel.DAILY, parent_id="p1")
    orphan = GoalNode(id="t-orphan", title="Orphan Task", level=GoalStackLevel.DAILY, parent_id=None)

    stack.add_node(vis)
    stack.add_node(proj)
    stack.add_node(task)
    stack.add_node(orphan)

    balancer = FactionBalancer()
    provider = DefaultGoalTrackerProvider(goal_stack=stack, balancer=balancer)
    app.state.goal_tracker_provider = provider
    return TestClient(app)


def test_goal_tracker_service_validate_endpoint(client: TestClient) -> None:
    """SPEC §25.12 Step 6: POST /goal-tracker/validate endpoint."""
    res = client.post("/goal-tracker/validate", json={"task_id": "t1"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["valid"] is True

    # Validate orphan task
    res_orphan = client.post("/goal-tracker/validate", json={"task_id": "t-orphan"})
    assert res_orphan.status_code == 200
    data_orphan = res_orphan.json()
    assert data_orphan["valid"] is False
    assert "Orphan" in data_orphan["message"]


def test_goal_tracker_service_orphans_endpoint(client: TestClient) -> None:
    """SPEC §25.12 Step 6: GET /goal-tracker/orphans endpoint."""
    res = client.get("/goal-tracker/orphans")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["count"] >= 1
    orphan_ids = [o["node_id"] for o in data["orphans"]]
    assert "t-orphan" in orphan_ids


def test_goal_tracker_service_balance_and_assignment_endpoints(client: TestClient) -> None:
    """SPEC §25.12 Step 4: Balance evaluation and assignment gating endpoints."""
    # Balance check
    allocs = {
        "allocations_minutes": {
            "Craft": 2400.0,
            "Health": 1500.0,
            "Leverage": 1200.0,
            "Expression": 900.0,
        }
    }
    res_b = client.post("/goal-tracker/balance-check", json=allocs)
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["status"] == "ok"
    assert data_b["balance_report"]["compliant"] is True

    # Assignment gating check
    assignment_payload = {
        "candidate_faction": "Craft",
        "proposed_minutes": 90.0,
        "current_allocations": {"Craft": 500.0, "Health": 50.0},
        "waiting_factions": ["Health"],
    }
    res_a = client.post("/goal-tracker/assignment-allowed", json=assignment_payload)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["status"] == "ok"
    assert data_a["allowed"] is False
    assert "blocked" in data_a["message"].lower()


def test_goal_tracker_service_status_endpoint(client: TestClient) -> None:
    """SPEC §25.12: GET /goal-tracker/status diagnostic endpoint."""
    res = client.get("/goal-tracker/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "default_goal_tracker_provider"
    assert data["enabled"] is True


def test_goal_tracker_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §25.12: Modular off-switches returning HTTP 503."""
    config.set("locus.goal_tracker_3_layer_stack.enabled", False)
    try:
        res = client.post("/goal-tracker/validate", json={"task_id": "t1"})
        assert res.status_code == 503
        data = res.json()
        assert "disabled" in data

        res_orphans = client.get("/goal-tracker/orphans")
        assert res_orphans.status_code == 503

        res_status = client.get("/goal-tracker/status")
        assert res_status.status_code == 503
    finally:
        config.set("locus.goal_tracker_3_layer_stack.enabled", True)

    config.set("locus.life_os.goal_tracker.enabled", False)
    try:
        res2 = client.post("/goal-tracker/validate", json={"task_id": "t1"})
        assert res2.status_code == 503
    finally:
        config.set("locus.life_os.goal_tracker.enabled", True)
