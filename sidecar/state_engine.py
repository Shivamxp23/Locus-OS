"""sidecar/state_engine.py - State Engine (Stage 3).

Implements Spec §2.4:
- Canonical DCS Calculation: DCS = ((E + M + S) / 3) * (1 - ST / 20).
- Operating Mode Determination: SURVIVAL, RECOVERY, NORMAL, DEEP_WORK, PEAK.
- Staleness penalty:
  - If no check-in today: scores * 0.9.
  - If no check-in in 3+ days: fallback to baseline (5, 5, 5, 7) + STALE_CHECKIN alert.
- State representation: { dcs, operating_mode, energy, mood, stress, sleep, active_alerts, inferred_cause_chain }.
- In-memory cache + Redis fallback support.
- Modularity switch: locus.state_engine.enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from sidecar.life_os.dcs import calculate_dcs
from sidecar.life_os.modes import OperatingMode, resolve_operating_mode


@dataclass
class CheckinRecord:
    """Check-in metrics for energy, mood, sleep, and stress."""

    energy: float = 7.0  # 1-10
    mood: float = 7.0  # 1-10
    sleep: float = 7.0  # 1-10
    stress: float = 4.0  # 0-10 (ST = stress * 2 in calculation)
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class CurrentState:
    """Multi-dimensional user physiological and operating state."""

    dcs: float
    operating_mode: OperatingMode
    energy: float
    mood: float
    stress: float
    sleep: float
    active_alerts: list[str] = field(default_factory=list)
    inferred_cause_chain: str = ""
    last_updated: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())

    def to_dict(self) -> dict[str, Any]:
        return {
            "dcs": round(self.dcs, 2),
            "operating_mode": self.operating_mode.value,
            "energy": round(self.energy, 2),
            "mood": round(self.mood, 2),
            "stress": round(self.stress, 2),
            "sleep": round(self.sleep, 2),
            "active_alerts": list(self.active_alerts),
            "inferred_cause_chain": self.inferred_cause_chain,
            "last_updated": self.last_updated,
        }


@runtime_checkable
class StateEngineProvider(Protocol):
    """Protocol for state engine providers."""

    def compute_state(self, last_checkin: Optional[CheckinRecord] = None, days_since_checkin: float = 0.0) -> CurrentState:
        """Compute CurrentState applying staleness penalties and mode mapping."""
        return CurrentState(
            dcs=5.0,
            operating_mode=OperatingMode.NORMAL,
            energy=5.0,
            mood=5.0,
            stress=5.0,
            sleep=5.0,
        )


class StateEngine:
    """Core State Engine implementing Spec §2.4."""

    BASELINE_ENERGY = 5.0
    BASELINE_MOOD = 5.0
    BASELINE_SLEEP = 5.0
    BASELINE_STRESS = 3.5  # yields ST = 7.0

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._cached_state: Optional[CurrentState] = None

    def compute_state(
        self,
        last_checkin: Optional[CheckinRecord] = None,
        days_since_checkin: float = 0.0,
    ) -> CurrentState:
        """Compute the current physiological state, applying staleness rules."""
        if not self.enabled:
            return CurrentState(
                dcs=5.0,
                operating_mode=OperatingMode.NORMAL,
                energy=5.0,
                mood=5.0,
                stress=5.0,
                sleep=5.0,
                active_alerts=["STATE_ENGINE_DISABLED"],
            )

        alerts: list[str] = []
        cause_chain = ""

        # Step 2: Staleness handling
        if last_checkin is None or days_since_checkin >= 3.0:
            # Fallback to baseline (5, 5, 5, 7) & queue STALE_CHECKIN alert
            energy = self.BASELINE_ENERGY
            mood = self.BASELINE_MOOD
            sleep = self.BASELINE_SLEEP
            stress = self.BASELINE_STRESS
            alerts.append("STALE_CHECKIN")
            cause_chain = "No check-in recorded for 3+ days: defaulted to baseline state."
        elif days_since_checkin >= 1.0:
            # Apply staleness penalty (all scores * 0.9)
            energy = max(1.0, last_checkin.energy * 0.9)
            mood = max(1.0, last_checkin.mood * 0.9)
            sleep = max(1.0, last_checkin.sleep * 0.9)
            stress = min(10.0, last_checkin.stress * 1.1)  # stress increases when stale
            alerts.append("CHECKIN_PENDING")
            cause_chain = "No check-in today: applied 10% staleness attenuation."
        else:
            energy = last_checkin.energy
            mood = last_checkin.mood
            sleep = last_checkin.sleep
            stress = last_checkin.stress
            cause_chain = f"Check-in fresh ({days_since_checkin*24:.1f}h ago)."

        # Step 3: Canonical DCS Calculation
        # DCS = ((E + M + S) / 3) * (1 - ST / 20)
        # Note: calculate_dcs in sidecar.life_os.dcs expects stress as raw 0-20 (ST = stress * 2)
        st_raw = min(20.0, max(0.0, stress * 2.0))
        dcs = calculate_dcs(energy=energy, mood=mood, sleep=sleep, stress=st_raw)

        # Step 4: Operating Mode Determination
        mode = resolve_operating_mode(dcs)

        state = CurrentState(
            dcs=dcs,
            operating_mode=mode,
            energy=energy,
            mood=mood,
            stress=stress,
            sleep=sleep,
            active_alerts=alerts,
            inferred_cause_chain=cause_chain,
        )
        self._cached_state = state
        return state

    def get_cached_state(self) -> Optional[CurrentState]:
        """Return cached CURRENT_STATE object."""
        return self._cached_state
