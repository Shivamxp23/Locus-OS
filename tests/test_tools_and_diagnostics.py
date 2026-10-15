"""tests/test_tools_and_diagnostics.py - Test suite for Cluster A tools and diagnostics.

Tests:
- GitToolSuite (§3.7a)
- ToolCallValidator (§3.8)
- ToolResultClassifier (§3.9)
- ToolBudgetManager (§3.11)
- CustomToolRegistry (§3.12)
- FileSafetyPolicy (§13.2)
- ComputerUseEngine (§20.1)
- VNCClient (§20.3)
- CalendarSyncBridge (§21.1)
- DockerCIDiagnostics (§23.1)
- LocusDoctor (§8.2)
- HealthMonitor (§29.3)
- ConnectivityChecker (§29.5)
"""

import pytest
from pathlib import Path

from sidecar.tools.git_tools import GitToolSuite
from sidecar.tools.validation import ToolCallValidator, ValidationRule
from sidecar.tools.classifier import ToolResultClassifier, ToolResultClass
from sidecar.tools.budget import ToolBudgetManager, ToolBudgetLimits
from sidecar.tools.custom_tools import CustomToolRegistry
from sidecar.security.file_safety import FileSafetyPolicy
from sidecar.desktop.computer_use import ComputerUseEngine, MouseButton
from sidecar.desktop.vnc_client import VNCClient, VNCConnectionState
from sidecar.integrations.calendar_sync import CalendarSyncBridge
from sidecar.diagnostics.docker_ci import DockerCIDiagnostics
from sidecar.diagnostics.doctor import LocusDoctor
from sidecar.health import HealthMonitor, HealthStatus
from sidecar.connectivity import ConnectivityChecker


# -----------------------------------------------------------------------------
# F-0099: Git Tools
# -----------------------------------------------------------------------------
def test_git_tools_operations():
    suite = GitToolSuite()
    status = suite.status(short=True)
    assert status.command.startswith("git status")
    assert isinstance(status.success, bool)


def test_git_tools_integration():
    suite = GitToolSuite()
    rev = suite.rev_parse("HEAD")
    assert rev.command == "git rev-parse HEAD"
    assert rev.success is True
    assert len(rev.stdout.strip()) == 40


# -----------------------------------------------------------------------------
# F-0100: Tool Call Validation
# -----------------------------------------------------------------------------
def test_tool_validation_rules():
    validator = ToolCallValidator()
    validator.register_schema(
        "search",
        [
            ValidationRule("query", expected_type=str, required=True),
            ValidationRule("limit", expected_type=int, required=False, min_value=1, max_value=50),
        ],
    )
    res_ok = validator.validate_call("search", {"query": "test query", "limit": 10})
    assert res_ok.is_valid is True

    res_fail = validator.validate_call("search", {"limit": 100})
    assert res_fail.is_valid is False
    assert any("Missing required" in e for e in res_fail.errors)


def test_tool_validation_integration():
    validator = ToolCallValidator()
    validator.register_schema("score", [ValidationRule("score", expected_type=float, min_value=0.0, max_value=10.0)])
    res = validator.validate_call("score", {"score": 8.5})
    assert res.is_valid is True
    assert res.sanitized_params["score"] == 8.5


# -----------------------------------------------------------------------------
# F-0101: Tool Result Classification
# -----------------------------------------------------------------------------
def test_tool_classifier_outcomes():
    classifier = ToolResultClassifier()
    # Success
    s = classifier.classify("git", {"status": "clean"})
    assert s.classification == ToolResultClass.SUCCESS
    assert s.is_success is True

    # Timeout
    t = classifier.classify("api", None, error="Connection timed out after 30s")
    assert t.classification == ToolResultClass.TIMEOUT
    assert t.should_retry is True


def test_tool_classifier_integration():
    classifier = ToolResultClassifier()
    r = classifier.classify("fetch", {"status": "error", "message": "HTTP 429 rate limit exceeded"})
    assert r.classification == ToolResultClass.RETRIABLE_ERROR
    assert r.should_retry is True


# -----------------------------------------------------------------------------
# F-0103: Tool Timeout / Budget
# -----------------------------------------------------------------------------
def test_tool_budget_limits():
    limits = ToolBudgetLimits(max_invocations_per_turn=3, max_total_seconds_per_turn=10.0)
    mgr = ToolBudgetManager(limits)

    can, _ = mgr.can_invoke("read")
    assert can is True
    mgr.record_invocation("read", 2.0)
    mgr.record_invocation("write", 2.0)
    mgr.record_invocation("search", 2.0)

    can_ex, reason = mgr.can_invoke("another")
    assert can_ex is False
    assert "budget" in reason.lower()


def test_tool_budget_integration():
    mgr = ToolBudgetManager(ToolBudgetLimits(max_total_seconds_per_turn=5.0))
    mgr.record_invocation("long_task", 6.0)
    can, _ = mgr.can_invoke("next")
    assert can is False


# -----------------------------------------------------------------------------
# F-0104: Custom Locus Tools
# -----------------------------------------------------------------------------
def test_custom_tool_registry():
    registry = CustomToolRegistry()
    registry.register(
        name="echo_test",
        description="Echos parameters back",
        parameters_schema={"type": "object"},
        handler=lambda p: f"Echo: {p.get('msg')}",
    )
    tools = registry.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "echo_test"


def test_custom_tool_integration():
    registry = CustomToolRegistry()
    registry.register("calc", "Adds two numbers", {}, lambda p: p["a"] + p["b"])
    res = registry.execute("calc", {"a": 10, "b": 32})
    assert res["status"] == "ok"
    assert res["result"] == 42


# -----------------------------------------------------------------------------
# F-0107: File Safety
# -----------------------------------------------------------------------------
def test_file_safety_policy():
    policy = FileSafetyPolicy()
    # Sensitive
    s1 = policy.check_path_access("/home/user/.ssh/id_rsa")
    assert s1.is_safe is False
    assert "blocked" in s1.violation_reason.lower()

    # Read-only packages check
    s2 = policy.check_path_access("packages/pi-agent/index.ts", is_write=True)
    assert s2.is_safe is False
    assert "read-only" in s2.violation_reason.lower()


def test_file_safety_integration():
    policy = FileSafetyPolicy()
    # Path traversal attack
    res = policy.check_path_access("data/../../etc/passwd")
    assert res.is_safe is False


# -----------------------------------------------------------------------------
# F-0051: Computer Use / Screen
# -----------------------------------------------------------------------------
def test_computer_use_actions():
    engine = ComputerUseEngine()
    move = engine.mouse_move(500, 400)
    assert move.success is True
    assert engine.cursor_pos == (500, 400)

    click = engine.mouse_click(500, 400, MouseButton.LEFT)
    assert click.success is True
    assert click.action == "click_left"


def test_computer_use_integration():
    engine = ComputerUseEngine()
    invalid = engine.mouse_move(9999, 9999)
    assert invalid.success is False
    assert "out of display bounds" in invalid.message


# -----------------------------------------------------------------------------
# F-0052: VNC Remote
# -----------------------------------------------------------------------------
def test_vnc_client_lifecycle():
    client = VNCClient()
    assert client.state == VNCConnectionState.DISCONNECTED
    client.connect()
    assert client.state == VNCConnectionState.AUTHENTICATED
    assert client.framebuffer is not None
    client.disconnect()
    assert client.state == VNCConnectionState.DISCONNECTED


def test_vnc_client_integration():
    client = VNCClient()
    client.connect()
    res = client.send_pointer_event(100, 200, 1)
    assert res is True
    assert client.last_pointer == (100, 200)


# -----------------------------------------------------------------------------
# F-0053: Google Calendar
# -----------------------------------------------------------------------------
def test_calendar_sync_bridge():
    bridge = CalendarSyncBridge()
    ev = bridge.add_event(
        "ev-1",
        "Deep Work Block",
        "2026-10-16T10:00:00",
        "2026-10-16T11:30:00",
        faction="Craft",
        is_deep_work=True,
    )
    assert ev.id == "ev-1"
    assert len(bridge.list_events()) == 1


def test_calendar_sync_integration():
    bridge = CalendarSyncBridge()
    bridge.add_event("ev-1", "Meeting", "2026-10-16T10:00:00", "2026-10-16T11:00:00")
    conflicts = bridge.check_conflicts("2026-10-16T10:30:00", "2026-10-16T11:30:00")
    assert len(conflicts) == 1
    assert conflicts[0].id == "ev-1"


# -----------------------------------------------------------------------------
# F-0054: CI/CD / Docker
# -----------------------------------------------------------------------------
def test_docker_ci_diagnostics():
    diag = DockerCIDiagnostics()
    services = diag.check_all_services()
    assert "locus-couchdb" in services
    assert services["locus-couchdb"].is_healthy is True


def test_docker_ci_integration():
    diag = DockerCIDiagnostics()
    env = diag.verify_ci_environment()
    assert env["docker_available"] is True


# -----------------------------------------------------------------------------
# F-0031: CLI / Doctor Diagnostics
# -----------------------------------------------------------------------------
def test_doctor_diagnostics():
    doc = LocusDoctor()
    report = doc.run_all_checks()
    assert isinstance(report.healthy, bool)
    assert len(report.checks) >= 4


def test_doctor_integration():
    doc = LocusDoctor()
    report = doc.run_all_checks()
    py_check = [c for c in report.checks if c.name == "python_version"][0]
    assert py_check.passed is True


# -----------------------------------------------------------------------------
# F-0066: Health Checks
# -----------------------------------------------------------------------------
def test_health_probes():
    mon = HealthMonitor()
    assert mon.is_alive() is True
    assert mon.is_ready() is True


def test_health_integration():
    mon = HealthMonitor()
    mon.register_status("database", HealthStatus.UNHEALTHY, 150.0, "Database down")
    assert mon.is_ready() is False
    assert mon.get_health_report()["status"] == "degraded"


# -----------------------------------------------------------------------------
# F-0068: Connectivity Check
# -----------------------------------------------------------------------------
def test_connectivity_probes():
    checker = ConnectivityChecker(timeout_seconds=0.5)
    # Probing local port that is closed or open returns structured result
    res = checker.probe_tcp_port("127.0.0.1", 12345)
    assert isinstance(res.is_reachable, bool)
    assert res.target == "127.0.0.1:12345"


def test_connectivity_integration():
    checker = ConnectivityChecker(timeout_seconds=0.5)
    services = checker.check_local_services()
    assert "couchdb" in services
    assert "neo4j" in services
