"""sidecar/mcp/client.py - Model Context Protocol (MCP) Client.

Implements Spec §18.1-18.5:
- Client connector for remote and local MCP servers.
- Manages initialize handshakes, tool discovery, and tool dispatching.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sidecar.mcp.server import MCPServer


class MCPClient:
    """Connects to an MCP server endpoint and executes tools."""

    def __init__(self, server: Optional[MCPServer] = None) -> None:
        self.server = server or MCPServer()
        self.is_initialized = False

    def initialize(self) -> bool:
        resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        self.is_initialized = "result" in resp
        return self.is_initialized

    def list_tools(self) -> list[dict[str, Any]]:
        resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
