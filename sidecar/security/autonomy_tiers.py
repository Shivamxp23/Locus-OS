"""
SPEC §13.4 lines 3308-3332:
Autonomy Tiers (F-0108 / US-70).

Implements:
1. AUTONOMY TIERS:
   - READONLY: read tools only, no writes, no terminal
   - SUPERVISED: write and terminal tools require explicit user approval (10-min TTL)
   - FULL: all tools allowed (trusted mode)
2. Tool categorization (read, write, terminal, system) with heuristic analysis and overrides.
3. Decision evaluation engine gating execution for beforeToolCall hook.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class AutonomyTier(str, Enum):
    """
    SPEC §13.4: Autonomy Tier levels.
    """
    READONLY = "readonly"
    SUPERVISED = "supervised"
    FULL = "full"

    @classmethod
    def from_str(cls, val: Optional[str]) -> "AutonomyTier":
        if not val:
            return cls.SUPERVISED
        v = str(val).strip().lower()
        if v in ("readonly", "read_only", "ro"):
            return cls.READONLY
        if v in ("full", "unrestricted", "trusted"):
            return cls.FULL
        return cls.SUPERVISED


class ToolCategory(str, Enum):
    """
    SPEC §13.4: Tool operation categories.
    """
    READ = "read"
    WRITE = "write"
    TERMINAL = "terminal"
    SYSTEM = "system"

    @classmethod
    def from_str(cls, val: Optional[str]) -> "ToolCategory":
        if not val:
            return cls.WRITE
        v = str(val).strip().lower()
        if v in ("read", "ro", "inspect"):
            return cls.READ
        if v in ("terminal", "command", "shell", "bash"):
            return cls.TERMINAL
        if v in ("system", "config", "admin"):
            return cls.SYSTEM
        return cls.WRITE


# Standard known tool name classifications
KNOWN_TOOL_CLASSIFICATIONS: Dict[str, ToolCategory] = {
    # Read-only tools
    "read_file": ToolCategory.READ,
    "read_resource": ToolCategory.READ,
    "list_resources": ToolCategory.READ,
    "search_web": ToolCategory.READ,
    "view_structure": ToolCategory.READ,
    "get_state": ToolCategory.READ,
    "list_dir": ToolCategory.READ,
    "query_graph": ToolCategory.READ,
    "get_node": ToolCategory.READ,
    "shortest_path": ToolCategory.READ,
    "grep": ToolCategory.READ,
    "glob": ToolCategory.READ,
    "find_files": ToolCategory.READ,
    "fetch_url": ToolCategory.READ,
    "inspect": ToolCategory.READ,
    "diff": ToolCategory.READ,
    # Write tools
    "write_file": ToolCategory.WRITE,
    "edit_file": ToolCategory.WRITE,
    "append_file": ToolCategory.WRITE,
    "remove_file": ToolCategory.WRITE,
    "delete_file": ToolCategory.WRITE,
    "touch_file": ToolCategory.WRITE,
    "move_file": ToolCategory.WRITE,
    "copy_file": ToolCategory.WRITE,
    "patch_file": ToolCategory.WRITE,
    "create_file": ToolCategory.WRITE,
    # Terminal tools
    "run_command": ToolCategory.TERMINAL,
    "bash": ToolCategory.TERMINAL,
    "exec_command": ToolCategory.TERMINAL,
    "shell": ToolCategory.TERMINAL,
    "cmd": ToolCategory.TERMINAL,
    "terminal": ToolCategory.TERMINAL,
    "powershell": ToolCategory.TERMINAL,
    "exec": ToolCategory.TERMINAL,
    # System tools
    "set_config": ToolCategory.SYSTEM,
    "update_settings": ToolCategory.SYSTEM,
    "shutdown": ToolCategory.SYSTEM,
    "restart_service": ToolCategory.SYSTEM,
    "install_extension": ToolCategory.SYSTEM,
}


@dataclass
class TierEvaluationDecision:
    """
    SPEC §13.4: Evaluation decision for a tool call under the current autonomy tier.
    """
    allowed: bool
    requires_approval: bool
    tier: str
    tool_name: str
    category: str
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutonomyTierManager:
    """
    SPEC §13.4: Autonomy Tier manager and policy engine.
    Controls tier configuration and evaluates tool permissions against tiers.
    """

    def __init__(
        self,
        initial_tier: Optional[Union[str, AutonomyTier]] = None,
        overrides: Optional[Dict[str, Union[str, ToolCategory]]] = None,
    ):
        if isinstance(initial_tier, AutonomyTier):
            self._tier = initial_tier
        else:
            self._tier = AutonomyTier.from_str(initial_tier or "supervised")

        self._overrides: Dict[str, ToolCategory] = {}
        if overrides:
            for tool_name, cat in overrides.items():
                self.register_tool_override(tool_name, cat)

    @property
    def tier(self) -> AutonomyTier:
        return self._tier

    def set_tier(self, tier: Union[str, AutonomyTier]) -> AutonomyTier:
        """Update active tier."""
        if isinstance(tier, AutonomyTier):
            self._tier = tier
        else:
            self._tier = AutonomyTier.from_str(tier)
        return self._tier

    def register_tool_override(self, tool_name: str, category: Union[str, ToolCategory]) -> None:
        """Register custom category override for a specific tool."""
        cat_enum = category if isinstance(category, ToolCategory) else ToolCategory.from_str(category)
        self._overrides[tool_name.strip().lower()] = cat_enum

    def classify_tool(
        self,
        tool_name: str,
        explicit_category: Optional[Union[str, ToolCategory]] = None,
    ) -> ToolCategory:
        """
        SPEC §13.4: Classify a tool into read, write, terminal, or system.
        """
        if explicit_category:
            return (
                explicit_category
                if isinstance(explicit_category, ToolCategory)
                else ToolCategory.from_str(explicit_category)
            )

        normalized = (tool_name or "").strip().lower()

        # Check explicit overrides
        if normalized in self._overrides:
            return self._overrides[normalized]

        # Check standard known tools
        if normalized in KNOWN_TOOL_CLASSIFICATIONS:
            return KNOWN_TOOL_CLASSIFICATIONS[normalized]

        # Pattern-based heuristics
        if re.search(r"^(run|exec|bash|cmd|terminal|shell|powershell|spawn)", normalized):
            return ToolCategory.TERMINAL
        if re.search(r"^(set_|sys|install|restart|shutdown|admin)", normalized):
            return ToolCategory.SYSTEM
        if re.search(r"^(read|get|list|search|query|fetch|find|check|show|view|inspect|describe|audit)", normalized):
            return ToolCategory.READ
        if re.search(r"^(write|edit|append|delete|remove|patch|update|modify|create|put|post|truncate)", normalized):
            return ToolCategory.WRITE

        # Default fallback is WRITE for safety
        return ToolCategory.WRITE

    def evaluate(
        self,
        tool_name: str,
        has_approval: bool = False,
        custom_category: Optional[Union[str, ToolCategory]] = None,
        tier_override: Optional[Union[str, AutonomyTier]] = None,
    ) -> TierEvaluationDecision:
        """
        SPEC §13.4: Evaluate whether a tool is permitted under the active tier.
        
        AUTONOMY TIERS:
        - READONLY: read tools only, no writes, no terminal
        - SUPERVISED: write tools require explicit user approval (10-min TTL)
        - FULL: all tools allowed (trusted mode)
        """
        if tier_override:
            active_tier = (
                tier_override
                if isinstance(tier_override, AutonomyTier)
                else AutonomyTier.from_str(tier_override)
            )
        else:
            active_tier = self._tier

        category = self.classify_tool(tool_name=tool_name, explicit_category=custom_category)

        # FULL: all tools allowed without approval
        if active_tier == AutonomyTier.FULL:
            return TierEvaluationDecision(
                allowed=True,
                requires_approval=False,
                tier=active_tier.value,
                tool_name=tool_name,
                category=category.value,
                reason="Full autonomy tier allows all tools without approval",
            )

        # READONLY: read tools only, no writes, no terminal
        if active_tier == AutonomyTier.READONLY:
            if category == ToolCategory.READ:
                return TierEvaluationDecision(
                    allowed=True,
                    requires_approval=False,
                    tier=active_tier.value,
                    tool_name=tool_name,
                    category=category.value,
                    reason="Read tools are permitted in READONLY autonomy tier",
                )
            if category == ToolCategory.TERMINAL:
                return TierEvaluationDecision(
                    allowed=False,
                    requires_approval=False,
                    tier=active_tier.value,
                    tool_name=tool_name,
                    category=category.value,
                    reason="Terminal execution tools are strictly blocked in READONLY autonomy tier",
                )
            if category == ToolCategory.WRITE:
                return TierEvaluationDecision(
                    allowed=False,
                    requires_approval=False,
                    tier=active_tier.value,
                    tool_name=tool_name,
                    category=category.value,
                    reason="Write tools are strictly blocked in READONLY autonomy tier",
                )
            return TierEvaluationDecision(
                allowed=False,
                requires_approval=False,
                tier=active_tier.value,
                tool_name=tool_name,
                category=category.value,
                reason=f"{category.value.capitalize()} tools are forbidden in READONLY autonomy tier",
            )

        # SUPERVISED: write and terminal tools require explicit user approval (10-min TTL)
        if active_tier == AutonomyTier.SUPERVISED:
            if category == ToolCategory.READ:
                return TierEvaluationDecision(
                    allowed=True,
                    requires_approval=False,
                    tier=active_tier.value,
                    tool_name=tool_name,
                    category=category.value,
                    reason="Read tools execute without approval in SUPERVISED autonomy tier",
                )

            # Non-read tools require user approval
            if has_approval:
                return TierEvaluationDecision(
                    allowed=True,
                    requires_approval=False,
                    tier=active_tier.value,
                    tool_name=tool_name,
                    category=category.value,
                    reason="Explicit user approval verified for execution in SUPERVISED autonomy tier",
                )

            return TierEvaluationDecision(
                allowed=False,
                requires_approval=True,
                tier=active_tier.value,
                tool_name=tool_name,
                category=category.value,
                reason=f"{category.value.capitalize()} tools require explicit user approval (10-min TTL) in SUPERVISED autonomy tier",
            )

        # Fallback safe
        return TierEvaluationDecision(
            allowed=False,
            requires_approval=True,
            tier=active_tier.value,
            tool_name=tool_name,
            category=category.value,
            reason="Unknown tier policy; blocking for safety",
        )

    def get_tiers_info(self) -> List[Dict[str, Any]]:
        """Return information about supported tiers."""
        return [
            {
                "tier": AutonomyTier.READONLY.value,
                "description": "Read tools only, no writes, no terminal",
                "allowed_categories": [ToolCategory.READ.value],
                "requires_approval": [],
            },
            {
                "tier": AutonomyTier.SUPERVISED.value,
                "description": "Write tools require explicit user approval (10-min TTL)",
                "allowed_categories": [ToolCategory.READ.value],
                "requires_approval": [ToolCategory.WRITE.value, ToolCategory.TERMINAL.value, ToolCategory.SYSTEM.value],
            },
            {
                "tier": AutonomyTier.FULL.value,
                "description": "All tools allowed (trusted mode)",
                "allowed_categories": [
                    ToolCategory.READ.value,
                    ToolCategory.WRITE.value,
                    ToolCategory.TERMINAL.value,
                    ToolCategory.SYSTEM.value,
                ],
                "requires_approval": [],
            },
        ]
