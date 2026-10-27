"""
SPEC §25.16 lines 4923-4936: Four-Level Emergency Protocol Provider (F-0117 / US-94).
Modular off-switches:
- locus.four_level_emergency_protocol.enabled (returns HTTP 503 when off)
- locus.life_os.emergency_protocol.enabled (when off, no emergency overrides; standard scheduling applies)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.emergency_protocol import (
    EmergencyAssessment,
    EmergencyLevel,
    EmergencyProtocolStatus,
    FourLevelEmergencyProtocol,
    ProtocolActivationResult,
    ProtocolDeactivationResult,
)

logger = logging.getLogger("locus.providers.emergency_protocol")


class BaseFourLevelEmergencyProtocolProvider(ABC):
    """
    Abstract contract for Four-Level Emergency Protocol Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def evaluate_situation(
        self,
        disruption_hours: float = 0.0,
        disruption_days: int = 0,
        is_life_event: bool = False,
        trigger_reason: str = "",
    ) -> Dict[str, Any]:
        """Evaluate disruption parameters and return emergency level recommendation."""

    @abstractmethod
    def activate_protocol(
        self,
        level: int,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Activate emergency protocol level."""

    @abstractmethod
    def deactivate_protocol(self) -> Dict[str, Any]:
        """Deactivate protocol and return to standard operation."""

    @abstractmethod
    def apply_scheduling_overrides(
        self,
        tasks: List[Dict[str, Any]],
        level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Apply scheduling overrides based on active or specified emergency level."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultFourLevelEmergencyProtocolProvider(BaseFourLevelEmergencyProtocolProvider):
    """
    Default provider wrapping FourLevelEmergencyProtocol with modular off-switch enforcement.
    """

    def __init__(
        self,
        protocol: Optional[FourLevelEmergencyProtocol] = None,
    ) -> None:
        self.protocol = protocol or FourLevelEmergencyProtocol()

    @property
    def name(self) -> str:
        return "default_four_level_emergency_protocol_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        switch = "locus.four_level_emergency_protocol.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def evaluate_situation(
        self,
        disruption_hours: float = 0.0,
        disruption_days: int = 0,
        is_life_event: bool = False,
        trigger_reason: str = "",
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Four-level emergency protocol is disabled",
                "disabled": switch,
            }

        assessment: EmergencyAssessment = self.protocol.evaluate(
            disruption_hours=disruption_hours,
            disruption_days=disruption_days,
            is_life_event=is_life_event,
            trigger_reason=trigger_reason,
        )
        return assessment.to_dict()

    def activate_protocol(
        self,
        level: int,
        reason: str = "",
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Four-level emergency protocol is disabled",
                "disabled": switch,
            }

        result: ProtocolActivationResult = self.protocol.activate(
            level=level,
            reason=reason,
        )
        return result.to_dict()

    def deactivate_protocol(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Four-level emergency protocol is disabled",
                "disabled": switch,
            }

        result: ProtocolDeactivationResult = self.protocol.deactivate()
        return result.to_dict()

    def apply_scheduling_overrides(
        self,
        tasks: List[Dict[str, Any]],
        level: Optional[int] = None,
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Four-level emergency protocol is disabled",
                "disabled": switch,
            }

        return self.protocol.apply_scheduling_overrides(
            tasks=tasks,
            level=level,
        )

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        subsystem_enabled = self.protocol.is_protocol_enabled()

        if not enabled:
            return {
                "status_code": 503,
                "detail": "Four-level emergency protocol is disabled",
                "disabled": switch,
                "feature_enabled": False,
                "subsystem_enabled": subsystem_enabled,
            }

        status: EmergencyProtocolStatus = self.protocol.get_status()
        res = status.to_dict()
        res["feature_enabled"] = True
        res["subsystem_enabled"] = subsystem_enabled
        return res
