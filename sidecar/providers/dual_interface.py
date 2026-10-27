"""
SPEC §28.1-28.6 lines 7380-7432: Dual-Interface & Check-ins Provider (F-0064 / US-101).
Modular off-switches:
- locus.dual_interface_checkins.enabled (master toggle, returns 503 when off)
- locus.gateway.dual_interface.enabled (subsystem toggle)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.providers.dual_interface")


class BaseDualInterfaceProvider(ABC):
    """
    Abstract contract for Dual-Interface, Check-ins, and Budget Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def route_interface_message(
        self, channel: str, session_id: str, content: str, sender: str = "user"
    ) -> Dict[str, Any]:
        """Route message from TUI or Telegram into unified session."""

    @abstractmethod
    def get_checkin_keyboard(self, slot: str) -> Dict[str, Any]:
        """Retrieve keyboard layout for given daily checkin slot."""

    @abstractmethod
    def submit_checkin(
        self,
        slot: str,
        energy: float = 7.0,
        stress: float = 3.0,
        mood: float = 0.5,
        readiness: str = "Ready to go!",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Submit structured check-in and calculate DCS operating mode."""

    @abstractmethod
    def get_budget_status(self) -> Dict[str, Any]:
        """Get token budget and inner loop skip recommendation."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultDualInterfaceProvider(BaseDualInterfaceProvider):
    """
    Default provider wrapping DualInterfaceEngine with modular off-switch enforcement.
    """

    FEATURE_SWITCH = "locus.dual_interface_checkins.enabled"

    def __init__(self, engine: Optional[Any] = None) -> None:
        if engine is None:
            from sidecar.gateway.dual_interface import DualInterfaceEngine
            self.engine = DualInterfaceEngine()
        else:
            self.engine = engine

    @property
    def name(self) -> str:
        return "default_dual_interface"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master toggle locus.dual_interface_checkins.enabled."""
        val = config.get(self.FEATURE_SWITCH)
        if val is not None and not config.is_enabled(self.FEATURE_SWITCH):
            return False, self.FEATURE_SWITCH
        return True, self.FEATURE_SWITCH

    def route_interface_message(
        self, channel: str, session_id: str, content: str, sender: str = "user"
    ) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        return self.engine.route_message(channel, session_id, content, sender)

    def get_checkin_keyboard(self, slot: str) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        kb = self.engine.get_keyboard_for_slot(slot)
        return {"slot": slot, "keyboard": kb, "status_code": 200}

    def submit_checkin(
        self,
        slot: str,
        energy: float = 7.0,
        stress: float = 3.0,
        mood: float = 0.5,
        readiness: str = "Ready to go!",
        notes: str = "",
    ) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        rec = self.engine.record_checkin(
            slot=slot,
            energy=energy,
            stress=stress,
            mood=mood,
            readiness=readiness,
            notes=notes,
        )
        out = rec.to_dict()
        out["status_code"] = 200
        return out

    def get_budget_status(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        status = self.engine.check_budget_status()
        status["status_code"] = 200
        return status

    def get_status(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        st = self.engine.get_status()
        st["provider_enabled"] = True
        st["provider_name"] = self.name
        st["status_code"] = 200
        return st
