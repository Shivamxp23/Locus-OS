"""
SPEC §9.4 lines 6057-6142: Integration tests for ACP Protocol Service Endpoints (F-0033 / US-64).
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


def test_service_acp_initialize(client: TestClient) -> None:
    """SPEC §9.4 lines 6071-6088: Test POST /protocols/acp/initialize."""
    payload = {
        "client_info": {
            "name": "integration-test-harness",
            "version": "1.0.0",
        }
    }
    res = client.post("/protocols/acp/initialize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "result" in data
    result = data["result"]
    assert result["protocolVersion"] == "1.0"
    assert result["capabilities"]["tools"] is True
    assert "sessionId" in result


def test_service_acp_execute_and_cancel(client: TestClient) -> None:
    """SPEC §9.4 lines 6090-6119: Test POST /protocols/acp/execute and POST /protocols/acp/cancel."""
    exec_payload = {
        "target_agent_id": "copilot-agent",
        "prompt": "Refactor database query",
        "tools": ["sql_lint", "explain"],
    }
    res_exec = client.post("/protocols/acp/execute", json=exec_payload)
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert exec_data["status"] == "completed"
    assert exec_data["target"] == "copilot-agent"
    assert len(exec_data["events"]) >= 2

    # Cancel request
    cancel_payload = {"request_id": 101}
    res_cancel = client.post("/protocols/acp/cancel", json=cancel_payload)
    assert res_cancel.status_code == 200
    cancel_data = res_cancel.json()
    assert cancel_data["method"] == "$/cancelRequest"


def test_service_acp_off_switch_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §9.4 line 6138: "Off -> 503 HTTP off-switch on /protocols/acp/* endpoints when locus.acp_protocol.enabled is False" """
    monkeypatch.setattr(
        "sidecar.config.get",
        lambda key, default=None: False if key == "locus.acp_protocol.enabled" else default,
    )
    monkeypatch.setattr(
        "sidecar.config.is_enabled",
        lambda key: False if key == "locus.acp_protocol.enabled" else True,
    )

    res_init = client.post("/protocols/acp/initialize", json={})
    assert res_init.status_code == 503
    assert "disabled" in res_init.json()

    res_exec = client.post("/protocols/acp/execute", json={"target_agent_id": "a", "prompt": "p"})
    assert res_exec.status_code == 503

    res_cancel = client.post("/protocols/acp/cancel", json={"request_id": 1})
    assert res_cancel.status_code == 503
