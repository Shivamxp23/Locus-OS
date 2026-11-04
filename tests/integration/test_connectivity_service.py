"""
Integration tests for Connectivity Check FastAPI endpoints (F-0068 / US-106).
SPEC §29.5 lines 7613-7671.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from sidecar import config
from sidecar.diagnostics.connectivity import ConnectivityChecker
from sidecar.providers.connectivity import DefaultConnectivityProvider
from sidecar.service import create_app


@pytest.fixture
def mock_checker():
    def mock_head(url: str, timeout: float):
        return 200, 14.2

    def mock_get(url: str, timeout: float):
        return 200, 8.5

    return ConnectivityChecker(http_head_fn=mock_head, http_get_fn=mock_get)


@pytest.fixture
def client(mock_checker):
    config.set("locus.connectivity_check.enabled", True)
    config.set("locus.connectivity_check.timeout", 5.0)

    app = create_app()
    # Inject mock provider with mock checker into app state
    app.state.connectivity_provider = DefaultConnectivityProvider(checker=mock_checker)

    with TestClient(app) as test_client:
        yield test_client

    config.set("locus.connectivity_check.enabled", True)


def test_connectivity_check_endpoint(client: TestClient):
    """SPEC §29.5 line 7636: "FUNCTION check_connectivity(timeout=5):" """
    # Test POST
    res_post = client.post("/connectivity/check", json={"timeout": 3.0, "force_refresh": True})
    assert res_post.status_code == 200
    data_post = res_post.json()
    assert data_post["status"] == "success"
    assert data_post["online"] is True
    assert data_post["latency_ms"] == 14.2

    # Test GET
    res_get = client.get("/connectivity/check")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert data_get["online"] is True


def test_connectivity_services_endpoint(client: TestClient):
    """SPEC §29.5 line 7647: "FUNCTION check_service_connectivity(services):" """
    payload = {
        "services": [
            {"name": "neo4j", "health_url": "http://127.0.0.1:7474"},
            {"name": "sidecar", "health_url": "http://127.0.0.1:8420/health"},
        ],
        "timeout": 2.0,
    }
    res = client.post("/connectivity/services", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "neo4j" in data["services"]
    assert data["services"]["neo4j"]["healthy"] is True


def test_connectivity_gates_endpoint(client: TestClient):
    """SPEC §29.5 line 7659: "// Used as gate before:" """
    res = client.get("/connectivity/gates")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["online"] is True
    assert data["skip_inner_loop_web"] is False
    assert data["force_local_model"] is False
    assert data["skip_vault_sync"] is False
    assert data["skip_web_search"] is False


def test_connectivity_status_endpoint(client: TestClient):
    """Diagnostic telemetry endpoint for connectivity checker subsystem."""
    res = client.get("/connectivity/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["enabled"] is True
    assert "endpoints" in data


def test_connectivity_off_switch_503(client: TestClient):
    """SPEC §29.5 line 7668: "- **Swappable / off state**: Always available (utility function). Used as a gate by Inner Loop, model escalation, and background tasks. If offline: Inner Loop skips web-dependent operations, model escalation forces local-only, web search returns empty results." """
    config.set("locus.connectivity_check.enabled", False)

    for route in ["/connectivity/check", "/connectivity/gates", "/connectivity/status"]:
        res = client.get(route)
        assert res.status_code == 503
        data = res.json()
        assert "disabled" in str(data).lower()

    res_post = client.post("/connectivity/services", json={"services": []})
    assert res_post.status_code == 503

