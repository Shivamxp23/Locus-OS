"""
tests/integration/test_stdp_reinforcement_service.py
Integration tests for STDP Reinforcement FastAPI service endpoints per SPEC §4.12 / F-0023.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    orig_get = config.get

    def _cfg_get(key: str, default=None):
        if key == "locus.memory.stdp.db_path":
            return tmp.name
        return orig_get(key, default)

    monkeypatch.setattr(config, "get", _cfg_get)
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None
    try:
        Path(tmp.name).unlink(missing_ok=True)
    except Exception:
        pass


def test_service_stdp_config(client: TestClient) -> None:
    """
    SPEC §4.12 line 1265: "A_plus = 0.15 // Max potentiation"
    Asserts config endpoint returns status ok and enabled configuration.
    """
    res = client.get("/memory/stdp/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["config"]["enabled"] is True
    assert data["config"]["a_plus"] == 0.15
    assert data["config"]["w_min"] == 0.05
    assert data["config"]["w_max"] == 1.00


def test_service_stdp_update(client: TestClient) -> None:
    """
    SPEC §4.12 line 1286: "FUNCTION apply_stdp_update(retrieval, outcome, current_weight) -> float:"
    Asserts HTTP endpoint computes LTP and LTD updates.
    """
    # Success outcome (LTP)
    res_ltp = client.post(
        "/memory/stdp/update",
        json={
            "retrieval": {"node_id": "n1", "edge_id": "e1", "retrieved_at": 1000.0},
            "outcome": {"session_id": "s1", "turn_id": "t1", "success": True, "occurred_at": 1050.0},
            "current_weight": 0.50,
        },
    )
    assert res_ltp.status_code == 200
    w_ltp = res_ltp.json()["updated_weight"]
    assert w_ltp > 0.50

    # Failure outcome (LTD)
    res_ltd = client.post(
        "/memory/stdp/update",
        json={
            "retrieval": {"node_id": "n1", "edge_id": "e1", "retrieved_at": 1000.0},
            "outcome": {"session_id": "s1", "turn_id": "t1", "success": False, "occurred_at": 1050.0},
            "current_weight": 0.50,
        },
    )
    assert res_ltd.status_code == 200
    w_ltd = res_ltd.json()["updated_weight"]
    assert w_ltd < 0.50


def test_service_edge_weights_and_pruning(client: TestClient) -> None:
    """
    SPEC §4.12 line 1313: "IF updated_w <= PRUNE_THRESHOLD: neo4j.tag_edge_for_pruning(edge.id, reason='STDP_DEPLETION')"
    Asserts edge weight retrieval, setting, and prune candidates inspection.
    """
    # Default weight
    res_default = client.get("/memory/stdp/weights/test_edge_123")
    assert res_default.status_code == 200
    assert res_default.json()["weight"] == 0.50

    # Set custom weight
    res_set = client.post("/memory/stdp/weights/test_edge_123", json={"weight": 0.06})
    assert res_set.status_code == 200
    assert res_set.json()["weight"] == 0.06

    # Verify prune candidate
    res_prune = client.get("/memory/stdp/prune_candidates")
    assert res_prune.status_code == 200
    candidate_ids = [c["edge_id"] for c in res_prune.json()["candidates"]]
    assert "test_edge_123" in candidate_ids


def test_service_process_turn_batch(client: TestClient) -> None:
    """
    SPEC §4.12 line 1307: "FUNCTION process_turn_stdp(turn_audit_log):"
    Asserts batch reinforcement cycle endpoint.
    """
    turn_payload = {
        "session_id": "sess_int",
        "turn_id": "turn_int",
        "traversed_edges": [
            {
                "edge_id": "edge_a",
                "retrieval_event": {"node_id": "n_a", "edge_id": "edge_a", "retrieved_at": 2000.0},
                "initial_weight": 0.50,
            },
            {
                "edge_id": "edge_b",
                "retrieval_event": {"node_id": "n_b", "edge_id": "edge_b", "retrieved_at": 2000.0},
                "initial_weight": 0.10,
            },
        ],
        "outcome": {
            "session_id": "sess_int",
            "turn_id": "turn_int",
            "success": False,
            "occurred_at": 2010.0,
        },
    }

    res = client.post("/memory/stdp/process_turn", json=turn_payload)
    assert res.status_code == 200
    data = res.json()["result"]
    assert data["session_id"] == "sess_int"
    assert len(data["updated_edges"]) == 2
    assert "edge_b" in data["pruned_tags"]


def test_service_off_switch_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    SPEC §4.12 line 1321: "Swappable / off state: locus.memory.stdp.enabled. Off -> Neo4j edge weights remain static; traversal uses unweighted paths."
    Asserts endpoints return 503 when off switch is disabled.
    """
    orig_get = config.get

    def _disabled_get(key: str, default=None):
        if key in ("locus.stdp_reinforcement.enabled", "locus.memory.stdp.enabled"):
            return False
        return orig_get(key, default)

    monkeypatch.setattr(config, "get", _disabled_get)
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        res = test_client.get("/memory/stdp/config")
        assert res.status_code == 503
        assert res.json() == {"disabled": "locus.stdp_reinforcement.enabled"}

        post_res = test_client.post("/memory/stdp/update", json={})
        assert post_res.status_code == 503
        assert post_res.json() == {"disabled": "locus.stdp_reinforcement.enabled"}
