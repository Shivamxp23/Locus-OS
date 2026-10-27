"""
Model Context Protocol package for Locus Sidecar.
"""
from __future__ import annotations

from sidecar.mcp.client import (
    BaseMcpClient,
    McpHttpClient,
    McpStdioClient,
    MockMcpClient,
)
from sidecar.mcp.registry import (
    McpRegistry,
    McpServerConfig,
    SecretRef,
)
from sidecar.mcp.sanitize import (
    MAX_DESCRIPTION_BYTES,
    sanitize_for_llm,
    strip_control_chars,
    strip_instruction_fences,
    truncate_to_bytes,
)
from sidecar.mcp.server import (
    LocusMcpServer,
    McpWriteRecord,
    ToolOperation,
)

__all__ = [
    "BaseMcpClient",
    "McpHttpClient",
    "McpStdioClient",
    "MockMcpClient",
    "McpRegistry",
    "McpServerConfig",
    "SecretRef",
    "MAX_DESCRIPTION_BYTES",
    "sanitize_for_llm",
    "strip_control_chars",
    "strip_instruction_fences",
    "truncate_to_bytes",
    "LocusMcpServer",
    "McpWriteRecord",
    "ToolOperation",
]
