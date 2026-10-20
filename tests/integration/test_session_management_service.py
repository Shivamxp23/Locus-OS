"""
SPEC §5.1-5.8: Session Management & Telegram Bridge Service Integration Tests (F-0027 / US-58).
Validates FastAPI sidecar endpoints:
  - GET /sessions/config
  - POST /sessions/create
  - GET /sessions/{session_id}
  - POST /sessions/{session_id}/fork
  - POST /sessions/{session_id}/resume
  - POST /sessions/{session_id}/export
  - POST /sessions/telegram/bridge
  - Modular off-switch (HTTP 503) when locus.session_management.enabled is False
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sidecar.providers.session_management import DefaultSessionManagementProvider
from sidecar.service import create_app


@pytest.fixture
def client_and_provider(tmp_path: Path) -> Generator[tuple[TestClient, DefaultSessionManagementProvider], None, None]:
    provider = DefaultSessionManagementProvider(
        sessions_dir=tmp_path / "sessions",
        db_path=tmp_path / "tg.db",
    )
    app = create_app()
    app.state.registry.register("session_management", "default_session_management", lambda **kw: provider)
    client = TestClient(app)
    yield client, provider


def test_service_sessions_config(client_and_provider: tuple[TestClient, DefaultSessionManagementProvider]) -> None:
    """SPEC §5.1-5.8 line 5729: GET /sessions/config returns provider status."""
    client, _ = client_and_provider
    res = client.get("/sessions/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "default_session_management"


def test_service_session_lifecycle_and_forking(client_and_provider: tuple[TestClient, DefaultSessionManagementProvider]) -> None:
    """SPEC §5.1-5.8 lines 5746-5769: Session creation, appending, forking, resume, and export."""
    client, provider = client_and_provider

    # 1. Create Session
    create_res = client.post("/sessions/create", json={"session_id": "service-test-s1"})
    assert create_res.status_code == 200
    cdata = create_res.json()
    assert cdata["status"] == "ok"
    assert cdata["session_id"] == "service-test-s1"

    # Add entries via provider
    session = provider.load_session("service-test-s1")
    from sidecar.sessions.session_manager import SessionEntry
    e1 = SessionEntry(type="message", role="user", content="Turn 1 from user")
    session.append(e1)
    e2 = SessionEntry(type="message", role="assistant", content="Turn 1 response from assistant")
    session.append(e2)

    # 2. Get Session
    get_res = client.get("/sessions/service-test-s1")
    assert get_res.status_code == 200
    gdata = get_res.json()
    assert gdata["session_id"] == "service-test-s1"
    assert gdata["entries_count"] == 3

    # 3. Fork Session
    fork_res = client.post(
        "/sessions/service-test-s1/fork",
        json={"fork_point": e2.id, "summary": "Forked after Turn 1 response"},
    )
    assert fork_res.status_code == 200
    fdata = fork_res.json()
    assert fdata["parent_session_id"] == "service-test-s1"
    assert fdata["fork_point"] == e2.id
    forked_id = fdata["session_id"]

    # 4. Resume Session
    resume_res = client.post("/sessions/service-test-s1/resume")
    assert resume_res.status_code == 200
    rdata = resume_res.json()
    assert rdata["session_id"] == "service-test-s1"
    assert rdata["messages_count"] == 2

    # 5. Export Session to markdown
    export_res = client.post("/sessions/service-test-s1/export", json={"format": "markdown"})
    assert export_res.status_code == 200
    edata = export_res.json()
    assert edata["status"] == "ok"
    assert "# Locus Session Transcript: service-test-s1" in edata["data"]


def test_service_telegram_bridge(client_and_provider: tuple[TestClient, DefaultSessionManagementProvider]) -> None:
    """SPEC §5.1-5.8 lines 5771-5792: POST /sessions/telegram/bridge."""
    client, _ = client_and_provider
    res = client.post(
        "/sessions/telegram/bridge",
        json={"telegram_chat_id": "tg-chat-42", "user_message": "Hello via HTTP bridge"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["chat_id"] == "tg-chat-42"
    assert "session_id" in data
    assert "Acknowledged" in data["response"]


def test_service_sessions_off_switch_503(client_and_provider: tuple[TestClient, DefaultSessionManagementProvider]) -> None:
    """SPEC §03 / §5.1-5.8: Off-switch returns 503 with disabled config key."""
    client, _ = client_and_provider

    with patch("sidecar.config.get", return_value=False), \
         patch("sidecar.config.is_enabled", return_value=False):
        res1 = client.get("/sessions/config")
        assert res1.status_code == 503
        assert res1.json()["disabled"] == "locus.session_management.enabled"

        res2 = client.post("/sessions/create", json={})
        assert res2.status_code == 503

        res3 = client.get("/sessions/service-test-s1")
        assert res3.status_code == 503

        res4 = client.post("/sessions/telegram/bridge", json={"telegram_chat_id": "1", "user_message": "hi"})
        assert res4.status_code == 503
