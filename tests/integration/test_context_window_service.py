"""
Integration tests for Context Window Management FastAPI endpoints (SPEC §1.6 & §4.17, F-0006).
Asserts token estimation, compaction endpoint with first-3/last-6 preservation,
CCR compress/retrieve roundtrip, and the modular 503 off-switch.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_estimate_endpoint(client):
    """SPEC §1.6 line 560: "estimateContextTokens(messages) → rough count"
    Asserts POST /context/estimate returns 200 with estimated token count.
    """
    res = client.post("/context/estimate", json={"text": "System prompt instructions for cognitive agent."})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["estimated_tokens"] >= 5

    res2 = client.post(
        "/context/estimate",
        json={
            "messages": [
                {"role": "user", "content": "Question 1"},
                {"role": "assistant", "content": "Answer 1"},
            ]
        },
    )
    assert res2.status_code == 200
    assert res2.json()["estimated_tokens"] >= 10


def test_compact_endpoint(client):
    """SPEC §1.6 line 562: "compact(messages, options) → CompactionResult"
    Asserts POST /context/compact compresses intermediate messages preserving bounds.
    """
    messages = [
        {"role": "user", "content": f"Turn {i} question"}
        if i % 2 == 1
        else {"role": "assistant", "content": f"Turn {i} detailed answer explaining system architecture."}
        for i in range(1, 15)
    ]
    res = client.post(
        "/context/compact",
        json={
            "messages": messages,
            "protect_first_n": 3,
            "protect_last_n": 6,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    compaction = data["compaction"]
    assert compaction["protected_count"] == 9
    assert len(compaction["compressed_messages"]) == 3 + 1 + 6
    assert len(compaction["cached_keys"]) == 1


def test_compress_and_retrieve_endpoints(client):
    """SPEC §1.6 line 577: "Locus replaces Pi's default compaction with Headroom CCR (§4.17)"
    Asserts text can be compressed into a CCR cache key and subsequently retrieved.
    """
    original_text = "Unique detailed report text for CCR verification test roundtrip."
    comp_res = client.post("/context/compress", json={"text": original_text})
    assert comp_res.status_code == 200
    comp_data = comp_res.json()["result"]
    cache_key = comp_data["cache_key"]
    assert cache_key != ""

    # Retrieve via GET /context/retrieve/{cache_key}
    ret_res = client.get(f"/context/retrieve/{cache_key}")
    assert ret_res.status_code == 200
    ret_data = ret_res.json()
    assert ret_data["status"] == "ok"
    assert ret_data["original"] == original_text

    # Non-existent key returns 404
    missing_res = client.get("/context/retrieve/non-existent-key-12345")
    assert missing_res.status_code == 404


def test_context_compression_service_off_switch_503(monkeypatch):
    """SPEC §1.6 line 579: "Swappable / off state: locus.compaction.provider (headroom-ccr | pi-default | simple-summarize). Off → raw message history grows unbounded until the LLM's context limit is hit."
    Asserts endpoints return 503 when locus.context_window_management.enabled is False.
    """
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "context_window_management" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "context_window_management" in key else True)
    app = create_app()
    client = TestClient(app)

    r1 = client.post("/context/estimate", json={"text": "hello"})
    assert r1.status_code == 503
    assert r1.json() == {"disabled": "locus.context_window_management.enabled"}

    r2 = client.post("/context/compact", json={"messages": []})
    assert r2.status_code == 503
    assert r2.json() == {"disabled": "locus.context_window_management.enabled"}

    r3 = client.post("/context/compress", json={"text": "hello"})
    assert r3.status_code == 503
    assert r3.json() == {"disabled": "locus.context_window_management.enabled"}

    r4 = client.get("/context/retrieve/any-key")
    assert r4.status_code == 503
    assert r4.json() == {"disabled": "locus.context_window_management.enabled"}
