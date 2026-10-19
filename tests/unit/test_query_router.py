"""
Unit tests for Query Router / Intent Classifier Stage 2 (SPEC §2.1-2.3 / F-0092 / US-32).
Asserts 8 canonical intent categories, anti-hallucination confidence gates,
temporal scope resolution, provider registry, and modular off-switches.
"""
import time
from typing import Any, Dict
import pytest

import sidecar.config as config
from sidecar.providers.query_router import (
    ALL_RETRIEVAL_SOURCES,
    BaseQueryRouterProvider,
    IntentType,
    RoutingManifest,
    TemporalScope,
)
from sidecar.registry import get_registry
from sidecar.router.classifier import (
    CLASSIFIER_SYSTEM_PROMPT,
    QueryRouterProvider,
    build_classifier_prompt,
    classify_query,
)


def test_routing_manifest_and_intent_types():
    """SPEC §2.1-2.3 line 1677: "Output payload: { intent_type, sources_required[], temporal_scope, deep_reasoning, confidence }"."""
    manifest = RoutingManifest(
        intent_type=IntentType.TASK_PLANNING.value,
        sources_required=["pg", "neo4j"],
        temporal_scope=TemporalScope.WEEK.value,
        deep_reasoning=True,
        confidence=0.95,
        start_ts=1700000000.0,
        end_ts=1700604800.0,
    )
    d = manifest.to_dict()
    assert d["intent_type"] == "TASK_PLANNING"
    assert d["sources_required"] == ["pg", "neo4j"]
    assert d["temporal_scope"] == "WEEK"
    assert d["deep_reasoning"] is True
    assert d["confidence"] == 0.95
    assert d["start_ts"] == 1700000000.0
    assert d["end_ts"] == 1700604800.0

    restored = RoutingManifest.from_dict(d)
    assert restored.intent_type == manifest.intent_type
    assert restored.sources_required == manifest.sources_required


def test_build_classifier_prompt():
    """SPEC §2.1-2.3 line 1669: "STEP 2: Build Classifier Prompt (<200 tokens)"."""
    prompt = build_classifier_prompt("What was my average sleep time last week?")
    assert "Classify user input into exactly one intent category" in prompt
    assert "Output JSON:" in prompt
    assert len(prompt.split()) < 150


def test_classification_all_8_intents():
    """SPEC §2.1-2.3 line 1670: "Intent Categories: FACTUAL_PERSONAL, BEHAVIORAL_PATTERN, KNOWLEDGE_RETRIEVAL, TASK_PLANNING, EMOTIONAL_STATE, EXTERNAL_KNOWLEDGE, SYNTHESIS, INFERENCE_REQUEST."."""
    provider = QueryRouterProvider()

    queries = {
        IntentType.TASK_PLANNING.value: "What are my priority tasks on the sprint roadmap for tomorrow?",
        IntentType.BEHAVIORAL_PATTERN.value: "Analyze my screen time habit and sleep routine over the last month.",
        IntentType.EMOTIONAL_STATE.value: "I am feeling stressed and overwhelmed with project deadlines.",
        IntentType.FACTUAL_PERSONAL.value: "What is my registered phone number and emergency contact?",
        IntentType.SYNTHESIS.value: "Synthesize a weekly overview and consolidate my project progress.",
        IntentType.INFERENCE_REQUEST.value: "Why did my productivity drop after 4 PM, correlate the cause?",
        IntentType.EXTERNAL_KNOWLEDGE.value: "What is the capital of Iceland and current weather?",
        IntentType.KNOWLEDGE_RETRIEVAL.value: "Lookup documentation on Neo4j schema definitions in my vault.",
    }

    for expected_intent, text in queries.items():
        res = provider.classify(text)
        assert res.intent_type == expected_intent, f"Expected {expected_intent} for '{text}', got {res.intent_type}"


def test_anti_hallucination_confidence_gate():
    """SPEC §2.1-2.3 line 1680: "IF confidence < 0.7: sources_required = [\"pg\", \"neo4j\", \"pgvector\", \"pageindex\"] (Query ALL sources)"."""
    provider = QueryRouterProvider()

    # Empty string drops confidence to 0.5 < 0.7, triggering all sources
    res_empty = provider.classify("")
    assert res_empty.confidence < 0.7
    assert res_empty.sources_required == ALL_RETRIEVAL_SOURCES

    # High confidence classification retains filtered specific sources
    res_high = provider.classify("What is my email address?")
    assert res_high.confidence >= 0.7
    assert set(res_high.sources_required) != set(ALL_RETRIEVAL_SOURCES)


def test_temporal_scope_resolution_today():
    """SPEC §2.1-2.3 line 1686: "TODAY → today 00:00 to 23:59 IST"."""
    provider = QueryRouterProvider()
    now = 1770000000.0  # arbitrary fixed timestamp

    start_ts, end_ts = provider.resolve_temporal_scope(TemporalScope.TODAY.value, "Asia/Kolkata", now_ts=now)
    assert start_ts is not None
    assert end_ts is not None
    assert start_ts < end_ts
    assert (end_ts - start_ts) >= 86399.0


def test_temporal_scope_resolution_week_and_month():
    """SPEC §2.1-2.3 line 1687: "WEEK  → last 7 days"."""
    provider = QueryRouterProvider()
    now = 1770000000.0

    start_w, end_w = provider.resolve_temporal_scope(TemporalScope.WEEK.value, now_ts=now)
    assert end_w == now
    assert start_w == now - (7 * 86400.0)

    start_m, end_m = provider.resolve_temporal_scope(TemporalScope.MONTH.value, now_ts=now)
    assert end_m == now
    assert start_m == now - (30 * 86400.0)


def test_temporal_scope_resolution_alltime():
    """SPEC §2.1-2.3 line 1689: "ALLTIME → no lower bound"."""
    provider = QueryRouterProvider()
    now = 1770000000.0

    start_a, end_a = provider.resolve_temporal_scope(TemporalScope.ALLTIME.value, now_ts=now)
    assert start_a is None
    assert end_a == now


def test_query_router_provider_registry():
    """SPEC §2.1-2.3 line 1699: "Provider Interface: Implements IntentClassifier"."""
    reg = get_registry()
    cls_router = reg.get_active_provider("query_router", default_name="default")
    assert cls_router is QueryRouterProvider

    cls_intent = reg.get_active_provider("intent_classifier", default_name="default")
    assert cls_intent is QueryRouterProvider


def test_query_router_modular_off_switch(monkeypatch):
    """SPEC §2.1-2.3 line 1700: "Integration: Called in Pi's transformContext hook at Stage 2."."""
    provider = QueryRouterProvider()
    assert provider.is_enabled() is True

    monkeypatch.setattr(config, "get", lambda k, d=None: False if "query_router" in k else True)
    assert provider.is_enabled() is False
