"""
SPEC §25.5-25.8 & §25.12: Scheduler and Operating Modes Provider.
Implements swappable SchedulerProvider with modular off-switches returning HTTP 503:
- locus.operating_modes_scheduler.enabled
- locus.life_os.goal_stack.enabled
- locus.life_os.action_gap.enabled
- locus.life_os.deferral.enabled
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.action_gap import (
    calculate_action_gap,
    evaluate_faction_action_gaps,
)
from sidecar.life_os.deferral import DeferralTracker
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)
from sidecar.life_os.lag import (
    calculate_lag_score,
    calculate_tws_lag_bonus,
    compute_faction_lag_report,
)
from sidecar.life_os.scheduler import CandidateTask, SixStepSchedulerEngine

logger = logging.getLogger("locus.providers.scheduler")


class BaseSchedulerProvider(ABC):
    """Abstract contract for Operating Modes & Scheduler provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self, feature: str = "scheduler") -> Tuple[bool, str]:
        """Check modular off-switches."""

    @abstractmethod
    def validate_goal_stack(self) -> Dict[str, Any]:
        """Validate three-layer goal stack."""

    @abstractmethod
    def evaluate_action_gaps(self, factions_data: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Evaluate action gaps across factions."""

    @abstractmethod
    def record_deferral(self, task_id: str, reason: str = "") -> Dict[str, Any]:
        """Record deferral for a task."""

    @abstractmethod
    def compute_lag_bonus(self, lag_hours: float) -> Dict[str, Any]:
        """Compute TWS bonus based on lag hours."""

    @abstractmethod
    def generate_schedule(
        self,
        dcs: float,
        candidate_tasks: List[Dict[str, Any]],
        enforce_goal_stack: bool = True,
    ) -> Dict[str, Any]:
        """Execute deterministic 6-step scheduler."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic subsystem status."""


class DefaultSchedulerProvider(BaseSchedulerProvider):
    """
    Concrete default scheduler provider implementing Operating Modes and Goal Stack scheduling.
    """

    def __init__(
        self,
        goal_stack: Optional[ThreeLayerGoalStack] = None,
        deferral_tracker: Optional[DeferralTracker] = None,
        scheduler_engine: Optional[SixStepSchedulerEngine] = None,
    ) -> None:
        self.goal_stack = goal_stack or ThreeLayerGoalStack()
        self.deferral_tracker = deferral_tracker or DeferralTracker()
        self.scheduler_engine = scheduler_engine or SixStepSchedulerEngine(goal_stack=self.goal_stack)

    @property
    def name(self) -> str:
        return "default_scheduler_provider"

    def is_feature_enabled(self, feature: str = "scheduler") -> Tuple[bool, str]:
        # Master scheduler switch
        for switch in (
            "locus.operating_modes_scheduler.enabled",
            "locus.scheduler.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch

        # Specific sub-feature switch checks
        sub_switches = {
            "goal_stack": "locus.life_os.goal_stack.enabled",
            "action_gap": "locus.life_os.action_gap.enabled",
            "deferral": "locus.life_os.deferral.enabled",
        }
        if feature in sub_switches:
            sub = sub_switches[feature]
            val = config.get(sub)
            if val is not None and not config.is_enabled(sub):
                return False, sub

        return True, ""

    def validate_goal_stack(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled("goal_stack")
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        res = self.goal_stack.validate_hierarchy()
        return {"status": "ok", **res}

    def evaluate_action_gaps(self, factions_data: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled("action_gap")
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        reports = evaluate_faction_action_gaps(factions_data)
        return {
            "status": "ok",
            "reports": [r.to_dict() for r in reports],
            "alerts_count": sum(1 for r in reports if r.alert),
        }

    def record_deferral(self, task_id: str, reason: str = "") -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled("deferral")
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        rec = self.deferral_tracker.record_deferral(task_id, reason=reason)
        return {"status": "ok", "record": rec.to_dict()}

    def compute_lag_bonus(self, lag_hours: float) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled("scheduler")
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        bonus = calculate_tws_lag_bonus(lag_hours)
        return {
            "status": "ok",
            "lag_hours": lag_hours,
            "tws_lag_bonus": bonus,
            "is_crisis": lag_hours > 6.0,
            "is_ahead": lag_hours < 0.0,
        }

    def generate_schedule(
        self,
        dcs: float,
        candidate_tasks: List[Dict[str, Any]],
        enforce_goal_stack: bool = True,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled("scheduler")
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}

        candidates = [
            CandidateTask(
                id=str(c.get("id", f"t-{i}")),
                title=str(c.get("title", f"Task {i}")),
                difficulty=int(c.get("difficulty", 5)),
                leverage=int(c.get("leverage", 5)),
                urgency=int(c.get("urgency", 5)),
                consequence=int(c.get("consequence", 5)),
                faction=str(c.get("faction", "Craft")),
                deferral_count=int(c.get("deferral_count", 0)),
                project_id=c.get("project_id"),
                estimated_minutes=int(c.get("estimated_minutes", 60)),
            )
            for i, c in enumerate(candidate_tasks)
        ]
        return self.scheduler_engine.generate_schedule(
            dcs=dcs,
            candidate_tasks=candidates,
            enforce_goal_stack=enforce_goal_stack,
        )

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled("scheduler")
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return {
            "status": "ok",
            "provider": self.name,
            "goal_stack_nodes_count": len(self.goal_stack._nodes),
            "parked_tasks_count": len(self.deferral_tracker.list_parked_tasks()),
        }


# Alias for backward compatibility / features.yaml symbol expectations
SchedulerProvider = DefaultSchedulerProvider
