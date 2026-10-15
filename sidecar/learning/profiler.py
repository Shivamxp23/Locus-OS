"""Locus User Learning, Profiling & Reward Model Engine (§1.7, §10.1, §10.3, §10.5-10.7).

Extracts implicit feedback signals from user conversations, tracks stylistic preferences,
scores model turns using a personal reward model, and reinforces successful patterns.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SignalType(str, Enum):
    CORRECTION = "correction"        # User explicitly corrected output
    APPROVAL = "approval"            # User approved or accepted output
    CLARIFICATION = "clarification"  # User asked for clarification
    FRUSTRATION = "frustration"      # Negative sentiment / repeated failure


@dataclass
class UserProfileSignal:
    signal_type: SignalType
    weight: float
    context: str
    inferred_preference: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": self.signal_type.value,
            "weight": self.weight,
            "context": self.context,
            "inferred_preference": self.inferred_preference,
            "timestamp": self.timestamp,
        }


class RewardModelScorer:
    """Computes alignment reward score (-1.0 to +1.0) based on turn interactions."""

    def compute_turn_reward(
        self,
        assistant_turn: str,
        user_response: str,
        execution_success: bool = True,
    ) -> float:
        score = 0.5 if execution_success else -0.5
        resp_lower = user_response.lower()

        positive_tokens = ["thanks", "perfect", "good", "great", "nice", "awesome", "proceed", "yes"]
        negative_tokens = ["no", "wrong", "stop", "error", "failed", "undo", "incorrect", "don't"]

        for t in positive_tokens:
            if t in resp_lower:
                score += 0.2
        for t in negative_tokens:
            if t in resp_lower:
                score -= 0.3

        return max(-1.0, min(1.0, score))


class UserLearningEngine:
    """Aggregates user interaction signals into an evolving developer profile."""

    def __init__(self):
        self.reward_scorer = RewardModelScorer()
        self.signals: List[UserProfileSignal] = []
        self.profile: Dict[str, Any] = {
            "prefers_terse_output": False,
            "preferred_languages": ["Python", "TypeScript"],
            "autonomy_comfort_level": 0.7,
            "satisfaction_score": 0.8,
        }

    def record_turn(
        self,
        assistant_turn: str,
        user_response: str,
        success: bool = True,
    ) -> float:
        reward = self.reward_scorer.compute_turn_reward(assistant_turn, user_response, success)

        if reward >= 0.5:
            sig = UserProfileSignal(
                signal_type=SignalType.APPROVAL,
                weight=reward,
                context=user_response[:80],
                inferred_preference="Satisfied with current approach",
            )
            self.signals.append(sig)
            self.profile["satisfaction_score"] = min(1.0, self.profile["satisfaction_score"] + 0.05)
        elif reward <= -0.2:
            sig = UserProfileSignal(
                signal_type=SignalType.CORRECTION,
                weight=reward,
                context=user_response[:80],
                inferred_preference="Adjusting parameters based on correction",
            )
            self.signals.append(sig)
            self.profile["satisfaction_score"] = max(0.0, self.profile["satisfaction_score"] - 0.08)

        # Check for conciseness preference
        if "concise" in user_response.lower() or "shorter" in user_response.lower():
            self.profile["prefers_terse_output"] = True

        return reward

    def get_profile_summary(self) -> Dict[str, Any]:
        return {
            "profile": self.profile,
            "total_signals_recorded": len(self.signals),
        }
