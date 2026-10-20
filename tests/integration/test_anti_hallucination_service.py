"""
SPEC §2.6 / F-0095 / US-35: Integration Tests for Anti-Hallucination Guard Service.
Asserts FastAPI routes `/guard/check`, `/guard/config`, and the 503 off-switch.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.service import create_app
from sidecar.providers.anti_hallucination import DEFAULT_CAVEAT_MESSAGE
from sidecar.anti_hallucination import clear_brain_errors


@pytest.fixture
def client():
    clear_brain_errors()
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    clear_brain_errors()
    config._CONFIG_CACHE = None


def test_guard_check_grounded_response(client):
    """SPEC §2.6 line 1848: Clean grounded responses are returned without caveats."""
    payload = {
        "llm_response": "You completed the compiler pass earlier today.",
        "context_forge_content": "User data: completed compiler pass in morning.",
        "mode": "warn",
    }
    resp = client.post("/guard/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    result = data["result"]
    assert result["block"] is False
    assert result["output_response"] == payload["llm_response"]
    assert len(result["ungrounded_claims"]) == 0


def test_guard_check_ungrounded_warn_mode(client):
    """SPEC §2.6 line 1844: Ungrounded claims in warn mode append caveat."""
    payload = {
        "llm_response": "Your sleep score was recorded as 99 yesterday.",
        "context_forge_content": "No sleep data available.",
        "mode": "warn",
    }
    resp = client.post("/guard/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    result = data["result"]
    assert result["block"] is False
    assert DEFAULT_CAVEAT_MESSAGE in result["output_response"]
    assert len(result["ungrounded_claims"]) > 0
    assert result["brain_error"]["severity"] == 1


def test_guard_check_ungrounded_strict_mode(client):
    """SPEC §2.6 line 1838: Ungrounded claims in strict mode reject response."""
    payload = {
        "llm_response": "You have 15 unfinished tasks in your vault.",
        "context_forge_content": "Vault contains 0 active tasks.",
        "mode": "strict",
    }
    resp = client.post("/guard/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    result = data["result"]
    assert result["block"] is True
    assert result["reason"] == "Response contained ungrounded claims"
    assert result["output_response"] == ""
    assert result["brain_error"]["severity"] == 2


def test_guard_config_endpoint(client):
    """SPEC §2.6: /guard/config returns status and mode."""
    resp = client.get("/guard/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["mode"] in ("warn", "strict", "off")


def test_guard_503_off_switch(monkeypatch):
    """Modularity architecture (03): Off switch on locus.brain.anti_hallucination.enabled returns 503."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "anti_hallucination" in key else True)
    app = create_app()
    with TestClient(app) as disabled_client:
        post_resp = disabled_client.post("/guard/check", json={"llm_response": "test", "context_forge_content": "test"})
        assert post_resp.status_code == 503
        assert post_resp.json()["disabled"] == "locus.brain.anti_hallucination.enabled"

        get_resp = disabled_client.get("/guard/config")
        assert get_resp.status_code == 503
        assert get_resp.json()["disabled"] == "locus.brain.anti_hallucination.enabled"


def test_hook_integration_endpoint(client):
    """SPEC §2.6 line 1857: Integration: Runs in Pi's afterToolCall hook for main response."""
    # Test checking response payload compatible with afterToolCall hook
    payload = {
        "llm_response": "Here is the summary of your project: you created 3 tasks.",
        "context_forge_content": "Identity: User. Projects: created 3 tasks.",
        "mode": "warn",
    }
    resp = client.post("/guard/check", json=payload)
    assert resp.status_code == 200
    assert resp.json()["result"]["block"] is False
