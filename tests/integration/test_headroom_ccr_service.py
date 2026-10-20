"""
SPEC §4.17: Token Compression (Headroom CCR) Integration Tests (F-0026 / US-56).
Validates FastAPI sidecar endpoints for Headroom CCR:
  - GET /compression/headroom/config
  - POST /compression/headroom/compress
  - GET /compression/headroom/retrieve/{cache_key}
  - POST /compression/headroom/retrieve
  - Modular off-switch (HTTP 503) when locus.headroom_ccr.enabled is False
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sidecar.context.headroom_pipeline import CompressConfig, HeadroomPipeline
from sidecar.providers.headroom_ccr import DefaultHeadroomCCRProvider
from sidecar.service import create_app


@pytest.fixture
def client_and_provider(tmp_path: Path) -> Generator[tuple[TestClient, DefaultHeadroomCCRProvider], None, None]:
    pipeline = HeadroomPipeline(cache_dir=tmp_path)
    provider = DefaultHeadroomCCRProvider(pipeline=pipeline)
    app = create_app()
    app.state.registry.register("compression_headroom_ccr", "default_headroom_ccr", lambda **kw: provider)
    client = TestClient(app)
    yield client, provider


def test_service_headroom_config(client_and_provider: tuple[TestClient, DefaultHeadroomCCRProvider]) -> None:
    """SPEC §4.17 line 690: resolve(CompressConfig, kwargs)
    Asserts GET /compression/headroom/config returns expected pipeline defaults.
    """
    client, _ = client_and_provider
    res = client.get("/compression/headroom/config")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "headroom-ccr"
    assert data["enabled"] is True
    assert data["protect_recent"] == 4
    assert data["min_tokens_to_compress"] == 250
    assert data["compress_user_messages"] is False


def test_service_headroom_compress_endpoint(client_and_provider: tuple[TestClient, DefaultHeadroomCCRProvider]) -> None:
    """SPEC §4.17 line 689: compress(messages, model, config) -> CompressResult
    Asserts POST /compression/headroom/compress runs pipeline and returns CompressResult.
    """
    client, _ = client_and_provider
    large_payload = json.dumps({"audit": ["entry"] * 60, "details": "repeated system log string " * 40})
    messages = [
        {"role": "system", "content": "System prompt for testing."},
        {"role": "assistant", "content": large_payload},
        {"role": "user", "content": "Recent 1"},
        {"role": "assistant", "content": "Recent 2"},
        {"role": "user", "content": "Recent 3"},
        {"role": "assistant", "content": "Recent 4"},
    ]

    res = client.post(
        "/compression/headroom/compress",
        json={"messages": messages, "config": {"min_tokens_to_compress": 100}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    result = data["result"]
    assert result["tokens_saved"] > 0
    assert result["ratio"] < 1.0
    assert len(result["cached_keys"]) >= 1
    assert "CCR" in result["transforms_applied"]


def test_service_headroom_retrieve_endpoint(client_and_provider: tuple[TestClient, DefaultHeadroomCCRProvider]) -> None:
    """SPEC §4.17 line 701: headroom_retrieve(cache_key) -> full original text
    Asserts GET /compression/headroom/retrieve/{cache_key} and POST retrieve endpoints.
    """
    client, provider = client_and_provider
    original_text = "Important architecture details cached for retrieval."
    key = provider.pipeline.ccr.store(original_text)

    # GET endpoint
    res_get = client.get(f"/compression/headroom/retrieve/{key}")
    assert res_get.status_code == 200
    assert res_get.json()["original"] == original_text

    # POST endpoint
    res_post = client.post("/compression/headroom/retrieve", json={"cache_key": key})
    assert res_post.status_code == 200
    assert res_post.json()["original"] == original_text

    # 404 for missing key
    res_missing = client.get("/compression/headroom/retrieve/unknown_missing_key")
    assert res_missing.status_code == 404


def test_service_headroom_off_switch_503(client_and_provider: tuple[TestClient, DefaultHeadroomCCRProvider]) -> None:
    """SPEC §4.17 line 711: Swappable / off state returning 503."""
    client, _ = client_and_provider
    with patch("sidecar.config.get", return_value=False), patch("sidecar.config.is_enabled", return_value=False):
        res_config = client.get("/compression/headroom/config")
        assert res_config.status_code == 503
        assert res_config.json()["disabled"] == "locus.headroom_ccr.enabled"

        res_compress = client.post(
            "/compression/headroom/compress",
            json={"messages": [{"role": "user", "content": "test"}]},
        )
        assert res_compress.status_code == 503

        res_retrieve = client.get("/compression/headroom/retrieve/some_key")
        assert res_retrieve.status_code == 503
