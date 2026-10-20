"""
SPEC §2.9 / F-0098 / US-38: Integration Tests for Image Generation Service.
Asserts FastAPI routes `/images/generate`, `/images/models`, `/images/config`,
and the modular 503 off-switch on locus.image_generation.enabled.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.service import create_app
from sidecar.image_generation import ImageGenerationProvider


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_generate_image_endpoint(client):
    """SPEC §2.9 line 2648: Generate image endpoint creates valid image payload."""
    payload = {
        "prompt": "An astronaut riding a horse on Mars, digital art",
        "model": "openai/dall-e-3",
        "size": "1024x1024",
    }
    resp = client.post("/images/generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "result" in data
    assert data["result"]["prompt"] == "An astronaut riding a horse on Mars, digital art"
    assert data["result"]["model_used"] == "openai/dall-e-3"
    assert data["result"]["mime_type"] == "image/png"
    assert "b64_data" in data["result"]


def test_generate_image_validation_error(client):
    """SPEC §2.9 line 2651: Empty prompt returns 400 Bad Request."""
    payload = {"prompt": "   "}
    resp = client.post("/images/generate", json=payload)
    assert resp.status_code == 400
    assert "cannot be empty" in resp.json()["detail"]


def test_list_image_models_endpoint(client):
    """SPEC §2.9 line 2649: List image models endpoint returns registered providers."""
    resp = client.get("/images/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "models" in data
    assert len(data["models"]) >= 4


def test_image_config_endpoint(client):
    """SPEC §2.9 line 2650: Image generation configuration endpoint."""
    resp = client.get("/images/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert "ImageGenerationProvider" in data["provider"]


def test_image_generation_503_off_switch(monkeypatch):
    """Modularity architecture (03): Off switch on locus.image_generation.enabled returns 503."""
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: False
        if "image_generation" in key or "images" in key
        else True,
    )
    app = create_app()
    with TestClient(app) as disabled_client:
        resp_gen = disabled_client.post("/images/generate", json={"prompt": "test"})
        assert resp_gen.status_code == 503
        assert resp_gen.json()["disabled"] == "locus.image_generation.enabled"

        resp_models = disabled_client.get("/images/models")
        assert resp_models.status_code == 503
        assert resp_models.json()["disabled"] == "locus.image_generation.enabled"

        resp_config = disabled_client.get("/images/config")
        assert resp_config.status_code == 503
        assert resp_config.json()["disabled"] == "locus.image_generation.enabled"
