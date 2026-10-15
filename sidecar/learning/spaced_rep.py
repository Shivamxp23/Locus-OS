"""Locus Spaced Repetition Engine (§30.5 / §30.6).

Implements the SuperMemo SM-2 interval scheduling algorithm to schedule reviews
for knowledge cards, facts, and code patterns extracted from vault notes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SpacedRepetitionCard:
    card_id: str
    front_prompt: str
    back_answer: str
    repetitions: int = 0
    interval_days: int = 1
    ease_factor: float = 2.5
    next_review_timestamp: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "front_prompt": self.front_prompt,
            "back_answer": self.back_answer,
            "repetitions": self.repetitions,
            "interval_days": self.interval_days,
            "ease_factor": self.ease_factor,
            "next_review_timestamp": self.next_review_timestamp,
            "tags": self.tags,
        }


class SpacedRepetitionEngine:
    """SuperMemo SM-2 spaced repetition scheduler."""

    def __init__(self):
        self.cards: Dict[str, SpacedRepetitionCard] = {}

    def add_card(self, card_id: str, front: str, back: str, tags: Optional[List[str]] = None) -> SpacedRepetitionCard:
        card = SpacedRepetitionCard(
            card_id=card_id,
            front_prompt=front,
            back_answer=back,
            tags=tags or [],
        )
        self.cards[card_id] = card
        return card

    def review_card(self, card_id: str, quality: int) -> SpacedRepetitionCard:
        """Processes a review with quality from 0 (complete blackout) to 5 (perfect recall)."""
        card = self.cards[card_id]
        quality = max(0, min(5, quality))

        if quality >= 3:
            if card.repetitions == 0:
                card.interval_days = 1
            elif card.repetitions == 1:
                card.interval_days = 6
            else:
                card.interval_days = int(round(card.interval_days * card.ease_factor))
            card.repetitions += 1
        else:
            card.repetitions = 0
            card.interval_days = 1

        # Update ease factor: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        card.ease_factor = max(1.3, card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        card.next_review_timestamp = time.time() + (card.interval_days * 86400)
        return card

    def get_due_cards(self) -> List[SpacedRepetitionCard]:
        now = time.time()
        return [c for c in self.cards.values() if c.next_review_timestamp <= now]
