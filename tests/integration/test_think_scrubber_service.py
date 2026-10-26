"""
SPEC §13.9 lines 3513-3598: Integration tests for Think Token Scrubbing (F-0042 / US-74).
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


def test_service_think_scrubber_feed_and_flush(client: TestClient) -> None:
    """SPEC §13.9 lines 3535-3575: Test POST /security/think_scrubber/feed and /flush."""
    # Reset scrubber
    res_reset = client.post("/security/think_scrubber/reset")
    assert res_reset.status_code == 200

    # Stream deltas
    delta1 = client.post("/security/think_scrubber/feed", json={"delta": "<think>Processing"})
    assert delta1.status_code == 200
    assert delta1.json()["visible"] == ""

    delta2 = client.post("/security/think_scrubber/feed", json={"delta": " thoughts</think>Final answer."})
    assert delta2.status_code == 200
    assert "Final answer." in delta2.json()["visible"]
    assert "Processing" not in delta2.json()["visible"]

    flush_res = client.post("/security/think_scrubber/flush")
    assert flush_res.status_code == 200


def test_service_think_scrubber_scrub_complete(client: TestClient) -> None:
    """SPEC §13.9 line 3595: Test POST /security/think_scrubber/scrub_complete."""
    payload = (
        "<thinking>\nStep 1: calculate derivative\nStep 2: simplify\n</thinking>\n"
        "The simplified result is 2x."
    )
    res = client.post("/security/think_scrubber/scrub_complete", json={"text": payload})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "<thinking>" not in data["scrubbed"]
    assert "</thinking>" not in data["scrubbed"]
    assert "Step 1: calculate" not in data["scrubbed"]
    assert data["scrubbed"] == "The simplified result is 2x."


def test_service_think_scrubber_tags(client: TestClient) -> None:
    """SPEC §13.9 line 3532: Test GET /security/think_scrubber/tags."""
    res = client.get("/security/think_scrubber/tags")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    tags = data["tags"]
    assert "think" in tags
    assert "thinking" in tags
    assert "reasoning" in tags
    assert "thought" in tags
    assert "REASONING_SCRATCHPAD" in tags


def test_service_think_scrubber_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §13.9 line 3591: Modular off-switches return HTTP 503."""
    # Off-switch 1: locus.think_token_scrubbing.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.think_token_scrubbing.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.think_token_scrubbing.enabled" else True)

    res_feed = client.post("/security/think_scrubber/feed", json={"delta": "<think>"})
    assert res_feed.status_code == 503
    assert res_feed.json()["disabled"] == "locus.think_token_scrubbing.enabled"

    res_flush = client.post("/security/think_scrubber/flush")
    assert res_flush.status_code == 503

    res_complete = client.post("/security/think_scrubber/scrub_complete", json={"text": "test"})
    assert res_complete.status_code == 503

    res_tags = client.get("/security/think_scrubber/tags")
    assert res_tags.status_code == 503

    # Off-switch 2: locus.security.think_scrubbing.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.think_scrubbing.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.think_scrubbing.enabled" else True)

    res2 = client.post("/security/think_scrubber/feed", json={"delta": "<think>"})
    assert res2.status_code == 503
