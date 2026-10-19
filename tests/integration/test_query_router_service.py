"""
Integration tests for Query Router / Intent Classifier FastAPI endpoints (SPEC §2.1-2.3 / F-0092 / US-32).
Asserts classification endpoint `/router/classify`, confidence gating, temporal scopes, and 503 off-switch.
"""
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.providers.query_router import (
    ALL_RETRIEVAL_SOURCES,
    BaseQueryRouterProvider,
    IntentType,
    RoutingManifest,
    TemporalScope,
)
from sidecar.router.classifier import QueryRouterProvider, classify_query
from sidecar.service import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_router_classify_endpoint_basic(client):
    """SPEC §2.1-2.3 line 1674: "STEP 3: DeepSeek V4 Flash (cheapest available) Classification Call"."""
    res = client.post(
        "/router/classify",
        json={
            "query": "Synthesize an overview of my project tasks for this week",
            "timezone": "Asia/Kolkata",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "manifest" in data
    manifest = data["manifest"]
    assert manifest["intent_type"] in [IntentType.SYNTHESIS.value, IntentType.TASK_PLANNING.value]
    assert manifest["temporal_scope"] == TemporalScope.WEEK.value
    assert manifest["start_ts"] is not None
    assert manifest["end_ts"] is not None


def test_router_classify_confidence_gate(client):
    """SPEC §2.1-2.3 line 1681: "sources_required = [\"pg\", \"neo4j\", \"pgvector\", \"pageindex\"] (Query ALL sources)"."""
    # Empty query triggers low confidence < 0.7 -> all sources required
    res = client.post("/router/classify", json={"query": ""})
    assert res.status_code == 200
    data = res.json()
    manifest = data["manifest"]
    assert manifest["confidence"] < 0.7
    assert manifest["sources_required"] == ALL_RETRIEVAL_SOURCES


def test_router_classify_503_off_switch(client, monkeypatch):
    """SPEC §2.1-2.3 line 1700: "Integration: Called in Pi's transformContext hook at Stage 2."."""
    monkeypatch.setattr(config, "get", lambda k, d=None: False if "query_router" in k else True)

    res = client.post(
        "/router/classify",
        json={"query": "Find documentation on vault syncing"},
    )
    assert res.status_code == 503
    data = res.json()
    assert data["disabled"] == "locus.query_router.enabled"
