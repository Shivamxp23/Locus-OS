"""
SPEC §25.12 lines 4801-4882: Goal Tracker (3-Layer Stack) & Faction Balancer Provider (F-0057 / US-90).
Modular off-switches returning HTTP 503:
- locus.goal_tracker_3_layer_stack.enabled
- locus.life_os.goal_tracker.enabled
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple

from sidecar import config
from sidecar.life_os.faction_balancer import (
    FactionBalanceReport,
    FactionBalancer,
    SCHEDULER_FACTION_TARGETS,
)
from sidecar.life_os.goal_stack import GoalNode, GoalStackLevel, ThreeLayerGoalStack

logger = logging.getLogger("locus.providers.goal_tracker")


class BaseGoalTrackerProvider(ABC):
    """Abstract contract for Goal Tracker (3-Layer Stack) and Faction Balancer provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check modular off-switches."""

    @abstractmethod
    def validate_task_hierarchy(self, task_id: str) -> Dict[str, Any]:
        """Validate 3-layer hierarchy (Outcome -> Project -> Task)."""

    @abstractmethod
    def detect_orphans(self) -> Dict[str, Any]:
        """Surface orphan tasks or projects lacking valid parents."""

    @abstractmethod
    def evaluate_faction_balance(
        self, allocations_minutes: Dict[str, float]
    ) -> Dict[str, Any]:
        """Evaluate weekly faction allocation compliance against targets & tolerance."""

    @abstractmethod
    def check_assignment_allowed(
        self,
        candidate_faction: str,
        proposed_minutes: float,
        current_allocations: Dict[str, float],
        waiting_factions: List[str],
    ) -> Dict[str, Any]:
        """Evaluate Step 4 constraint balancing check."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultGoalTrackerProvider(BaseGoalTrackerProvider):
    """
    Default provider wrapping ThreeLayerGoalStack and FactionBalancer
    with modular off-switch enforcement.
    """

    def __init__(
        self,
        goal_stack: Optional[ThreeLayerGoalStack] = None,
        balancer: Optional[FactionBalancer] = None,
    ) -> None:
        self.goal_stack = goal_stack or ThreeLayerGoalStack()
        self.balancer = balancer or FactionBalancer()

    @property
    def name(self) -> str:
        return "default_goal_tracker_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        for switch in (
            "locus.goal_tracker_3_layer_stack.enabled",
            "locus.life_os.goal_tracker.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def validate_task_hierarchy(self, task_id: str) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal tracker is disabled",
                "disabled": switch,
            }
        ok, msg = self.goal_stack.validate_task(task_id)
        return {
            "status": "ok",
            "task_id": task_id,
            "valid": ok,
            "message": msg,
        }

    def detect_orphans(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal tracker is disabled",
                "disabled": switch,
            }
        orphans = self.goal_stack.detect_orphan_tasks()
        return {
            "status": "ok",
            "count": len(orphans),
            "orphans": orphans,
        }

    def evaluate_faction_balance(
        self, allocations_minutes: Dict[str, float]
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal tracker is disabled",
                "disabled": switch,
            }
        report = self.balancer.evaluate_allocations(allocations_minutes)
        return {
            "status": "ok",
            "balance_report": report.to_dict(),
        }

    def check_assignment_allowed(
        self,
        candidate_faction: str,
        proposed_minutes: float,
        current_allocations: Dict[str, float],
        waiting_factions: List[str],
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal tracker is disabled",
                "disabled": switch,
            }
        allowed, msg = self.balancer.is_assignment_allowed(
            candidate_faction=candidate_faction,
            proposed_minutes=proposed_minutes,
            current_allocations=current_allocations,
            waiting_factions=set(waiting_factions),
        )
        return {
            "status": "ok",
            "allowed": allowed,
            "message": msg,
            "candidate_faction": candidate_faction,
            "proposed_minutes": proposed_minutes,
        }

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Goal tracker is disabled",
                "disabled": switch,
            }
        return {
            "status": "ok",
            "provider": self.name,
            "enabled": True,
            "total_nodes": len(self.goal_stack._nodes),
            "targets": dict(SCHEDULER_FACTION_TARGETS),
            "tolerance": self.balancer.tolerance,
        }


# Canonical alias
GoalTrackerProvider = DefaultGoalTrackerProvider
