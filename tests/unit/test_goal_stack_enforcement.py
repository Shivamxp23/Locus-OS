"""
SPEC §25.14 lines 4897-4909: Goal Stack Enforcement Unit Tests (F-0115 / US-92).
"""
import pytest
from sidecar import config
from sidecar.life_os.goal_enforcement import (
    BriefingOrphanReport,
    EnforcementResult,
    GoalStackEnforcer,
)
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)
from sidecar.providers.goal_enforcement import (
    BaseGoalStackEnforcementProvider,
    DefaultGoalStackEnforcementProvider,
)


@pytest.fixture(autouse=True)
def clean_config():
    """Reset configuration keys around each test."""
    config.set("locus.goal_stack_enforcement.enabled", True)
    config.set("locus.life_os.goal_enforcement.enabled", True)
    yield
    config.set("locus.goal_stack_enforcement.enabled", True)
    config.set("locus.life_os.goal_enforcement.enabled", True)


def create_sample_stack() -> ThreeLayerGoalStack:
    """Helper creating a sample 3-layer stack."""
    stack = ThreeLayerGoalStack()
    # Outcome (Vision)
    stack.add_node(
        GoalNode(
            id="outcome-1",
            title="Master Distributed Systems",
            level=GoalStackLevel.VISION,
            faction="Craft",
        )
    )
    # Project (Milestone)
    stack.add_node(
        GoalNode(
            id="proj-1",
            title="Ship Raft Consensus Engine",
            level=GoalStackLevel.MILESTONE,
            parent_id="outcome-1",
            faction="Craft",
        )
    )
    # Daily Task
    stack.add_node(
        GoalNode(
            id="task-1",
            title="Implement Log Compaction Tests",
            level=GoalStackLevel.DAILY,
            parent_id="proj-1",
            faction="Craft",
        )
    )
    return stack


def test_valid_goal_stack_enforcement():
    """SPEC §25.14 line 4901: "every task MUST parent to a project; every project MUST parent to an outcome." """
    stack = create_sample_stack()
    enforcer = GoalStackEnforcer()

    # Valid task enforcement
    task_res = enforcer.enforce_task("task-1", stack)
    assert task_res.allowed is True
    assert task_res.enforced is True
    assert task_res.valid is True
    assert task_res.details["outcome_id"] == "outcome-1"

    # Valid project enforcement
    proj_res = enforcer.enforce_project("proj-1", stack)
    assert proj_res.allowed is True
    assert proj_res.enforced is True
    assert proj_res.valid is True
    assert proj_res.details["outcome_id"] == "outcome-1"


def test_orphan_task_enforcement_rejection():
    """SPEC §25.14 line 4901: "every task MUST parent to a project; every project MUST parent to an outcome." """
    stack = create_sample_stack()
    enforcer = GoalStackEnforcer()

    # Add orphan task (missing parent)
    stack.add_node(
        GoalNode(
            id="task-orphan-1",
            title="Unparented Random Coding Task",
            level=GoalStackLevel.DAILY,
            parent_id=None,
        )
    )

    res = enforcer.enforce_task("task-orphan-1", stack)
    assert res.allowed is False
    assert res.enforced is True
    assert res.valid is False
    assert any("Orphan task detected" in r for r in res.reasons)

    # Add task with non-existent parent
    stack.add_node(
        GoalNode(
            id="task-orphan-2",
            title="Ghost Parent Task",
            level=GoalStackLevel.DAILY,
            parent_id="non-existent-proj",
        )
    )
    res2 = enforcer.enforce_task("task-orphan-2", stack)
    assert res2.allowed is False
    assert res2.valid is False


def test_orphan_project_enforcement_rejection():
    """SPEC §25.14 line 4901: "every task MUST parent to a project; every project MUST parent to an outcome." """
    stack = create_sample_stack()
    enforcer = GoalStackEnforcer()

    # Add unparented project
    stack.add_node(
        GoalNode(
            id="proj-orphan-1",
            title="Orphan Project Milestone",
            level=GoalStackLevel.MILESTONE,
            parent_id=None,
        )
    )

    proj_res = enforcer.enforce_project("proj-orphan-1", stack)
    assert proj_res.allowed is False
    assert proj_res.enforced is True
    assert proj_res.valid is False
    assert any("Orphan project detected" in r for r in proj_res.reasons)

    # Task under orphan project must also fail enforcement
    stack.add_node(
        GoalNode(
            id="task-child-of-orphan-proj",
            title="Task under unparented project",
            level=GoalStackLevel.DAILY,
            parent_id="proj-orphan-1",
        )
    )
    task_res = enforcer.enforce_task("task-child-of-orphan-proj", stack)
    assert task_res.allowed is False
    assert task_res.valid is False
    assert any("Orphan project detected" in r for r in task_res.reasons)


def test_off_switch_allows_orphan_tasks():
    """SPEC §25.14 line 4905: "Swappable / off state: locus.life_os.goal_enforcement.enabled. Off -> orphan tasks are allowed." """
    stack = create_sample_stack()
    enforcer = GoalStackEnforcer()

    stack.add_node(
        GoalNode(
            id="task-orphan-allowed",
            title="Free floating exploratory task",
            level=GoalStackLevel.DAILY,
            parent_id=None,
        )
    )

    # Disable goal enforcement
    config.set("locus.life_os.goal_enforcement.enabled", False)
    assert enforcer.is_enforcement_enabled() is False

    # Enforcement is bypassed: allowed=True, enforced=False
    res = enforcer.enforce_task("task-orphan-allowed", stack)
    assert res.allowed is True
    assert res.enforced is False
    assert res.valid is True
    assert res.details.get("bypass") is True


def test_surface_orphans_for_morning_briefing():
    """SPEC §25.14 line 4901: "Orphan tasks surfaced during morning briefing." """
    stack = create_sample_stack()
    enforcer = GoalStackEnforcer()

    # When clean:
    clean_report = enforcer.surface_orphans_for_briefing(stack)
    assert clean_report.orphan_count == 0
    assert "0 orphan tasks detected" in clean_report.briefing_text

    # Add orphan task and orphan project
    stack.add_node(
        GoalNode(
            id="task-orphan-briefing",
            title="Review obscure protocol paper",
            level=GoalStackLevel.DAILY,
            parent_id=None,
        )
    )
    stack.add_node(
        GoalNode(
            id="proj-orphan-briefing",
            title="Explore legacy repo",
            level=GoalStackLevel.MILESTONE,
            parent_id=None,
        )
    )

    alert_report = enforcer.surface_orphans_for_briefing(stack)
    assert alert_report.orphan_count == 2
    assert "Morning Briefing Alert: 1 orphan task(s) and 1 orphan project(s) detected" in alert_report.briefing_text
    assert "Review obscure protocol paper" in alert_report.briefing_text


def test_provider_contract_and_modular_off_switch():
    """SPEC §25.14 lines 4897-4909: Provider contract and modular off-switch locus.goal_stack_enforcement.enabled."""
    stack = create_sample_stack()
    provider = DefaultGoalStackEnforcementProvider(stack=stack)
    assert isinstance(provider, BaseGoalStackEnforcementProvider)
    assert provider.name == "default_goal_stack_enforcement_provider"

    # Enforce task through provider
    res = provider.enforce_task("task-1")
    assert res["allowed"] is True
    assert res["valid"] is True

    # Disable master switch -> 503
    config.set("locus.goal_stack_enforcement.enabled", False)
    off_task = provider.enforce_task("task-1")
    assert off_task["status_code"] == 503
    assert off_task["disabled"] == "locus.goal_stack_enforcement.enabled"

    off_proj = provider.enforce_project("proj-1")
    assert off_proj["status_code"] == 503

    off_orphans = provider.surface_briefing_orphans()
    assert off_orphans["status_code"] == 503

    off_audit = provider.audit_stack()
    assert off_audit["status_code"] == 503
