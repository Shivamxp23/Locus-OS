"""sidecar/life_os/emergency_protocol.py - Four-Level Emergency Protocol.

Implements Spec §25.16:
- Level 1 (Minor Incident): Alert notification only, standard schedule preserved.
- Level 2 (Urgent Interruption): Pause current block, queue 30m urgent response block.
- Level 3 (Severe Crisis): Clear today's discretionary schedule, allow only Health/Leverage recovery blocks.
- Level 4 (Catastrophic Emergency): Total override, lock non-emergency tools, activate emergency response mode.
- Crisis hierarchy strictly enforced: Health > Leverage > Craft > Expression.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Optional

from sidecar.life_os.factions import Faction


class EmergencyLevel(IntEnum):
    LEVEL_1_MINOR = 1
    LEVEL_2_URGENT = 2
    LEVEL_3_SEVERE = 3
    LEVEL_4_CRISIS = 4


@dataclass
class EmergencyState:
    active_level: EmergencyLevel
    reason: str
    affected_faction: Faction
    allowed_factions: list[Faction]
    schedule_action: str
    tool_lock_enabled: bool


class EmergencyProtocolEngine:
    """Manages the 4-level emergency escalation protocol."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.current_state: Optional[EmergencyState] = None

    def trigger_emergency(
        self,
        level: EmergencyLevel,
        reason: str,
        affected_faction: Faction = Faction.HEALTH,
    ) -> EmergencyState:
        """Trigger an emergency level escalation."""
        if not self.enabled:
            state = EmergencyState(
                active_level=level,
                reason=reason,
                affected_faction=affected_faction,
                allowed_factions=list(Faction),
                schedule_action="none_disabled",
                tool_lock_enabled=False,
            )
            self.current_state = state
            return state

        if level == EmergencyLevel.LEVEL_1_MINOR:
            state = EmergencyState(
                active_level=level,
                reason=reason,
                affected_faction=affected_faction,
                allowed_factions=list(Faction),
                schedule_action="notify_user",
                tool_lock_enabled=False,
            )
        elif level == EmergencyLevel.LEVEL_2_URGENT:
            state = EmergencyState(
                active_level=level,
                reason=reason,
                affected_faction=affected_faction,
                allowed_factions=list(Faction),
                schedule_action="insert_30m_response_block",
                tool_lock_enabled=False,
            )
        elif level == EmergencyLevel.LEVEL_3_SEVERE:
            # Only Health and Leverage permitted
            state = EmergencyState(
                active_level=level,
                reason=reason,
                affected_faction=affected_faction,
                allowed_factions=[Faction.HEALTH, Faction.LEVERAGE],
                schedule_action="clear_discretionary_schedule",
                tool_lock_enabled=False,
            )
        else:  # LEVEL_4_CRISIS
            # Only Health permitted, non-emergency tools locked
            state = EmergencyState(
                active_level=level,
                reason=reason,
                affected_faction=affected_faction,
                allowed_factions=[Faction.HEALTH],
                schedule_action="total_emergency_override",
                tool_lock_enabled=True,
            )

        self.current_state = state
        return state

    def resolve_emergency(self) -> None:
        """Clear active emergency and restore normal operating rules."""
        self.current_state = None

    def is_action_allowed(self, faction: Faction) -> bool:
        """Check if an action in the given faction is permitted under current emergency level."""
        if not self.enabled or not self.current_state:
            return True
        return faction in self.current_state.allowed_factions
