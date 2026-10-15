"""sidecar/mcp/server.py - Model Context Protocol (MCP) Server.

Implements Spec §18.1-18.5:
- JSON-RPC 2.0 protocol endpoint for MCP tools and resources.
- Registers standard Locus tools and bridges Obsidian vault operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]


class MCPServer:
    """Model Context Protocol JSON-RPC Server implementation."""

    def __init__(self, server_name: str = "locus-mcp-server", version: str = "1.0.0") -> None:
        self.server_name = server_name
        self.version = version
        self.tools: dict[str, MCPTool] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        self.tools[name] = MCPTool(name, description, input_schema, handler)

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": self.server_name, "version": self.version},
                    "capabilities": {"tools": {}},
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.input_schema,
                        }
                        for t in self.tools.values()
                    ]
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            tool = self.tools.get(tool_name)
            if not tool:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method/Tool '{tool_name}' not found"},
                }
            try:
                out = tool.handler(tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": str(out)}]},
                }
            except Exception as ex:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(ex)},
                }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unhandled MCP method: {method}"},
        }
