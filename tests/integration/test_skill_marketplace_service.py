"""
SPEC §9.2 lines 6000-6056: Integration tests for Skill Marketplace Service Endpoints (F-0119 / US-63).
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


def test_service_skill_marketplace_sources_and_manifest(client: TestClient) -> None:
    """SPEC §9.2 lines 6025-6035: Verify GET /skills/marketplace/sources and GET /skills/marketplace/manifest."""
    # 1. Sources
    res_sources = client.get("/skills/marketplace/sources")
    assert res_sources.status_code == 200
    data = res_sources.json()
    assert data["status"] == "ok"
    assert "pi-gallery" in data["sources"]
    assert "anthropic" in data["sources"]

    # 2. Manifest
    res_manifest = client.get("/skills/marketplace/manifest?source=pi-gallery&skill_name=web-scraper")
    assert res_manifest.status_code == 200
    m_data = res_manifest.json()
    assert m_data["status"] == "ok"
    assert m_data["manifest"]["name"] == "web-scraper"
    assert "prerequisites" in m_data


def test_service_skill_marketplace_install_and_list(client: TestClient) -> None:
    """SPEC §9.2 lines 6024-6048: Test POST /skills/marketplace/install and GET /skills/marketplace/installed."""
    payload = {
        "source": "pi-gallery",
        "skill_name": "git-commit-helper",
    }
    res_install = client.post("/skills/marketplace/install", json=payload)
    assert res_install.status_code == 200
    inst_data = res_install.json()
    assert inst_data["success"] is True
    assert inst_data["skill_name"] == "git-commit-helper"

    # Verify listing includes installed skill
    res_list = client.get("/skills/marketplace/installed")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["status"] == "ok"
    assert any(s.get("name") == "git-commit-helper" for s in list_data["installed"])


def test_service_skill_marketplace_off_switch_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §9.2 line 6055: "Off -> 503 HTTP off-switch on /skills/marketplace/* endpoints when locus.skill_system_multi_source_marketplace.enabled is False" """
    monkeypatch.setattr(
        "sidecar.config.get",
        lambda key, default=None: False if key == "locus.skill_system_multi_source_marketplace.enabled" else default,
    )
    monkeypatch.setattr(
        "sidecar.config.is_enabled",
        lambda key: False if key == "locus.skill_system_multi_source_marketplace.enabled" else True,
    )

    res_src = client.get("/skills/marketplace/sources")
    assert res_src.status_code == 503
    assert "disabled" in res_src.json()

    res_man = client.get("/skills/marketplace/manifest?source=pi-gallery&skill_name=dummy")
    assert res_man.status_code == 503

    res_inst = client.post("/skills/marketplace/install", json={"source": "pi-gallery", "skill_name": "dummy"})
    assert res_inst.status_code == 503

    res_list = client.get("/skills/marketplace/installed")
    assert res_list.status_code == 503
