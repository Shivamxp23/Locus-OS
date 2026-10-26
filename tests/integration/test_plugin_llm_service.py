"""
SPEC §9.9 lines 6143-6199: Integration tests for Plugin LLM Sandboxing & Auxiliary Bridge (F-0034 / US-65).
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


def test_service_plugin_llm_generate(client: TestClient) -> None:
    """SPEC §9.9 lines 6165-6187: Test POST /plugins/llm/generate execution."""
    payload = {
        "plugin_id": "test-integration-plugin",
        "messages": [
            {"role": "user", "content": "Extract structured entities from this note"}
        ],
        "max_tokens": 150,
        "temperature": 0.2,
    }
    res = client.post("/plugins/llm/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["plugin_id"] == "test-integration-plugin"
    assert "content" in data
    assert "quota" in data
    assert data["quota"]["tokens_used_today"] > 0


def test_service_plugin_llm_quota_and_reset(client: TestClient) -> None:
    """SPEC §9.9 lines 6162-6164: Test GET /plugins/llm/quota and POST /plugins/llm/reset."""
    # Check quota
    res_quota = client.get("/plugins/llm/quota?plugin_id=test-integration-plugin")
    assert res_quota.status_code == 200
    quota_data = res_quota.json()
    assert quota_data["status"] == "ok"
    assert "quota" in quota_data
    assert quota_data["quota"]["plugin_id"] == "test-integration-plugin"

    # Reset quota
    res_reset = client.post("/plugins/llm/reset", json={"plugin_id": "test-integration-plugin"})
    assert res_reset.status_code == 200
    reset_data = res_reset.json()
    assert reset_data["status"] == "ok"
    assert reset_data["quota"]["tokens_used_today"] == 0


def test_service_plugin_llm_usage(client: TestClient) -> None:
    """SPEC §9.9 lines 6189-6190: Test GET /plugins/llm/usage aggregate records."""
    res = client.get("/plugins/llm/usage")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "plugins" in data


def test_service_plugin_llm_disabled_returns_503(client: TestClient, monkeypatch) -> None:
    """SPEC §9.9 line 6189: Test 503 response when locus.plugin_llm.enabled is off."""
    monkeypatch.setattr(config, "get", lambda k: False if k == "locus.plugin_llm.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.plugin_llm.enabled" else True)

    res_gen = client.post(
        "/plugins/llm/generate",
        json={"plugin_id": "disabled-test", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert res_gen.status_code == 503
    assert res_gen.json().get("disabled") == "locus.plugin_llm.enabled"

    res_quota = client.get("/plugins/llm/quota?plugin_id=disabled-test")
    assert res_quota.status_code == 503

    res_reset = client.post("/plugins/llm/reset", json={"plugin_id": "disabled-test"})
    assert res_reset.status_code == 503

    res_usage = client.get("/plugins/llm/usage")
    assert res_usage.status_code == 503
