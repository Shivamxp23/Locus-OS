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

        current_section = ""
        lines = content.splitlines()
        extracted_values: List[str] = []
        extracted_wants: List[str] = []
        persona_lines: List[str] = []

        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith("#"):
                header_raw = trimmed.lstrip("#").strip()
                header_text = header_raw.lower()
                if "soul:" in header_text or "name:" in header_text:
                    parts = header_raw.split(":", 1)
                    if len(parts) > 1 and parts[1].strip():
                        self.profile.name = parts[1].strip()
                    current_section = "name"
                elif "core value" in header_text or "values" in header_text:
                    current_section = "values"
                elif "want" in header_text or "desire" in header_text or "motivation" in header_text:
                    current_section = "wants"
                elif "persona" in header_text or "identity" in header_text:
                    current_section = "persona"
                elif "tone" in header_text or "voice" in header_text:
                    current_section = "tone"
                elif "curiosity" in header_text or "drive" in header_text:
                    current_section = "drive"
                elif "name" in header_text:
                    current_section = "name"
                else:
                    current_section = "other"
                continue

            if not trimmed:
                continue

            if current_section == "values":
                if trimmed.startswith(("-", "*", "+")) or (trimmed[0].isdigit() and len(trimmed) > 2 and trimmed[1:3] in (". ", ") ")):
                    val = trimmed.lstrip("-*+ 0123456789.)").strip()
                    if val:
                        extracted_values.append(val)
                elif ":" in trimmed:
                    val = trimmed.split(":", 1)[1].strip()
                    if val:
                        extracted_values.append(val)
            elif current_section == "wants":
                if trimmed.startswith(("-", "*", "+")) or (trimmed[0].isdigit() and len(trimmed) > 2 and trimmed[1:3] in (". ", ") ")):
                    want = trimmed.lstrip("-*+ 0123456789.)").strip()
                    if want:
                        extracted_wants.append(want)
                elif ":" in trimmed:
                    want = trimmed.split(":", 1)[1].strip()
                    if want:
                        extracted_wants.append(want)
            elif current_section == "persona":
                persona_lines.append(trimmed)
            elif current_section == "tone":
                if ":" in trimmed:
                    self.profile.conversational_tone = trimmed.split(":", 1)[1].strip()
                else:
                    self.profile.conversational_tone = trimmed
            elif current_section == "drive":
                try:
                    val_str = trimmed.split(":", 1)[1] if ":" in trimmed else trimmed
                    self.profile.curiosity_drive = float(val_str.strip())
                except ValueError:
                    pass
            elif current_section == "name":
                name_val = trimmed.split(":", 1)[1] if ":" in trimmed else trimmed
                if name_val.strip():
                    self.profile.name = name_val.strip()

        if extracted_values:
            self.profile.core_values = extracted_values
        if extracted_wants:
            self.profile.internal_wants = extracted_wants
        if persona_lines:
            self.profile.persona_summary = " ".join(persona_lines)

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
