"""
SPEC §2.1-2.3 / F-0092 / US-32: Query Router / Intent Classifier Provider Contract.
Defines the 8 canonical intent categories, temporal scopes, and Routing Manifest.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IntentType(str, Enum):
    """The 8 canonical intent categories per SPEC §2.1-2.3 STEP 2."""
    FACTUAL_PERSONAL = "FACTUAL_PERSONAL"
    BEHAVIORAL_PATTERN = "BEHAVIORAL_PATTERN"
    KNOWLEDGE_RETRIEVAL = "KNOWLEDGE_RETRIEVAL"
    TASK_PLANNING = "TASK_PLANNING"
    EMOTIONAL_STATE = "EMOTIONAL_STATE"
    EXTERNAL_KNOWLEDGE = "EXTERNAL_KNOWLEDGE"
    SYNTHESIS = "SYNTHESIS"
    INFERENCE_REQUEST = "INFERENCE_REQUEST"


class TemporalScope(str, Enum):
    """Temporal scope bounds per SPEC §2.1-2.3 STEP 5."""
    TODAY = "TODAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    ALLTIME = "ALLTIME"


ALL_RETRIEVAL_SOURCES = ["pg", "neo4j", "pgvector", "pageindex"]


@dataclass
class RoutingManifest:
    """
    SPEC §2.1-2.3 STEP 3 & STEP 6: Routing Manifest object.
    Payload: { intent_type, sources_required, temporal_scope, deep_reasoning, confidence, start_ts, end_ts }
    """
    intent_type: str
    sources_required: List[str] = field(default_factory=lambda: ["pg", "pgvector"])
    temporal_scope: str = TemporalScope.ALLTIME.value
    deep_reasoning: bool = False
    confidence: float = 1.0
    start_ts: Optional[float] = None
    end_ts: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "sources_required": list(self.sources_required),
            "temporal_scope": self.temporal_scope,
            "deep_reasoning": self.deep_reasoning,
            "confidence": round(self.confidence, 4),
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RoutingManifest:
        return cls(
            intent_type=data.get("intent_type", IntentType.KNOWLEDGE_RETRIEVAL.value),
            sources_required=list(data.get("sources_required") or ["pg", "pgvector"]),
            temporal_scope=data.get("temporal_scope", TemporalScope.ALLTIME.value),
            deep_reasoning=bool(data.get("deep_reasoning", False)),
            confidence=float(data.get("confidence", 1.0)),
            start_ts=data.get("start_ts"),
            end_ts=data.get("end_ts"),
        )


class BaseQueryRouterProvider(ABC):
    """
    Abstract base provider for Query Router / Intent Classifier (Stage 2).
    """

    @abstractmethod
    def classify(
        self,
        query: str,
        timezone: str = "Asia/Kolkata",
        now_ts: Optional[float] = None,
    ) -> RoutingManifest:
        """
        Classify raw query and return full Routing Manifest.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_temporal_scope(
        self,
        scope: str,
        timezone: str = "Asia/Kolkata",
        now_ts: Optional[float] = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Resolve start and end Unix timestamps for a temporal scope.
        """
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check modular off-switch."""
        raise NotImplementedError
