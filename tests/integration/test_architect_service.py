"""
SPEC §10.8 lines 6306-6355: Integration tests for Self-Evolving Architect Bot (F-0120 / US-66).
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_service_architect_scan(client: TestClient) -> None:
    """SPEC §10.8 line 6319: Test POST /architect/scan signal gathering and proposal."""
    payload = {
        "reward_model": [{"turn": 1, "reward": 0.25, "issue": "confusing phrasing"}],
        "life_os_metrics": {"deferral_count": 6},
    }
    res = client.post("/architect/scan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["candidates_count"] >= 1
    assert len(data["candidates"]) >= 1


def test_service_architect_candidates_and_apply(client: TestClient) -> None:
    """SPEC §10.8 lines 6319-6334: Test GET /architect/candidates and POST /architect/apply."""
    # First ensure we have candidates
    scan_res = client.post("/architect/scan", json={"life_os_metrics": {"deferral_count": 4}})
    assert scan_res.status_code == 200

    # Get candidates list
    res_list = client.get("/architect/candidates")
    assert res_list.status_code == 200
    cands = res_list.json()["candidates"]
    assert len(cands) >= 1
    cand_id = cands[0]["id"]

    # Apply candidate
    res_apply = client.post("/architect/apply", json={"candidate_id": cand_id})
    assert res_apply.status_code == 200
    apply_data = res_apply.json()
    assert apply_data["status"] == "ok"
    assert "outcome" in apply_data


def test_service_architect_history(client: TestClient) -> None:
    """SPEC §10.8 lines 6335-6337: Test GET /architect/history outcome recording."""
    res = client.get("/architect/history")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert isinstance(data["history"], list)


def test_service_architect_disabled_returns_503(client: TestClient, monkeypatch) -> None:
    """SPEC §10.8 line 6345: Test 503 response when locus.architect.enabled is False."""
    monkeypatch.setattr(config, "get", lambda k: False if k == "locus.architect.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.architect.enabled" else True)

    res_scan = client.post("/architect/scan", json={})
    assert res_scan.status_code == 503
    assert res_scan.json().get("disabled") == "locus.architect.enabled"

    res_cands = client.get("/architect/candidates")
    assert res_cands.status_code == 503

    res_apply = client.post("/architect/apply", json={"candidate_id": "any"})
    assert res_apply.status_code == 503

    res_hist = client.get("/architect/history")
    assert res_hist.status_code == 503
