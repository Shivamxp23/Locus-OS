"""tests/test_router_classifier.py - Unit & Integration Tests for Query Router.

Tests Spec §2.1-2.3:
- Intent categorization into 8 canonical categories.
- Temporal scope resolution (TODAY, WEEK, MONTH, ALLTIME) to timestamps.
- Anti-Hallucination Confidence Gate: fallback to all sources if confidence < 0.7.
- Modularity switch: locus.router.classifier.enabled=False.
- RoutingManifest serializability.
"""

from datetime import datetime
import pytest

from sidecar.router.classifier import (
    IST,
    IntentCategory,
    IntentClassifier,
    IntentClassifierProvider,
    RoutingManifest,
    TemporalScope,
)


def test_intent_classifier_protocol_conformance():
    classifier = IntentClassifier()
    assert isinstance(classifier, IntentClassifierProvider)


def test_intent_categorization_and_sources():
    classifier = IntentClassifier(enabled=True)

    # 1. Emotional state
    m1 = classifier.classify("I feel very stressed and tired today")
    assert m1.intent_type == IntentCategory.EMOTIONAL_STATE
    assert m1.sources_required == ["pg"]
    assert m1.temporal_scope == TemporalScope.TODAY

    # 2. Behavioral pattern
    m2 = classifier.classify("What is my routine pattern this week?")
    assert m2.intent_type == IntentCategory.BEHAVIORAL_PATTERN
    assert "neo4j" in m2.sources_required
    assert m2.deep_reasoning is True
    assert m2.temporal_scope == TemporalScope.WEEK

    # 3. Task planning
    m3 = classifier.classify("What tasks are on my schedule this month?")
    assert m3.intent_type == IntentCategory.TASK_PLANNING
    assert "pageindex" in m3.sources_required
    assert m3.temporal_scope == TemporalScope.MONTH

    # 4. External knowledge
    m4 = classifier.classify("Search web for latest news on Python 3.14")
    assert m4.intent_type == IntentCategory.EXTERNAL_KNOWLEDGE
    assert m4.sources_required == ["web"]

    # 5. Factual personal
    m5 = classifier.classify("What is my name and birthday?")
    assert m5.intent_type == IntentCategory.FACTUAL_PERSONAL
    assert "pg" in m5.sources_required


def test_confidence_gate_queries_all_sources():
    """Confidence Gate: if confidence < 0.7, query all 4 sources."""
    classifier = IntentClassifier(enabled=True)
    # Ambiguous query triggers fallback with low confidence
    m = classifier.classify("something ambiguous without keywords")
    assert m.confidence < 0.7
    assert set(m.sources_required) == {"pg", "neo4j", "pgvector", "pageindex"}


def test_temporal_scope_resolution():
    classifier = IntentClassifier()
    ref_time = datetime(2027, 5, 1, 14, 30, tzinfo=IST)

    scope_today, start_today, end_today = classifier.resolve_temporal_scope("what happened today?", ref_time)
    assert scope_today == TemporalScope.TODAY
    assert end_today > start_today

    scope_week, start_week, end_week = classifier.resolve_temporal_scope("show my week logs", ref_time)
    assert scope_week == TemporalScope.WEEK
    assert end_week > start_week

    scope_all, start_all, end_all = classifier.resolve_temporal_scope("general history query", ref_time)
    assert scope_all == TemporalScope.ALLTIME
    assert start_all == 0.0


def test_classifier_modularity_disabled():
    classifier = IntentClassifier(enabled=False)
    m = classifier.classify("I feel tired")
    assert m.confidence == 0.5
    assert set(m.sources_required) == {"pg", "neo4j", "pgvector", "pageindex"}
    assert m.metadata.get("disabled") is True


def test_routing_manifest_serialization():
    classifier = IntentClassifier()
    m = classifier.classify("plan my day today")
    d = m.to_dict()
    assert d["intent_type"] == IntentCategory.TASK_PLANNING.value
    assert isinstance(d["start_ts"], float)
    assert isinstance(d["end_ts"], float)
    assert isinstance(d["sources_required"], list)
