"""
SPEC §2.4 / F-0093 / US-33: State Engine (Stage 3) Provider Contract.
Defines check-in records, canonical DCS formulas, operating mode thresholds,
and the CurrentState snapshot structure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class OperatingMode(str, Enum):
    """Operating modes per LOCUS_SYSTEM_v1.md §4 and SPEC §2.4 STEP 4."""
    SURVIVAL = "SURVIVAL"
    RECOVERY = "RECOVERY"
    NORMAL = "NORMAL"
    DEEP_WORK = "DEEP_WORK"
    PEAK = "PEAK"


@dataclass
class CheckInRecord:
    """Check-in record from morning or ambient input."""
    energy: float  # 1.0 - 10.0
    mood: float  # 1.0 - 10.0
    sleep: float  # 1.0 - 10.0
    stress: float  # 0.0 - 10.0 (converted to 0-20 via ST = stress * 2)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "energy": self.energy,
            "mood": self.mood,
            "sleep": self.sleep,
            "stress": self.stress,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CheckInRecord:
        return cls(
            energy=float(data.get("energy", 5.0)),
            mood=float(data.get("mood", 5.0)),
            sleep=float(data.get("sleep", 5.0)),
            stress=float(data.get("stress", 5.0)),
            timestamp=float(data.get("timestamp", time.time())),
        )


@dataclass
class CurrentState:
    """
    SPEC §2.4 STEP 5: CURRENT_STATE snapshot object.
    Object fields: { dcs, operating_mode, energy, mood, stress, sleep, active_alerts[], inferred_cause_chain }
    """
    dcs: float
    operating_mode: str
    energy: float
    mood: float
    sleep: float
    stress: float
    active_alerts: List[str] = field(default_factory=list)
    inferred_cause_chain: Optional[str] = None
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dcs": round(self.dcs, 2),
            "operating_mode": self.operating_mode,
            "energy": round(self.energy, 2),
            "mood": round(self.mood, 2),
            "sleep": round(self.sleep, 2),
            "stress": round(self.stress, 2),
            "active_alerts": list(self.active_alerts),
            "inferred_cause_chain": self.inferred_cause_chain,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CurrentState:
        return cls(
            dcs=float(data.get("dcs", 5.0)),
            operating_mode=data.get("operating_mode", OperatingMode.NORMAL.value),
            energy=float(data.get("energy", 5.0)),
            mood=float(data.get("mood", 5.0)),
            sleep=float(data.get("sleep", 5.0)),
            stress=float(data.get("stress", 5.0)),
            active_alerts=list(data.get("active_alerts") or []),
            inferred_cause_chain=data.get("inferred_cause_chain"),
            updated_at=float(data.get("updated_at", time.time())),
        )


class BaseStateEngineProvider(ABC):
    """
    Abstract Base Provider for Locus State Engine (Stage 3).
    """

    @abstractmethod
    def calculate_dcs(self, energy: float, mood: float, sleep: float, stress: float) -> float:
        """Calculate canonical DCS using: ((E + M + S) / 3) * (1 - ST / 20)."""
        raise NotImplementedError

    @abstractmethod
    def determine_operating_mode(self, dcs: float) -> str:
        """Determine operating mode from DCS thresholds (SURVIVAL -> PEAK)."""
        raise NotImplementedError

    @abstractmethod
    def process_checkin(
        self,
        checkin: CheckInRecord,
        now_ts: Optional[float] = None,
    ) -> CurrentState:
        """Process check-in and update CurrentState."""
        raise NotImplementedError

    @abstractmethod
    def get_current_state(self, now_ts: Optional[float] = None) -> CurrentState:
        """Retrieve current cached state, applying staleness penalties if applicable."""
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check modular off-switch."""
        raise NotImplementedError
