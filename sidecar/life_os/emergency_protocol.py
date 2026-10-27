"""
SPEC §25.16 lines 4923-4936: Four-Level Emergency Protocol (F-0117 / US-94).
Logic:
    Level 1 (minor) -> Level 4 (crisis).
    Each level unlocks different tool permissions and overrides scheduling.
    Crisis hierarchy: Health > Leverage > Craft > Expression.
    Level 1: Minor disruption (lost 1-2h) -> redistribute lowest-priority task to tomorrow.
    Level 2: Moderate disruption (lost full day) -> mark low-DCS, redistribute deferred, check faction lag.
    Level 3: Major disruption (lost 3+ days) -> enter SURVIVAL mode. Golden Emergency Rule:
             redistribute over 2 weeks minimum (14 days), fresh weekly review on recovery.
    Level 4: Life event / crisis -> suspend Faction 4 (Expression) completely. Lock Faction 1
             (Health) non-negotiables harder. Acknowledge Factions 2 & 3 lag. Plan recovery window.
Off state:
    locus.life_os.emergency_protocol.enabled: Off -> no emergency overrides; standard scheduling applies.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.life_os.emergency_protocol")

CRISIS_FACTION_ORDER = [
    "Health/Stability",
    "Leverage/Money",
    "Craft/Skills",
    "Expression/Explore",
]

FACTION_ALIASES: Dict[str, str] = {
    "health": "Health/Stability",
    "health/stability": "Health/Stability",
    "stability": "Health/Stability",
    "leverage": "Leverage/Money",
    "leverage/money": "Leverage/Money",
    "money": "Leverage/Money",
    "craft": "Craft/Skills",
    "craft/skills": "Craft/Skills",
    "skills": "Craft/Skills",
    "expression": "Expression/Explore",
    "expression/explore": "Expression/Explore",
    "explore": "Expression/Explore",
}


class EmergencyLevel(IntEnum):
    LEVEL_0_NORMAL = 0
    LEVEL_1_MINOR = 1
    LEVEL_2_MODERATE = 2
    LEVEL_3_MAJOR = 3
    LEVEL_4_CRISIS = 4


@dataclass
class EmergencyAssessment:
    level: int
    level_name: str
    description: str
    mode_override: str
    recommended_action: str
    redistribution_window_days: int
    affected_factions: Dict[str, str]
    tool_permissions: Dict[str, bool]
    overrides_applied: bool = True
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "level_name": self.level_name,
            "description": self.description,
            "mode_override": self.mode_override,
            "recommended_action": self.recommended_action,
            "redistribution_window_days": self.redistribution_window_days,
            "affected_factions": self.affected_factions,
            "tool_permissions": self.tool_permissions,
            "overrides_applied": self.overrides_applied,
            "enabled": self.enabled,
        }


@dataclass
class ProtocolActivationResult:
    success: bool
    level: int
    level_name: str
    mode_override: str
    message: str
    redistribution_window_days: int
    tool_permissions: Dict[str, bool]
    affected_factions: Dict[str, str]
    overrides_applied: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "level": self.level,
            "level_name": self.level_name,
            "mode_override": self.mode_override,
            "message": self.message,
            "redistribution_window_days": self.redistribution_window_days,
            "tool_permissions": self.tool_permissions,
            "affected_factions": self.affected_factions,
            "overrides_applied": self.overrides_applied,
        }


@dataclass
class ProtocolDeactivationResult:
    success: bool
    previous_level: int
    message: str
    require_weekly_review: bool
    redistribution_window_days: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "previous_level": self.previous_level,
            "message": self.message,
            "require_weekly_review": self.require_weekly_review,
            "redistribution_window_days": self.redistribution_window_days,
        }


@dataclass
class EmergencyProtocolStatus:
    current_level: int
    current_level_name: str
    is_emergency_active: bool
    mode_override: str
    enabled: bool
    redistribution_window_days: int
    tool_permissions: Dict[str, bool]
    crisis_hierarchy: List[str]
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_level": self.current_level,
            "current_level_name": self.current_level_name,
            "is_emergency_active": self.is_emergency_active,
            "mode_override": self.mode_override,
            "enabled": self.enabled,
            "redistribution_window_days": self.redistribution_window_days,
            "tool_permissions": self.tool_permissions,
            "crisis_hierarchy": self.crisis_hierarchy,
            "history": self.history,
        }


class FourLevelEmergencyProtocol:
    """
    SPEC §25.16: Four-Level Emergency Protocol engine managing escalation levels,
    tool permissions, mode overrides, and crisis faction hierarchy.
    """

    SWITCH_KEY = "locus.life_os.emergency_protocol.enabled"

    def __init__(self) -> None:
        self._current_level: EmergencyLevel = EmergencyLevel.LEVEL_0_NORMAL
        self._is_active: bool = False
        self._history: List[Dict[str, Any]] = []

    def is_protocol_enabled(self) -> bool:
        """Check subsystem off-switch."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def normalize_faction(self, faction: str) -> str:
        key = (faction or "").strip().lower()
        return FACTION_ALIASES.get(key, "Craft/Skills")

    def get_crisis_rank(self, faction: str) -> int:
        canonical = self.normalize_faction(faction)
        try:
            return CRISIS_FACTION_ORDER.index(canonical)
        except ValueError:
            return 99

    def get_tool_permissions(self, level: int | EmergencyLevel) -> Dict[str, bool]:
        """
        Tool permissions unlocked per emergency level.
        Higher levels restrict discretionary tools and unlock emergency/recovery overrides.
        """
        lvl = int(level)
        if lvl <= 0:
            return {
                "task_create_discretionary": True,
                "task_create_emergency": True,
                "scheduling_override": False,
                "discretionary_scheduling": True,
                "expression_work_allowed": True,
                "recovery_window_planning": False,
                "survival_tools_only": False,
            }
        elif lvl == 1:
            return {
                "task_create_discretionary": True,
                "task_create_emergency": True,
                "scheduling_override": True,
                "discretionary_scheduling": True,
                "expression_work_allowed": True,
                "recovery_window_planning": False,
                "survival_tools_only": False,
            }
        elif lvl == 2:
            return {
                "task_create_discretionary": False,
                "task_create_emergency": True,
                "scheduling_override": True,
                "discretionary_scheduling": False,
                "expression_work_allowed": True,
                "recovery_window_planning": False,
                "survival_tools_only": False,
            }
        elif lvl == 3:
            return {
                "task_create_discretionary": False,
                "task_create_emergency": True,
                "scheduling_override": True,
                "discretionary_scheduling": False,
                "expression_work_allowed": False,
                "recovery_window_planning": True,
                "survival_tools_only": True,
            }
        else:  # Level 4
            return {
                "task_create_discretionary": False,
                "task_create_emergency": True,
                "scheduling_override": True,
                "discretionary_scheduling": False,
                "expression_work_allowed": False,
                "recovery_window_planning": True,
                "survival_tools_only": False,
            }

    def evaluate(
        self,
        disruption_hours: float = 0.0,
        disruption_days: int = 0,
        is_life_event: bool = False,
        trigger_reason: str = "",
    ) -> EmergencyAssessment:
        """
        Evaluate disruption parameters and return assessment.
        If subsystem off-switch is disabled, no emergency overrides apply.
        """
        enabled = self.is_protocol_enabled()
        if not enabled:
            return EmergencyAssessment(
                level=EmergencyLevel.LEVEL_0_NORMAL,
                level_name="NORMAL",
                description="Emergency protocol disabled via config; standard scheduling always applies",
                mode_override="NORMAL",
                recommended_action="None (standard scheduling)",
                redistribution_window_days=1,
                affected_factions={},
                tool_permissions=self.get_tool_permissions(0),
                overrides_applied=False,
                enabled=False,
            )

        if is_life_event or disruption_days >= 7:
            lvl = EmergencyLevel.LEVEL_4_CRISIS
            name = "LEVEL_4_CRISIS"
            desc = "Life event (exam season, crunch, emotional crisis). Suspend Faction 4, lock Health."
            mode = "CRISIS"
            action = "Suspend Faction 4 discretionary work. Lock Faction 1 non-negotiables. Plan recovery window."
            window = 14
            factions = {
                "Health/Stability": "LOCKED_NON_NEGOTIABLE",
                "Leverage/Money": "ACKNOWLEDGED_LAG",
                "Craft/Skills": "ACKNOWLEDGED_LAG",
                "Expression/Explore": "SUSPENDED",
            }
        elif disruption_days >= 3 or disruption_hours >= 72.0:
            lvl = EmergencyLevel.LEVEL_3_MAJOR
            name = "LEVEL_3_MAJOR"
            desc = "Major disruption (lost 3+ days: illness, family, crisis). Enter SURVIVAL mode."
            mode = "SURVIVAL"
            action = "Enter SURVIVAL mode. Redistribute over 2 weeks minimum (14 days). Fresh weekly review on recovery."
            window = 14
            factions = {
                "Health/Stability": "PRESERVED",
                "Leverage/Money": "DEFERRED",
                "Craft/Skills": "DEFERRED",
                "Expression/Explore": "DEFERRED",
            }
        elif disruption_days >= 1 or disruption_hours >= 8.0:
            lvl = EmergencyLevel.LEVEL_2_MODERATE
            name = "LEVEL_2_MODERATE"
            desc = "Moderate disruption (lost full day). Mark low-DCS, redistribute all deferred tasks."
            mode = "LOW_DCS"
            action = "Mark today low-DCS. Redistribute all deferred tasks. Check faction lag."
            window = 2
            factions = {
                "Health/Stability": "ACTIVE",
                "Leverage/Money": "CHECK_LAG",
                "Craft/Skills": "CHECK_LAG",
                "Expression/Explore": "CHECK_LAG",
            }
        elif disruption_hours >= 1.0:
            lvl = EmergencyLevel.LEVEL_1_MINOR
            name = "LEVEL_1_MINOR"
            desc = "Minor disruption (lost 1-2 hours). Redistribute lowest-priority task to tomorrow."
            mode = "NORMAL"
            action = "Redistribute lowest-priority task to tomorrow. No schedule recalculation needed."
            window = 1
            factions = {
                "Health/Stability": "ACTIVE",
                "Leverage/Money": "ACTIVE",
                "Craft/Skills": "ACTIVE",
                "Expression/Explore": "ACTIVE",
            }
        else:
            lvl = EmergencyLevel.LEVEL_0_NORMAL
            name = "LEVEL_0_NORMAL"
            desc = "No emergency disruption detected. Standard operations."
            mode = "NORMAL"
            action = "Standard scheduling."
            window = 1
            factions = {
                "Health/Stability": "ACTIVE",
                "Leverage/Money": "ACTIVE",
                "Craft/Skills": "ACTIVE",
                "Expression/Explore": "ACTIVE",
            }

        return EmergencyAssessment(
            level=lvl,
            level_name=name,
            description=desc,
            mode_override=mode,
            recommended_action=action,
            redistribution_window_days=window,
            affected_factions=factions,
            tool_permissions=self.get_tool_permissions(lvl),
            overrides_applied=True,
            enabled=True,
        )

    def activate(
        self,
        level: int | EmergencyLevel,
        reason: str = "",
    ) -> ProtocolActivationResult:
        """
        Activate specific emergency protocol level.
        """
        enabled = self.is_protocol_enabled()
        lvl = int(level)

        if not enabled:
            return ProtocolActivationResult(
                success=True,
                level=0,
                level_name="NORMAL",
                mode_override="NORMAL",
                message="Emergency protocol disabled via config; standard scheduling always applies",
                redistribution_window_days=1,
                tool_permissions=self.get_tool_permissions(0),
                affected_factions={},
                overrides_applied=False,
            )

        if lvl < 0 or lvl > 4:
            raise ValueError(f"Invalid emergency level {lvl}; must be 0-4")

        self._current_level = EmergencyLevel(lvl)
        self._is_active = (lvl > 0)

        # Build assessment
        is_life_event = (lvl == 4)
        days = 3 if lvl == 3 else (1 if lvl == 2 else 0)
        hours = 2.0 if lvl == 1 else 0.0
        assessment = self.evaluate(
            disruption_hours=hours,
            disruption_days=days,
            is_life_event=is_life_event,
            trigger_reason=reason,
        )

        entry = {
            "action": "activate",
            "level": lvl,
            "level_name": assessment.level_name,
            "reason": reason,
            "mode_override": assessment.mode_override,
            "window_days": assessment.redistribution_window_days,
        }
        self._history.append(entry)

        return ProtocolActivationResult(
            success=True,
            level=lvl,
            level_name=assessment.level_name,
            mode_override=assessment.mode_override,
            message=f"Emergency Level {lvl} ({assessment.level_name}) activated: {reason or 'no reason given'}",
            redistribution_window_days=assessment.redistribution_window_days,
            tool_permissions=assessment.tool_permissions,
            affected_factions=assessment.affected_factions,
            overrides_applied=True,
        )

    def deactivate(self) -> ProtocolDeactivationResult:
        """
        Deactivate emergency protocol and restore standard operation.
        Applies Golden Emergency Rule (weekly review and 14-day redistribution) if leaving Level 3/4.
        """
        prev_level = int(self._current_level)
        self._current_level = EmergencyLevel.LEVEL_0_NORMAL
        self._is_active = False

        require_review = (prev_level >= 3)
        window = 14 if require_review else 1

        entry = {
            "action": "deactivate",
            "previous_level": prev_level,
            "require_weekly_review": require_review,
            "redistribution_window_days": window,
        }
        self._history.append(entry)

        return ProtocolDeactivationResult(
            success=True,
            previous_level=prev_level,
            message=f"Emergency protocol deactivated (was Level {prev_level}). Restoring standard scheduling.",
            require_weekly_review=require_review,
            redistribution_window_days=window,
        )

    def apply_scheduling_overrides(
        self,
        tasks: List[Dict[str, Any]],
        level: Optional[int | EmergencyLevel] = None,
    ) -> Dict[str, Any]:
        """
        Apply scheduling overrides according to the emergency level.
        Crisis hierarchy: Health > Leverage > Craft > Expression.
        Level 1: moves lowest TWS task to tomorrow.
        Level 2: defers uncompleted tasks.
        Level 3: survival mode, non-negotiables only.
        Level 4: suspends all Expression tasks completely, orders remaining by crisis hierarchy.
        """
        enabled = self.is_protocol_enabled()
        active_lvl = int(level if level is not None else self._current_level)

        if not enabled or active_lvl == 0:
            return {
                "tasks_retained": tasks,
                "tasks_deferred": [],
                "tasks_suspended": [],
                "mode": "NORMAL",
                "overrides_applied": False,
                "level": 0,
            }

        retained: List[Dict[str, Any]] = []
        deferred: List[Dict[str, Any]] = []
        suspended: List[Dict[str, Any]] = []

        if active_lvl == 1:
            # Shift lowest-priority task to tomorrow
            if not tasks:
                return {
                    "tasks_retained": [],
                    "tasks_deferred": [],
                    "tasks_suspended": [],
                    "mode": "NORMAL",
                    "overrides_applied": True,
                    "level": 1,
                }
            sorted_tasks = sorted(tasks, key=lambda t: float(t.get("tws", 0.0)))
            deferred = [sorted_tasks[0]]
            retained = sorted_tasks[1:]
            return {
                "tasks_retained": retained,
                "tasks_deferred": deferred,
                "tasks_suspended": [],
                "mode": "NORMAL",
                "overrides_applied": True,
                "level": 1,
            }

        elif active_lvl == 2:
            # Low DCS: keep non-negotiables / high priority, defer rest
            for t in tasks:
                if t.get("is_non_negotiable") or t.get("is_emergency") or float(t.get("tws", 0.0)) >= 8.0:
                    retained.append(t)
                else:
                    deferred.append(t)
            return {
                "tasks_retained": retained,
                "tasks_deferred": deferred,
                "tasks_suspended": [],
                "mode": "LOW_DCS",
                "overrides_applied": True,
                "level": 2,
            }

        elif active_lvl == 3:
            # Survival mode: non-negotiables only, all discretionary deferred
            for t in tasks:
                canonical_faction = self.normalize_faction(t.get("faction", ""))
                if t.get("is_non_negotiable") or t.get("is_emergency") or canonical_faction == "Health/Stability":
                    retained.append(t)
                else:
                    deferred.append(t)
            return {
                "tasks_retained": retained,
                "tasks_deferred": deferred,
                "tasks_suspended": [],
                "mode": "SURVIVAL",
                "overrides_applied": True,
                "level": 3,
                "redistribution_window_days": 14,
            }

        else:  # Level 4: Crisis
            # Suspend Faction 4 (Expression) entirely.
            # Order remaining by crisis hierarchy: Health > Leverage > Craft > Expression.
            for t in tasks:
                canonical = self.normalize_faction(t.get("faction", ""))
                if canonical == "Expression/Explore":
                    suspended.append(t)
                else:
                    retained.append(t)

            # Sort retained strictly by crisis rank, then TWS
            retained.sort(
                key=lambda t: (
                    self.get_crisis_rank(t.get("faction", "")),
                    -float(t.get("tws", 0.0)),
                )
            )

            return {
                "tasks_retained": retained,
                "tasks_deferred": deferred,
                "tasks_suspended": suspended,
                "mode": "CRISIS",
                "overrides_applied": True,
                "level": 4,
                "redistribution_window_days": 14,
            }

    def get_status(self) -> EmergencyProtocolStatus:
        enabled = self.is_protocol_enabled()
        lvl = self._current_level if enabled else EmergencyLevel.LEVEL_0_NORMAL
        is_active = self._is_active if enabled else False
        lvl_num = int(lvl)

        mode_map = {
            0: "NORMAL",
            1: "NORMAL",
            2: "LOW_DCS",
            3: "SURVIVAL",
            4: "CRISIS",
        }
        window_map = {
            0: 1,
            1: 1,
            2: 2,
            3: 14,
            4: 14,
        }

        return EmergencyProtocolStatus(
            current_level=lvl_num,
            current_level_name=lvl.name,
            is_emergency_active=is_active,
            mode_override=mode_map.get(lvl_num, "NORMAL"),
            enabled=enabled,
            redistribution_window_days=window_map.get(lvl_num, 1),
            tool_permissions=self.get_tool_permissions(lvl_num),
            crisis_hierarchy=CRISIS_FACTION_ORDER,
            history=list(self._history),
        )
