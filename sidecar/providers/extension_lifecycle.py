"""
Base provider definitions for Extension Lifecycle (SPEC §1.5, F-0005).
Defines contracts for the 25+ canonical lifecycle events, hook registration,
priority-ordered dispatch, and error containment across all extensions.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


CANONICAL_LIFECYCLE_EVENTS: List[str] = [
    # Core turn and message lifecycle
    "session_start",
    "turn_start",
    "message_start",
    "message_update",
    "message_end",
    "tool_execution_start",
    "tool_execution_update",
    "tool_execution_end",
    "turn_end",
    "agent_start",
    "agent_end",
    "session_shutdown",
    # Extended lifecycle & tree/session navigation
    "before_compact",
    "after_compact",
    "before_tree",
    "session_switch",
    "replaced_session",
    "context_usage_update",
    # Environment & resource events
    "project_trust",
    "resources_discover",
    "session_info_changed",
    "session_before_fork",
    "session_compact_failed",
    "mcp_servers_change",
    # Provider & model hooks
    "before_provider_request",
    "before_provider_headers",
    "after_provider_response",
    "provider_stream_event",
    "before_agent_start",
    "agent_before_settle",
    "agent_settled",
    "model_select",
    "thinking_level_select",
    "tool_call",
    "tool_result",
    "user_bash",
    "input",
]


@dataclass
class ExtensionHookDescriptor:
    hook_id: str
    extension_id: str
    event: str
    priority: int = 100
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hook_id": self.hook_id,
            "extension_id": self.extension_id,
            "event": self.event,
            "priority": self.priority,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class LifecycleDispatchResult:
    event: str
    hooks_executed: int
    hooks_skipped: int
    errors: List[Dict[str, Any]]
    modified_payload: Dict[str, Any]
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "hooks_executed": self.hooks_executed,
            "hooks_skipped": self.hooks_skipped,
            "errors": self.errors,
            "modified_payload": self.modified_payload,
            "duration_ms": self.duration_ms,
        }


class BaseExtensionLifecycleProvider(ABC):
    """Abstract contract for extension lifecycle management and event dispatch."""

    @abstractmethod
    def list_events(self) -> List[str]:
        """Return the canonical list of 25+ supported lifecycle events."""
        raise NotImplementedError

    @abstractmethod
    def register_hook(
        self,
        extension_id: str,
        event: str,
        handler: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
        priority: int = 100,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExtensionHookDescriptor:
        """Register a hook handler for a lifecycle event."""
        raise NotImplementedError

    @abstractmethod
    def unregister_hook(self, hook_id: str) -> bool:
        """Unregister a hook by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_hooks(
        self,
        extension_id: Optional[str] = None,
        event: Optional[str] = None,
    ) -> List[ExtensionHookDescriptor]:
        """List registered hooks filtered by extension or event."""
        raise NotImplementedError

    @abstractmethod
    def dispatch_event(
        self,
        event: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> LifecycleDispatchResult:
        """Dispatch a lifecycle event across all active extensions in priority order."""
        raise NotImplementedError

    @abstractmethod
    def is_extension_enabled(self, extension_id: str) -> bool:
        """Check whether an individual extension is enabled."""
        raise NotImplementedError

    @abstractmethod
    def set_extension_enabled(self, extension_id: str, enabled: bool) -> None:
        """Enable or disable an individual extension."""
        raise NotImplementedError
