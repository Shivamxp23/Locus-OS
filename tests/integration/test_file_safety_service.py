"""
SPEC §13.2 lines 3141-3165: Integration tests for File Safety (F-0107 / US-69).
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


def test_service_file_validate(client: TestClient) -> None:
    """SPEC §13.2: Test POST /security/file/validate."""
    # Benign path inside cwd
    res = client.post("/security/file/validate", json={"path": "sidecar/service.py", "operation": "read"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["decision"]["allowed"] is True

    # Traversal escaping jail
    res_esc = client.post("/security/file/validate", json={"path": "../../Windows/System32/calc.exe", "operation": "read"})
    assert res_esc.status_code == 200
    esc_data = res_esc.json()
    assert esc_data["status"] == "ok"
    assert esc_data["decision"]["allowed"] is False
    assert esc_data["decision"]["violation_type"] in ("outside_jail", "blocked_pattern")


def test_service_file_record_and_history(client: TestClient) -> None:
    """SPEC §13.2 line 3149: Test POST /security/file/record and GET /security/file/history."""
    res_rec = client.post(
        "/security/file/record",
        json={"path": "sample.py", "operation": "create", "content": "print(123)"},
    )
    assert res_rec.status_code == 200
    rec_data = res_rec.json()
    assert rec_data["status"] == "ok"
    assert rec_data["record"]["path"] == "sample.py"
    assert rec_data["record"]["size_bytes"] == len("print(123)")

    res_hist = client.get("/security/file/history?limit=10")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert hist_data["status"] == "ok"
    assert isinstance(hist_data["history"], list)
    assert len(hist_data["history"]) >= 1


def test_service_file_safety_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §13.2 line 3158: Modular off-switches return 503."""
    # Off-switch 1: locus.file_safety.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.file_safety.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.file_safety.enabled" else True)

    res_v = client.post("/security/file/validate", json={"path": "test.txt"})
    assert res_v.status_code == 503
    assert res_v.json()["disabled"] == "locus.file_safety.enabled"

    res_r = client.post("/security/file/record", json={"path": "test.txt", "operation": "read"})
    assert res_r.status_code == 503

    res_h = client.get("/security/file/history")
    assert res_h.status_code == 503

    # Off-switch 2: locus.security.file_safety.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.file_safety.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.file_safety.enabled" else True)

    res2 = client.post("/security/file/validate", json={"path": "test.txt"})
    assert res2.status_code == 503
