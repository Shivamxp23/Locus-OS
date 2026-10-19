"""
Integration tests for Context Forge FastAPI endpoints (SPEC §2.5 / F-0094 / US-34).
Asserts endpoints `/forge/assemble`, `/forge/config`, and 503 off-switch.
"""
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.providers.context_forge import (
    ANTI_HALLUCINATION_INSTRUCTION,
    BaseContextForgeProvider,
    ContextForgeResult,
    LayerBudgetConfig,
    RetrievalInput,
)
from sidecar.service import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    original_enabled = config.get("locus.brain.context_forge.enabled")
    original_legacy = config.get("locus.context_forge.enabled")
    original_layers = config.get("locus.brain.context_forge.layers")
    config.set("locus.brain.context_forge.enabled", True)
    config.set("locus.context_forge.enabled", True)
    yield
    config.set("locus.brain.context_forge.enabled", original_enabled)
    config.set("locus.context_forge.enabled", original_legacy)
    config.set("locus.brain.context_forge.layers", original_layers)


def test_forge_assemble_endpoint(client):
    """SPEC §2.5 line 1799: "Delivers complete <=800 token context block + metadata to Conductor."."""
    payload = {
        "retrieval_input": {
            "identity": {
                "life_goals": ["Ship autonomous Locus OS"],
                "active_factions": ["Systems Architect"],
            },
            "temporal": {
                "operating_mode": "PEAK",
                "dcs": 8.8,
            },
            "events": [
                {"task": "Build Context Forge", "dur": 45, "q": 9}
            ],
            "neo4j_paths": [
                {"path_str": "task_A → behavior_B (w:0.84) → outcome_C", "weight": 0.84}
            ],
            "semantic_snippets": [
                {"text": "Relevant architectural pattern for context assembly", "similarity": 0.9}
            ],
            "web_results": [],
            "intent_requires_web": False,
        }
    }
    res = client.post("/forge/assemble", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "result" in data
    result = data["result"]
    assert "assembled_prompt" in result
    assert ANTI_HALLUCINATION_INSTRUCTION in result["assembled_prompt"]
    assert "Ship autonomous Locus OS" in result["assembled_prompt"]
    assert result["total_tokens"] <= 800
    assert len(result["layers"]) == 6
    assert len(result["hebbian_updates"]) == 1


def test_forge_config_endpoint(client):
    """SPEC §2.5 line 1807: "Layer Budgets: Configurable via locus.brain.context_forge.layers (Identity 80t, Temporal 60t, Events 180t, Neo4j 150t, pgvector 200t, Web 100t; Hard total limit: 800 tokens)."."""
    res = client.get("/forge/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert "budgets" in data
    budgets = data["budgets"]
    assert budgets["identity_limit"] == 80
    assert budgets["temporal_limit"] == 60
    assert budgets["events_limit"] == 180
    assert budgets["neo4j_limit"] == 150
    assert budgets["semantic_limit"] == 200
    assert budgets["web_limit"] == 100
    assert budgets["total_limit"] == 800


def test_forge_503_off_switch(client):
    """SPEC §2.5 line 1808: "Compression Fallback: If total tokens > 800, Headroom CCR is triggered on Layers 5 & 3. Layers 1 & 2 are strictly protected from pruning."."""
    config.set("locus.brain.context_forge.enabled", False)
    config.set("locus.context_forge.enabled", False)

    # Both GET /forge/config and POST /forge/assemble must return HTTP 503
    cfg_res = client.get("/forge/config")
    assert cfg_res.status_code == 503
    assert cfg_res.json() == {"disabled": "locus.brain.context_forge.enabled"}

    assemble_res = client.post("/forge/assemble", json={"retrieval_input": {}})
    assert assemble_res.status_code == 503
    assert assemble_res.json() == {"disabled": "locus.brain.context_forge.enabled"}
