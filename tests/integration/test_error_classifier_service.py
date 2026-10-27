"""
SPEC §29.1 lines 7435-7471: Integration tests for Error Classifier endpoints (F-0065 / US-102).
Tests FastAPI endpoints under /diagnostics/error/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.diagnostics.error_classifier import ErrorClassifier
from sidecar.providers.error_classifier import DefaultErrorClassifierProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    classifier = ErrorClassifier()
    provider = DefaultErrorClassifierProvider(classifier=classifier)
    app.state.error_classifier_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.error_classifier.enabled", True)
    config.set("locus.diagnostics.error_classifier.enabled", True)
    yield
    config.set("locus.error_classifier.enabled", True)
    config.set("locus.diagnostics.error_classifier.enabled", True)


def test_classify_endpoint_rate_limit(client: TestClient) -> None:
    """SPEC §29.1: POST /diagnostics/error/classify with 429."""
    payload = {
        "error": {
            "status": 429,
            "message": "Too Many Requests: quota exceeded",
        }
    }
    res = client.post("/diagnostics/error/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "rate_limit"
    assert data["action"] == "auto_retry"
    assert data["retryable"] is True
    assert data["max_retries"] == 3


def test_classify_endpoint_server_error(client: TestClient) -> None:
    """SPEC §29.1: POST /diagnostics/error/classify with 500."""
    payload = {
        "error": {
            "status": 500,
            "message": "Internal Server Error in upstream cluster",
        }
    }
    res = client.post("/diagnostics/error/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "server_error"
    assert data["action"] == "retry_then_fallback"
    assert data["fallback_model_recommended"] is True


def test_taxonomy_endpoint(client: TestClient) -> None:
    """SPEC §29.1: GET /diagnostics/error/taxonomy."""
    res = client.get("/diagnostics/error/taxonomy")
    assert res.status_code == 200
    data = res.json()
    assert len(data["categories"]) == 7
    assert "rate_limit" in data["categories"]
    assert "auth_failure" in data["categories"]
    assert "context_overflow" in data["categories"]
    assert "server_error" in data["categories"]
    assert "timeout" in data["categories"]
    assert "content_filter" in data["categories"]
    assert "unknown" in data["categories"]


def test_status_endpoint(client: TestClient) -> None:
    """SPEC §29.1: GET /diagnostics/error/status."""
    res = client.get("/diagnostics/error/status")
    assert res.status_code == 200
    data = res.json()
    assert data["subsystem_enabled"] is True
    assert data["provider_enabled"] is True
    assert data["provider_name"] == "default_error_classifier"


def test_error_classifier_off_switch_503(client: TestClient) -> None:
    """SPEC §29.1: Modular off-switch locus.error_classifier.enabled returns HTTP 503."""
    config.set("locus.error_classifier.enabled", False)

    res1 = client.post("/diagnostics/error/classify", json={"error": 429})
    assert res1.status_code == 503

    res2 = client.get("/diagnostics/error/taxonomy")
    assert res2.status_code == 503

    res3 = client.get("/diagnostics/error/status")
    assert res3.status_code == 503
