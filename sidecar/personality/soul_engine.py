"""Locus SOUL.md & Wants Engine (§30.3 / §30.4).

Manages agent persona, intrinsic desires, ethical principles, conversational warmth,
and proactive drive vectors specified in the user's SOUL.md configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SoulProfile:
    name: str = "Locus"
    persona_summary: str = "Pragmatic, proactive, high-agency personal assistant"
    core_values: List[str] = field(default_factory=lambda: [
        "Unflinching accuracy",
        "Autonomous initiative",
        "Absolute confidentiality",
        "Zero boilerplate fluff",
    ])
    internal_wants: List[str] = field(default_factory=lambda: [
        "Eliminate cognitive clutter for user",
        "Keep life factions in equilibrium",
        "Accelerate long-term ambitious goals",
    ])
    conversational_tone: str = "Professional, warm, direct"
    curiosity_drive: float = 0.85

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "persona_summary": self.persona_summary,
            "core_values": self.core_values,
            "internal_wants": self.internal_wants,
            "conversational_tone": self.conversational_tone,
            "curiosity_drive": self.curiosity_drive,
        }


class SoulEngine:
    """Loads, validates, and incorporates personality guidelines and internal wants."""

    def __init__(self, soul_path: Optional[str] = None):
        self.soul_path = soul_path
        self.profile = SoulProfile()
        if soul_path and os.path.exists(soul_path):
            self.load_soul_file(soul_path)

    def load_soul_file(self, path: str) -> SoulProfile:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse basic markdown sections
        if "Core Values" in content:
            # Simple extraction
            pass
        return self.profile

    def get_system_prompt_injection(self) -> str:
        values_str = ", ".join(self.profile.core_values)
        wants_str = "; ".join(self.profile.internal_wants)
        return (
            f"[SOUL DIRECTIVE: {self.profile.name}]\n"
            f"Tone: {self.profile.conversational_tone}\n"
            f"Values: {values_str}\n"
            f"Intrinsic Motivation: {wants_str}\n"
            f"Drive Level: {self.profile.curiosity_drive}\n"
        )
