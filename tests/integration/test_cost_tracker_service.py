"""
Integration tests for Usage / Cost Tracking FastAPI endpoints (SPEC §1.10 / F-0010 / US-29).
Asserts cost calculation, usage recording, session summary, pricing resolution/overrides, and 503 off-switch.
"""
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_cost_calculate_endpoint(client):
    """SPEC §1.10 line 2329: "FUNCTION calculate_cost(usage: CanonicalUsage, pricing: PricingEntry):"."""
    res = client.post(
        "/cost/calculate",
        json={
            "usage": {
                "input_tokens": 100000,
                "output_tokens": 20000,
                "cache_read_tokens": 50000,
            },
            "model": "claude-3-5-sonnet",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["cost"]["amount_usd"] > 0
    assert "$" in data["cost"]["label"]


def test_cost_record_and_session_endpoints(client):
    """SPEC §1.10 line 2337: "CREDITS TRACKER (session accumulator):"."""
    record_res = client.post(
        "/cost/record",
        json={
            "usage": {
                "input_tokens": 50000,
                "output_tokens": 10000,
            },
            "model": "gpt-4o",
        },
    )
    assert record_res.status_code == 200
    record_data = record_res.json()
    assert record_data["status"] == "ok"
    assert record_data["cost"]["amount_usd"] > 0
    assert "session" in record_data

    # Retrieve session summary via GET
    session_res = client.get("/cost/session")
    assert session_res.status_code == 200
    session_data = session_res.json()
    assert session_data["status"] == "ok"
    assert session_data["session"]["session_tokens"] >= 60000
    assert session_data["session"]["session_usd"] > 0
    assert "Session: $" in session_data["session"]["display"]


def test_cost_pricing_and_override_endpoints(client):
    """SPEC §1.10 line 2322: "FUNCTION resolve_pricing(provider, model, base_url):"."""
    # Resolve official pricing
    p_res = client.get("/cost/pricing?model=gpt-4o-mini")
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert p_data["status"] == "ok"
    assert p_data["pricing"]["input_cost_per_million"] == 0.15
    assert p_data["pricing"]["source"] == "official_docs_snapshot"

    # Set custom override
    override_res = client.post(
        "/cost/pricing/override",
        json={
            "model": "custom-override-llm",
            "pricing": {
                "input_cost_per_million": 5.50,
                "output_cost_per_million": 22.00,
            },
        },
    )
    assert override_res.status_code == 200
    override_data = override_res.json()
    assert override_data["status"] == "ok"

    # Verify custom override takes effect
    check_res = client.get("/cost/pricing?model=custom-override-llm")
    assert check_res.status_code == 200
    assert check_res.json()["pricing"]["input_cost_per_million"] == 5.50
    assert check_res.json()["pricing"]["source"] == "user_override"


def test_cost_tracker_service_503_off_switch(monkeypatch):
    """SPEC §1.10 line 2354: "Swappable / off state: locus.tracking.cost.enabled. Off → no cost calculation; footer shows token counts only without dollar amounts."."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "usage_cost" in key or "cost" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "usage_cost" in key or "cost" in key else True)
    app = create_app()
    client = TestClient(app)

    r1 = client.post("/cost/calculate", json={})
    assert r1.status_code == 503
    assert r1.json()["disabled"] == "locus.usage_cost_tracking.enabled"

    r2 = client.post("/cost/record", json={})
    assert r2.status_code == 503

    r3 = client.get("/cost/session")
    assert r3.status_code == 503

    r4 = client.get("/cost/pricing?model=gpt-4o")
    assert r4.status_code == 503

    r5 = client.post("/cost/pricing/override", json={"model": "gpt-4o"})
    assert r5.status_code == 503
