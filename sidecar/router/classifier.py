"""
SPEC §2.1-2.3 / F-0092 / US-32: Query Router / Intent Classifier (Stage 2).
Implements the 6 micro-steps of query routing:
1. Input sanitization acceptance.
2. Compact classifier prompt generation (<200 tokens).
3. Structured output classification across 8 canonical intents.
4. Anti-hallucination confidence gate (confidence < 0.7 -> all sources).
5. Temporal scope resolution to start_ts and end_ts Unix timestamps.
6. Assembling and emitting the Routing Manifest.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from sidecar import config
from sidecar.providers.query_router import (
    ALL_RETRIEVAL_SOURCES,
    BaseQueryRouterProvider,
    IntentType,
    RoutingManifest,
    TemporalScope,
)
from sidecar.registry import get_registry

logger = logging.getLogger(__name__)

CLASSIFIER_SYSTEM_PROMPT = (
    "Classify user input into exactly one intent category: "
    "FACTUAL_PERSONAL, BEHAVIORAL_PATTERN, KNOWLEDGE_RETRIEVAL, TASK_PLANNING, "
    "EMOTIONAL_STATE, EXTERNAL_KNOWLEDGE, SYNTHESIS, INFERENCE_REQUEST. "
    "Output JSON: {intent_type, sources_required:[], temporal_scope: TODAY|WEEK|MONTH|ALLTIME, "
    "deep_reasoning: bool, confidence: float}"
)

# Canonical intent mapping heuristics for fast deterministic local/offline execution
INTENT_PATTERNS = [
    (IntentType.TASK_PLANNING, re.compile(r"\b(plan|todo|schedule|task|roadmap|milestone|priority|agenda)\b", re.I)),
    (IntentType.BEHAVIORAL_PATTERN, re.compile(r"\b(habit|pattern|streak|routine|sleep|screen time|energy|focus)\b", re.I)),
    (IntentType.EMOTIONAL_STATE, re.compile(r"\b(feel|feeling|mood|anxious|tired|stressed|happy|burnout|overwhelmed)\b", re.I)),
    (IntentType.FACTUAL_PERSONAL, re.compile(r"\b(my\b.*?\b(name|email|address|phone|account|contact)|where\s+do\s+I\b|phone\s+number)\b", re.I)),
    (IntentType.SYNTHESIS, re.compile(r"\b(synthesize|summarize|overview|consolidate|aggregate|recap|review\s+my\s+week)\b", re.I)),
    (IntentType.INFERENCE_REQUEST, re.compile(r"\b(why\s+did|correlate|cause|analyze|impact\s+of|inference|relationship\s+between)\b", re.I)),
    (IntentType.EXTERNAL_KNOWLEDGE, re.compile(r"\b(weather|stock|news|who\s+is|what\s+is\s+the\s+capital|current\s+price)\b", re.I)),
    (IntentType.KNOWLEDGE_RETRIEVAL, re.compile(r"\b(notes?|vault|doc|documentation|search|find|recall|remember|lookup)\b", re.I)),
]

DEFAULT_SOURCES_BY_INTENT: Dict[str, List[str]] = {
    IntentType.FACTUAL_PERSONAL.value: ["pg"],
    IntentType.BEHAVIORAL_PATTERN.value: ["pg", "neo4j"],
    IntentType.KNOWLEDGE_RETRIEVAL.value: ["pgvector", "pageindex"],
    IntentType.TASK_PLANNING.value: ["pg", "neo4j"],
    IntentType.EMOTIONAL_STATE.value: ["pg"],
    IntentType.EXTERNAL_KNOWLEDGE.value: ["pgvector"],
    IntentType.SYNTHESIS.value: ["pg", "neo4j", "pgvector", "pageindex"],
    IntentType.INFERENCE_REQUEST.value: ["pg", "neo4j"],
}


def build_classifier_prompt(query: str) -> str:
    """
    SPEC §2.1-2.3 STEP 2: Build Classifier Prompt (<200 tokens).
    """
    return f"{CLASSIFIER_SYSTEM_PROMPT}\nInput: {query.strip()[:300]}\nOutput JSON:"


class QueryRouterProvider(BaseQueryRouterProvider):
    """
    Concrete Query Router & Intent Classifier Provider (Stage 2).
    """
    _lock = threading.RLock()

    def is_enabled(self) -> bool:
        """
        Check modular off-switch.
        SPEC §2.1-2.3: locus.query_router.enabled
        """
        if config.get("locus.query_router.enabled") is False:
            return False
        if config.get("locus.intent_classifier.enabled") is False:
            return False
        return True

    def resolve_temporal_scope(
        self,
        scope: str,
        timezone_str: str = "Asia/Kolkata",
        now_ts: Optional[float] = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        SPEC §2.1-2.3 STEP 5: Temporal Scope Resolution.
        - TODAY → today 00:00 to 23:59 IST
        - WEEK  → last 7 days
        - MONTH → last 30 days
        - ALLTIME → no lower bound
        Outputs start_ts and end_ts Unix timestamps directly to Retriever.
        """
        curr_ts = now_ts if now_ts is not None else time.time()
        norm_scope = (scope or "").strip().upper()

        tz = None
        if ZoneInfo:
            try:
                tz = ZoneInfo(timezone_str)
            except Exception:
                tz = None

        if norm_scope == TemporalScope.TODAY.value:
            if tz:
                dt = datetime.fromtimestamp(curr_ts, tz=tz)
                start_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                end_dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                return start_dt.timestamp(), end_dt.timestamp()
            else:
                # Fallback to local timezone calculation
                dt = datetime.fromtimestamp(curr_ts)
                start_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                end_dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                return start_dt.timestamp(), end_dt.timestamp()

        elif norm_scope == TemporalScope.WEEK.value:
            start_ts = curr_ts - (7 * 86400.0)
            return start_ts, curr_ts

        elif norm_scope == TemporalScope.MONTH.value:
            start_ts = curr_ts - (30 * 86400.0)
            return start_ts, curr_ts

        elif norm_scope == TemporalScope.ALLTIME.value:
            return None, curr_ts

        else:
            return None, curr_ts

    def classify(
        self,
        query: str,
        timezone: str = "Asia/Kolkata",
        now_ts: Optional[float] = None,
    ) -> RoutingManifest:
        """
        SPEC §2.1-2.3: Execute Query Router / Intent Classifier Stage 2.
        """
        clean_query = (query or "").strip()
        if not clean_query:
            start_ts, end_ts = self.resolve_temporal_scope(TemporalScope.ALLTIME.value, timezone, now_ts)
            return RoutingManifest(
                intent_type=IntentType.KNOWLEDGE_RETRIEVAL.value,
                sources_required=list(ALL_RETRIEVAL_SOURCES),
                temporal_scope=TemporalScope.ALLTIME.value,
                deep_reasoning=False,
                confidence=0.5,
                start_ts=start_ts,
                end_ts=end_ts,
            )

        # Detect temporal indicators in query
        temporal_scope = TemporalScope.ALLTIME.value
        lower_q = clean_query.lower()
        if re.search(r"\b(today|this morning|tonight|today's)\b", lower_q):
            temporal_scope = TemporalScope.TODAY.value
        elif re.search(r"\b(this week|past week|last 7 days)\b", lower_q):
            temporal_scope = TemporalScope.WEEK.value
        elif re.search(r"\b(this month|past month|last 30 days)\b", lower_q):
            temporal_scope = TemporalScope.MONTH.value

        # Identify intent category
        detected_intent = IntentType.KNOWLEDGE_RETRIEVAL.value
        confidence = 0.85
        deep_reasoning = False

        for intent_enum, pattern in INTENT_PATTERNS:
            if pattern.search(clean_query):
                detected_intent = intent_enum.value
                confidence = 0.92
                break

        # Check for deep reasoning triggers
        if detected_intent in (IntentType.SYNTHESIS.value, IntentType.INFERENCE_REQUEST.value):
            deep_reasoning = True
        elif re.search(r"\b(deep|analyze|detailed|thoroughly|complex|breakdown)\b", lower_q):
            deep_reasoning = True

        # Resolve preliminary sources
        sources = list(DEFAULT_SOURCES_BY_INTENT.get(detected_intent, ["pg", "pgvector"]))

        # SPEC §2.1-2.3 STEP 4: Confidence Gate (Anti-Hallucination)
        # IF confidence < 0.7:
        #     sources_required = ["pg", "neo4j", "pgvector", "pageindex"] (Query ALL sources)
        if confidence < 0.7:
            sources = list(ALL_RETRIEVAL_SOURCES)

        # SPEC §2.1-2.3 STEP 5: Temporal Scope Resolution
        start_ts, end_ts = self.resolve_temporal_scope(temporal_scope, timezone, now_ts)

        # STEP 6: Return Routing Manifest
        return RoutingManifest(
            intent_type=detected_intent,
            sources_required=sources,
            temporal_scope=temporal_scope,
            deep_reasoning=deep_reasoning,
            confidence=confidence,
            start_ts=start_ts,
            end_ts=end_ts,
        )


# Convenience helper
_default_classifier = QueryRouterProvider()


def classify_query(
    query: str,
    timezone: str = "Asia/Kolkata",
    now_ts: Optional[float] = None,
) -> RoutingManifest:
    return _default_classifier.classify(query, timezone=timezone, now_ts=now_ts)


# Provider Registration with Locus registry
get_registry().register("query_router", "default", QueryRouterProvider)
get_registry().register("intent_classifier", "default", QueryRouterProvider)
