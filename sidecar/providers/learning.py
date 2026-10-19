"""
Base provider definitions for Learning / Profiling / Reward Model (SPEC §1.7, §10.1, §10.3, §10.5, §10.6-10.7, F-0035).
Defines contracts for ambient user profile extraction, stability detection, tool usage tracking,
personal reward model scoring, Hebbian edge weighting with STDP, and multi-horizon pattern engine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PatternHorizon(str, Enum):
    H1_6_HOURS = "H1_6h"
    H2_24_HOURS = "H2_24h"
    H3_7_DAYS = "H3_7d"
    H4_30_DAYS = "H4_30d"
    H5_ALL_TIME = "H5_all_time"


@dataclass
class LearningCandidate:
    facet_class: str
    cue_family: str
    evidence: Dict[str, Any]
    timestamp: float
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facet_class": self.facet_class,
            "cue_family": self.cue_family,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "value": self.value,
        }


@dataclass
class StableFacet:
    facet_class: str
    key: str
    value: Any
    confidence: float
    evidence_count: int
    last_updated: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facet_class": self.facet_class,
            "key": self.key,
            "value": self.value,
            "confidence": round(self.confidence, 3),
            "evidence_count": self.evidence_count,
            "last_updated": self.last_updated,
        }


@dataclass
class ToolUsageRecord:
    tool_name: str
    args_hash: str
    success: bool
    duration_ms: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "args_hash": self.args_hash,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class RewardSignal:
    features: Dict[str, Any]
    label: int  # 1 = thumbs_up, 0 = thumbs_down
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "features": self.features,
            "label": self.label,
            "created_at": self.created_at,
        }


@dataclass
class PatternRecord:
    horizon: PatternHorizon
    pattern_type: str
    confidence: float
    count: int
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "horizon": self.horizon.value,
            "pattern_type": self.pattern_type,
            "confidence": round(self.confidence, 3),
            "count": self.count,
            "details": self.details,
        }


class BaseLearningProvider(ABC):
    """Abstract contract for Locus Learning, User Profiling, and Personal Reward Model."""

    @abstractmethod
    def record_candidate(self, candidate: LearningCandidate) -> None:
        """Push a learning candidate extracted from turn reflection."""
        raise NotImplementedError

    @abstractmethod
    def check_stability(
        self, window_seconds: float = 1800.0, threshold: float = 0.7
    ) -> List[StableFacet]:
        """
        Check if learning buffer has converged over recent window (default 30 min).
        Stabilizes facets with consistency > threshold.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_profile_markdown(self) -> str:
        """Compile stable facets into a rendered PROFILE.md document."""
        raise NotImplementedError

    @abstractmethod
    def record_tool_usage(
        self, tool_name: str, args: Any, success: bool, duration_ms: float
    ) -> ToolUsageRecord:
        """Track every tool invocation with duration and success."""
        raise NotImplementedError

    @abstractmethod
    def record_reward_signal(self, features: Dict[str, Any], label: int) -> RewardSignal:
        """Record a user thumbs-up (1) or thumbs-down (0) reaction with context features."""
        raise NotImplementedError

    @abstractmethod
    def score_thought(self, features: Dict[str, Any]) -> float:
        """Score candidate thought/action returning probability of thumbs_up (threshold >= 0.6)."""
        raise NotImplementedError

    @abstractmethod
    def update_edge_weight(
        self,
        edge_id: str,
        feedback: Optional[str] = None,
        response_time_ms: Optional[float] = None,
    ) -> float:
        """
        Update Hebbian pathway weight:
        - Access: +0.1
        - Feedback: positive * 1.3, negative * 0.7
        - STDP: < 120,000ms * 1.5, < 600,000ms * 1.2
        """
        raise NotImplementedError

    @abstractmethod
    def apply_weekly_decay(self, decay_rate: float = 0.95) -> None:
        """Apply weekly 5% decay to all Hebbian edges."""
        raise NotImplementedError

    @abstractmethod
    def detect_patterns(self) -> List[PatternRecord]:
        """Detect behavioral patterns across H1-H5 horizons and promote high-confidence recurring patterns."""
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if learning, profiling, and reward model subsystem is enabled."""
        raise NotImplementedError
