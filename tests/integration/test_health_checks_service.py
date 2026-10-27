"""
Integration tests for Health Checks FastAPI endpoints (F-0066 / US-104).
SPEC §29.3 lines 7501-7530.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from sidecar import config
from sidecar.service import create_app


@pytest.fixture
def client():
    config.set("locus.health_checks.enabled", True)
    config.set("locus.diagnostics.health_checks.enabled", True)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config.set("locus.health_checks.enabled", True)
    config.set("locus.diagnostics.health_checks.enabled", True)


def test_diagnostics_health_all_endpoint(client: TestClient):
    """SPEC §29.3 line 7512: Health check all endpoint returns results."""
    res = client.get("/diagnostics/health/all")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "results" in data
    assert "count" in data


def test_diagnostics_health_report_endpoint(client: TestClient):
    """SPEC §29.3 line 7512: Health check report endpoint."""
    res = client.get("/diagnostics/health/report")
    assert res.status_code == 200
    data = res.json()
    assert "overall_status" in data
    assert "total_providers" in data
    assert "healthy_providers" in data


def test_diagnostics_health_status_endpoint(client: TestClient):
    """SPEC §29.3 line 7527: Health checks diagnostic status endpoint."""
    res = client.get("/diagnostics/health/status")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "default_health_checks"
    assert data["feature_enabled"] is True


def test_diagnostics_health_off_switch_503(client: TestClient):
    """SPEC §29.3 line 7527: Modular off-switch returns HTTP 503."""
    config.set("locus.health_checks.enabled", False)
    res_all = client.get("/diagnostics/health/all")
    assert res_all.status_code == 503
    assert "disabled" in res_all.json()["detail"].lower()

    res_report = client.get("/diagnostics/health/report")
    assert res_report.status_code == 503

    res_status = client.get("/diagnostics/health/status")
    assert res_status.status_code == 503
