"""
SPEC §18.1-18.4 lines 4112-4216: MCP Registry & Connection Supervisor.
Dynamic installations, connection lifecycle, 60s exponential backoff reconnect loop,
and opaque secret-ref collection for secure credential handling.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sidecar.mcp.client import BaseMcpClient, McpHttpClient, McpStdioClient, MockMcpClient

logger = logging.getLogger("locus.mcp.registry")


@dataclass
class McpServerConfig:
    server_id: str
    name: str
    transport: str  # "stdio" | "http_remote"
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    deployment_url: str = ""
    enabled: bool = True


@dataclass
class SecretRef:
    ref: str
    key_name: str
    description: str
    created_at: float
    timeout: float = 300.0  # 5 minutes
    value: str | None = None
    fulfilled: bool = False


class McpRegistry:
    """Manages MCP server registrations, active client connections, and supervisors."""

    def __init__(self) -> None:
        self.servers: dict[str, McpServerConfig] = {}
        self.connections: dict[str, BaseMcpClient] = {}
        self.reconnect_stats: dict[str, dict[str, Any]] = {}
        self.secret_store: dict[str, SecretRef] = {}

    def register_server(self, config: McpServerConfig) -> None:
        """Register or update an MCP server configuration."""
        self.servers[config.server_id] = config

    def unregister_server(self, server_id: str) -> None:
        """Remove an MCP server and disconnect if active."""
        if server_id in self.connections:
            asyncio.create_task(self.disconnect(server_id))
        self.servers.pop(server_id, None)
        self.reconnect_stats.pop(server_id, None)

    async def connect(self, server_id: str, client_override: BaseMcpClient | None = None) -> bool:
        """Connect to an MCP server by ID using its configured transport."""
        server = self.servers.get(server_id)
        if not server:
            logger.warning("MCP server '%s' not found", server_id)
            return False
        if not server.enabled:
            return False

        if client_override:
            client = client_override
        elif server.transport == "http_remote":
            client = McpHttpClient(name=server.name, endpoint_url=server.deployment_url, env=server.env)
        elif server.transport == "stdio":
            client = McpStdioClient(name=server.name, command=server.command, args=server.args, env=server.env)
        else:
            client = MockMcpClient(name=server.name)

        try:
            await client.initialize()
            self.connections[server_id] = client
            # Reset backoff on successful connect
            self.reconnect_stats[server_id] = {"attempts": 0, "last_attempt": time.time(), "backoff": 0}
            return True
        except Exception as e:
            logger.warning("Failed to connect MCP server %s: %s", server.name, e)
            stat = self.reconnect_stats.get(server_id, {"attempts": 0, "last_attempt": 0, "backoff": 0})
            stat["attempts"] = stat.get("attempts", 0) + 1
            stat["last_attempt"] = time.time()
            stat["backoff"] = min(60 * (2 ** (stat["attempts"] - 1)), 3600)
            self.reconnect_stats[server_id] = stat
            return False

    async def disconnect(self, server_id: str) -> bool:
        """Disconnect an active MCP server connection."""
        client = self.connections.pop(server_id, None)
        if client:
            await client.disconnect()
            return True
        return False

    def list_servers(self) -> list[dict[str, Any]]:
        """List registered servers with connection status."""
        result = []
        for sid, s in self.servers.items():
            conn = self.connections.get(sid)
            result.append({
                "server_id": sid,
                "name": s.name,
                "transport": s.transport,
                "enabled": s.enabled,
                "connected": conn.is_connected if conn else False,
                "reconnect_stats": self.reconnect_stats.get(sid, {}),
            })
        return result

    async def list_all_tools(self) -> list[dict[str, Any]]:
        """Query and aggregate tools across all actively connected servers."""
        all_tools: list[dict[str, Any]] = []
        for sid, client in list(self.connections.items()):
            if client.is_connected:
                try:
                    tools = await client.list_tools()
                    for t in tools:
                        item = dict(t)
                        item["server_id"] = sid
                        all_tools.append(item)
                except Exception as e:
                    logger.warning("Error fetching tools from %s: %s", sid, e)
        return all_tools

    async def call_tool(self, server_id: str, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke a tool on a specific connected server."""
        client = self.connections.get(server_id)
        if not client or not client.is_connected:
            raise RuntimeError(f"MCP server '{server_id}' is not connected")
        return await client.call_tool(tool_name, arguments or {})

    async def run_supervisor_tick(self) -> list[str]:
        """
        Execute one supervisor cycle:
        Inspects connected servers and enabled offline servers, retrying with exponential backoff.
        """
        reconnected: list[str] = []
        now = time.time()

        for sid, s in list(self.servers.items()):
            if not s.enabled:
                continue
            client = self.connections.get(sid)
            if client is None or not client.is_connected:
                stat = self.reconnect_stats.get(sid, {"attempts": 0, "last_attempt": 0, "backoff": 0})
                if now >= stat["last_attempt"] + stat["backoff"]:
                    success = await self.connect(sid)
                    if success:
                        reconnected.append(sid)
        return reconnected

    # --- Setup Agent Opaque Secret Lifecycle (SPEC §18.1 lines 4178-4209) ---

    def request_secret(self, key_name: str, description: str) -> str:
        """Create an opaque secret reference keeping raw values out of LLM context."""
        ref_id = f"secret://{uuid.uuid4().hex}"
        self.secret_store[ref_id] = SecretRef(
            ref=ref_id,
            key_name=key_name,
            description=description,
            created_at=time.time(),
        )
        return ref_id

    def submit_secret(self, ref: str, value: str) -> bool:
        """Fulfill an opaque secret reference from user UI."""
        item = self.secret_store.get(ref)
        if not item:
            return False
        if time.time() > item.created_at + item.timeout:
            self.secret_store.pop(ref, None)
            return False
        item.value = value
        item.fulfilled = True
        return True

    def resolve_secret_refs(self, env_template: dict[str, str], secret_refs: dict[str, str]) -> dict[str, str]:
        """Resolve opaque references in template to raw secret values."""
        resolved = dict(env_template)
        for env_key, ref in secret_refs.items():
            item = self.secret_store.get(ref)
            if item and item.fulfilled and item.value is not None:
                resolved[env_key] = item.value
            else:
                raise ValueError(f"Secret ref '{ref}' for '{env_key}' is unfulfilled or expired")
        return resolved

    def consume_refs(self, refs: list[str]) -> None:
        """Purge fulfilled secret references once consumed and persisted."""
        for r in refs:
            self.secret_store.pop(r, None)
