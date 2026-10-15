"""sidecar/ingestion/rough_note_parser.py - Rough Note Parser & Idea Tracker.

Implements Spec §27.5:
- Ingests unstructured braindumps, speech-to-text transcripts, bullet journals.
- Extracts actionable tasks, detected project linkages, factions, priorities, and tags.
- Converts raw thoughts into structured Life OS candidate records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sidecar.life_os.factions import Faction


@dataclass
class ParsedIdea:
    title: str
    detected_faction: Faction
    is_actionable: bool
    estimated_difficulty: float = 5.0
    detected_tags: list[str] = field(default_factory=list)
    raw_snippet: str = ""


class RoughNoteParser:
    """Parses raw notes and braindumps into structured Life OS concepts."""

    FACTION_KEYWORDS = {
        Faction.HEALTH: ["workout", "gym", "run", "sleep", "diet", "doctor", "health", "water", "rest"],
        Faction.CRAFT: ["code", "build", "debug", "refactor", "feature", "pr", "deploy", "engineering"],
        Faction.LEVERAGE: ["finance", "invest", "tax", "automate", "system", "contract", "wealth", "revenue"],
        Faction.EXPRESSION: ["write", "essay", "blog", "draw", "tweet", "video", "publish", "music"],
    }

    ACTION_VERBS = ["todo", "fix", "buy", "call", "write", "finish", "review", "schedule", "deploy", "test"]

    def parse_note(self, text: str) -> list[ParsedIdea]:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        ideas: list[ParsedIdea] = []

        for line in lines:
            clean = re.sub(r"^[-*•\d\.\s\[\]]+", "", line).strip()
            if not clean:
                continue

            # Detect tags (#tag)
            tags = re.findall(r"#([\w/-]+)", clean)
            title = re.sub(r"#[\w/-]+", "", clean).strip()

            lower_text = clean.lower()
            # Detect faction from tags first
            lower_tags = [t.lower() for t in tags]
            detected_faction = None
            for faction in Faction:
                if faction.value.lower() in lower_tags:
                    detected_faction = faction
                    break

            if not detected_faction:
                detected_faction = Faction.CRAFT
                for faction, keywords in self.FACTION_KEYWORDS.items():
                    if any(re.search(rf"\b{re.escape(kw)}\b", lower_text) for kw in keywords):
                        detected_faction = faction
                        break

            # Detect actionability
            is_actionable = any(lower_text.startswith(verb) for verb in self.ACTION_VERBS) or "todo" in lower_text

            ideas.append(
                ParsedIdea(
                    title=title,
                    detected_faction=detected_faction,
                    is_actionable=is_actionable,
                    detected_tags=[f"#{t}" for t in tags],
                    raw_snippet=line,
                )
            )

        return ideas
