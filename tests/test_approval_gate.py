import pytest
import time
from sidecar.security.approval_gate import (
    ApprovalStatus,
    ApprovalRequest,
    ApprovalGate,
)


def test_queue_and_approve():
    gate = ApprovalGate(default_ttl=600)
    req = gate.queue_approval(tool_name="bash", params={"cmd": "npm install"})
    assert req.status == ApprovalStatus.PENDING.value
    assert gate.get_status(req.task_id) == ApprovalStatus.PENDING.value

    assert gate.approve(req.task_id)
    assert gate.get_status(req.task_id) == ApprovalStatus.APPROVED.value


def test_queue_and_reject():
    gate = ApprovalGate(default_ttl=600)
    req = gate.queue_approval(tool_name="write", params={"path": "critical.py"})
    assert gate.reject(req.task_id)
    assert gate.get_status(req.task_id) == ApprovalStatus.REJECTED.value


def test_ttl_expiration_auto_reject():
    # 0.1 second TTL
    gate = ApprovalGate(default_ttl=0.1)
    req = gate.queue_approval(tool_name="bash", params={"cmd": "git push"})
    time.sleep(0.15)

    # Cannot approve expired request
    assert not gate.approve(req.task_id)
    assert gate.get_status(req.task_id) == ApprovalStatus.EXPIRED.value
    assert len(gate.list_pending()) == 0
