"""
SPEC §25.14 lines 4897-4909: Goal Stack Enforcement Provider (F-0115 / US-92).
Modular off-switches:
- locus.goal_stack_enforcement.enabled (returns HTTP 503 when off)
- locus.life_os.goal_enforcement.enabled (when off, orphan tasks/projects are allowed)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.goal_enforcement import (
    BriefingOrphanReport,
    EnforcementResult,
    GoalStackEnforcer,
)
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)

logger = logging.getLogger("locus.providers.goal_enforcement")


class BaseGoalStackEnforcementProvider(ABC):
    """
    Abstract contract for Goal Stack Enforcement Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def enforce_task(
        self,
        task_id: str,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Enforce task parenting to project and outcome."""

    @abstractmethod
    def enforce_project(
        self,
        project_id: str,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Enforce project parenting to outcome."""

    @abstractmethod
    def surface_briefing_orphans(
        self,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Surface orphan tasks and projects formatted for morning briefing."""

    @abstractmethod
    def audit_stack(
        self,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Audit full stack for orphan tasks and projects."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultGoalStackEnforcementProvider(BaseGoalStackEnforcementProvider):
    """
    Default provider wrapping GoalStackEnforcer with modular off-switch enforcement.
    """

    def __init__(
        self,
        enforcer: Optional[GoalStackEnforcer] = None,
        stack: Optional[ThreeLayerGoalStack] = None,
    ) -> None:
        self.enforcer = enforcer or GoalStackEnforcer()
        self.stack = stack or ThreeLayerGoalStack()

    @property
    def name(self) -> str:
        return "default_goal_stack_enforcement_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        switch = "locus.goal_stack_enforcement.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def _build_or_get_stack(
        self,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> ThreeLayerGoalStack:
        """
        Build a ThreeLayerGoalStack from provided node dicts or return current stack.
        """
        if not stack_nodes:
            return self.stack

        stk = ThreeLayerGoalStack()
        for item in stack_nodes:
            lvl_str = item.get("level", "daily").lower()
            try:
                level = GoalStackLevel(lvl_str)
            except ValueError:
                level = GoalStackLevel.DAILY

            node = GoalNode(
                id=item["id"],
                title=item.get("title", item["id"]),
                level=level,
                parent_id=item.get("parent_id"),
                faction=item.get("faction"),
                status=item.get("status", "active"),
                metadata=item.get("metadata", {}),
            )
            stk.add_node(node)
        return stk

    def enforce_task(
        self,
        task_id: str,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal stack enforcement is disabled",
                "disabled": switch,
            }

        stk = self._build_or_get_stack(stack_nodes)
        result = self.enforcer.enforce_task(task_id, stk)
        return result.to_dict()

    def enforce_project(
        self,
        project_id: str,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal stack enforcement is disabled",
                "disabled": switch,
            }

        stk = self._build_or_get_stack(stack_nodes)
        result = self.enforcer.enforce_project(project_id, stk)
        return result.to_dict()

    def surface_briefing_orphans(
        self,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal stack enforcement is disabled",
                "disabled": switch,
            }

        stk = self._build_or_get_stack(stack_nodes)
        report = self.enforcer.surface_orphans_for_briefing(stk)
        return report.to_dict()

    def audit_stack(
        self,
        stack_nodes: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal stack enforcement is disabled",
                "disabled": switch,
            }

        stk = self._build_or_get_stack(stack_nodes)
        result = self.enforcer.audit_stack(stk)
        return result.to_dict()

    def get_status(self) -> Dict[str, Any]:
        master_enabled, master_switch = self.is_feature_enabled()
        subsystem_enabled = self.enforcer.is_enforcement_enabled()
        return {
            "provider": self.name,
            "master_enabled": master_enabled,
            "master_switch": master_switch,
            "subsystem_enabled": subsystem_enabled,
            "subsystem_switch": self.enforcer.SWITCH_KEY,
            "total_registered_nodes": len(self.stack._nodes),
        }
