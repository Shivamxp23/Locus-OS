"""
Integration tests for Tool System service routes (SPEC §1.3, F-0003, US-22).
Verifies /tools/list, /tools/execute, and the 503 off-switch.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from sidecar import config
from sidecar.registry import ProviderRegistry
from sidecar.service import create_app
from sidecar.tool_system import ToolSystemProvider


@pytest.fixture
def test_app():
    reg = ProviderRegistry()
    reg.register("tool_system", "default_tool_system", ToolSystemProvider)
    app = create_app(registry=reg)
    return app


def test_tool_system_service_list_tools(test_app):
    """SPEC §1.3 line 464: Test /tools/list returns registered canonical tools."""
    client = TestClient(test_app)
    resp = client.get("/tools/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["count"] == 13
    tool_names = [t["name"] for t in data["tools"]]
    assert "locus_checkin" in tool_names
    assert "locus_vault" in tool_names
    assert "locus_memory" in tool_names


def test_tool_system_service_execute_tool(test_app):
    """SPEC §1.3 line 451: Test /tools/execute runs a tool and returns AgentToolResult."""
    client = TestClient(test_app)
    payload = {
        "tool": "locus_vault",
        "params": {
            "action": "read",
            "path": "00-System/Goals.md",
        },
    }
    resp = client.post("/tools/execute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "result" in data
    assert not data["result"]["isError"]


def test_tool_system_modular_off_switch_503(monkeypatch, test_app):
    """SPEC §1.3 acceptance criteria: Modular off-switch locus.tool_system_13_canonical_tools.enabled returns 503."""
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "tool_system" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "tool_system" in key else True)
    client = TestClient(test_app)

    # Test /tools/list 503
    resp_list = client.get("/tools/list")
    assert resp_list.status_code == 503
    assert resp_list.json() == {"disabled": "locus.tool_system_13_canonical_tools.enabled"}

    # Test /tools/execute 503
    resp_exec = client.post("/tools/execute", json={"tool": "locus_checkin", "params": {}})
    assert resp_exec.status_code == 503
    assert resp_exec.json() == {"disabled": "locus.tool_system_13_canonical_tools.enabled"}
