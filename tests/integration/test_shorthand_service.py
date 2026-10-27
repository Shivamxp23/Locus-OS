"""
SPEC §27.3 lines 7115-7151: Integration tests for LOCUS_SHORTHAND endpoints (F-0122 / US-96).
Tests FastAPI endpoints under /compression/shorthand/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.compression.shorthand import LocusShorthandCompressor
from sidecar.providers.shorthand import DefaultShorthandCompressorProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    compressor = LocusShorthandCompressor()
    provider = DefaultShorthandCompressorProvider(compressor=compressor)
    app.state.shorthand_compressor_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.locus_shorthand_4_text_compressor.enabled", True)
    config.set("locus.compression.shorthand.enabled", True)
    yield
    config.set("locus.locus_shorthand_4_text_compressor.enabled", True)
    config.set("locus.compression.shorthand.enabled", True)


def test_shorthand_service_compress_endpoint(client: TestClient) -> None:
    """SPEC §27.3: POST /compression/shorthand/compress."""
    payload = {
        "text": "The project was delayed because of weather and therefore we rescheduled with team.",
        "strip_articles": True,
    }
    res = client.post("/compression/shorthand/compress", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["compressed"] is True
    assert "∵" in data["compressed_text"]
    assert "∴" in data["compressed_text"]
    assert "w/" in data["compressed_text"]
    assert data["tokens_saved"] > 0


def test_shorthand_service_decompress_endpoint(client: TestClient) -> None:
    """SPEC §27.3: POST /compression/shorthand/decompress."""
    payload = {
        "text": "plan accepted ∵ tests pass ∴ ship w/ confidence",
    }
    res = client.post("/compression/shorthand/decompress", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "because" in data["decompressed_text"]
    assert "therefore" in data["decompressed_text"]
    assert "with" in data["decompressed_text"]


def test_shorthand_service_compress_event_endpoint(client: TestClient) -> None:
    """SPEC §27.3: POST /compression/shorthand/compress-event."""
    payload = {
        "event_type": "task_completion",
        "data": {"task": "Core Loop", "dur": 60, "q": 9},
    }
    res = client.post("/compression/shorthand/compress-event", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["compressed_event"] == "{✓:Core_Loop,dur:60,q:9}"


def test_shorthand_service_decoder_and_status_endpoints(client: TestClient) -> None:
    """SPEC §27.3: GET /compression/shorthand/decoder and GET /compression/shorthand/status."""
    res_dec = client.get("/compression/shorthand/decoder")
    assert res_dec.status_code == 200
    data_dec = res_dec.json()
    assert "∵" in data_dec["decoder"]
    assert data_dec["count"] >= 12

    res_st = client.get("/compression/shorthand/status")
    assert res_st.status_code == 200
    data_st = res_st.json()
    assert data_st["feature_enabled"] is True
    assert data_st["subsystem_enabled"] is True
    assert data_st["dictionary_size"] >= 12


def test_shorthand_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §27.3: Modular off-switches returning HTTP 503."""
    config.set("locus.locus_shorthand_4_text_compressor.enabled", False)

    res_comp = client.post("/compression/shorthand/compress", json={"text": "sample"})
    assert res_comp.status_code == 503
    assert res_comp.json()["disabled"] == "locus.locus_shorthand_4_text_compressor.enabled"

    res_dec = client.post("/compression/shorthand/decompress", json={"text": "sample"})
    assert res_dec.status_code == 503

    res_ev = client.post("/compression/shorthand/compress-event", json={"event_type": "checkin", "data": {}})
    assert res_ev.status_code == 503

    res_dict = client.get("/compression/shorthand/decoder")
    assert res_dict.status_code == 503

    res_st = client.get("/compression/shorthand/status")
    assert res_st.status_code == 503
