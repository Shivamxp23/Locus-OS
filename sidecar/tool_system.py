"""
Implementation of Tool System for Locus (SPEC §1.3, F-0003).
Provides 13 Canonical Tools, lifecycle management, and individual tool toggling.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from sidecar import config as cfg
from sidecar.providers.tool_system import (
    AgentTool,
    AgentToolResult,
    BaseToolSystemProvider,
    BeforeToolCallResult,
    ExecutionMode,
)

logger = logging.getLogger(__name__)


def _create_canonical_tools() -> Dict[str, AgentTool]:
    """Instantiate the 13 canonical Locus tools per SPEC §1.3."""
    return {
        "locus_checkin": AgentTool(
            name="locus_checkin",
            label="Locus Check-in",
            description="Submit daily check-in, mood assessment, and energy levels to update DCS.",
            schema={
                "type": "object",
                "properties": {
                    "energy": {"type": "number", "minimum": 1, "maximum": 10},
                    "mood": {"type": "string"},
                    "reflection": {"type": "string"},
                },
                "required": ["energy", "mood"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        ),
        "locus_life": AgentTool(
            name="locus_life",
            label="Locus Life OS",
            description="Inspect and adjust operating modes, faction distributions, and DCS metrics.",
            schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["get_metrics", "set_mode", "adjust_faction"]},
                    "mode": {"type": "string"},
                    "faction": {"type": "string"},
                    "delta": {"type": "number"},
                },
                "required": ["action"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        ),
        "locus_goals": AgentTool(
            name="locus_goals",
            label="Locus Goals",
            description="Query, distill, and track long-term and short-term goals in the goal stack.",
            schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "add", "complete", "distill"]},
                    "title": {"type": "string"},
                    "level": {"type": "string"},
                },
                "required": ["action"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        ),
        "locus_memory": AgentTool(
            name="locus_memory",
            label="Locus Memory",
            description="Search and recall episodic and semantic facts from Neo4j agent memory.",
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            execution_mode=ExecutionMode.PARALLEL,
        ),
        "locus_vault": AgentTool(
            name="locus_vault",
            label="Locus Vault",
            description="Read and write notes in the Obsidian vault with CouchDB synchronization.",
            schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["read", "write", "search"]},
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["action", "path"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        ),
        "locus_brain": AgentTool(
            name="locus_brain",
            label="Locus Brain",
            description="Query knowledge graphs and semantic associations across notes.",
            schema={
                "type": "object",
                "properties": {
                    "concept": {"type": "string"},
                    "depth": {"type": "integer", "default": 2},
                },
                "required": ["concept"],
            },
            execution_mode=ExecutionMode.PARALLEL,
        ),
        "locus_research": AgentTool(
            name="locus_research",
            label="Locus Research",
            description="Perform autonomous multi-source literature and topic research synthesis.",
            schema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "depth": {"type": "string", "enum": ["quick", "deep"]},
                },
                "required": ["topic"],
            },
            execution_mode=ExecutionMode.PARALLEL,
        ),
        "locus_delegate_code": AgentTool(
            name="locus_delegate_code",
            label="Locus Code Delegation",
            description="Delegate complex coding tasks to external harnesses (Claude Code, opencode, Pi).",
            schema={
                "type": "object",
                "properties": {
                    "harness": {"type": "string", "enum": ["claude_code", "opencode", "pi"]},
                    "prompt": {"type": "string"},
                    "timeout_seconds": {"type": "integer", "default": 300},
                },
                "required": ["harness", "prompt"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        ),
        "locus_doctor": AgentTool(
            name="locus_doctor",
            label="Locus Doctor",
            description="Run diagnostics and verify sidecar service health and integrity.",
            schema={
                "type": "object",
                "properties": {
                    "component": {"type": "string", "default": "all"},
                },
            },
            execution_mode=ExecutionMode.PARALLEL,
        ),
        "locus_pageindex": AgentTool(
            name="locus_pageindex",
            label="Locus PageIndex",
            description="Index and search long structured documents with hierarchical chapter trees.",
            schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["index", "query"]},
                    "path": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["action"],
            },
            execution_mode=ExecutionMode.PARALLEL,
        ),
        "locus_diagram": AgentTool(
            name="locus_diagram",
            label="Locus Diagram",
            description="Generate, validate, and render Mermaid diagrams for architectures and workflows.",
            schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "diagram_type": {"type": "string", "default": "flowchart"},
                },
                "required": ["code"],
            },
            execution_mode=ExecutionMode.PARALLEL,
        ),
        "locus_capture": AgentTool(
            name="locus_capture",
            label="Locus Capture",
            description="Quickly capture fleeting thoughts, tasks, or links into the system inbox.",
            schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["content"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        ),
        "locus_schedule": AgentTool(
            name="locus_schedule",
            label="Locus Schedule",
            description="Schedule background actions, recurring cron triggers, and reminders.",
            schema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "list", "remove"]},
                    "cron": {"type": "string"},
                    "task_name": {"type": "string"},
                },
                "required": ["action"],
            },
            execution_mode=ExecutionMode.SEQUENTIAL,
        ),
    }


class ToolSystemProvider(BaseToolSystemProvider):
    """Concrete Tool System Provider managing canonical and custom tools."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config
        self._tools: Dict[str, AgentTool] = _create_canonical_tools()
        self._before_hooks: List[Callable[[Dict[str, Any]], BeforeToolCallResult]] = []
        self._after_hooks: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

    def register_tool(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def is_tool_enabled(self, name: str) -> bool:
        # Check global off-switch first
        if self._config is not None:
            if not self._config.get("locus.tool_system_13_canonical_tools.enabled", True):
                return False
            key = f"locus.tools.{name}.enabled"
            return bool(self._config.get(key, True))
        val = cfg.get("locus.tool_system_13_canonical_tools.enabled")
        if val is not None and not cfg.is_enabled("locus.tool_system_13_canonical_tools.enabled"):
            return False
        key = f"locus.tools.{name}.enabled"
        val = cfg.get(key)
        if val is not None and not cfg.is_enabled(key):
            return False
        return True

    def list_tools(self) -> List[AgentTool]:
        return [t for t in self._tools.values() if self.is_tool_enabled(t.name)]

    def get_tool(self, name: str) -> Optional[AgentTool]:
        if not self.is_tool_enabled(name):
            return None
        return self._tools.get(name)

    def add_before_hook(self, hook: Callable[[Dict[str, Any]], BeforeToolCallResult]) -> None:
        self._before_hooks.append(hook)

    def add_after_hook(self, hook: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._after_hooks.append(hook)

    def validate_tool_arguments(self, tool: AgentTool, args: Dict[str, Any]) -> None:
        schema = tool.schema
        if not isinstance(args, dict):
            raise ValueError(f"Arguments for tool {tool.name} must be a dictionary")
        required = schema.get("required", [])
        for field in required:
            if field not in args:
                raise ValueError(f"Missing required parameter '{field}' for tool '{tool.name}'")

    def execute_tool(
        self,
        name: str,
        tool_call_id: str,
        raw_params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentToolResult:
        """
        Execute tool through the full 5-step lifecycle:
        1. prepareToolCallArguments(tool, toolCall)
        2. validateToolArguments(tool, preparedToolCall)
        3. config.beforeToolCall hook -> check {block: true}
        4. tool.execute(toolCallId, validatedArgs, signal)
        5. config.afterToolCall hook -> override result
        """
        tool = self.get_tool(name)
        if not tool:
            return AgentToolResult(
                content=[{"type": "text", "text": f"Tool '{name}' is not registered or is disabled."}],
                details={"tool": name, "tool_call_id": tool_call_id},
                is_error=True,
            )

        # 1. Prepare arguments hook
        prepared_args = raw_params
        if tool.prepare_arguments:
            try:
                prepared_args = tool.prepare_arguments(raw_params)
            except Exception as e:
                return AgentToolResult(
                    content=[{"type": "text", "text": f"Error preparing arguments: {str(e)}"}],
                    details={"tool": name, "error": str(e)},
                    is_error=True,
                )

        # 2. Validate arguments
        try:
            self.validate_tool_arguments(tool, prepared_args)
        except ValueError as e:
            return AgentToolResult(
                content=[{"type": "text", "text": f"Schema validation error: {str(e)}"}],
                details={"tool": name, "error": str(e)},
                is_error=True,
            )

        # 3. beforeToolCall hook
        hook_context = {
            "toolCallId": tool_call_id,
            "tool": name,
            "args": prepared_args,
            "context": context or {},
        }
        for before_hook in self._before_hooks:
            res = before_hook(hook_context)
            if res.block:
                return AgentToolResult(
                    content=[{"type": "text", "text": f"Tool execution blocked: {res.reason or 'Policy block'}"}],
                    details={"tool": name, "blocked": True, "reason": res.reason},
                    is_error=True,
                )

        # 4. tool.execute
        try:
            result = tool.execute(tool_call_id, prepared_args)
        except Exception as e:
            result = AgentToolResult(
                content=[{"type": "text", "text": f"Tool execution exception: {str(e)}"}],
                details={"tool": name, "error": str(e)},
                is_error=True,
            )

        # 5. afterToolCall hook
        after_context = {
            "toolCallId": tool_call_id,
            "tool": name,
            "args": prepared_args,
            "result": result,
            "context": context or {},
        }
        for after_hook in self._after_hooks:
            overrides = after_hook(after_context)
            if overrides:
                if "content" in overrides:
                    result.content = overrides["content"]
                if "details" in overrides:
                    result.details = overrides["details"]
                if "is_error" in overrides:
                    result.is_error = overrides["is_error"]
                if "terminate" in overrides:
                    result.terminate = overrides["terminate"]

        return result
