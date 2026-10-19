"""
Base provider interface for Tool System (SPEC §1.3, F-0003).
Defines contracts for AgentTool, AgentToolResult, lifecycle hooks, and canonical tool registry.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class ExecutionMode(str, Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


@dataclass
class TextContent:
    text: str
    type: str = "text"


@dataclass
class ImageContent:
    data: str
    mime_type: str = "image/png"
    type: str = "image"


ToolContent = Union[TextContent, ImageContent]


@dataclass
class AgentToolResult:
    content: List[Dict[str, Any]] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    terminate: bool = False
    is_error: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "details": self.details,
            "terminate": self.terminate,
            "isError": self.is_error,
        }


@dataclass
class AgentTool:
    name: str
    label: str
    description: str
    schema: Dict[str, Any]
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    prepare_arguments: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    execute_handler: Optional[Callable[[str, Dict[str, Any], Optional[Any]], AgentToolResult]] = None

    def execute(self, tool_call_id: str, params: Dict[str, Any], signal: Optional[Any] = None) -> AgentToolResult:
        if self.execute_handler:
            return self.execute_handler(tool_call_id, params, signal)
        return AgentToolResult(
            content=[{"type": "text", "text": f"Tool {self.name} executed successfully"}],
            details={"tool": self.name, "tool_call_id": tool_call_id, "params": params},
        )


@dataclass
class BeforeToolCallResult:
    block: bool = False
    reason: Optional[str] = None


class BaseToolSystemProvider(ABC):
    """Abstract base provider for managing Locus canonical tools and lifecycle."""

    @abstractmethod
    def list_tools(self) -> List[AgentTool]:
        """Return all registered and currently enabled AgentTools."""
        raise NotImplementedError

    @abstractmethod
    def get_tool(self, name: str) -> Optional[AgentTool]:
        """Retrieve a specific tool by name if registered and enabled."""
        raise NotImplementedError

    @abstractmethod
    def register_tool(self, tool: AgentTool) -> None:
        """Register a new or custom tool."""
        raise NotImplementedError

    @abstractmethod
    def is_tool_enabled(self, name: str) -> bool:
        """Check if an individual tool is enabled via config."""
        raise NotImplementedError

    @abstractmethod
    def execute_tool(
        self,
        name: str,
        tool_call_id: str,
        raw_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentToolResult:
        """Execute a tool through the full 5-step lifecycle."""
        raise NotImplementedError
