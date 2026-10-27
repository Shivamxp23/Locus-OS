"""
SPEC §25.9 lines 4740-4758: Emergency Task Injection Provider (F-0111 / US-87).
Modular off-switches returning HTTP 503:
- locus.emergency_task_injection.enabled
- locus.life_os.emergency.enabled
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.emergency import EmergencyTask, EmergencyTaskInjector

logger = logging.getLogger("locus.providers.emergency")


class BaseEmergencyTaskProvider(ABC):
    """Abstract contract for emergency task injection."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Evaluate modular off-switches."""

    @abstractmethod
    def prioritize_tasks(
        self,
        tasks: List[Dict[str, Any]],
        bypass_tws: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Order tasks respecting emergency status and faction crisis hierarchy."""

    @abstractmethod
    def inject_task(
        self,
        timeline: List[Dict[str, Any]],
        task: Dict[str, Any],
        at_index: int = 0,
    ) -> Dict[str, Any]:
        """Inject emergency task into active schedule timeline."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Subsystem health and diagnostic state."""


class DefaultEmergencyTaskProvider(BaseEmergencyTaskProvider):
    """
    Default provider wrapping EmergencyTaskInjector with modular off-switch enforcement.
    """

    def __init__(self, injector: Optional[EmergencyTaskInjector] = None) -> None:
        self.injector = injector or EmergencyTaskInjector()

    @property
    def name(self) -> str:
        return "default_emergency_task_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        for switch in (
            "locus.emergency_task_injection.enabled",
            "locus.life_os.emergency.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def prioritize_tasks(
        self,
        tasks: List[Dict[str, Any]],
        bypass_tws: Optional[bool] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}

        # If bypass_tws is not explicitly provided, check locus.life_os.emergency.enabled
        should_bypass = bypass_tws if bypass_tws is not None else config.get("locus.life_os.emergency.enabled", True) is not False

        candidate_tasks = [
            EmergencyTask(
                id=str(t.get("id", f"t-{i}")),
                title=str(t.get("title", f"Task {i}")),
                faction=str(t.get("faction", "Craft")),
                difficulty=int(t.get("difficulty", 5)),
                tws=float(t.get("tws", 0.0)),
                is_emergency=bool(t.get("is_emergency", False) or t.get("tag") == "EMERGENCY"),
                estimated_minutes=int(t.get("estimated_minutes", 60)),
                metadata=t.get("metadata", {}),
            )
            for i, t in enumerate(tasks)
        ]

        sorted_tasks = self.injector.prioritize_tasks(candidate_tasks, bypass_tws=should_bypass)
        return {
            "status": "ok",
            "bypass_tws": should_bypass,
            "total_tasks": len(sorted_tasks),
            "emergency_tasks_count": sum(1 for t in sorted_tasks if t.is_emergency),
            "tasks": [t.to_dict() for t in sorted_tasks],
        }

    def inject_task(
        self,
        timeline: List[Dict[str, Any]],
        task: Dict[str, Any],
        at_index: int = 0,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}

        em_task = EmergencyTask(
            id=str(task.get("id", "emergency-task")),
            title=str(task.get("title", "Emergency Task")),
            faction=str(task.get("faction", "Health")),
            difficulty=int(task.get("difficulty", 5)),
            tws=float(task.get("tws", 0.0)),
            is_emergency=True,
            estimated_minutes=int(task.get("estimated_minutes", 60)),
            metadata=task.get("metadata", {}),
        )

        updated_timeline = self.injector.inject_into_schedule(timeline, em_task, at_index=at_index)
        return {
            "status": "ok",
            "injected_task_id": em_task.id,
            "timeline_length": len(updated_timeline),
            "timeline": updated_timeline,
        }

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return {
            "status": "ok",
            "provider": self.name,
            "crisis_hierarchy": [
                "Health/Stability",
                "Leverage/Money",
                "Craft/Skills",
                "Expression/Explore",
            ],
        }


# Alias for backwards compatibility
EmergencyTaskProvider = DefaultEmergencyTaskProvider
