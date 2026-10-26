"""
SPEC §13.10 lines 3599-3668: Integration tests for Message Sanitization (F-0043 / US-75).
"""
from __future__ import annotations

import json
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_service_sanitize_text(client: TestClient) -> None:
    """SPEC §13.10 line 3614: Test POST /security/sanitize/text."""
    raw = "Header content with \ud800 surrogate and \udc00 valid suffix."
    # Use ensure_ascii=True to serialize surrogates across HTTP transport without client encode crash
    body = json.dumps({"text": raw}, ensure_ascii=True).encode("utf-8")
    res = client.post("/security/sanitize/text", content=body, headers={"Content-Type": "application/json"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    sanitized = data["sanitized"]
    assert "\ud800" not in sanitized
    assert "\udc00" not in sanitized
    assert "\ufffd" in sanitized


def test_service_sanitize_structure(client: TestClient) -> None:
    """SPEC §13.10 line 3620: Test POST /security/sanitize/structure."""
    payload = {
        "status": "ready",
        "nested": {
            "key": "corrupt\udbffdata",
            "values": ["clean", "bad\ud800item"],
        },
    }
    body = json.dumps({"payload": payload}, ensure_ascii=True).encode("utf-8")
    res = client.post("/security/sanitize/structure", content=body, headers={"Content-Type": "application/json"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["found"] is True
    assert "\udbff" not in data["sanitized"]["nested"]["key"]
    assert "\ufffd" in data["sanitized"]["nested"]["key"]
    assert "\ud800" not in data["sanitized"]["nested"]["values"][1]


def test_service_sanitize_messages(client: TestClient) -> None:
    """SPEC §13.10 line 3644: Test POST /security/sanitize/messages."""
    messages = [
        {"role": "user", "content": "Question with \ud900 surrogate"},
        {"role": "assistant", "content": "Clean answer"},
    ]
    body = json.dumps({"messages": messages}, ensure_ascii=True).encode("utf-8")
    res = client.post("/security/sanitize/messages", content=body, headers={"Content-Type": "application/json"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    cleaned = data["messages"]
    assert "\ud900" not in cleaned[0]["content"]
    assert "\ufffd" in cleaned[0]["content"]
    assert cleaned[1]["content"] == "Clean answer"


def test_service_message_sanitizer_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §13.10 line 3662: Modular off-switches return HTTP 503."""
    # Off-switch 1: locus.message_sanitization.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.message_sanitization.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.message_sanitization.enabled" else True)

    res_t = client.post("/security/sanitize/text", json={"text": "test"})
    assert res_t.status_code == 503
    assert res_t.json()["disabled"] == "locus.message_sanitization.enabled"

    res_s = client.post("/security/sanitize/structure", json={"payload": {}})
    assert res_s.status_code == 503

    res_m = client.post("/security/sanitize/messages", json={"messages": []})
    assert res_m.status_code == 503

    # Off-switch 2: locus.security.message_sanitization.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.message_sanitization.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.message_sanitization.enabled" else True)

    res2 = client.post("/security/sanitize/text", json={"text": "test"})
    assert res2.status_code == 503
