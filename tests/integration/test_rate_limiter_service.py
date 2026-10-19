"""
Integration tests for Rate Limit Tracking FastAPI endpoints (SPEC §1.9 / F-0009 / US-28).
Asserts header parsing, state retrieval, display formatting, throttle checks, and 503 off-switch.
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


def test_rate_limit_parse_and_state_endpoints(client):
    """SPEC §1.9 line 2236: "FUNCTION parse_rate_limit_headers(response_headers, provider):"."""
    headers = {
        "x-ratelimit-limit-requests": "120",
        "x-ratelimit-remaining-requests": "90",
        "x-ratelimit-reset-requests": "25s",
        "x-ratelimit-limit-tokens": "50000",
        "x-ratelimit-remaining-tokens": "40000",
        "x-ratelimit-reset-tokens": "10s",
    }
    parse_res = client.post(
        "/ratelimit/parse",
        json={"headers": headers, "provider": "test-svc-prov"},
    )
    assert parse_res.status_code == 200
    parse_data = parse_res.json()
    assert parse_data["status"] == "ok"
    assert parse_data["state"]["requests_min"]["limit"] == 120
    assert parse_data["state"]["requests_min"]["remaining"] == 90
    assert parse_data["state"]["tokens_min"]["limit"] == 50000

    # Retrieve state via GET
    state_res = client.get("/ratelimit/state?provider=test-svc-prov")
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert state_data["status"] == "ok"
    assert state_data["state"]["provider"] == "test-svc-prov"
    assert state_data["state"]["requests_min"]["used"] == 30


def test_rate_limit_display_endpoint(client):
    """SPEC §1.9 line 2250: "FUNCTION format_rate_limit_display(state):"."""
    headers = {
        "x-ratelimit-limit-requests": "60",
        "x-ratelimit-remaining-requests": "45",
        "x-ratelimit-reset-requests": "15s",
        "x-ratelimit-limit-tokens": "100000",
        "x-ratelimit-remaining-tokens": "88000",
        "x-ratelimit-reset-tokens": "30s",
    }
    client.post("/ratelimit/parse", json={"headers": headers, "provider": "display-prov"})

    res = client.get("/ratelimit/display?provider=display-prov")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["has_data"] is True
    assert "RPM: 15/60 (25%)" in data["display"]
    assert "TPM: 12K/100K (12%)" in data["display"]


def test_rate_limit_throttle_check_endpoint(client):
    """SPEC §1.9 line 2260: "FUNCTION should_throttle(state, safety_margin=0.1):"."""
    now = time.time()
    # Under limit threshold (remaining 4 < 10% of 60)
    low_state = {
        "requests_min": {"limit": 60, "remaining": 4, "reset_seconds": 12.0, "captured_at": now},
        "tokens_min": {"limit": 100000, "remaining": 50000, "reset_seconds": 10.0, "captured_at": now},
    }
    res = client.post(
        "/ratelimit/throttle/check",
        json={"state": low_state, "safety_margin": 0.1},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["should_throttle"] is True
    assert data["throttle_seconds"] > 0

    # Safe state (remaining 55 > 10% of 60)
    safe_state = {
        "requests_min": {"limit": 60, "remaining": 55, "reset_seconds": 12.0, "captured_at": now},
        "tokens_min": {"limit": 100000, "remaining": 90000, "reset_seconds": 10.0, "captured_at": now},
    }
    safe_res = client.post(
        "/ratelimit/throttle/check",
        json={"state": safe_state, "safety_margin": 0.1},
    )
    assert safe_res.status_code == 200
    safe_data = safe_res.json()
    assert safe_data["should_throttle"] is False
    assert safe_data["throttle_seconds"] == 0.0


def test_rate_limit_service_503_off_switch(monkeypatch):
    """SPEC §1.9 line 2271: "Swappable / off state: locus.tracking.rate_limit.enabled. Off → rate limit headers not parsed; TUI footer shows no rate-limit status; no pre-call throttling."."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "rate_limit" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "rate_limit" in key else True)
    app = create_app()
    client = TestClient(app)

    r1 = client.post("/ratelimit/parse", json={"headers": {}})
    assert r1.status_code == 503
    assert r1.json()["disabled"] == "locus.rate_limit_tracking.enabled"

    r2 = client.get("/ratelimit/state")
    assert r2.status_code == 503

    r3 = client.post("/ratelimit/throttle/check", json={})
    assert r3.status_code == 503

    r4 = client.get("/ratelimit/display")
    assert r4.status_code == 503
