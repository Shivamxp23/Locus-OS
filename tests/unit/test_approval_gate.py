"""
Unit tests for Approval Gate (SPEC §13.5 / F-0109 / US-71).
"""
import time
import pytest

from sidecar.security.approval_store import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStore,
)
from sidecar.providers.approval_gate import (
    BaseApprovalGateProvider,
    DefaultApprovalGateProvider,
)
import sidecar.config as config


def test_queue_approval_creates_pending_request():
    """SPEC §13.5 line 3343: "FUNCTION queue_approval(task_id, changes, ttl=600):" """
    store = ApprovalStore(default_ttl=600)
    req = store.queue_approval(task_id="task-1", changes={"tool": "write_file", "path": "test.txt"})
    assert req.task_id == "task-1"
    assert req.status == ApprovalStatus.PENDING.value
    assert req.changes == {"tool": "write_file", "path": "test.txt"}
    assert req.created_at <= time.time()
    assert req.expires_at > req.created_at


def test_queue_approval_default_ttl():
    """SPEC §13.5 line 3344: "approval_store.set(task_id, { changes, status: "pending", expires: now()+ttl })" """
    store = ApprovalStore(default_ttl=600)
    req = store.queue_approval(task_id="task-2", changes="delete_database")
    # TTL is approximately 600 seconds
    diff = req.expires_at - req.created_at
    assert pytest.approx(diff, 1.0) == 600


def test_resolve_approval_to_approved():
    """SPEC §13.5 line 3350: "IF status == "approved": RETURN true" """
    store = ApprovalStore()
    store.queue_approval("task-appr", {"action": "write"})
    res = store.resolve_approval("task-appr", ApprovalStatus.APPROVED, resolved_by="test_user")
    assert res is not None
    assert res.status == ApprovalStatus.APPROVED.value
    assert res.resolved_by == "test_user"
    assert res.resolved_at is not None


def test_resolve_approval_to_rejected():
    """SPEC §13.5 line 3351: "IF status == "rejected": RETURN false" """
    store = ApprovalStore()
    store.queue_approval("task-rej", {"action": "delete"})
    res = store.resolve_approval("task-rej", ApprovalStatus.REJECTED, resolved_by="admin")
    assert res is not None
    assert res.status == ApprovalStatus.REJECTED.value
    assert res.resolved_by == "admin"


def test_ttl_expiration_auto_reject():
    """SPEC §13.5 line 3353: "RETURN false  // TTL expired = auto-reject" """
    store = ApprovalStore(default_ttl=1)  # 1-second TTL
    req = store.queue_approval("task-exp", "sample_changes", ttl=1)
    # Manually backdate created and expires
    req.created_at = time.time() - 10
    req.expires_at = time.time() - 5

    fetched = store.get_approval("task-exp")
    assert fetched is not None
    assert fetched.status == ApprovalStatus.EXPIRED.value
    assert fetched.resolved_by == "ttl_auto_reject"


def test_wait_for_approval_resolves_approved():
    """SPEC §13.5 line 3347: "FUNCTION wait_for_approval(task_id, ttl):" """
    store = ApprovalStore(default_ttl=10)
    store.queue_approval("task-wait-appr", "changes")

    # In background or synchronous pre-resolution
    store.resolve_approval("task-wait-appr", "approved")
    approved = store.wait_for_approval("task-wait-appr", timeout=1.0)
    assert approved is True


def test_wait_for_approval_resolves_rejected():
    """SPEC §13.5 line 3351: "IF status == "rejected": RETURN false" """
    store = ApprovalStore(default_ttl=10)
    store.queue_approval("task-wait-rej", "changes")

    store.resolve_approval("task-wait-rej", "rejected")
    approved = store.wait_for_approval("task-wait-rej", timeout=1.0)
    assert approved is False


def test_wait_for_approval_times_out():
    """SPEC §13.5 line 3353: "RETURN false  // TTL expired = auto-reject" """
    store = ApprovalStore(default_ttl=10)
    store.queue_approval("task-wait-timeout", "changes")

    # Wait with very short timeout without resolving
    approved = store.wait_for_approval("task-wait-timeout", timeout=0.05, poll_interval=0.01)
    assert approved is False


def test_list_pending_only_returns_active_unexpired():
    """SPEC §13.5 line 3357: "Repo vs .locus: code in locus-os; approval state is runtime-only (in-memory + Redis fallback), not persisted to .locus" """
    store = ApprovalStore()
    store.queue_approval("p1", "c1")
    store.queue_approval("p2", "c2")
    store.resolve_approval("p1", "approved")

    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0].task_id == "p2"


def test_provider_modular_off_switches(monkeypatch):
    """SPEC §13.5 line 3358: "Swappable / off state: locus.security.approval_gate.enabled. Off -> all tool calls proceed without user confirmation (only autonomy tier governs)." """
    provider = DefaultApprovalGateProvider()
    assert provider.is_available() is True

    # Test locus.approval_gate.enabled: false
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.approval_gate.enabled" else default)
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.approval_gate.enabled" else True)
    assert provider.is_available() is False

    # Test locus.security.approval_gate.enabled: false
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.security.approval_gate.enabled" else default)
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.security.approval_gate.enabled" else True)
    assert provider.is_available() is False


def test_swappable_provider_swap():
    """SPEC §13.5 line 3358: "Swappable / off state: locus.security.approval_gate.enabled. Off -> all tool calls proceed without user confirmation (only autonomy tier governs)." """
    class CustomApprovalProvider(BaseApprovalGateProvider):
        def is_available(self) -> bool:
            return True

        def queue_approval(self, task_id: str, changes, ttl=None):
            return {"status": "ok", "request": {"task_id": task_id, "status": "approved"}}

        def get_status(self, task_id: str):
            return {"status": "ok", "request": {"task_id": task_id, "status": "approved"}}

        def resolve(self, task_id: str, status: str, resolved_by=None):
            return {"status": "ok", "request": {"task_id": task_id, "status": status}}

        def wait(self, task_id: str, timeout=None):
            return {"status": "ok", "approved": True}

        def list_pending(self):
            return []

    custom = CustomApprovalProvider()
    assert isinstance(custom, BaseApprovalGateProvider)
    res = custom.queue_approval("task-swap", "changes")
    assert res["request"]["status"] == "approved"
