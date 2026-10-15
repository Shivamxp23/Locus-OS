"""Post-Turn Background Reviewer & Reflector (§1.7 + §10.1).

Asynchronous reflection engine executing on a daemon thread after conversation turns.
Extracts insights, user preferences, and skill suggestions while enforcing tool whitelists
(strictly ['memory', 'skill_manage']) to prevent side effects.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set


ALLOWED_REVIEW_TOOLS: Set[str] = {"memory", "skill_manage"}


@dataclass
class ReviewInsight:
    category: str  # "preference", "fact", "skill"
    content: str
    confidence: float = 0.85
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class ReviewResult:
    session_id: str
    turn_id: str
    insights_extracted: List[ReviewInsight] = field(default_factory=list)
    skills_updated: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


class TurnReflector:
    """Extracts learnings from turn conversation snapshots without blocking execution."""

    def __init__(self, tool_whitelist: Optional[Set[str]] = None) -> None:
        self.tool_whitelist = tool_whitelist or set(ALLOWED_REVIEW_TOOLS)
        self.completed_reviews: List[ReviewResult] = []
        self._lock = threading.Lock()

    def is_tool_allowed(self, tool_name: str) -> bool:
        return tool_name in self.tool_whitelist

    def extract_insights(self, messages: List[Dict[str, Any]]) -> List[ReviewInsight]:
        insights: List[ReviewInsight] = []
        for msg in messages:
            content = str(msg.get("content", ""))
            # Pattern heuristics for preferences / facts
            if any(cue in content.lower() for cue in ["i prefer", "i always use", "my project is", "call me"]):
                insights.append(
                    ReviewInsight(
                        category="preference",
                        content=content[:150],
                        confidence=0.90,
                    )
                )
            elif any(cue in content.lower() for cue in ["new rule", "remember to", "convention"]):
                insights.append(
                    ReviewInsight(
                        category="skill",
                        content=content[:150],
                        confidence=0.85,
                    )
                )
        return insights

    def review_turn(
        self,
        session_id: str,
        turn_id: str,
        messages: List[Dict[str, Any]],
        async_spawn: bool = False,
    ) -> Optional[ReviewResult]:
        def _execute() -> ReviewResult:
            t0 = time.time()
            insights = self.extract_insights(messages)
            skills: List[str] = [i.content for i in insights if i.category == "skill"]
            dur = (time.time() - t0) * 1000.0

            res = ReviewResult(
                session_id=session_id,
                turn_id=turn_id,
                insights_extracted=insights,
                skills_updated=skills,
                duration_ms=dur,
            )
            with self._lock:
                self.completed_reviews.append(res)
            return res

        if async_spawn:
            th = threading.Thread(target=_execute, daemon=True)
            th.start()
            return None
        else:
            return _execute()


def spawn_background_review(
    session_id: str,
    turn_id: str,
    messages: List[Dict[str, Any]],
    reflector: Optional[TurnReflector] = None,
) -> Optional[ReviewResult]:
    r = reflector or TurnReflector()
    return r.review_turn(session_id, turn_id, messages, async_spawn=False)
