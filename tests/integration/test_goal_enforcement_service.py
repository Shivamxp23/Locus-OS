"""
SPEC §25.14 lines 4897-4909: Integration tests for Goal Stack Enforcement endpoints (F-0115 / US-92).
Tests FastAPI endpoints under /goal-enforcement/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.goal_enforcement import GoalStackEnforcer
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)
from sidecar.providers.goal_enforcement import DefaultGoalStackEnforcementProvider
from sidecar.service import create_app


def build_test_stack() -> ThreeLayerGoalStack:
    stack = ThreeLayerGoalStack()
    stack.add_node(
        GoalNode(
            id="outcome-alpha",
            title="Vision Outcome Alpha",
            level=GoalStackLevel.VISION,
            faction="Craft",
        )
    )
    stack.add_node(
        GoalNode(
            id="proj-alpha",
            title="Project Milestone Alpha",
            level=GoalStackLevel.MILESTONE,
            parent_id="outcome-alpha",
            faction="Craft",
        )
    )
    stack.add_node(
        GoalNode(
            id="task-alpha",
            title="Task Alpha",
            level=GoalStackLevel.DAILY,
            parent_id="proj-alpha",
            faction="Craft",
        )
    )
    return stack


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    enforcer = GoalStackEnforcer()
    stack = build_test_stack()
    provider = DefaultGoalStackEnforcementProvider(enforcer=enforcer, stack=stack)
    app.state.goal_enforcement_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.goal_stack_enforcement.enabled", True)
    config.set("locus.life_os.goal_enforcement.enabled", True)
    yield
    config.set("locus.goal_stack_enforcement.enabled", True)
    config.set("locus.life_os.goal_enforcement.enabled", True)


def test_goal_enforcement_service_enforce_task_endpoint(client: TestClient) -> None:
    """SPEC §25.14: POST /goal-enforcement/enforce-task."""
    # Enforce existing valid task
    payload = {"task_id": "task-alpha"}
    res = client.post("/goal-enforcement/enforce-task", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["allowed"] is True
    assert data["valid"] is True
    assert data["enforced"] is True

    # Enforce with dynamic stack nodes including an orphan
    dynamic_payload = {
        "task_id": "orphan-dyn-task",
        "stack_nodes": [
            {
                "id": "orphan-dyn-task",
                "title": "Orphan dynamic task",
                "level": "daily",
                "parent_id": None,
            }
        ],
    }
    res_orphan = client.post("/goal-enforcement/enforce-task", json=dynamic_payload)
    assert res_orphan.status_code == 200
    data_orphan = res_orphan.json()
    assert data_orphan["allowed"] is False
    assert data_orphan["valid"] is False


def test_goal_enforcement_service_enforce_project_endpoint(client: TestClient) -> None:
    """SPEC §25.14: POST /goal-enforcement/enforce-project."""
    payload = {"project_id": "proj-alpha"}
    res = client.post("/goal-enforcement/enforce-project", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["allowed"] is True
    assert data["valid"] is True


def test_goal_enforcement_service_briefing_orphans_endpoint(client: TestClient) -> None:
    """SPEC §25.14: GET & POST /goal-enforcement/briefing-orphans."""
    # GET clean stack
    res = client.get("/goal-enforcement/briefing-orphans")
    assert res.status_code == 200
    data = res.json()
    assert data["orphan_count"] == 0
    assert "0 orphan tasks detected" in data["briefing_text"]

    # POST with orphans in stack_nodes
    post_payload = {
        "stack_nodes": [
            {"id": "o-task", "title": "Orphan Task 1", "level": "daily", "parent_id": None},
            {"id": "o-proj", "title": "Orphan Proj 1", "level": "milestone", "parent_id": None},
        ]
    }
    res_post = client.post("/goal-enforcement/briefing-orphans", json=post_payload)
    assert res_post.status_code == 200
    data_post = res_post.json()
    assert data_post["orphan_count"] == 2
    assert "Morning Briefing Alert" in data_post["briefing_text"]


def test_goal_enforcement_service_audit_endpoint(client: TestClient) -> None:
    """SPEC §25.14: POST /goal-enforcement/audit."""
    payload = {
        "stack_nodes": [
            {"id": "vis-1", "title": "Vision", "level": "vision", "faction": "Craft"},
            {"id": "proj-1", "title": "Project", "level": "milestone", "parent_id": "vis-1"},
            {"id": "task-1", "title": "Task", "level": "daily", "parent_id": "proj-1"},
        ]
    }
    res = client.post("/goal-enforcement/audit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["allowed"] is True
    assert data["valid"] is True


def test_goal_enforcement_service_status_endpoint(client: TestClient) -> None:
    """SPEC §25.14: GET /goal-enforcement/status."""
    res = client.get("/goal-enforcement/status")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "default_goal_stack_enforcement_provider"
    assert data["master_enabled"] is True
    assert data["subsystem_enabled"] is True


def test_goal_enforcement_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §25.14: Modular off-switches returning HTTP 503."""
    config.set("locus.goal_stack_enforcement.enabled", False)

    res_task = client.post("/goal-enforcement/enforce-task", json={"task_id": "task-alpha"})
    assert res_task.status_code == 503
    assert res_task.json()["disabled"] == "locus.goal_stack_enforcement.enabled"

    res_proj = client.post("/goal-enforcement/enforce-project", json={"project_id": "proj-alpha"})
    assert res_proj.status_code == 503

    res_orphans_get = client.get("/goal-enforcement/briefing-orphans")
    assert res_orphans_get.status_code == 503

    res_orphans_post = client.post("/goal-enforcement/briefing-orphans", json={})
    assert res_orphans_post.status_code == 503

    res_audit = client.post("/goal-enforcement/audit", json={})
    assert res_audit.status_code == 503

    res_status = client.get("/goal-enforcement/status")
    assert res_status.status_code == 503
