"""
Abstract base provider and data models for Custom Locus Tools (SPEC §3.12 / F-0104).
Defines contracts for registration, toggling, schema introspection, and execution
of custom Locus agent tools.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CustomToolSpec:
    """Specification and schema for a custom Locus tool."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    category: str = "custom"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.parameters),
            "category": self.category,
            "enabled": self.enabled,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CustomToolSpec:
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            category=data.get("category", "custom"),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class CustomToolResult:
    """Execution outcome for a custom Locus tool."""
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


@dataclass
class CustomLocusToolsConfig:
    """Configuration for custom tools registry and individual toggles."""
    enabled: bool = True
    tool_toggles: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "tool_toggles": dict(self.tool_toggles),
        }


class BaseCustomLocusToolsProvider(ABC):
    """Interface for Custom Locus Tools providers."""

    def __init__(self, name: str = "custom_locus_tools") -> None:
        self.name = name

    @abstractmethod
    def register_tool(self, spec: CustomToolSpec) -> bool:
        """Register a new custom tool or update an existing tool definition."""
        pass

    @abstractmethod
    def unregister_tool(self, tool_name: str) -> bool:
        """Remove a custom tool from registry by name."""
        pass

    @abstractmethod
    def get_tool(self, tool_name: str) -> Optional[CustomToolSpec]:
        """Retrieve tool specification by name if registered."""
        pass

    @abstractmethod
    def list_tools(self, include_disabled: bool = False) -> List[CustomToolSpec]:
        """List registered tools, optionally filtering out disabled tools."""
        pass

    @abstractmethod
    def is_tool_enabled(self, tool_name: str) -> bool:
        """Check whether a specific tool is enabled."""
        pass

    @abstractmethod
    def set_tool_enabled(self, tool_name: str, enabled: bool) -> None:
        """Toggle a specific tool's enabled state."""
        pass

    @abstractmethod
    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> CustomToolResult:
        """Execute a custom tool with validated parameters."""
        pass

    @abstractmethod
    def get_config(self) -> CustomLocusToolsConfig:
        """Return the active custom tools configuration."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return provider health status and diagnostics."""
        pass
