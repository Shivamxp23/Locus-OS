"""
SPEC §2.6a / F-0097 / US-36: Integration Tests for Streaming (SSE) Service.
Asserts FastAPI routes `/stream/events`, `/stream/config`, and the 503 off-switch.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.service import create_app
from sidecar.providers.streaming_sse import SSEEvent
from sidecar.streaming_sse import StreamingSSEProvider


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_stream_events_endpoint(client):
    """SPEC §2.6a line 2644: SSE stream events endpoint returns text/event-stream."""
    resp = client.get("/stream/events?text=Testing%20SSE%20stream&chunk_size=8")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    content = resp.text
    assert "event: delta\n" in content
    assert "data: " in content
    assert "event: done\n" in content


def test_stream_config_endpoint(client):
    """SPEC §2.6a line 2645: SSE configuration endpoint."""
    resp = client.get("/stream/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["media_type"] == "text/event-stream"
    assert "StreamingSSEProvider" in data["provider"]


def test_stream_503_off_switch(monkeypatch):
    """Modularity architecture (03): Off switch on locus.streaming_sse.enabled returns 503."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "streaming_sse" in key else True)
    app = create_app()
    with TestClient(app) as disabled_client:
        get_events_resp = disabled_client.get("/stream/events")
        assert get_events_resp.status_code == 503
        assert get_events_resp.json()["disabled"] == "locus.streaming_sse.enabled"

        get_config_resp = disabled_client.get("/stream/config")
        assert get_config_resp.status_code == 503
        assert get_config_resp.json()["disabled"] == "locus.streaming_sse.enabled"
