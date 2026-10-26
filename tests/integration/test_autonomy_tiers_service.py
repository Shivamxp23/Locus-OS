"""
SPEC §13.4 lines 3308-3332: Integration tests for Autonomy Tiers (F-0108 / US-70).
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


def test_service_autonomy_get_and_set_tier(client: TestClient) -> None:
    """SPEC §13.4 line 3328: Test GET and POST /security/autonomy/tier."""
    res_get = client.get("/security/autonomy/tier")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["status"] == "ok"
    assert "tier" in data

    res_set = client.post("/security/autonomy/tier", json={"tier": "readonly"})
    assert res_set.status_code == 200
    assert res_set.json()["tier"] == "readonly"

    res_check = client.get("/security/autonomy/tier")
    assert res_check.json()["tier"] == "readonly"


def test_service_autonomy_evaluate(client: TestClient) -> None:
    """SPEC §13.4 line 3327: Test POST /security/autonomy/evaluate."""
    # Under readonly tier
    client.post("/security/autonomy/tier", json={"tier": "readonly"})

    # Read tool allowed
    res_read = client.post("/security/autonomy/evaluate", json={"tool_name": "read_file"})
    assert res_read.status_code == 200
    assert res_read.json()["decision"]["allowed"] is True

    # Write tool blocked
    res_write = client.post("/security/autonomy/evaluate", json={"tool_name": "write_file"})
    assert res_write.status_code == 200
    assert res_write.json()["decision"]["allowed"] is False
    assert res_write.json()["decision"]["requires_approval"] is False

    # Under supervised tier
    client.post("/security/autonomy/tier", json={"tier": "supervised"})

    # Write tool without approval -> requires approval
    res_sup_unapproved = client.post("/security/autonomy/evaluate", json={"tool_name": "write_file", "has_approval": False})
    assert res_sup_unapproved.status_code == 200
    assert res_sup_unapproved.json()["decision"]["allowed"] is False
    assert res_sup_unapproved.json()["decision"]["requires_approval"] is True

    # Write tool with approval -> allowed
    res_sup_approved = client.post("/security/autonomy/evaluate", json={"tool_name": "write_file", "has_approval": True})
    assert res_sup_approved.status_code == 200
    assert res_sup_approved.json()["decision"]["allowed"] is True

    # Under full tier
    client.post("/security/autonomy/tier", json={"tier": "full"})
    res_full = client.post("/security/autonomy/evaluate", json={"tool_name": "run_command", "has_approval": False})
    assert res_full.status_code == 200
    assert res_full.json()["decision"]["allowed"] is True


def test_service_autonomy_classify(client: TestClient) -> None:
    """SPEC §13.4 line 3327: Test POST /security/autonomy/classify."""
    res = client.post("/security/autonomy/classify", json={"tool_name": "run_command"})
    assert res.status_code == 200
    assert res.json()["category"] == "terminal"

    res_custom = client.post("/security/autonomy/classify", json={"tool_name": "custom_probe", "category": "read"})
    assert res_custom.status_code == 200
    assert res_custom.json()["category"] == "read"


def test_service_autonomy_tiers_list(client: TestClient) -> None:
    """SPEC §13.4 line 3320: Test GET /security/autonomy/tiers."""
    res = client.get("/security/autonomy/tiers")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert len(data["tiers"]) == 3
    tier_names = [t["tier"] for t in data["tiers"]]
    assert "readonly" in tier_names
    assert "supervised" in tier_names
    assert "full" in tier_names


def test_service_autonomy_tiers_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §13.4 line 3329: Modular off-switches return 503."""
    # Off-switch 1: locus.autonomy_tiers.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.autonomy_tiers.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.autonomy_tiers.enabled" else True)

    res_g = client.get("/security/autonomy/tier")
    assert res_g.status_code == 503
    assert res_g.json()["disabled"] == "locus.autonomy_tiers.enabled"

    res_s = client.post("/security/autonomy/tier", json={"tier": "full"})
    assert res_s.status_code == 503

    res_e = client.post("/security/autonomy/evaluate", json={"tool_name": "read_file"})
    assert res_e.status_code == 503

    res_c = client.post("/security/autonomy/classify", json={"tool_name": "read_file"})
    assert res_c.status_code == 503

    res_t = client.get("/security/autonomy/tiers")
    assert res_t.status_code == 503

    # Off-switch 2: locus.security.autonomy_tiers.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.autonomy_tiers.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.autonomy_tiers.enabled" else True)

    res2 = client.get("/security/autonomy/tier")
    assert res2.status_code == 503
