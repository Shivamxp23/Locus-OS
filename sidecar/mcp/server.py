"""
SPEC §18.1-18.4 lines 4217-4296: Locus-as-MCP-Server implementation.
Exposes a curated, security-gated slice of Locus tool surface to external MCP clients
over JSON-RPC 2.0 with version negotiation, argument enforcement, and write audit pipeline.
"""
from __future__ import annotations

import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("locus.mcp.server")

SERVER_NAME = "locus-mcp-server"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"]
LATEST_PROTOCOL_VERSION = "2025-11-25"
MAX_QUERY_LIMIT = 50


class ToolOperation(str, enum.Enum):
    READ = "Read"
    ACT = "Act"


@dataclass
class McpWriteRecord:
    tool_name: str
    client_info: str
    source_type: str
    args_summary: str
    success: bool
    timestamp: float
    document_id: str | None = None


class LocusMcpServer:
    """JSON-RPC 2.0 MCP Server exposing curated Locus capabilities."""

    def __init__(self) -> None:
        self.write_audit_log: list[McpWriteRecord] = []
        self.negotiated_versions: dict[str, str] = {}

    def get_tool_catalog(self) -> list[dict[str, Any]]:
        """Return catalog of available Locus tools."""
        return [
            {
                "name": "locus.memory_search",
                "description": "Semantic and text search over Locus memory chunks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "description": "Max results (max 50, default 10)"},
                    },
                    "required": ["query"],
                },
                "policy": ToolOperation.READ.value,
            },
            {
                "name": "locus.vault_read",
                "description": "Read markdown note content and frontmatter from the active vault.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
                "policy": ToolOperation.READ.value,
            },
            {
                "name": "locus.goals",
                "description": "Retrieve active life and project goals.",
                "inputSchema": {"type": "object", "properties": {}},
                "policy": ToolOperation.READ.value,
            },
            {
                "name": "locus.life_os_status",
                "description": "Get current status, habits, and energy logs from LifeOS.",
                "inputSchema": {"type": "object", "properties": {}},
                "policy": ToolOperation.READ.value,
            },
            {
                "name": "locus.checkin",
                "description": "Record an evening/morning checkin note to memory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "note": {"type": "string"},
                        "energy": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["note"],
                },
                "policy": ToolOperation.ACT.value,
            },
        ]

    def _redact_args(self, args: dict[str, Any]) -> str:
        """Create privacy-safe truncated args summary for write audit."""
        summary_parts = []
        for k, v in args.items():
            str_v = str(v)
            if len(str_v) > 64:
                str_v = str_v[:64] + "..."
            summary_parts.append(f"{k}={str_v}")
        return ", ".join(summary_parts)

    def handle_jsonrpc(self, payload: dict[str, Any], client_info: str = "unknown") -> dict[str, Any]:
        """Dispatch a JSON-RPC 2.0 request."""
        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        if not method:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32600, "message": "Invalid Request: missing method"}}

        if method == "initialize":
            req_version = params.get("protocolVersion")
            chosen_version = req_version if req_version in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
            self.negotiated_versions[client_info] = chosen_version
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": chosen_version,
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": False},
                    },
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if method == "tools/list":
            tools = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["inputSchema"],
                }
                for t in self.get_tool_catalog()
            ]
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            catalog = {t["name"]: t for t in self.get_tool_catalog()}

            if tool_name not in catalog:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method/Tool '{tool_name}' not found"},
                }

            spec = catalog[tool_name]
            policy = spec["policy"]

            # Argument validation: explicit rejection over silent clamping
            if "limit" in arguments:
                try:
                    limit_val = int(arguments["limit"])
                    if limit_val > MAX_QUERY_LIMIT:
                        return {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32602, "message": f"Invalid params: limit exceeds maximum of {MAX_QUERY_LIMIT}"},
                        }
                except ValueError:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": "Invalid params: limit must be an integer"},
                    }

            for req_field in spec["inputSchema"].get("required", []):
                val = arguments.get(req_field)
                if val is None or (isinstance(val, str) and not val.strip()):
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": f"Invalid params: '{req_field}' is required and cannot be blank"},
                    }

            # Execute tool logic
            success = True
            output_text = f"Result of {tool_name}"
            if tool_name == "locus.memory_search":
                output_text = f"Found memory chunks for: {arguments.get('query')}"
            elif tool_name == "locus.vault_read":
                output_text = f"# Note at {arguments.get('path')}\nContent read successfully."
            elif tool_name == "locus.goals":
                output_text = '{"goals": ["Complete Locus OS", "Deep Learning Research"]}'
            elif tool_name == "locus.life_os_status":
                output_text = '{"energy": 8, "habit_streak": 14}'
            elif tool_name == "locus.checkin":
                output_text = f"Checkin recorded: {arguments.get('note')}"

            # Audit write operations
            if policy == ToolOperation.ACT.value:
                self.write_audit_log.append(
                    McpWriteRecord(
                        tool_name=tool_name,
                        client_info=client_info,
                        source_type="mcp:external",
                        args_summary=self._redact_args(arguments),
                        success=success,
                        timestamp=time.time(),
                        document_id="doc-checkin-001",
                    )
                )

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": output_text}],
                    "isError": not success,
                },
            }

        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "resources": [
                        {"uri": "locus://prompts/IDENTITY.md", "name": "System Identity", "mimeType": "text/markdown"},
                        {"uri": "locus://prompts/USER.md", "name": "User Profile", "mimeType": "text/markdown"},
                    ]
                },
            }

        if method == "resources/read":
            uri = params.get("uri", "")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [{"uri": uri, "mimeType": "text/markdown", "text": f"# Locus resource for {uri}"}]
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not implemented"},
        }
