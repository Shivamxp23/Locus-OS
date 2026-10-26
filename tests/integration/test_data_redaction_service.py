"""
SPEC §13.8 lines 3438-3512: Integration tests for Data Redaction (F-0041 / US-73).
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


def test_service_redact_text(client: TestClient) -> None:
    """SPEC §13.8 lines 3478-3490: Test POST /security/redact/text."""
    raw = (
        "Connecting to https://api.openai.com/v1/models?token=secret1234567890 "
        "with Bearer sk-1234567890abcdef1234567890"
    )
    res = client.post("/security/redact/text", json={"text": raw})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    redacted = data["redacted"]
    assert "sk-1234567890abcdef1234567890" not in redacted
    assert "token=secret1234567890" not in redacted
    assert "token=***REDACTED***" in redacted


def test_service_redact_structure(client: TestClient) -> None:
    """SPEC §13.8 lines 3497-3502: Test POST /security/redact/structure."""
    payload = {
        "user_id": "usr_9988",
        "api_key": "sk-secret12345678901234567890",
        "metadata": {
            "password": "supersecretpassword123",
            "session": "short",
            "active": True,
        },
        "logs": [
            "User logged in from 127.0.0.1",
            "API key used: sk-ant-api03-1234567890abcdef1234567890",  # guard:allow-secret
        ],
    }
    res = client.post("/security/redact/structure", json={"payload": payload})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    redacted = data["redacted"]
    assert redacted["user_id"] == "usr_9988"
    assert redacted["api_key"] == "sk-sec...7890"
    assert redacted["metadata"]["password"] == "supers...d123"
    assert redacted["metadata"]["session"] == "***REDACTED***"
    assert redacted["metadata"]["active"] is True
    assert "sk-ant-api03-1234567890" not in redacted["logs"][1]


def test_service_redact_patterns_list(client: TestClient) -> None:
    """SPEC §13.8 line 3469: Test GET /security/redact/patterns."""
    res = client.get("/security/redact/patterns")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    vendors = [p["vendor"] for p in data["patterns"]]
    assert "OpenAI" in vendors
    assert "Anthropic" in vendors
    assert "Google" in vendors
    assert "GitHub Classic PAT" in vendors


def test_service_data_redaction_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §13.8 line 3480: Modular off-switches return HTTP 503."""
    # Off-switch 1: locus.data_redaction.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.data_redaction.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.data_redaction.enabled" else True)

    res_t = client.post("/security/redact/text", json={"text": "sk-12345678901234567890"})
    assert res_t.status_code == 503
    assert res_t.json()["disabled"] == "locus.data_redaction.enabled"

    res_s = client.post("/security/redact/structure", json={"payload": {"api_key": "secret"}})
    assert res_s.status_code == 503

    res_p = client.get("/security/redact/patterns")
    assert res_p.status_code == 503

    # Off-switch 2: locus.security.data_redaction.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.data_redaction.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.data_redaction.enabled" else True)

    res2 = client.post("/security/redact/text", json={"text": "sk-12345678901234567890"})
    assert res2.status_code == 503
