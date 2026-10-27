"""
SPEC §25.5-25.8 & §25.12: Integration tests for Operating Modes & Scheduler service routes (F-0056 / US-86).
Tests FastAPI endpoints under /scheduler/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.life_os.deferral import DeferralTracker
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)
from sidecar.life_os.scheduler import SixStepSchedulerEngine
from sidecar.providers.scheduler import DefaultSchedulerProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    goal_stack = ThreeLayerGoalStack()

    # Pre-populate valid goal stack hierarchy
    vision = GoalNode(id="v-root", title="Vision Outcome", level=GoalStackLevel.VISION, faction="Craft")
    milestone = GoalNode(id="m-project", title="Milestone Project", level=GoalStackLevel.MILESTONE, parent_id="v-root")
    task = GoalNode(id="t-daily", title="Daily Task", level=GoalStackLevel.DAILY, parent_id="m-project")
    for n in (vision, milestone, task):
        goal_stack.add_node(n)

    deferral_tracker = DeferralTracker()
    engine = SixStepSchedulerEngine(goal_stack=goal_stack)
    provider = DefaultSchedulerProvider(
        goal_stack=goal_stack,
        deferral_tracker=deferral_tracker,
        scheduler_engine=engine,
    )
    app.state.operating_modes_scheduler_provider = provider
    return TestClient(app)


def test_scheduler_service_goal_stack_and_orphans(client: TestClient) -> None:
    """SPEC §25.5: POST /scheduler/goal-stack/validate and GET /scheduler/goal-stack/orphans."""
    res = client.post("/scheduler/goal-stack/validate")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["valid"] is True
    assert data["orphan_count"] == 0

    orphans_res = client.get("/scheduler/goal-stack/orphans")
    assert orphans_res.status_code == 200
    orphans_data = orphans_res.json()
    assert orphans_data["status"] == "ok"
    assert orphans_data["orphan_count"] == 0


def test_scheduler_service_action_gap_evaluation(client: TestClient) -> None:
    """SPEC §25.6: POST /scheduler/action-gap/evaluate."""
    payload = {
        "factions": {
            "Craft": {"declared_priority": 8.0, "actual_hours": 16.0, "target_hours": 20.0},
            "Health": {"declared_priority": 9.0, "actual_hours": 2.0, "target_hours": 20.0},
        }
    }
    res = client.post("/scheduler/action-gap/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert len(data["reports"]) == 2
    assert data["alerts_count"] == 1


def test_scheduler_service_deferral_lifecycle(client: TestClient) -> None:
    """SPEC §25.7: POST /scheduler/deferral/record and GET /scheduler/deferral/status/{task_id}."""
    # 1st deferral
    res1 = client.post("/scheduler/deferral/record", json={"task_id": "test-task-1", "reason": "delayed"})
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["status"] == "ok"
    assert d1["record"]["deferral_count"] == 1
    assert d1["record"]["action"] == "normal"

    # Status route
    status_res = client.get("/scheduler/deferral/status/test-task-1")
    assert status_res.status_code == 200
    assert status_res.json()["record"]["deferral_count"] == 1


def test_scheduler_service_lag_bonus(client: TestClient) -> None:
    """SPEC §25.8: POST /scheduler/lag/bonus."""
    res_crisis = client.post("/scheduler/lag/bonus", json={"lag_hours": 7.5})
    assert res_crisis.status_code == 200
    data = res_crisis.json()
    assert data["status"] == "ok"
    assert data["tws_lag_bonus"] == 4.0
    assert data["is_crisis"] is True


def test_scheduler_service_schedule_generate(client: TestClient) -> None:
    """SPEC §25.12: POST /scheduler/schedule/generate."""
    tasks = [
        {"id": "t-daily", "title": "Daily Task", "difficulty": 6, "leverage": 7, "urgency": 8, "project_id": "m-project"},
    ]
    res = client.post("/scheduler/schedule/generate", json={"dcs": 7.0, "tasks": tasks, "enforce_goal_stack": True})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["mode"] == "DEEP_WORK"
    assert len(data["timeline"]) > 0
    assert data["goal_stack_validation"]["passed"] is True


def test_scheduler_service_status(client: TestClient) -> None:
    """SPEC §25.5: GET /scheduler/status diagnostic endpoint."""
    res = client.get("/scheduler/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "default_scheduler_provider"
    assert "goal_stack_nodes_count" in data


def test_scheduler_service_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify HTTP 503 when locus.operating_modes_scheduler.enabled or sub-switches are disabled."""
    # Test master switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.operating_modes_scheduler.enabled" else True)
    res = client.get("/scheduler/status")
    assert res.status_code == 503
    assert res.json()["disabled"] == "locus.operating_modes_scheduler.enabled"

    # Test goal_stack sub-switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.life_os.goal_stack.enabled" else True)
    res_gs = client.post("/scheduler/goal-stack/validate")
    assert res_gs.status_code == 503
    assert res_gs.json()["disabled"] == "locus.life_os.goal_stack.enabled"

    # Test action_gap sub-switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.life_os.action_gap.enabled" else True)
    res_ag = client.post("/scheduler/action-gap/evaluate", json={"factions": {}})
    assert res_ag.status_code == 503
    assert res_ag.json()["disabled"] == "locus.life_os.action_gap.enabled"

    # Test deferral sub-switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.life_os.deferral.enabled" else True)
    res_def = client.post("/scheduler/deferral/record", json={"task_id": "t1"})
    assert res_def.status_code == 503
    assert res_def.json()["disabled"] == "locus.life_os.deferral.enabled"
