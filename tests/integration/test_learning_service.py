"""
Integration tests for Learning / Profiling / Reward Model FastAPI endpoints (SPEC §1.7, §10.1, §10.3, §10.5, §10.6-10.7, F-0035 / US-27).
Asserts candidate recording, stability check, profile retrieval, tool tracking,
reward scoring, Hebbian edge weight updates, pattern detection, and 503 off-switch.
"""
import time
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_learning_candidate_and_stability_endpoints(client):
    """SPEC §10.3 line 2943: "FUNCTION check_stability():"."""
    now = time.time()
    for _ in range(3):
        res = client.post(
            "/learning/candidate",
            json={
                "facet_class": "code_style",
                "cue_family": "explicit_ask",
                "evidence": {"snippet": "always use pytest"},
                "value": "always use pytest",
                "timestamp": now,
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    # Check stability
    stab_res = client.post("/learning/stability/check", json={"window_seconds": 3600, "threshold": 0.6})
    assert stab_res.status_code == 200
    stab_data = stab_res.json()
    assert stab_data["status"] == "ok"
    assert len(stab_data["stabilized"]) >= 1


def test_user_profile_endpoint(client):
    """SPEC §10.3 line 2971: "FUNCTION generate_profile():"."""
    res = client.get("/learning/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "# Locus User Profile" in data["profile"]


def test_tool_usage_tracking_endpoint(client):
    """SPEC §10.3 line 2959: "FUNCTION on_tool_call(tool_name, args, result, duration):"."""
    res = client.post(
        "/learning/tool-usage",
        json={
            "tool_name": "locus_memory",
            "args": {"action": "query", "key": "preferences"},
            "success": True,
            "duration_ms": 15.2,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["record"]["tool_name"] == "locus_memory"
    assert len(data["record"]["args_hash"]) == 16


def test_reward_signal_and_scoring_endpoints(client):
    """SPEC §10.5 line 6234: "THRESHOLD: ≥ 0.6 for proactive output delivery"."""
    sig_res = client.post(
        "/learning/reward/signal",
        json={"features": {"dcs_at_response": 88.0}, "label": 1},
    )
    assert sig_res.status_code == 200
    assert sig_res.json()["status"] == "ok"

    score_res = client.post(
        "/learning/reward/score",
        json={
            "features": {
                "dcs_at_response": 85.0,
                "confidence": 0.9,
                "was_proactive": True,
                "context_forge_tokens_used": 400,
            }
        },
    )
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert score_data["status"] == "ok"
    assert score_data["probability"] >= 0.60
    assert score_data["deliver_proactive"] is True


def test_hebbian_update_endpoint(client):
    """SPEC §10.6 line 6255: "edge.weight += 0.1  // access reinforcement"."""
    res = client.post(
        "/learning/hebbian/update",
        json={"edge_id": "service-test-edge", "feedback": "positive"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["edge_id"] == "service-test-edge"
    assert data["weight"] > 1.0


def test_patterns_endpoint(client):
    """SPEC §10.7 line 6281: "MULTI-HORIZON PATTERN ENGINE (5 horizons):"."""
    res = client.get("/learning/patterns")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert isinstance(data["patterns"], list)


def test_learning_off_switch_503(monkeypatch):
    """SPEC §10.1 line 2863: "skip_memory = true,   // don't recursively trigger memory writes"."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "learning_profiling_reward_model" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "learning_profiling_reward_model" in key else True)
    app = create_app()
    client = TestClient(app)

    r1 = client.post("/learning/candidate", json={})
    assert r1.status_code == 503
    assert r1.json() == {"disabled": "locus.learning_profiling_reward_model.enabled"}

    r2 = client.post("/learning/stability/check", json={})
    assert r2.status_code == 503

    r3 = client.get("/learning/profile")
    assert r3.status_code == 503

    r4 = client.post("/learning/tool-usage", json={})
    assert r4.status_code == 503

    r5 = client.post("/learning/reward/signal", json={})
    assert r5.status_code == 503

    r6 = client.post("/learning/reward/score", json={})
    assert r6.status_code == 503

    r7 = client.post("/learning/hebbian/update", json={"edge_id": "e1"})
    assert r7.status_code == 503

    r8 = client.get("/learning/patterns")
    assert r8.status_code == 503
