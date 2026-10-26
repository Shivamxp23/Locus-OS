"""
SPEC §13.5 lines 3333-3365: Integration tests for Approval Gate (F-0109 / US-71).
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_service_approval_lifecycle(client: TestClient) -> None:
    """SPEC §13.5 lines 3343-3353: Test full approval request, status, resolve, and wait lifecycle."""
    task_id = "test-service-task-1"
    # Queue approval
    res_q = client.post("/security/approval/request", json={"task_id": task_id, "changes": {"op": "rm -rf /tmp/data"}})
    assert res_q.status_code == 200
    q_data = res_q.json()
    assert q_data["status"] == "ok"
    assert q_data["request"]["task_id"] == task_id
    assert q_data["request"]["status"] == "pending"

    # Check status
    res_s = client.get(f"/security/approval/status?task_id={task_id}")
    assert res_s.status_code == 200
    assert res_s.json()["request"]["status"] == "pending"

    # List pending
    res_p = client.get("/security/approval/pending")
    assert res_p.status_code == 200
    pending_ids = [p["task_id"] for p in res_p.json()["pending"]]
    assert task_id in pending_ids

    # Resolve approval
    res_r = client.post("/security/approval/resolve", json={"task_id": task_id, "status": "approved", "resolved_by": "tester"})
    assert res_r.status_code == 200
    assert res_r.json()["request"]["status"] == "approved"

    # Wait confirms approval
    res_w = client.post("/security/approval/wait", json={"task_id": task_id, "timeout": 0.5})
    assert res_w.status_code == 200
    assert res_w.json()["approved"] is True


def test_service_approval_rejection(client: TestClient) -> None:
    """SPEC §13.5 line 3351: Test rejection flow."""
    task_id = "test-service-task-rej"
    client.post("/security/approval/request", json={"task_id": task_id, "changes": "drop tables"})
    client.post("/security/approval/resolve", json={"task_id": task_id, "status": "rejected", "resolved_by": "security_officer"})

    res_w = client.post("/security/approval/wait", json={"task_id": task_id, "timeout": 0.5})
    assert res_w.status_code == 200
    assert res_w.json()["approved"] is False


def test_service_approval_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §13.5 line 3358: Modular off-switches return 503."""
    # Off-switch 1: locus.approval_gate.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.approval_gate.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.approval_gate.enabled" else True)

    res_req = client.post("/security/approval/request", json={"task_id": "test"})
    assert res_req.status_code == 503
    assert res_req.json()["disabled"] == "locus.approval_gate.enabled"

    res_stat = client.get("/security/approval/status?task_id=test")
    assert res_stat.status_code == 503

    res_res = client.post("/security/approval/resolve", json={"task_id": "test", "status": "approved"})
    assert res_res.status_code == 503

    res_w = client.post("/security/approval/wait", json={"task_id": "test"})
    assert res_w.status_code == 503

    res_p = client.get("/security/approval/pending")
    assert res_p.status_code == 503

    # Off-switch 2: locus.security.approval_gate.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.approval_gate.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.approval_gate.enabled" else True)

    res2 = client.post("/security/approval/request", json={"task_id": "test"})
    assert res2.status_code == 503
