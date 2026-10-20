"""
SPEC §3.11 / F-0103 / US-44: Integration Tests for Tool Timeout / Budget Service.
Asserts FastAPI routes `/tools/timeout/resolve`, `/tools/timeout/record`,
`/tools/timeout/remaining`, `/tools/timeout/reset`, `/tools/timeout/config`,
and the modular 503 off-switch on locus.tool_timeout_budget.enabled.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_timeout_resolve_endpoint(client):
    """SPEC §3.11 line 2703: "Verdict: 🆕 LOCUS-NEW · Source: OpenHuman tool_timeout · Repo vs .locus: locus-os" """
    # 1. Default tool resolve
    resp = client.post(
        "/tools/timeout/resolve",
        json={"tool_name": "unknown_tool"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["resolution"]["timeout_secs"] == 120.0

    # 2. Per-tool override
    resp_bash = client.post(
        "/tools/timeout/resolve",
        json={"tool_name": "bash"},
    )
    assert resp_bash.status_code == 200
    assert resp_bash.json()["resolution"]["timeout_secs"] == 300.0


def test_timeout_record_and_remaining_endpoint(client):
    """SPEC §3.11 line 2703: "Verdict: 🆕 LOCUS-NEW · Source: OpenHuman tool_timeout · Repo vs .locus: locus-os" """
    # Reset with 100s budget
    resp_reset = client.post(
        "/tools/timeout/reset",
        json={"total_budget_secs": 100.0},
    )
    assert resp_reset.status_code == 200

    # Check remaining
    resp_rem1 = client.get("/tools/timeout/remaining")
    assert resp_rem1.status_code == 200
    assert resp_rem1.json()["remaining_turn_budget_secs"] == 100.0

    # Record 25s execution
    resp_rec = client.post(
        "/tools/timeout/record",
        json={"tool_name": "bash", "elapsed_secs": 25.0, "timed_out": False},
    )
    assert resp_rec.status_code == 200

    # Check remaining after record
    resp_rem2 = client.get("/tools/timeout/remaining")
    assert resp_rem2.status_code == 200
    assert resp_rem2.json()["remaining_turn_budget_secs"] == 75.0


def test_timeout_resolve_missing_tool_name(client):
    """SPEC §3.11 line 2703: "Verdict: 🆕 LOCUS-NEW · Source: OpenHuman tool_timeout · Repo vs .locus: locus-os" """
    resp = client.post("/tools/timeout/resolve", json={})
    assert resp.status_code == 400


def test_timeout_config_endpoint(client):
    """SPEC §3.11 line 2704: "Swappable / off state: locus.tools.timeout.enabled. Off → no per-tool timeout enforcement." """
    resp = client.get("/tools/timeout/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "ToolTimeoutBudgetProvider"
    assert "config" in data
    assert "health" in data


def test_timeout_off_switch_503(client, monkeypatch):
    """SPEC §3.11 line 2704: "Swappable / off state: locus.tools.timeout.enabled. Off → no per-tool timeout enforcement." """
    original_get = config.get

    def fake_get(key: str, default=None):
        if key == "locus.tool_timeout_budget.enabled":
            return False
        return original_get(key, default)

    monkeypatch.setattr(config, "get", fake_get)

    # 1. POST resolve returns 503
    resp_res = client.post("/tools/timeout/resolve", json={"tool_name": "bash"})
    assert resp_res.status_code == 503
    assert resp_res.json()["disabled"] == "locus.tool_timeout_budget.enabled"

    # 2. GET config returns 503
    resp_cfg = client.get("/tools/timeout/config")
    assert resp_cfg.status_code == 503


def test_tools_timeout_off_switch_503(client, monkeypatch):
    """SPEC §3.11 line 2704: "Swappable / off state: locus.tools.timeout.enabled. Off → no per-tool timeout enforcement." """
    original_get = config.get

    def fake_get(key: str, default=None):
        if key == "locus.tools.timeout.enabled":
            return False
        return original_get(key, default)

    monkeypatch.setattr(config, "get", fake_get)

    resp_res = client.post("/tools/timeout/resolve", json={"tool_name": "bash"})
    assert resp_res.status_code == 503
