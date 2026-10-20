"""
SPEC §3.7a / F-0099 / US-40: Integration Tests for Git Tools Service.
Asserts FastAPI routes `/git/status`, `/git/diff`, `/git/commit`, `/git/log`, `/git/config`,
and the modular 503 off-switch on locus.git_tools.enabled.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_git_status_endpoint(client):
    """SPEC §3.7a: GET /git/status returns working tree status and branch."""
    resp = client.get("/git/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "result" in data
    res = data["result"]
    assert "branch" in res
    assert "clean" in res
    assert isinstance(res["staged"], list)
    assert isinstance(res["unstaged"], list)
    assert isinstance(res["untracked"], list)


def test_git_diff_endpoint(client):
    """SPEC §3.7a: POST /git/diff returns diff text and modification statistics."""
    resp = client.post("/git/diff", json={"staged": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "result" in data
    res = data["result"]
    assert "diff" in res
    assert "files_changed" in res
    assert "insertions" in res
    assert "deletions" in res


def test_git_commit_validation_error(client):
    """SPEC §3.7a: Empty commit message returns 400 Bad Request."""
    resp = client.post("/git/commit", json={"message": "   "})
    assert resp.status_code == 400
    assert "cannot be empty" in resp.json()["detail"]


def test_git_log_endpoint(client):
    """SPEC §3.7a: GET /git/log returns recent commit history."""
    resp = client.get("/git/log?max_count=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "log" in data
    assert len(data["log"]) >= 1
    first = data["log"][0]
    assert "hash" in first
    assert "author" in first
    assert "message" in first


def test_git_config_endpoint(client):
    """SPEC §3.7a: GET /git/config returns git tools status and provider."""
    resp = client.get("/git/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "GitToolsProvider"
    assert data["git_binary"] is not None


def test_git_tools_503_off_switch(monkeypatch):
    """Modularity architecture (03): Off switch on locus.git_tools.enabled returns 503."""
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: False
        if "git_tools" in key or "tools.git" in key
        else True,
    )
    app = create_app()
    with TestClient(app) as disabled_client:
        resp_status = disabled_client.get("/git/status")
        assert resp_status.status_code == 503
        assert resp_status.json()["disabled"] == "locus.git_tools.enabled"

        resp_diff = disabled_client.post("/git/diff", json={})
        assert resp_diff.status_code == 503
        assert resp_diff.json()["disabled"] == "locus.git_tools.enabled"

        resp_commit = disabled_client.post("/git/commit", json={"message": "test"})
        assert resp_commit.status_code == 503
        assert resp_commit.json()["disabled"] == "locus.git_tools.enabled"

        resp_log = disabled_client.get("/git/log")
        assert resp_log.status_code == 503
        assert resp_log.json()["disabled"] == "locus.git_tools.enabled"

        resp_config = disabled_client.get("/git/config")
        assert resp_config.status_code == 503
        assert resp_config.json()["disabled"] == "locus.git_tools.enabled"
