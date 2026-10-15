"""sidecar/router/classifier.py - Query Router / Intent Classifier (Stage 2).

Implements Spec §2.1-2.3:
- 8 Intent categories:
  FACTUAL_PERSONAL, BEHAVIORAL_PATTERN, KNOWLEDGE_RETRIEVAL,
  TASK_PLANNING, EMOTIONAL_STATE, EXTERNAL_KNOWLEDGE, SYNTHESIS, INFERENCE_REQUEST.
- Temporal scope resolution: TODAY, WEEK, MONTH, ALLTIME.
- Anti-Hallucination Confidence Gate: If confidence < 0.7, queries all sources.
- Generates RoutingManifest used by Conductor and Retrieval pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

# IST timezone: UTC+05:30
IST = timezone(timedelta(hours=5, minutes=30))


class IntentCategory(str, Enum):
    FACTUAL_PERSONAL = "FACTUAL_PERSONAL"
    BEHAVIORAL_PATTERN = "BEHAVIORAL_PATTERN"
    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"
    TASK_PLANNING = "TASK_PLANNING"
    EMOTIONAL_STATE = "EMOTIONAL_STATE"
    EXTERNAL_KNOWLEDGE = "EXTERNAL_KNOWLEDGE"
    SYNTHESIS = "SYNTHESIS"
    INFERENCE_REQUEST = "INFERENCE_REQUEST"


class TemporalScope(str, Enum):
    TODAY = "TODAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    ALLTIME = "ALLTIME"


@dataclass
class RoutingManifest:
    """Routing Manifest output delivered to Conductor."""

    intent_type: IntentCategory
    sources_required: list[str]
    temporal_scope: TemporalScope
    start_ts: float
    end_ts: float
    deep_reasoning: bool
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "sources_required": self.sources_required,
            "temporal_scope": self.temporal_scope.value,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "deep_reasoning": self.deep_reasoning,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@runtime_checkable
class IntentClassifierProvider(Protocol):
    """Protocol for intent classifiers."""

    def classify(self, message: str) -> RoutingManifest:
        """Classify message intent and return routing manifest."""
        return RoutingManifest(
            intent_type=IntentCategory.KNOWLEDGE_RETRIEVAL,
            sources_required=["pg"],
            temporal_scope=TemporalScope.ALLTIME,
            start_ts=0.0,
            end_ts=0.0,
            deep_reasoning=False,
            confidence=0.0,
        )


class IntentClassifier:
    """Core Query Router / Intent Classifier implementing Spec §2.1-2.3."""

    ALL_SOURCES = ["pg", "neo4j", "pgvector", "pageindex"]

    def __init__(self, enabled: bool = True, default_confidence: float = 0.9):
        self.enabled = enabled
        self.default_confidence = default_confidence

    @staticmethod
    def resolve_temporal_scope(message: str, now: Optional[datetime] = None) -> tuple[TemporalScope, float, float]:
        """Resolve temporal scope string into start and end unix timestamps."""
        current_time = now or datetime.now(IST)
        msg = message.lower()

        if any(w in msg for w in ["today", "tonight", "this morning", "this afternoon", "hours ago"]):
            scope = TemporalScope.TODAY
            start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end = current_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif any(w in msg for w in ["week", "past week", "last 7 days", "few days"]):
            scope = TemporalScope.WEEK
            start = (current_time - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = current_time
        elif any(w in msg for w in ["month", "past month", "last 30 days", "recently"]):
            scope = TemporalScope.MONTH
            start = (current_time - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = current_time
        else:
            scope = TemporalScope.ALLTIME
            start = datetime(1970, 1, 1, tzinfo=timezone.utc)
            end = current_time

        return scope, start.timestamp(), end.timestamp()

    def classify(self, message: str, now: Optional[datetime] = None) -> RoutingManifest:
        """Classify a sanitized user query into a RoutingManifest."""
        if not self.enabled:
            scope, start_ts, end_ts = self.resolve_temporal_scope(message, now)
            return RoutingManifest(
                intent_type=IntentCategory.KNOWLEDGE_RETRIEVAL,
                sources_required=list(self.ALL_SOURCES),
                temporal_scope=scope,
                start_ts=start_ts,
                end_ts=end_ts,
                deep_reasoning=False,
                confidence=0.5,
                metadata={"disabled": True},
            )

        msg = message.strip().lower()
        scope, start_ts, end_ts = self.resolve_temporal_scope(message, now)

        # Rule-based fast-path intent resolution
        if any(w in msg for w in ["feel", "stressed", "tired", "sad", "anxious", "happy", "mood"]):
            intent = IntentCategory.EMOTIONAL_STATE
            sources = ["pg"]
            deep_reasoning = False
            confidence = 0.85
        elif any(w in msg for w in ["habit", "pattern", "routine", "usually", "trend", "when do i"]):
            intent = IntentCategory.BEHAVIORAL_PATTERN
            sources = ["pg", "neo4j"]
            deep_reasoning = True
            confidence = 0.88
        elif any(w in msg for w in ["schedule", "plan", "todo", "task", "deadline", "priority", "tws"]):
            intent = IntentCategory.TASK_PLANNING
            sources = ["pg", "pageindex"]
            deep_reasoning = False
            confidence = 0.90
        elif any(w in msg for w in ["why", "cause", "lead to", "correlate", "explain why", "inference"]):
            intent = IntentCategory.INFERENCE_REQUEST
            sources = ["neo4j", "pgvector"]
            deep_reasoning = True
            confidence = 0.85
        elif any(w in msg for w in ["summary", "synthesize", "overview", "review my"]):
            intent = IntentCategory.SYNTHESIS
            sources = ["pg", "neo4j", "pgvector"]
            deep_reasoning = True
            confidence = 0.82
        elif any(w in msg for w in ["who is", "weather", "news", "what is the capital", "google", "web"]):
            intent = IntentCategory.EXTERNAL_KNOWLEDGE
            sources = ["web"]
            deep_reasoning = False
            confidence = 0.90
        elif any(w in msg for w in ["my name", "my age", "my goal", "my birthday", "where do i live"]):
            intent = IntentCategory.FACTUAL_PERSONAL
            sources = ["pg", "pgvector"]
            deep_reasoning = False
            confidence = 0.92
        else:
            intent = IntentCategory.KNOWLEDGE_RETRIEVAL
            sources = ["pgvector", "pageindex"]
            deep_reasoning = False
            confidence = 0.65  # Triggers confidence gate fallback!

        # Step 4: Confidence Gate (Anti-Hallucination)
        if confidence < 0.7:
            sources_required = list(self.ALL_SOURCES)
        else:
            sources_required = sources

        return RoutingManifest(
            intent_type=intent,
            sources_required=sources_required,
            temporal_scope=scope,
            start_ts=start_ts,
            end_ts=end_ts,
            deep_reasoning=deep_reasoning,
            confidence=confidence,
        )
