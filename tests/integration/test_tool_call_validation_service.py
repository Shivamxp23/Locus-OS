"""
SPEC §3.8 / F-0100 / US-41: Integration Tests for Tool Call Validation Service.
Asserts FastAPI routes `/tools/validate`, `/tools/observe`, `/tools/reset`, `/tools/validation/config`,
and the modular 503 off-switch on locus.tool_call_validation.enabled.
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


def test_tools_validate_endpoint_valid_and_schema_error(client):
    """SPEC §3.8 line 2690: "Keep Pi's wrapper. Steal Hermes' guardrails."."""
    schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        },
        "required": ["query"],
    }

    # 1. Valid params
    resp = client.post(
        "/tools/validate",
        json={"tool_name": "search_files", "params": {"query": "test", "limit": 5}, "schema": schema},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["decision"]["action"] == "allow"
    assert data["decision"]["allows_execution"] is True

    # 2. Schema violation (missing required 'query')
    resp_err = client.post(
        "/tools/validate",
        json={"tool_name": "search_files", "params": {"limit": 5}, "schema": schema},
    )
    assert resp_err.status_code == 200
    err_data = resp_err.json()
    assert err_data["status"] == "ok"
    assert err_data["decision"]["action"] == "block"
    assert err_data["decision"]["code"] == "schema_validation_failed"
    assert err_data["decision"]["allows_execution"] is False


def test_tools_validate_missing_tool_name(client):
    """SPEC §3.8 line 2688: "Verdict: AUGMENT · Source: Pi tool-definition-wrapper.ts + Hermes tool_guardrails.py"."""
    resp = client.post("/tools/validate", json={"params": {"q": "hello"}})
    assert resp.status_code == 400
    assert "Missing required field: tool_name" in resp.json()["detail"]


def test_tools_observe_endpoint_and_failure_streak(client):
    """SPEC §3.8 line 2688: "Verdict: AUGMENT · Source: Pi tool-definition-wrapper.ts + Hermes tool_guardrails.py"."""
    tool_name = "terminal"
    params = {"cmd": "bad_failing_cmd"}

    # Simulate 4 consecutive failures
    for i in range(4):
        resp = client.post(
            "/tools/observe",
            json={"tool_name": tool_name, "params": params, "result": "Error: command not found", "failed": True},
        )
        assert resp.status_code == 200
        obs = resp.json()["observation"]
        assert obs["tool_name"] == tool_name
        assert obs["streak_count"] == i + 1

    # Now validate before next call: should be BLOCKED due to repeated exact failure
    resp_val = client.post(
        "/tools/validate",
        json={"tool_name": tool_name, "params": params},
    )
    assert resp_val.status_code == 200
    dec = resp_val.json()["decision"]
    assert dec["action"] == "block"
    assert dec["code"] == "repeated_exact_failure_block"
    assert dec["allows_execution"] is False


def test_tools_reset_endpoint(client):
    """SPEC §3.8 line 2689: "Swappable / off state: Always on (safety critical)"."""
    tool_name = "terminal"
    params = {"cmd": "faulty_command"}

    for _ in range(4):
        client.post(
            "/tools/observe",
            json={"tool_name": tool_name, "params": params, "result": "Error", "failed": True},
        )

    # Check blocked
    resp_val = client.post("/tools/validate", json={"tool_name": tool_name, "params": params})
    assert resp_val.json()["decision"]["action"] == "block"

    # Reset
    resp_reset = client.post("/tools/reset", json={})
    assert resp_reset.status_code == 200
    assert resp_reset.json()["reset"] is True

    # Validate again: allowed!
    resp_val2 = client.post("/tools/validate", json={"tool_name": tool_name, "params": params})
    assert resp_val2.json()["decision"]["action"] == "allow"


def test_tools_validation_config_endpoint(client):
    """SPEC §3.8 line 2690: "Keep Pi's wrapper. Steal Hermes' guardrails."."""
    resp = client.get("/tools/validation/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert "ToolCallValidationProvider" in data["provider"]
    assert "config" in data
    assert data["config"]["hard_stop_enabled"] is True


def test_tool_call_validation_503_off_switch(client):
    """SPEC §3.8 line 2689: "Swappable / off state: Always on (safety critical)"."""
    try:
        config.set("locus.tool_call_validation.enabled", False)

        resp1 = client.post("/tools/validate", json={"tool_name": "read_file"})
        assert resp1.status_code == 503
        assert resp1.json() == {"disabled": "locus.tool_call_validation.enabled"}

        resp2 = client.post("/tools/observe", json={"tool_name": "read_file"})
        assert resp2.status_code == 503
        assert resp2.json() == {"disabled": "locus.tool_call_validation.enabled"}

        resp3 = client.post("/tools/reset", json={})
        assert resp3.status_code == 503
        assert resp3.json() == {"disabled": "locus.tool_call_validation.enabled"}

        resp4 = client.get("/tools/validation/config")
        assert resp4.status_code == 503
        assert resp4.json() == {"disabled": "locus.tool_call_validation.enabled"}
    finally:
        config.set("locus.tool_call_validation.enabled", True)
