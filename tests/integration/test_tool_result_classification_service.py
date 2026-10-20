"""
SPEC §3.9 / F-0101 / US-42: Integration Tests for Tool Result Classification Service.
Asserts FastAPI routes `/tools/classify-result`, `/tools/classification/config`,
and the modular 503 off-switch on locus.tool_result_classification.enabled.
"""
import json
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


def test_classify_result_endpoint_success(client):
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    resp = client.post(
        "/tools/classify-result",
        json={
            "tool_name": "read_file",
            "result": "File line 1\nFile line 2",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["classification"]["status"] == "success"
    assert data["classification"]["is_success"] is True
    assert data["classification"]["has_side_effect"] is False


def test_classify_result_endpoint_failure(client):
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    resp = client.post(
        "/tools/classify-result",
        json={
            "tool_name": "bash",
            "result": "SyntaxError: invalid token",
            "exit_code": 1,
            "error": "SyntaxError: invalid token",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["classification"]["status"] == "failure"
    assert data["classification"]["is_failure"] is True
    assert data["classification"]["has_side_effect"] is True


def test_classify_result_endpoint_partial(client):
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    payload = json.dumps({
        "bytes_written": 128,
        "lint": {"status": "error", "output": "Unused import sys"},
    })
    resp = client.post(
        "/tools/classify-result",
        json={
            "tool_name": "write_file",
            "result": payload,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["classification"]["status"] == "partial"
    assert data["classification"]["is_partial"] is True
    assert data["classification"]["file_mutation_landed"] is True


def test_classify_result_missing_tool_name(client):
    """SPEC §3.9 line 2695: "Scope: Classify results as success/failure/partial." """
    resp = client.post(
        "/tools/classify-result",
        json={"result": "Some output"},
    )
    assert resp.status_code == 400
    assert "tool_name" in resp.json().get("detail", "")


def test_classification_config_endpoint(client):
    """SPEC §3.9 line 2694: "Swappable / off state: locus.tools.result_classification.enabled. Off → results not classified." """
    resp = client.get("/tools/classification/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "ToolResultClassificationProvider"
    assert "config" in data
    assert "health" in data


def test_classification_off_switch_503(client, monkeypatch):
    """SPEC §3.9 line 2694: "Swappable / off state: locus.tools.result_classification.enabled. Off → results not classified." """
    original_get = config.get

    def fake_get(key: str, default=None):
        if key == "locus.tool_result_classification.enabled":
            return False
        return original_get(key, default)

    monkeypatch.setattr(config, "get", fake_get)

    # 1. POST route returns 503
    resp_post = client.post(
        "/tools/classify-result",
        json={"tool_name": "read_file", "result": "ok"},
    )
    assert resp_post.status_code == 503
    assert resp_post.json()["disabled"] == "locus.tool_result_classification.enabled"

    # 2. GET config route returns 503
    resp_get = client.get("/tools/classification/config")
    assert resp_get.status_code == 503
    assert resp_get.json()["disabled"] == "locus.tool_result_classification.enabled"


def test_classification_tools_off_switch_503(client, monkeypatch):
    """SPEC §3.9 line 2694: "Swappable / off state: locus.tools.result_classification.enabled. Off → results not classified." """
    original_get = config.get

    def fake_get(key: str, default=None):
        if key == "locus.tools.result_classification.enabled":
            return False
        return original_get(key, default)

    monkeypatch.setattr(config, "get", fake_get)

    resp_post = client.post(
        "/tools/classify-result",
        json={"tool_name": "read_file", "result": "ok"},
    )
    assert resp_post.status_code == 503
