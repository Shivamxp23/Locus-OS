"""
SPEC §9.4 lines 6057-6142: Unit tests for ACP Protocol (F-0033 / US-64).
"""
from __future__ import annotations

import json
from typing import Any, Dict
import pytest

from sidecar.acp_server import ACPClient, ACPEvent, ACPServer
from sidecar.providers.acp_protocol import (
    BaseACPClientProvider,
    DefaultACPClientProvider,
)


def test_acp_server_handle_initialize() -> None:
    """SPEC §9.4 lines 6071-6088: "FUNCTION initialize(client_info: Dict) -> Dict: payload = { 'jsonrpc': '2.0', 'method': 'initialize', ... }" """
    server = ACPServer()
    msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "1.0",
            "clientInfo": {"name": "test-client", "version": "1.0"},
            "capabilities": {"tools": True, "sampling": True},
        },
    }
    res = server.handle_message(msg)
    assert res["jsonrpc"] == "2.0"
    assert res["id"] == 1
    result = res["result"]
    assert result["protocolVersion"] == "1.0"
    assert "sessionId" in result
    assert result["capabilities"]["tools"] is True


def test_acp_server_handle_execute() -> None:
    """SPEC §9.4 lines 6090-6111: "FUNCTION dispatch_agent_task(target_agent_id: string, prompt: string, tools: List) -> AsyncIterator[ACPEvent]:" """
    server = ACPServer()
    msg = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "agent/execute",
        "params": {
            "target": "researcher-agent",
            "prompt": "Analyze market trends",
            "availableTools": ["web_search", "fetch"],
            "sessionId": "test-session",
        },
    }
    res = server.handle_message(msg)
    assert res["jsonrpc"] == "2.0"
    assert res["id"] == 2
    result = res["result"]
    assert result["status"] == "completed"
    assert result["target"] == "researcher-agent"
    events = result["events"]
    assert len(events) >= 2
    assert any(e["event_type"] == "progress" for e in events)
    assert any(e["event_type"] == "completed" for e in events)


def test_acp_server_handle_cancel() -> None:
    """SPEC §9.4 lines 6113-6119: "FUNCTION cancel_request(req_id: int): notification = { 'jsonrpc': '2.0', 'method': '$/cancelRequest', 'params': { 'requestId': req_id } }" """
    server = ACPServer()
    cancel_msg = {
        "jsonrpc": "2.0",
        "method": "$/cancelRequest",
        "params": {"requestId": 42},
    }
    res = server.handle_message(cancel_msg)
    assert res["method"] == "$/cancelRequest"
    assert res["params"]["status"] == "acknowledged"
    assert 42 in server.cancelled_requests

    # Verify cancelled request gets error response
    exec_msg = {
        "jsonrpc": "2.0",
        "id": 42,
        "method": "agent/execute",
        "params": {"prompt": "should fail"},
    }
    exec_res = server.handle_message(exec_msg)
    assert "error" in exec_res
    assert exec_res["error"]["code"] == -32000


def test_acp_client_initialize_and_dispatch() -> None:
    """SPEC §9.4 lines 6066-6120: "CLASS ACPClient: transport, session_id, request_id, pending_requests" """
    server = ACPServer()
    client = ACPClient(server=server)

    init_res = client.initialize()
    assert "result" in init_res
    assert client.session_id.startswith("acp-session-")

    events = client.dispatch_agent_task(
        target_agent_id="coder",
        prompt="Write a fibonacci function",
        tools=["python_eval"],
    )
    assert len(events) >= 2
    assert isinstance(events[0], ACPEvent)

    cancel_res = client.cancel_request(99)
    assert cancel_res["method"] == "$/cancelRequest"


def test_acp_server_invalid_jsonrpc_envelope() -> None:
    """SPEC §9.4 lines 6057-6065: Validate JSON-RPC 2.0 version envelope and unknown method error."""
    server = ACPServer()
    # Invalid jsonrpc version
    bad_msg = {"jsonrpc": "1.0", "id": 1, "method": "initialize"}
    res = server.handle_message(bad_msg)
    assert res["error"]["code"] == -32600

    # Unknown method
    unknown_msg = {"jsonrpc": "2.0", "id": 2, "method": "nonexistent/method"}
    res2 = server.handle_message(unknown_msg)
    assert res2["error"]["code"] == -32601


def test_acp_provider_off_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §9.4 line 6138: "Swappable / off state: locus.acp_protocol.enabled. Off -> 503 HTTP off-switch" """
    provider = DefaultACPClientProvider()
    assert provider.is_available() is True

    init_data = provider.initialize()
    assert "result" in init_data

    # Off-switch
    monkeypatch.setattr(
        "sidecar.config.get",
        lambda key, default=None: False if key == "locus.acp_protocol.enabled" else default,
    )
    assert provider.is_available() is False

    with pytest.raises(RuntimeError, match="disabled"):
        provider.initialize()

    with pytest.raises(RuntimeError, match="disabled"):
        provider.execute("agent", "prompt")

    with pytest.raises(RuntimeError, match="disabled"):
        provider.cancel(1)
