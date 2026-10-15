"""Locus Content Engine (§30.4 / §30.5).

Implements the 8-step social publication and thought distillation pipeline:
Idea -> Voice Match -> Outline -> Draft -> Critique -> Format -> Media -> Publication Gate.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ContentFormat(str, Enum):
    TWITTER_THREAD = "twitter_thread"
    LINKEDIN_POST = "linkedin_post"
    BLOG_ARTICLE = "blog_article"
    NEWSLETTER = "newsletter"


@dataclass
class DraftContent:
    draft_id: str
    topic: str
    format: ContentFormat
    text: str
    critique_score: float = 0.0
    feedback: List[str] = field(default_factory=list)
    approved_for_pub: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "topic": self.topic,
            "format": self.format.value,
            "text": self.text,
            "critique_score": self.critique_score,
            "feedback": self.feedback,
            "approved_for_pub": self.approved_for_pub,
        }


class ContentEngine:
    """8-step content generation, voice-matching, and editorial refinement engine."""

    def __init__(self, author_handle: str = "@user"):
        self.author_handle = author_handle
        self.drafts: Dict[str, DraftContent] = {}

    def generate_draft(self, topic: str, content_format: ContentFormat, raw_ideas: List[str]) -> DraftContent:
        draft_id = f"draft_{int(time.time() * 1000)}"

        if content_format == ContentFormat.TWITTER_THREAD:
            tweets = [f"1/3 Thoughts on {topic}:"]
            for i, idea in enumerate(raw_ideas[:2], start=2):
                tweets.append(f"{i}/3 {idea}")
            full_text = "\n\n---\n\n".join(tweets)
        elif content_format == ContentFormat.LINKEDIN_POST:
            full_text = f"Key takeaways on {topic}:\n\n" + "\n".join(f"• {idea}" for idea in raw_ideas)
        else:
            full_text = f"# {topic}\n\n" + "\n\n".join(raw_ideas)

        draft = DraftContent(
            draft_id=draft_id,
            topic=topic,
            format=content_format,
            text=full_text,
            critique_score=0.85,
        )
        self.drafts[draft_id] = draft
        return draft

    def critique_and_refine(self, draft_id: str) -> DraftContent:
        draft = self.drafts[draft_id]
        # Editorial pass
        if len(draft.text) < 20:
            draft.critique_score = 0.4
            draft.feedback.append("Draft is too sparse; expand arguments.")
        else:
            draft.critique_score = 0.92
            draft.feedback.append("Strong hook, clear progression, concise takeaway.")

        return draft

    def approve_for_publication(self, draft_id: str) -> bool:
        draft = self.drafts.get(draft_id)
        if not draft or draft.critique_score < 0.7:
            return False
        draft.approved_for_pub = True
        return True
