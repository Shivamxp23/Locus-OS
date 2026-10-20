"""
SPEC §4.16: Context Compression Integration Tests (F-0110 / US-55).
Validates FastAPI sidecar endpoints for config status, threshold evaluation,
Hermes 7-step context compression, model updates, and modular off-switch (503).
"""
from __future__ import annotations

from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sidecar.compaction.context_engine import DefaultCompactionProvider
from sidecar.providers.compaction import CompactionConfig
from sidecar.service import create_app


@pytest.fixture
def client_and_provider() -> Generator[tuple[TestClient, DefaultCompactionProvider], None, None]:
    cfg = CompactionConfig(
        threshold_percent=0.75,
        protect_first_n=3,
        protect_last_n=6,
        default_context_length=128000,
    )
    provider = DefaultCompactionProvider(config=cfg)
    app = create_app()
    app.state.registry.register("compaction", "default", lambda **kw: provider)
    app.state.registry.register("compaction", "hermes_context_engine", lambda **kw: provider)
    client = TestClient(app)
    yield client, provider


def test_service_compaction_config(client_and_provider: tuple[TestClient, DefaultCompactionProvider]) -> None:
    """SPEC §4.16 line 3951: "threshold_percent: float = 0.75   // compress at 75% usage"
    Asserts GET /compaction/config endpoint returns valid active config and engine metrics.
    """
    client, _ = client_and_provider
    res = client.get("/compaction/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "hermes_context_engine"
    assert data["config"]["threshold_percent"] == 0.75
    assert data["config"]["protect_first_n"] == 3
    assert data["config"]["protect_last_n"] == 6
    assert data["threshold_tokens"] == 96000


def test_service_should_compress_endpoint(client_and_provider: tuple[TestClient, DefaultCompactionProvider]) -> None:
    """SPEC §4.16 line 3957: "should_compress(prompt_tokens)   // check if compaction needed"
    Asserts POST /compaction/should-compress correctly evaluates whether prompt tokens exceed threshold.
    """
    client, _ = client_and_provider
    res_under = client.post("/compaction/should-compress", json={"prompt_tokens": 50000})
    assert res_under.status_code == 200
    assert res_under.json()["should_compress"] is False

    res_over = client.post("/compaction/should-compress", json={"prompt_tokens": 98000})
    assert res_over.status_code == 200
    assert res_over.json()["should_compress"] is True


def test_service_compress_context_flow_endpoint(client_and_provider: tuple[TestClient, DefaultCompactionProvider]) -> None:
    """SPEC §4.16 line 3974: "FUNCTION compress_context(agent, messages, focus_topic=None):"
    Asserts POST /compaction/compress executes 7-step compression and returns rotated session ID.
    """
    client, _ = client_and_provider
    messages = [
        {"role": "system", "content": "You are Locus OS"}
    ] + [
        {"role": "user" if i % 2 == 1 else "assistant", "content": f"Turn {i} content details"}
        for i in range(1, 15)
    ]

    res = client.post(
        "/compaction/compress",
        json={
            "messages": messages,
            "focus_topic": "Vectorless search",
            "session_id": "session_test_original",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    result = data["result"]
    assert result["was_compressed"] is True
    assert result["intermediate_count"] == 5
    assert result["new_session_id"] != "session_test_original"
    assert len(result["compressed_messages"]) == 11


def test_service_update_model_endpoint(client_and_provider: tuple[TestClient, DefaultCompactionProvider]) -> None:
    """SPEC §4.16 line 3970: "update_model(model, context_length, ...) // recalculate thresholds"
    Asserts POST /compaction/engine/update-model updates model parameters and recalculates threshold tokens.
    """
    client, _ = client_and_provider
    res = client.post(
        "/compaction/engine/update-model",
        json={
            "model": "deepseek-v4-flash",
            "context_length": 64000,
            "threshold_percent": 0.80,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["model"] == "deepseek-v4-flash"
    assert data["context_length"] == 64000
    assert data["threshold_percent"] == 0.80
    assert data["threshold_tokens"] == 51200


def test_service_compaction_off_switch_503(client_and_provider: tuple[TestClient, DefaultCompactionProvider]) -> None:
    """SPEC §4.16 line 4024: "Provider Interface: CompactionProvider"
    Asserts disabling locus.context_compression.enabled triggers HTTP 503 on all /compaction routes.
    """
    client, _ = client_and_provider
    with patch("sidecar.config.get", return_value=False), patch("sidecar.config.is_enabled", return_value=False):
        res_cfg = client.get("/compaction/config")
        assert res_cfg.status_code == 503
        assert res_cfg.json() == {"disabled": "locus.context_compression.enabled"}

        res_should = client.post("/compaction/should-compress", json={"prompt_tokens": 100000})
        assert res_should.status_code == 503
        assert res_should.json() == {"disabled": "locus.context_compression.enabled"}

        res_comp = client.post("/compaction/compress", json={"messages": []})
        assert res_comp.status_code == 503
        assert res_comp.json() == {"disabled": "locus.context_compression.enabled"}
