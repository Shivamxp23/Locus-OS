"""
SPEC §2.7-2.8 / F-0096 / US-37: Integration Tests for Intelligent Model Routing Service.
Asserts FastAPI routes `/routing/decide`, `/routing/health`, `/routing/quality-check`, `/routing/config`,
and the modular 503 off-switch on locus.intelligent_model_routing_quality_based_fallback.enabled.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.service import create_app
from sidecar.model_routing import ModelRoutingProvider


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_routing_decide_endpoint(client):
    """SPEC §2.7-2.8 line 1896: Model routing decide endpoint returns policy decision."""
    payload = {
        "model": "hint:quick",
        "hints": {"latency_budget": "low", "cost_sensitivity": "medium"},
    }
    resp = client.post("/routing/decide", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "decision" in data
    assert data["decision"]["category"] == "lightweight"
    assert "primary" in data["decision"]


def test_routing_quality_check_endpoint(client):
    """SPEC §2.7-2.8 line 1942: Model routing quality-check endpoint evaluates refusal and length."""
    # Refusal text should flag as low quality
    refusal_payload = {"text": "I cannot fulfill this request."}
    resp = client.post("/routing/quality-check", json=refusal_payload)
    assert resp.status_code == 200
    assert resp.json()["low_quality"] is True

    # Valid response should not flag as low quality
    valid_payload = {"text": "Here is a complete, detailed answer that fulfills your request."}
    resp_valid = client.post("/routing/quality-check", json=valid_payload)
    assert resp_valid.status_code == 200
    assert resp_valid.json()["low_quality"] is False


def test_routing_config_endpoint(client):
    """SPEC §2.7-2.8 line 2015: Model routing configuration endpoint."""
    resp = client.get("/routing/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert "ModelRoutingProvider" in data["provider"]


def test_routing_503_off_switch(monkeypatch):
    """Modularity architecture (03): Off switch on locus.intelligent_model_routing_quality_based_fallback.enabled returns 503."""
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: False
        if "intelligent_model_routing_quality_based_fallback" in key or "routing" in key
        else True,
    )
    app = create_app()
    with TestClient(app) as disabled_client:
        resp_decide = disabled_client.post("/routing/decide", json={"model": "hint:quick"})
        assert resp_decide.status_code == 503
        assert resp_decide.json()["disabled"] == "locus.intelligent_model_routing_quality_based_fallback.enabled"

        resp_health = disabled_client.get("/routing/health")
        assert resp_health.status_code == 503
        assert resp_health.json()["disabled"] == "locus.intelligent_model_routing_quality_based_fallback.enabled"

        resp_quality = disabled_client.post("/routing/quality-check", json={"text": "test"})
        assert resp_quality.status_code == 503
        assert resp_quality.json()["disabled"] == "locus.intelligent_model_routing_quality_based_fallback.enabled"

        resp_config = disabled_client.get("/routing/config")
        assert resp_config.status_code == 503
        assert resp_config.json()["disabled"] == "locus.intelligent_model_routing_quality_based_fallback.enabled"
