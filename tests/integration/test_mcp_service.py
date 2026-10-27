"""
SPEC §18.1-18.4 lines 4033-4325: Integration tests for MCP Server/Client routes (F-0048 / US-81).
Tests FastAPI endpoints under /mcp/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.mcp.client import MockMcpClient
from sidecar.mcp.registry import McpServerConfig
from sidecar.providers.mcp import DefaultMcpProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    # Instantiate and configure DefaultMcpProvider with a test server
    provider = DefaultMcpProvider()
    provider.registry.register_server(
        McpServerConfig(
            server_id="srv-mock-1",
            name="srv-mock-1",
            transport="mock",
            enabled=True,
        )
    )
    app.state.mcp_provider = provider
    return TestClient(app)


def test_service_mcp_status(client: TestClient) -> None:
    """SPEC §18.1 line 4033: GET /mcp/status endpoint returns readiness."""
    res = client.get("/mcp/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "registered_servers" in data


def test_service_mcp_connect_and_disconnect(client: TestClient) -> None:
    """SPEC §18.1 line 4145: POST /mcp/servers/connect and /disconnect."""
    res_conn = client.post("/mcp/servers/connect", json={"server_id": "srv-mock-1"})
    assert res_conn.status_code == 200
    assert res_conn.json()["connected"] is True

    res_list = client.get("/mcp/servers/list")
    assert res_list.status_code == 200
    servers = res_list.json()["servers"]
    assert any(s["server_id"] == "srv-mock-1" and s["connected"] is True for s in servers)

    res_dis = client.post("/mcp/servers/disconnect", json={"server_id": "srv-mock-1"})
    assert res_dis.status_code == 200
    assert res_dis.json()["disconnected"] is True


def test_service_mcp_tools_list_and_call(client: TestClient) -> None:
    """SPEC §18.1 line 4080: GET /mcp/tools/list and POST /mcp/tools/call."""
    # Connect server first
    client.post("/mcp/servers/connect", json={"server_id": "srv-mock-1"})

    res_tools = client.get("/mcp/tools/list")
    assert res_tools.status_code == 200
    tools = res_tools.json()["tools"]
    assert any(t["name"] == "echo" for t in tools)

    res_call = client.post(
        "/mcp/tools/call",
        json={"server_id": "srv-mock-1", "tool_name": "echo", "arguments": {"message": "integration test"}},
    )
    assert res_call.status_code == 200
    data = res_call.json()
    assert data["status"] == "ok"
    assert data["result"]["content"][0]["text"] == "integration test"


def test_service_mcp_jsonrpc_server_endpoint(client: TestClient) -> None:
    """SPEC §18.4 line 4228: POST /mcp/server/jsonrpc dispatch."""
    req = {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "tools/list",
    }
    res = client.post("/mcp/server/jsonrpc", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["jsonrpc"] == "2.0"
    assert "tools" in data["result"]
    names = [t["name"] for t in data["result"]["tools"]]
    assert "locus.memory_search" in names


def test_service_mcp_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §18.1 line 4033: Off-switch returns HTTP 503."""
    # Switch 1: locus.mcp_server_client.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.mcp_server_client.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.mcp_server_client.enabled" else True)

    res_status = client.get("/mcp/status")
    assert res_status.status_code == 503
    assert res_status.json()["disabled"] == "locus.mcp_server_client.enabled"

    res_tools = client.get("/mcp/tools/list")
    assert res_tools.status_code == 503

    res_conn = client.post("/mcp/servers/connect", json={"server_id": "any"})
    assert res_conn.status_code == 503

    # Switch 2: locus.mcp.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.mcp.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.mcp.enabled" else True)

    res_status2 = client.get("/mcp/status")
    assert res_status2.status_code == 503
    assert res_status2.json()["disabled"] == "locus.mcp.enabled"
