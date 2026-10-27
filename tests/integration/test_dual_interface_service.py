"""
SPEC §28.1-28.6 lines 7380-7432: Integration tests for Dual Interface, Check-ins, and Budget endpoints (F-0064 / US-101).
Tests FastAPI endpoints under /gateway/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.gateway.dual_interface import DualInterfaceEngine
from sidecar.providers.dual_interface import DefaultDualInterfaceProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    engine = DualInterfaceEngine(daily_budget_usd=0.05)
    provider = DefaultDualInterfaceProvider(engine=engine)
    app.state.dual_interface_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.dual_interface_checkins.enabled", True)
    config.set("locus.gateway.dual_interface.enabled", True)
    yield
    config.set("locus.dual_interface_checkins.enabled", True)
    config.set("locus.gateway.dual_interface.enabled", True)


def test_dual_interface_message_endpoint(client: TestClient) -> None:
    """SPEC §28.1: POST /gateway/interface/message."""
    payload = {
        "channel": "telegram",
        "session_id": "integration-sess-1",
        "content": "Check-in from integration test",
        "sender": "user",
    }
    res = client.post("/gateway/interface/message", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "BRIDGED"
    assert data["session_id"] == "integration-sess-1"
    assert data["total_messages"] == 1


def test_dual_interface_checkin_keyboard_endpoint(client: TestClient) -> None:
    """SPEC §28.2: GET /gateway/checkin/keyboard."""
    res = client.get("/gateway/checkin/keyboard?slot=07:30_MORNING")
    assert res.status_code == 200
    data = res.json()
    assert data["slot"] == "07:30_MORNING"
    assert len(data["keyboard"]) >= 3


def test_dual_interface_checkin_submit_endpoint(client: TestClient) -> None:
    """SPEC §28.2: POST /gateway/checkin/submit."""
    payload = {
        "slot": "07:30_MORNING",
        "energy": 8.5,
        "stress": 2.0,
        "mood": 0.7,
        "readiness": "All systems go",
        "notes": "Testing integration checkin endpoint",
    }
    res = client.post("/gateway/checkin/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["slot"] == "07:30_MORNING"
    assert data["operating_mode"] == "FLOW"
    assert data["dcs_score"] > 8.0


def test_dual_interface_cost_budget_endpoint(client: TestClient) -> None:
    """SPEC §28.3: GET /gateway/cost/budget."""
    res = client.get("/gateway/cost/budget")
    assert res.status_code == 200
    data = res.json()
    assert "daily_tokens" in data
    assert "daily_cost_usd" in data
    assert "daily_budget_usd" in data
    assert "skip_inner_loop_recommended" in data


def test_dual_interface_status_endpoint(client: TestClient) -> None:
    """SPEC §28.1-28.6: GET /gateway/interface/status."""
    res = client.get("/gateway/interface/status")
    assert res.status_code == 200
    data = res.json()
    assert data["subsystem_enabled"] is True
    assert data["provider_enabled"] is True


def test_dual_interface_off_switch_503(client: TestClient) -> None:
    """Master toggle locus.dual_interface_checkins.enabled returns 503."""
    config.set("locus.dual_interface_checkins.enabled", False)

    res_msg = client.post("/gateway/interface/message", json={"channel": "tui", "session_id": "s", "content": "c"})
    assert res_msg.status_code == 503

    res_kb = client.get("/gateway/checkin/keyboard")
    assert res_kb.status_code == 503

    res_sub = client.post("/gateway/checkin/submit", json={"slot": "07:30_MORNING"})
    assert res_sub.status_code == 503

    res_bgt = client.get("/gateway/cost/budget")
    assert res_bgt.status_code == 503

    res_st = client.get("/gateway/interface/status")
    assert res_st.status_code == 503
