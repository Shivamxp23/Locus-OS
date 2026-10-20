"""
SPEC §3.12 / F-0104 / US-45: Integration Tests for Custom Locus Tools Service.
Asserts FastAPI routes `/tools/custom/list`, `/tools/custom/{tool_name}`,
`/tools/custom/execute`, `/tools/custom/{tool_name}/toggle`, `/tools/custom/config`,
and the modular 503 off-switch on locus.custom_locus_tools.enabled.
"""
from __future__ import annotations

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


def test_list_custom_tools_endpoint(client):
    """SPEC §3.12 line 2709: "See §1.3 for the 8 custom Locus tools." """
    resp = client.get("/tools/custom/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    tool_names = [t["name"] for t in data["tools"]]
    assert "locus_checkin" in tool_names
    assert "locus_memory" in tool_names
    assert "locus_delegate_code" in tool_names


def test_get_custom_tool_endpoint(client):
    """SPEC §3.12 line 2707: "- **Verdict**: 🆕 LOCUS-NEW · **Source**: Locus-unique" """
    resp = client.get("/tools/custom/locus_checkin")
    assert resp.status_code == 200
    tool = resp.json()["tool"]
    assert tool["name"] == "locus_checkin"
    assert tool["category"] == "life_os"

    resp_404 = client.get("/tools/custom/non_existent_tool_xyz")
    assert resp_404.status_code == 404


def test_execute_custom_tool_endpoint(client):
    """SPEC §3.12 line 2707: "- **Verdict**: 🆕 LOCUS-NEW · **Source**: Locus-unique" """
    resp = client.post(
        "/tools/custom/execute",
        json={
            "tool_name": "locus_checkin",
            "parameters": {
                "energy": 9.0,
                "mood": 8.0,
                "sleep_hours": 7.5,
                "stress": 2.0,
                "notes": "Testing integration endpoint",
            },
        },
    )
    assert resp.status_code == 200
    res = resp.json()["result"]
    assert res["success"] is True
    assert res["tool_name"] == "locus_checkin"
    assert res["output"]["recorded"] is True
    assert res["output"]["operating_mode"] in ("PEAK", "DEEP_WORK")


def test_toggle_custom_tool_endpoint(client):
    """SPEC §3.12 line 2708: "Individual tools toggleable via locus.tools.<name>.enabled" """
    # Disable locus_vault
    resp_toggle_off = client.post(
        "/tools/custom/locus_vault/toggle",
        json={"enabled": False},
    )
    assert resp_toggle_off.status_code == 200
    assert resp_toggle_off.json()["enabled"] is False

    # Check that locus_vault is excluded from active list
    resp_list = client.get("/tools/custom/list")
    assert resp_list.status_code == 200
    active_names = [t["name"] for t in resp_list.json()["tools"]]
    assert "locus_vault" not in active_names

    # Toggle back on
    resp_toggle_on = client.post(
        "/tools/custom/locus_vault/toggle",
        json={"enabled": True},
    )
    assert resp_toggle_on.status_code == 200
    assert resp_toggle_on.json()["enabled"] is True


def test_custom_tools_config_endpoint(client):
    """SPEC §3.12 line 2706: "## Feature §3.12: Custom Locus Tools" """
    resp = client.get("/tools/custom/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "CustomLocusToolsProvider"
    assert data["health"]["total_tools"] >= 8


def test_custom_tools_off_switch_503(client, monkeypatch):
    """SPEC §3.12 line 2708: "Swappable / off state" """
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: False if key in ("locus.custom_locus_tools.enabled", "locus.tools.custom.enabled") else default,
    )

    resp_list = client.get("/tools/custom/list")
    assert resp_list.status_code == 503
    assert resp_list.json() == {"disabled": "locus.custom_locus_tools.enabled"}

    resp_get = client.get("/tools/custom/locus_checkin")
    assert resp_get.status_code == 503

    resp_exec = client.post("/tools/custom/execute", json={"tool_name": "locus_checkin", "parameters": {}})
    assert resp_exec.status_code == 503

    resp_toggle = client.post("/tools/custom/locus_checkin/toggle", json={"enabled": False})
    assert resp_toggle.status_code == 503

    resp_cfg = client.get("/tools/custom/config")
    assert resp_cfg.status_code == 503
