"""
SPEC §18.1-18.4 lines 4033-4325: MCP Provider for Locus Sidecar.
Provides modular off-switch locus.mcp_server_client.enabled returning HTTP 503.
"""
from __future__ import annotations

import abc
import logging
from typing import Any

import sidecar.config as config
from sidecar.mcp.client import BaseMcpClient
from sidecar.mcp.registry import McpRegistry, McpServerConfig
from sidecar.mcp.server import LocusMcpServer

logger = logging.getLogger("locus.providers.mcp")


class BaseMcpProvider(abc.ABC):
    """Abstract base provider for Model Context Protocol Server and Client operations."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_feature_enabled(self) -> tuple[bool, str]:
        """Check if MCP features are enabled via config."""
        raise NotImplementedError

    @abc.abstractmethod
    async def connect_server(self, server_id: str, client_override: BaseMcpClient | None = None) -> dict[str, Any]:
        """Connect to an MCP server."""
        raise NotImplementedError

    @abc.abstractmethod
    async def disconnect_server(self, server_id: str) -> dict[str, Any]:
        """Disconnect an MCP server."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_servers(self) -> list[dict[str, Any]]:
        """List registered MCP servers."""
        raise NotImplementedError

    @abc.abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        """Aggregate tools across all connected MCP servers."""
        raise NotImplementedError

    @abc.abstractmethod
    async def call_tool(self, server_id: str, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Call a tool on a connected MCP server."""
        raise NotImplementedError

    @abc.abstractmethod
    def handle_server_jsonrpc(self, payload: dict[str, Any], client_info: str = "unknown") -> dict[str, Any]:
        """Process inbound JSON-RPC 2.0 requests to Locus-as-MCP-server."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Return provider status and metrics."""
        raise NotImplementedError


class DefaultMcpProvider(BaseMcpProvider):
    """Default provider managing MCP client connections, registry, and server endpoints."""

    def __init__(self, registry: McpRegistry | None = None, server: LocusMcpServer | None = None) -> None:
        self.registry = registry or McpRegistry()
        self.server = server or LocusMcpServer()

    @property
    def name(self) -> str:
        return "default_mcp_provider"

    def is_feature_enabled(self) -> tuple[bool, str]:
        """Evaluate modular off-switches."""
        for switch in ("locus.mcp_server_client.enabled", "locus.mcp.enabled"):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    async def connect_server(self, server_id: str, client_override: BaseMcpClient | None = None) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        success = await self.registry.connect(server_id, client_override=client_override)
        return {"status": "ok" if success else "failed", "server_id": server_id, "connected": success}

    async def disconnect_server(self, server_id: str) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        disconnected = await self.registry.disconnect(server_id)
        return {"status": "ok", "server_id": server_id, "disconnected": disconnected}

    def list_servers(self) -> list[dict[str, Any]]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return [{"error": "feature_disabled", "disabled": switch, "status_code": 503}]
        return self.registry.list_servers()

    async def list_tools(self) -> list[dict[str, Any]]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return [{"error": "feature_disabled", "disabled": switch, "status_code": 503}]
        return await self.registry.list_all_tools()

    async def call_tool(self, server_id: str, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return await self.registry.call_tool(server_id, tool_name, arguments or {})

    def handle_server_jsonrpc(self, payload: dict[str, Any], client_info: str = "unknown") -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return self.server.handle_jsonrpc(payload, client_info=client_info)

    def get_status(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return {
            "status": "ready",
            "provider": self.name,
            "registered_servers": len(self.registry.servers),
            "active_connections": len(self.registry.connections),
            "audit_records": len(self.server.write_audit_log),
        }
