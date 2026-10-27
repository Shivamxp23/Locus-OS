"""
SPEC §29.2 lines 7472-7500: Integration tests for Auxiliary LLM Client endpoints (F-0124 / US-103).
Tests FastAPI endpoints under /auxiliary/llm/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.diagnostics.auxiliary_client import AuxiliaryLLMClient
from sidecar.providers.auxiliary_llm import DefaultAuxiliaryLLMProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    llm_client = AuxiliaryLLMClient()
    provider = DefaultAuxiliaryLLMProvider(client=llm_client)
    app.state.auxiliary_llm_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.auxiliary_llm_client.enabled", True)
    config.set("locus.auxiliary_client.enabled", True)
    yield
    config.set("locus.auxiliary_llm_client.enabled", True)
    config.set("locus.auxiliary_client.enabled", True)


def test_auxiliary_generate_endpoint(client: TestClient) -> None:
    """SPEC §29.2: POST /auxiliary/llm/generate."""
    payload = {
        "prompt": "Index research link takeaways",
        "system_prompt": "You are a research indexer",
    }
    res = client.post("/auxiliary/llm/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_auxiliary"] is True
    assert "Auxiliary Client" in data["content"]
    assert data["total_tokens"] > 0
    assert data["cost_usd"] > 0.0


def test_auxiliary_model_endpoint(client: TestClient) -> None:
    """SPEC §29.2: GET /auxiliary/llm/model."""
    res = client.get("/auxiliary/llm/model")
    assert res.status_code == 200
    data = res.json()
    assert data["model"] == "deepseek-v4-flash"
    assert "base_url" in data


def test_auxiliary_status_endpoint(client: TestClient) -> None:
    """SPEC §29.2: GET /auxiliary/llm/status."""
    res = client.get("/auxiliary/llm/status")
    assert res.status_code == 200
    data = res.json()
    assert data["auxiliary_enabled"] is True
    assert data["provider_enabled"] is True
    assert data["provider_name"] == "default_auxiliary_llm"


def test_auxiliary_off_switch_503(client: TestClient) -> None:
    """SPEC §29.2: Master toggle locus.auxiliary_llm_client.enabled returns HTTP 503."""
    config.set("locus.auxiliary_llm_client.enabled", False)

    res1 = client.post("/auxiliary/llm/generate", json={"prompt": "hi"})
    assert res1.status_code == 503

    res2 = client.get("/auxiliary/llm/model")
    assert res2.status_code == 503

    res3 = client.get("/auxiliary/llm/status")
    assert res3.status_code == 503
