"""Test suite for Wave 8A: Observability, Diagnostics, Notifications & Code Graph.

Covers:
- F-0065: Error Classifier (§29.1)
- F-0067: Notifications (§29.4)
- F-0069: Code Graph Analysis (§29.6)
- F-0070: Subconscious Background Processing (§29.7)
- F-0071: Workflows Engine (§29.8)
- F-0064: Dual Interface / Check-ins (§28.1-28.6)
"""

import time
import pytest

from sidecar.diagnostics.error_classifier import ErrorCategory, ClassifiedError, ErrorClassifier
from sidecar.gateway.notifications import NotificationPriority, NotificationPayload, NotificationDispatcher
from sidecar.codegraph.graph import SymbolKind, CodeSymbolNode, CodeDependencyGraph
from sidecar.subconscious.subconscious_engine import SubconsciousTask, SubconsciousTaskState, SubconsciousEngine
from sidecar.workflows.workflow import StepStatus, WorkflowStep, WorkflowExecutionResult, WorkflowEngine
from sidecar.interface.dual_interface import CheckInType, CheckInSchedule, DualInterfaceBridge


# -----------------------------------------------------------------------------
# F-0065: Error Classifier
# -----------------------------------------------------------------------------
def test_error_classifier_unit():
    classifier = ErrorClassifier()
    err = "Rate limit reached for gpt-4o: TPM limit 30000 exceeded. Please retry after 15s."
    classified = classifier.classify(err)
    assert classified.category == ErrorCategory.RATE_LIMIT
    assert classified.is_retryable is True
    assert classified.retry_delay_seconds == 15.0


def test_error_classifier_integration():
    classifier = ErrorClassifier()
    # Context overflow
    c1 = classifier.classify("Prompt tokens 132000 exceeded maximum context length 128000")
    assert c1.category == ErrorCategory.CONTEXT_OVERFLOW
    assert c1.is_retryable is False

    # Auth failure
    c2 = classifier.classify("401 Unauthorized: Invalid API key provided")
    assert c2.category == ErrorCategory.AUTH_FAILURE

    # Timeout
    c3 = classifier.classify("Request timed out after 30000ms")
    assert c3.category == ErrorCategory.TIMEOUT
    assert c3.is_retryable is True


# -----------------------------------------------------------------------------
# F-0067: Notifications
# -----------------------------------------------------------------------------
def test_notifications_unit():
    dispatcher = NotificationDispatcher(throttle_window_seconds=1.0)
    payload = NotificationPayload(
        title="Build Complete",
        body="All 22 unit tests passed.",
        priority=NotificationPriority.NORMAL,
        category="ci",
    )
    res = dispatcher.dispatch(payload)
    assert res.get("desktop") is True
    assert len(dispatcher.history) == 1


def test_notifications_integration():
    dispatcher = NotificationDispatcher(throttle_window_seconds=10.0)
    delivered_alerts = []

    dispatcher.register_handler("telegram", lambda p: delivered_alerts.append(p.title) or True)

    p1 = NotificationPayload("Alert 1", "Initial warning", priority=NotificationPriority.NORMAL, category="system")
    res1 = dispatcher.dispatch(p1)
    assert res1.get("telegram") is True

    # Throttled duplicate
    p2 = NotificationPayload("Alert 2", "Duplicate warning", priority=NotificationPriority.NORMAL, category="system")
    res2 = dispatcher.dispatch(p2)
    assert res2.get("throttled") is True

    # Urgent bypasses throttle
    p3 = NotificationPayload("Urgent 3", "Emergency halt", priority=NotificationPriority.URGENT, category="system")
    res3 = dispatcher.dispatch(p3)
    assert res3.get("telegram") is True
    assert len(delivered_alerts) == 2


# -----------------------------------------------------------------------------
# F-0069: Code Graph Analysis
# -----------------------------------------------------------------------------
def test_codegraph_unit():
    graph = CodeDependencyGraph()
    py_code = """
class BaseService:
    def execute(self):
        pass

class UserService(BaseService):
    def get_user(self):
        return "Alice"
"""
    extracted = graph.parse_python_source("service.py", py_code)
    assert len(extracted) >= 2
    assert "UserService" in graph.nodes
    assert "BaseService" in graph.edges["UserService"]


def test_codegraph_integration():
    graph = CodeDependencyGraph()
    n1 = CodeSymbolNode("DatabaseEngine", SymbolKind.CLASS, "db.py", 10)
    n2 = CodeSymbolNode("Repository", SymbolKind.CLASS, "repo.py", 20)
    n3 = CodeSymbolNode("ApiController", SymbolKind.CLASS, "api.py", 30)

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    # ApiController -> Repository -> DatabaseEngine
    graph.add_dependency("ApiController", "Repository")
    graph.add_dependency("Repository", "DatabaseEngine")

    # If DatabaseEngine changes, impact radius includes Repository and ApiController
    impacted = graph.get_impact_radius("DatabaseEngine", max_depth=3)
    assert "Repository" in impacted
    assert "ApiController" in impacted


# -----------------------------------------------------------------------------
# F-0070: Subconscious Background Processing
# -----------------------------------------------------------------------------
def test_subconscious_unit():
    engine = SubconsciousEngine(idle_threshold_seconds=0.01)
    executed = []
    engine.register_task("cache_clean", "Clean stale caches", 0.05, lambda: executed.append("clean"))
    time.sleep(0.02)
    ran = engine.step()
    assert "cache_clean" in ran
    assert len(executed) == 1


def test_subconscious_integration():
    engine = SubconsciousEngine(idle_threshold_seconds=0.01)
    state = {"count": 0}

    engine.register_task("housekeeping", "Update indices", 0.02, lambda: state.update(count=state["count"] + 1), priority=8)
    time.sleep(0.02)
    engine.step()
    assert state["count"] == 1

    # Active user resets idle
    engine.record_activity()
    ran = engine.step()
    assert len(ran) == 0  # not idle


# -----------------------------------------------------------------------------
# F-0071: Workflows Engine
# -----------------------------------------------------------------------------
def test_workflows_unit():
    engine = WorkflowEngine()
    engine.register_action("echo", lambda params, ctx: params["msg"])

    steps = [
        WorkflowStep("s1", "echo", params={"msg": "hello"}),
    ]
    res = engine.execute_workflow("wf1", steps)
    assert res.success is True
    assert res.step_results["s1"] == "hello"


def test_workflows_integration():
    engine = WorkflowEngine()
    engine.register_action("fetch_data", lambda params, ctx: [10, 20, 30])
    engine.register_action("compute_sum", lambda params, ctx: sum(ctx["step_1"]))

    steps = [
        WorkflowStep("step_1", "fetch_data"),
        WorkflowStep("step_2", "compute_sum", depends_on=["step_1"]),
    ]
    res = engine.execute_workflow("wf_pipeline", steps)
    assert res.success is True
    assert res.step_results["step_2"] == 60


# -----------------------------------------------------------------------------
# F-0064: Dual Interface / Check-ins
# -----------------------------------------------------------------------------
def test_dual_interface_unit():
    bridge = DualInterfaceBridge("session_alpha")
    m1 = bridge.post_message("tui", "user", "Hello from TUI")
    m2 = bridge.post_message("telegram", "user", "Reply from Telegram")
    assert len(bridge.get_unified_history()) == 2
    assert bridge.active_interface == "telegram"


def test_dual_interface_integration():
    bridge = DualInterfaceBridge("session_alpha")
    item = bridge.trigger_check_in(CheckInType.MORNING_KICKOFF)
    assert item.delivered is True
    assert "top 3 goals" in item.prompt

    bridge.record_check_in_response(CheckInType.MORNING_KICKOFF, "Deep work on Locus OS")
    assert item.response == "Deep work on Locus OS"
    # Check that response was merged into history
    hist = bridge.get_unified_history()
    assert any("Check-in [morning_kickoff]" in m["text"] for m in hist)
