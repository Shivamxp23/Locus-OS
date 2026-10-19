"""
SPEC §2.4 / F-0093 / US-33: Locus State Engine (Stage 3).
Implements the 5 micro-steps of cognitive state tracking:
1. Event-driven write trigger reception.
2. Last check-in read with staleness penalties (scores * 0.9 if no checkin today; baseline + STALE_CHECKIN alert if >=3 days).
3. Canonical Daily Capacity Score (DCS) calculation: ((E + M + S) / 3) * (1 - ST / 20).
4. Operating Mode determination across 5 tiers (SURVIVAL -> PEAK).
5. State snapshot cache (CURRENT_STATE) with thread-safe class state.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from sidecar import config
from sidecar.providers.state_engine import (
    BaseStateEngineProvider,
    CheckInRecord,
    CurrentState,
    OperatingMode,
)
from sidecar.registry import get_registry

logger = logging.getLogger(__name__)

# Default baseline values if no checkin in 3+ days
DEFAULT_BASELINE = {
    "energy": 5.0,
    "mood": 5.0,
    "sleep": 5.0,
    "stress": 7.0,  # input_stress 3.5 -> ST = 7.0
}


class StateEngineProvider(BaseStateEngineProvider):
    """
    Concrete State Engine Provider (Stage 3).
    """
    _lock = threading.RLock()
    _last_checkin: Optional[CheckInRecord] = None
    _current_state: Optional[CurrentState] = None

    def __init__(self) -> None:
        with self._lock:
            if StateEngineProvider._current_state is None:
                # Initialize default nominal state
                dcs = self.calculate_dcs(5.0, 5.0, 5.0, 2.5)
                mode = self.determine_operating_mode(dcs)
                StateEngineProvider._current_state = CurrentState(
                    dcs=dcs,
                    operating_mode=mode,
                    energy=5.0,
                    mood=5.0,
                    sleep=5.0,
                    stress=2.5,
                    active_alerts=[],
                    inferred_cause_chain=None,
                    updated_at=time.time(),
                )

    def is_enabled(self) -> bool:
        """
        Check modular off-switch.
        SPEC §2.4: locus.state_engine.enabled
        """
        if config.get("locus.state_engine.enabled") is False:
            return False
        return True

    def calculate_dcs(
        self,
        energy: float,
        mood: float,
        sleep: float,
        stress: float,
    ) -> float:
        """
        SPEC §2.4 STEP 3: Canonical DCS Calculation
        Formula: DCS = ((E + M + S) / 3) × (1 - ST / 20)
        where:
          E = Energy level (1-10)
          M = Mood valence (1-10)
          S = Sleep quality (1-10)
          ST = Stress score (0-20, computed as input_stress × 2)
        Output Range: 0.0 to 10.0 float.
        """
        e = max(1.0, min(10.0, float(energy)))
        m = max(1.0, min(10.0, float(mood)))
        s = max(1.0, min(10.0, float(sleep)))

        # Convert input stress (0-10) to ST (0-20)
        input_stress = max(0.0, min(10.0, float(stress)))
        st = input_stress * 2.0

        base_avg = (e + m + s) / 3.0
        stress_factor = max(0.0, 1.0 - (st / 20.0))
        dcs = base_avg * stress_factor

        return round(max(0.0, min(10.0, dcs)), 2)

    def determine_operating_mode(self, dcs: float) -> str:
        """
        SPEC §2.4 STEP 4: Operating Mode Determination (LOCUS_SYSTEM_v1.md §4 thresholds)
        - DCS 0.0 - 2.0  → SURVIVAL
        - DCS 2.1 - 4.0  → RECOVERY
        - DCS 4.1 - 6.0  → NORMAL
        - DCS 6.1 - 8.0  → DEEP_WORK
        - DCS 8.1 - 10.0 → PEAK
        """
        score = float(dcs)
        if score <= 2.0:
            return OperatingMode.SURVIVAL.value
        elif score <= 4.0:
            return OperatingMode.RECOVERY.value
        elif score <= 6.0:
            return OperatingMode.NORMAL.value
        elif score <= 8.0:
            return OperatingMode.DEEP_WORK.value
        else:
            return OperatingMode.PEAK.value

    def process_checkin(
        self,
        checkin: CheckInRecord,
        now_ts: Optional[float] = None,
    ) -> CurrentState:
        """
        SPEC §2.4 STEP 1 & STEP 3-5: Process check-in and update CurrentState.
        """
        with self._lock:
            curr_ts = now_ts if now_ts is not None else time.time()
            StateEngineProvider._last_checkin = checkin

            dcs = self.calculate_dcs(
                energy=checkin.energy,
                mood=checkin.mood,
                sleep=checkin.sleep,
                stress=checkin.stress,
            )
            mode = self.determine_operating_mode(dcs)

            alerts: List[str] = []
            cause_chain: Optional[str] = None

            if dcs <= 2.0:
                alerts.append("CRITICAL_CAPACITY_LOW")
                cause_chain = "Low sleep and high stress combined to breach survival threshold"
            elif dcs <= 4.0:
                alerts.append("RECOVERY_REQUIRED")
                cause_chain = "Depleted reserves indicate gentle cognitive load only"

            state = CurrentState(
                dcs=dcs,
                operating_mode=mode,
                energy=checkin.energy,
                mood=checkin.mood,
                sleep=checkin.sleep,
                stress=checkin.stress,
                active_alerts=alerts,
                inferred_cause_chain=cause_chain,
                updated_at=curr_ts,
            )
            StateEngineProvider._current_state = state
            return state

    def get_current_state(self, now_ts: Optional[float] = None) -> CurrentState:
        """
        SPEC §2.4 STEP 2 & STEP 5: Read last check-in with staleness penalties.
        - If no check-in today: apply staleness penalty (all scores × 0.9).
        - If no check-in in 3+ days: default to baseline (5,5,5,7) & queue STALE_CHECKIN alert.
        """
        with self._lock:
            curr_ts = now_ts if now_ts is not None else time.time()
            checkin = StateEngineProvider._last_checkin

            if checkin is None:
                # No recorded checkin ever
                alerts = ["STALE_CHECKIN"]
                e = DEFAULT_BASELINE["energy"]
                m = DEFAULT_BASELINE["mood"]
                s = DEFAULT_BASELINE["sleep"]
                input_stress = DEFAULT_BASELINE["stress"] / 2.0
                dcs = self.calculate_dcs(e, m, s, input_stress)
                mode = self.determine_operating_mode(dcs)
                return CurrentState(
                    dcs=dcs,
                    operating_mode=mode,
                    energy=e,
                    mood=m,
                    sleep=s,
                    stress=input_stress,
                    active_alerts=alerts,
                    inferred_cause_chain="No recent check-in recorded; defaulted to baseline",
                    updated_at=curr_ts,
                )

            age_seconds = curr_ts - checkin.timestamp

            # 3+ days (3 * 86400 = 259200 seconds)
            if age_seconds >= (3 * 86400):
                alerts = ["STALE_CHECKIN"]
                e = DEFAULT_BASELINE["energy"]
                m = DEFAULT_BASELINE["mood"]
                s = DEFAULT_BASELINE["sleep"]
                input_stress = DEFAULT_BASELINE["stress"] / 2.0
                dcs = self.calculate_dcs(e, m, s, input_stress)
                mode = self.determine_operating_mode(dcs)
                return CurrentState(
                    dcs=dcs,
                    operating_mode=mode,
                    energy=e,
                    mood=m,
                    sleep=s,
                    stress=input_stress,
                    active_alerts=alerts,
                    inferred_cause_chain="Check-in older than 3 days; defaulted to baseline",
                    updated_at=curr_ts,
                )

            # Not today (> 24 hours = 86400 seconds)
            elif age_seconds >= 86400:
                alerts = ["CHECKIN_DUE_TODAY"]
                # Apply staleness penalty: all scores * 0.9
                e = checkin.energy * 0.9
                m = checkin.mood * 0.9
                s = checkin.sleep * 0.9
                input_stress = checkin.stress * 1.1  # slightly increased stress on staleness
                dcs = self.calculate_dcs(e, m, s, input_stress)
                mode = self.determine_operating_mode(dcs)
                return CurrentState(
                    dcs=dcs,
                    operating_mode=mode,
                    energy=e,
                    mood=m,
                    sleep=s,
                    stress=input_stress,
                    active_alerts=alerts,
                    inferred_cause_chain="Staleness penalty applied (no check-in today)",
                    updated_at=curr_ts,
                )

            # Fresh checkin
            if StateEngineProvider._current_state is not None:
                return StateEngineProvider._current_state

            dcs = self.calculate_dcs(checkin.energy, checkin.mood, checkin.sleep, checkin.stress)
            mode = self.determine_operating_mode(dcs)
            return CurrentState(
                dcs=dcs,
                operating_mode=mode,
                energy=checkin.energy,
                mood=checkin.mood,
                sleep=checkin.sleep,
                stress=checkin.stress,
                active_alerts=[],
                inferred_cause_chain=None,
                updated_at=curr_ts,
            )

    def reset(self) -> None:
        """Reset state engine for clean test isolation."""
        with self._lock:
            StateEngineProvider._last_checkin = None
            StateEngineProvider._current_state = None


# Provider registration
get_registry().register("state_engine", "default", StateEngineProvider)
