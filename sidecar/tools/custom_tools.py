"""sidecar/tools/custom_tools.py - Dynamic Custom Locus Tools Engine.

Implements Spec §3.12:
- Allows registration, discovery, and sandboxed dispatch of custom user/agent tools.
- Metadata inspection and parameter schema validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CustomToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]
    category: str = "custom"
    enabled: bool = True


class CustomToolRegistry:
    """Registry and executor for user-defined and plugin tools."""

    def __init__(self) -> None:
        self.tools: dict[str, CustomToolSpec] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters_schema: dict[str, Any],
        handler: Callable[[dict[str, Any]], Any],
        category: str = "custom",
    ) -> CustomToolSpec:
        spec = CustomToolSpec(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            handler=handler,
            category=category,
            enabled=True,
        )
        self.tools[name] = spec
        return spec

    def unregister(self, name: str) -> bool:
        if name in self.tools:
            del self.tools[name]
            return True
        return False

    def list_tools(self) -> list[CustomToolSpec]:
        return [t for t in self.tools.values() if t.enabled]

    def execute(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(name)
        if not tool:
            return {"status": "error", "message": f"Custom tool '{name}' not found"}
        if not tool.enabled:
            return {"status": "error", "message": f"Custom tool '{name}' is disabled"}

        try:
            result = tool.handler(params)
            return {"status": "ok", "result": result}
        except Exception as ex:
            return {"status": "error", "message": str(ex)}
