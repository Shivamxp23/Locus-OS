"""
Integration tests for Model Management service routes (SPEC §1.4, F-0004, US-23).
Verifies /models/list, /models/resolve, and the 503 off-switch.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from sidecar import config
from sidecar.model_escalation import ModelEscalationProvider
from sidecar.registry import ProviderRegistry
from sidecar.service import create_app


@pytest.fixture
def model_app():
    reg = ProviderRegistry()
    reg.register("model_management", "default_model_management", ModelEscalationProvider)
    app = create_app(registry=reg)
    return app


def test_model_service_list_models(model_app):
    """SPEC §1.4 line 486: Test /models/list returns model catalog with tiers."""
    client = TestClient(model_app)
    resp = client.get("/models/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert len(data["models"]) >= 3
    model_ids = [m["model_id"] for m in data["models"]]
    assert "deepseek/deepseek-chat" in model_ids
    assert "google/gemini-2.5-pro" in model_ids


def test_model_service_resolve_escalation(model_app):
    """SPEC §1.4 line 489: Test /models/resolve evaluates turn complexity and escalates model."""
    client = TestClient(model_app)
    payload = {
        "task_type": "deep_architecture",
        "estimated_tokens": 70000,
        "complexity_score": 8.0,
        "is_sunday_synthesis": False,
    }
    resp = client.post("/models/resolve", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["decision"]["tier"] == "reasoning"
    assert data["decision"]["model_id"] == "google/gemini-2.5-pro"
    assert data["decision"]["swapped"] is True


def test_model_escalation_modular_off_switch_503(monkeypatch, model_app):
    """SPEC §1.4 acceptance criteria: Modular off-switch locus.model_management_escalation.enabled returns 503."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "model_management" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "model_management" in key else True)
    client = TestClient(model_app)

    # Test /models/list 503
    resp_list = client.get("/models/list")
    assert resp_list.status_code == 503
    assert resp_list.json() == {"disabled": "locus.model_management_escalation.enabled"}

    # Test /models/resolve 503
    resp_resolve = client.post("/models/resolve", json={"task_type": "general"})
    assert resp_resolve.status_code == 503
    assert resp_resolve.json() == {"disabled": "locus.model_management_escalation.enabled"}
