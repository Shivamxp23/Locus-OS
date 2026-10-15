"""Autonomy Tiers Engine (§13.4).

Implements OpenHuman-style 3-tier autonomy model for agent tool execution:
- READONLY: Read-only inspection tools allowed; mutating file writes and shell execution denied.
- SUPERVISED: Default mode; read tools execute freely; mutating tools require approval gates.
- FULL: Unrestricted autonomous execution for trusted workflows.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class AutonomyTier(str, Enum):
    READONLY = "readonly"
    SUPERVISED = "supervised"
    FULL = "full"


READ_ONLY_TOOLS: Set[str] = {
    "read",
    "grep",
    "find",
    "ls",
    "locus_memory",
    "locus_doctor",
    "locus_pageindex",
    "locus_diagram",
    "locus_research",
}

MUTATING_TOOLS: Set[str] = {
    "write",
    "edit",
    "bash",
    "terminal",
    "locus_vault",
    "locus_delegate_code",
}


class AutonomyManager:
    """Enforces tool execution permissions across configured autonomy tiers."""

    def __init__(self, current_tier: AutonomyTier = AutonomyTier.SUPERVISED) -> None:
        self.current_tier = current_tier

    def set_tier(self, tier: AutonomyTier) -> None:
        self.current_tier = tier

    def can_execute_tool(self, tool_name: str) -> Tuple[bool, bool, str]:
        """Returns (is_allowed, requires_approval, reason)."""
        clean_name = tool_name.lower().strip()

        if self.current_tier == AutonomyTier.FULL:
            return True, False, "Full autonomy active: all tools permitted"

        if clean_name in READ_ONLY_TOOLS:
            return True, False, "Read-only tool permitted"

        if self.current_tier == AutonomyTier.READONLY:
            return False, False, f"Denied: Tool '{clean_name}' is mutating, but AutonomyTier is READONLY"

        if self.current_tier == AutonomyTier.SUPERVISED:
            if clean_name in MUTATING_TOOLS:
                return True, True, f"Tool '{clean_name}' requires approval in SUPERVISED tier"
            # Default fallback for unknown tools in supervised mode
            return True, True, f"Tool '{clean_name}' requires approval in SUPERVISED tier"

        return False, False, "Unknown autonomy tier state"
