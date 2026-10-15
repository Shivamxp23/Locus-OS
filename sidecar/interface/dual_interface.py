"""Locus Dual Interface & Check-ins Bridge (§28.1-28.6).

Bridges CLI/TUI and Telegram interfaces so they share identical conversation context,
session history, and state, while scheduling 4 daily structured check-ins.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CheckInType(str, Enum):
    MORNING_KICKOFF = "morning_kickoff"  # 08:30: Day objectives, top 3 tasks, energy
    MIDDAY_CHECK = "midday_check"        # 13:00: Morning progress, blockers, afternoon adjustment
    EVENING_WRAP = "evening_wrap"        # 18:00: Wins, deferred tasks, faction balance
    NIGHTLY_REVIEW = "nightly_review"    # 22:00: Reflection, tomorrow setup, sleep readiness


@dataclass
class CheckInSchedule:
    check_in_type: CheckInType
    scheduled_time_str: str  # "HH:MM"
    prompt: str
    options: List[str]
    delivered: bool = False
    response: Optional[str] = None
    response_timestamp: Optional[float] = None


class DualInterfaceBridge:
    """Synchronizes state across TUI and Telegram interfaces with structured check-ins."""

    def __init__(self, session_id: str = "primary_session"):
        self.session_id = session_id
        self.message_history: List[Dict[str, Any]] = []
        self.active_interface: str = "tui"  # "tui" or "telegram"
        self.check_ins: Dict[CheckInType, CheckInSchedule] = {
            CheckInType.MORNING_KICKOFF: CheckInSchedule(
                check_in_type=CheckInType.MORNING_KICKOFF,
                scheduled_time_str="08:30",
                prompt="Good morning! What are the top 3 goals for today?",
                options=["Deep work block", "Clear backlog", "Team meetings", "Admin / Life tasks"],
            ),
            CheckInType.MIDDAY_CHECK: CheckInSchedule(
                check_in_type=CheckInType.MIDDAY_CHECK,
                scheduled_time_str="13:00",
                prompt="Midday sync: Any blockers on your primary focus?",
                options=["On track", "Minor distraction", "Blocked by dependency", "Need replan"],
            ),
            CheckInType.EVENING_WRAP: CheckInSchedule(
                check_in_type=CheckInType.EVENING_WRAP,
                scheduled_time_str="18:00",
                prompt="Evening wrap: How did your faction priorities balance today?",
                options=["Balanced", "Heavy work focus", "Health prioritized", "Social evening"],
            ),
            CheckInType.NIGHTLY_REVIEW: CheckInSchedule(
                check_in_type=CheckInType.NIGHTLY_REVIEW,
                scheduled_time_str="22:00",
                prompt="Nightly reflection: Ready to log off and reset for tomorrow?",
                options=["Ready for rest", "Reading notes", "Need to write brief journal"],
            ),
        }

    def post_message(self, source_interface: str, sender: str, text: str) -> Dict[str, Any]:
        self.active_interface = source_interface
        entry = {
            "source": source_interface,
            "sender": sender,
            "text": text,
            "timestamp": time.time(),
        }
        self.message_history.append(entry)
        return entry

    def get_unified_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.message_history[-limit:]

    def trigger_check_in(self, check_in_type: CheckInType) -> CheckInSchedule:
        item = self.check_ins[check_in_type]
        item.delivered = True
        return item

    def record_check_in_response(self, check_in_type: CheckInType, response_text: str) -> None:
        item = self.check_ins[check_in_type]
        item.response = response_text
        item.response_timestamp = time.time()
        # Also post into unified message history
        self.post_message(
            source_interface="check_in",
            sender="system",
            text=f"Check-in [{check_in_type.value}]: {response_text}",
        )
