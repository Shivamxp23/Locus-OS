"""
SPEC §28.1-28.6 lines 7380-7432:
Dual-Interface (TUI + Telegram), 4 Daily Structured Check-ins, and Cost Budget Engine (F-0064 / US-101).
Source: Comprehensive Locus System Design.html + locus_microsystems.html
Logic:
    1. Dual-Interface Session Unification:
       - Both TUI and Telegram share the same session state.
       - Telegram messages bridge to Pi session; TUI messages connect directly.
       - Unified conversation timeline.
    2. 4 Daily Structured Check-ins:
       - 07:30 Morning: Energy, Stress, Readiness -> DCS calculation -> operating mode.
       - 13:00 Afternoon: Progress check + Energy update.
       - 18:00 Evening: Reflection + Remaining tasks.
       - 22:00 Night: Gratitude, Tomorrow prep, Wind-down.
       - Generates inline keyboard payloads.
    3. Zero-Cost Constraint & Budget Guard:
       - Tracks token consumption per day and per session.
       - Skips inner loop run if >80% daily budget used.
Off state:
    locus.gateway.dual_interface.enabled: when off, session bridge & checkins return disabled status.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.gateway.dual_interface")


class CheckInSlot(str, Enum):
    MORNING = "07:30_MORNING"
    AFTERNOON = "13:00_AFTERNOON"
    EVENING = "18:00_EVENING"
    NIGHT = "22:00_NIGHT"


@dataclass
class CheckInRecord:
    """Captured check-in data record."""
    slot: str
    energy: float  # 1 - 10
    stress: float  # 1 - 10
    mood: float    # -1.0 to 1.0
    readiness: str
    notes: str
    dcs_score: float
    operating_mode: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionMessage:
    """Unified message across TUI and Telegram."""
    channel: str  # "telegram" | "tui"
    session_id: str
    content: str
    sender: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DualInterfaceEngine:
    """
    SPEC §28.1-28.6: Unified Dual-Interface & Check-in manager.
    """

    SWITCH_KEY = "locus.gateway.dual_interface.enabled"

    def __init__(self, daily_budget_usd: float = 0.05) -> None:
        self.daily_budget_usd = daily_budget_usd
        self._sessions: Dict[str, List[SessionMessage]] = {}
        self._checkins: List[CheckInRecord] = []
        self._daily_tokens: int = 0
        self._daily_cost_usd: float = 0.0

    def is_enabled(self) -> bool:
        """Subsystem off-switch check."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def route_message(self, channel: str, session_id: str, content: str, sender: str = "user") -> Dict[str, Any]:
        """
        SPEC §28.1:
        Session unification:
        telegram_message -> session_bridge -> pi_session
        tui_message -> pi_session (direct)
        Both write to same session timeline.
        """
        if not self.is_enabled():
            return {
                "status": "DISABLED",
                "error": "Dual-interface subsystem is disabled",
                "status_code": 503,
            }

        msg = SessionMessage(
            channel=channel.lower(),
            session_id=session_id,
            content=content,
            sender=sender,
        )

        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(msg)

        # Estimate tokens and cost (DeepSeek Flash heuristic: ~$0.14 per 1M tokens)
        token_count = max(1, len(content) // 4)
        cost = (token_count / 1_000_000.0) * 0.14
        self.record_usage(token_count, cost)

        return {
            "status": "BRIDGED",
            "session_id": session_id,
            "channel": channel,
            "message": msg.to_dict(),
            "total_messages": len(self._sessions[session_id]),
            "status_code": 200,
        }

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve unified message history."""
        return [m.to_dict() for m in self._sessions.get(session_id, [])]

    def get_keyboard_for_slot(self, slot: str) -> List[List[Dict[str, str]]]:
        """
        SPEC §28.2: 4 Daily Structured Check-Ins inline keyboard layouts.
        """
        slot_clean = slot.strip().upper()

        if "MORNING" in slot_clean or "07:30" in slot_clean:
            return [
                [
                    {"text": "Energy: 1-3 😴", "callback_data": "energy:2"},
                    {"text": "Energy: 4-6 🙂", "callback_data": "energy:5"},
                    {"text": "Energy: 7-10 🔥", "callback_data": "energy:8"},
                ],
                [
                    {"text": "Stress: Low", "callback_data": "stress:2"},
                    {"text": "Stress: Medium", "callback_data": "stress:5"},
                    {"text": "Stress: High", "callback_data": "stress:8"},
                ],
                [
                    {"text": "Ready to go!", "callback_data": "readiness:ready"},
                    {"text": "Need a slow start", "callback_data": "readiness:slow"},
                    {"text": "Not feeling it", "callback_data": "readiness:off"},
                ],
            ]

        elif "AFTERNOON" in slot_clean or "13:00" in slot_clean:
            return [
                [
                    {"text": "On Track 🚀", "callback_data": "progress:good"},
                    {"text": "Behind Schedule ⏳", "callback_data": "progress:behind"},
                    {"text": "Blocked 🛑", "callback_data": "progress:blocked"},
                ],
                [
                    {"text": "Energy: High", "callback_data": "energy:8"},
                    {"text": "Energy: Medium", "callback_data": "energy:5"},
                    {"text": "Energy: Slump 🥱", "callback_data": "energy:3"},
                ],
            ]

        elif "EVENING" in slot_clean or "18:00" in slot_clean:
            return [
                [
                    {"text": "All Done ✅", "callback_data": "evening:complete"},
                    {"text": "Wrap Up 1-2 📝", "callback_data": "evening:wrapup"},
                    {"text": "Defer Remaining ⏩", "callback_data": "evening:defer"},
                ],
                [
                    {"text": "Reflect & Log", "callback_data": "action:reflect"},
                ],
            ]

        else:  # NIGHT / 22:00
            return [
                [
                    {"text": "Grateful & Ready for Bed 🌙", "callback_data": "night:ready"},
                    {"text": "Tomorrow Planned 📅", "callback_data": "night:planned"},
                ],
                [
                    {"text": "Log Journal", "callback_data": "action:journal"},
                ],
            ]

    def calculate_dcs(self, energy: float, stress: float, mood: float) -> Tuple[float, str]:
        """
        Calculate DCS (Daily Capacity Score) and operating mode per SPEC §28.2:
        dcs = (energy * 0.4) + ((10 - stress) * 0.3) + ((mood + 1) * 5 * 0.3)
        Range: 0.0 - 10.0
        """
        e = max(1.0, min(10.0, float(energy)))
        s = max(1.0, min(10.0, float(stress)))
        m = max(-1.0, min(1.0, float(mood)))

        dcs = (e * 0.4) + ((10.0 - s) * 0.3) + (((m + 1.0) * 5.0) * 0.3)
        dcs = round(max(0.0, min(10.0, dcs)), 2)

        if dcs >= 7.5:
            mode = "FLOW"
        elif dcs >= 5.0:
            mode = "BALANCED"
        elif dcs >= 3.0:
            mode = "RECOVERY"
        else:
            mode = "MINIMAL"

        return dcs, mode

    def record_checkin(
        self,
        slot: str,
        energy: float = 7.0,
        stress: float = 3.0,
        mood: float = 0.5,
        readiness: str = "Ready to go!",
        notes: str = "",
    ) -> CheckInRecord:
        """
        SPEC §28.2: Record structured daily check-in.
        """
        dcs, mode = self.calculate_dcs(energy, stress, mood)
        rec = CheckInRecord(
            slot=slot,
            energy=energy,
            stress=stress,
            mood=mood,
            readiness=readiness,
            notes=notes,
            dcs_score=dcs,
            operating_mode=mode,
        )
        self._checkins.append(rec)
        return rec

    def record_usage(self, tokens: int, cost_usd: float) -> None:
        """Track token count and cost against daily budget."""
        self._daily_tokens += tokens
        self._daily_cost_usd += cost_usd

    def check_budget_status(self) -> Dict[str, Any]:
        """
        SPEC §28.3:
        Zero-cost constraint:
        Estimated daily cost: ~$0.012/day.
        Inner Loop skips run if >80% daily budget used.
        """
        usage_pct = (self._daily_cost_usd / self.daily_budget_usd) * 100.0 if self.daily_budget_usd > 0 else 0.0
        skip_inner_loop = usage_pct >= 80.0

        return {
            "daily_tokens": self._daily_tokens,
            "daily_cost_usd": round(self._daily_cost_usd, 5),
            "daily_budget_usd": self.daily_budget_usd,
            "budget_usage_pct": round(usage_pct, 2),
            "skip_inner_loop_recommended": skip_inner_loop,
            "default_model": "DeepSeek V4 Flash",
        }

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""
        return {
            "subsystem_enabled": self.is_enabled(),
            "active_sessions_count": len(self._sessions),
            "total_checkins_count": len(self._checkins),
            "budget": self.check_budget_status(),
        }
