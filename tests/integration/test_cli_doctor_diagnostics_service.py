"""
SPEC §8.1-8.10 lines 5485, 5598, 5606, 5655: Integration tests for CLI Doctor Diagnostics Service Endpoints (F-0031 / US-62).
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


def test_service_system_doctor(client: TestClient) -> None:
    """SPEC §8.1-8.10 line 5606: "IF data == 'locus:cmd:doctor': results = sidecar_client.get('/system/doctor')" """
    res = client.get("/system/doctor")
    assert res.status_code == 200
    data = res.json()
    assert "overall_pass" in data
    assert "checks" in data
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) >= 5


def test_service_system_reload_and_config(client: TestClient) -> None:
    """SPEC §8.1-8.10 lines 5485, 5598: Test POST /system/reload and GET/POST /system/config."""
    # 1. Reload subsystem
    res = client.post("/system/reload", json={"subsystem": "memory"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "reloaded"
    assert data["subsystem"] == "memory"

    # 2. Set config
    res2 = client.post("/system/config", json={"key": "locus.test_flag", "val": True})
    assert res2.status_code == 200
    assert res2.json()["status"] == "updated"
    assert res2.json()["key"] == "locus.test_flag"

    # 3. Get config
    res3 = client.get("/system/config?key=locus.test_flag")
    assert res3.status_code == 200
    assert res3.json()["config"] is True

    # 4. Get all config
    res4 = client.get("/system/config")
    assert res4.status_code == 200
    assert isinstance(res4.json()["config"], dict)


def test_service_system_off_switch_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §8.1-8.10 line 5444: "Off -> 503 HTTP off-switch on /system/* endpoints when locus.cli_doctor_diagnostics.enabled is False" """
    monkeypatch.setattr(
        "sidecar.config.get",
        lambda key, default=None: False if key == "locus.cli_doctor_diagnostics.enabled" else default,
    )
    monkeypatch.setattr(
        "sidecar.config.is_enabled",
        lambda key: False if key == "locus.cli_doctor_diagnostics.enabled" else True,
    )

    res_doc = client.get("/system/doctor")
    assert res_doc.status_code == 503
    assert "disabled" in res_doc.json()

    res_rel = client.post("/system/reload", json={"subsystem": "all"})
    assert res_rel.status_code == 503

    res_cfg_get = client.get("/system/config")
    assert res_cfg_get.status_code == 503

    res_cfg_post = client.post("/system/config", json={"key": "k", "val": "v"})
    assert res_cfg_post.status_code == 503
