"""
SPEC §4.18: Memory Provider Interface Integration Tests (F-0118 / US-57).
Validates FastAPI sidecar endpoints for Memory Provider & Stackable Memory Manager:
  - GET /memory/provider/config
  - POST /memory/provider/prefetch
  - POST /memory/provider/sync-turn
  - GET /memory/provider/tools
  - POST /memory/provider/tool-call
  - Modular off-switch (HTTP 503) when locus.memory_provider.enabled is False
"""
from __future__ import annotations

import json
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sidecar.memory.provider_interface import DefaultMemoryProvider, MemoryManager
from sidecar.service import create_app


@pytest.fixture
def client_and_manager() -> Generator[tuple[TestClient, MemoryManager], None, None]:
    mgr = MemoryManager()
    p1 = DefaultMemoryProvider(name="test_primary")
    mgr.register_provider(p1, session_id="s_service_test", is_primary=True)
    app = create_app()
    app.state.registry.register("memory_provider_manager", "default_memory_manager", lambda **kw: mgr)
    client = TestClient(app)
    yield client, mgr


def test_service_memory_provider_config(client_and_manager: tuple[TestClient, MemoryManager]) -> None:
    """SPEC §4.18 line 5253: is_available() & runtime status.
    Asserts GET /memory/provider/config returns active primary and list of registered providers.
    """
    client, _ = client_and_manager
    res = client.get("/memory/provider/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["primary"] == "test_primary"
    assert "test_primary" in data["active_providers"]
    assert data["count"] >= 1


def test_service_memory_provider_prefetch_and_sync_turn(client_and_manager: tuple[TestClient, MemoryManager]) -> None:
    """SPEC §4.18 lines 5260, 5267: prefetch & sync_turn.
    Asserts syncing a turn allows subsequent prefetch recall over HTTP.
    """
    client, _ = client_and_manager

    # Sync a completed conversational turn
    res_sync = client.post(
        "/memory/provider/sync-turn",
        json={
            "user_content": "Where is the cognitive architecture defined?",
            "assistant_content": "The cognitive architecture is specified in LOCUS_SYSTEM_v1.md.",
            "session_id": "s_service_test",
        },
    )
    assert res_sync.status_code == 200
    assert res_sync.json()["synced"] is True

    # Prefetch query
    res_prefetch = client.post(
        "/memory/provider/prefetch",
        json={"query": "cognitive architecture", "session_id": "s_service_test"},
    )
    assert res_prefetch.status_code == 200
    data = res_prefetch.json()
    assert "cognitive architecture" in data["context"] or "LOCUS_SYSTEM_v1" in data["context"]


def test_service_memory_provider_tools_and_call(client_and_manager: tuple[TestClient, MemoryManager]) -> None:
    """SPEC §4.18 lines 5270-5271: get_tool_schemas & handle_tool_call."""
    client, _ = client_and_manager

    # List schemas
    res_tools = client.get("/memory/provider/tools")
    assert res_tools.status_code == 200
    tools = res_tools.json()["tools"]
    assert any(t.get("function", {}).get("name") == "test_primary_search" for t in tools)

    # Invoke tool call
    res_call = client.post(
        "/memory/provider/tool-call",
        json={"tool_name": "test_primary_search", "args": {"query": "test"}},
    )
    assert res_call.status_code == 200
    call_data = json.loads(res_call.json()["result"])
    assert call_data.get("status") == "ok"


def test_service_memory_provider_off_switch_503(client_and_manager: tuple[TestClient, MemoryManager]) -> None:
    """SPEC §4.18 line 5308: Modular off-switch returning 503."""
    client, _ = client_and_manager
    with patch("sidecar.config.get", return_value=False), patch("sidecar.config.is_enabled", return_value=False):
        res_cfg = client.get("/memory/provider/config")
        assert res_cfg.status_code == 503
        assert res_cfg.json()["disabled"] == "locus.memory_provider.enabled"

        res_pf = client.post("/memory/provider/prefetch", json={"query": "test"})
        assert res_pf.status_code == 503

        res_sync = client.post(
            "/memory/provider/sync-turn",
            json={"user_content": "u", "assistant_content": "a"},
        )
        assert res_sync.status_code == 503
