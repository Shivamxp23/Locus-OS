"""
SPEC §27.4 lines 7152-7191: Integration tests for 3-Level Tag Hierarchy endpoints (F-0123 / US-97).
Tests FastAPI endpoints under /vault/tags/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.vault.tag_manager import TagManager
from sidecar.providers.tag_manager import DefaultTagHierarchyProvider
from sidecar.service import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    manager = TagManager()
    provider = DefaultTagHierarchyProvider(manager=manager)
    app.state.tag_hierarchy_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.3_level_tag_hierarchy_semantic_indexing.enabled", True)
    config.set("locus.vault.tag_manager.enabled", True)
    yield
    config.set("locus.3_level_tag_hierarchy_semantic_indexing.enabled", True)
    config.set("locus.vault.tag_manager.enabled", True)


def test_tag_hierarchy_service_normalize_endpoint(client: TestClient) -> None:
    """SPEC §27.4: POST /vault/tags/normalize."""
    payload = {"tags": ["#coding", "#sleep", "#business"]}
    res = client.post("/vault/tags/normalize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 3
    assert "#craft/coding" in data["normalized_tags"]
    assert "#health/sleep" in data["normalized_tags"]
    assert "#leverage/business" in data["normalized_tags"]


def test_tag_hierarchy_service_validate_endpoint(client: TestClient) -> None:
    """SPEC §27.4: POST /vault/tags/validate."""
    payload = {"tag": "#craft/architecture/system-design"}
    res = client.post("/vault/tags/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["level"] == 3
    assert data["domain"] == "craft"
    assert data["category"] == "architecture"
    assert data["instance"] == "system-design"


def test_tag_hierarchy_service_index_endpoint(client: TestClient) -> None:
    """SPEC §27.4: POST /vault/tags/index."""
    payload = {
        "note_path": "02_PROJECTS/HEALTH/Running.md",
        "tags": ["#cardio", "#workout"],
    }
    res = client.post("/vault/tags/index", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["note_path"] == "02_PROJECTS/HEALTH/Running.md"
    assert data["domain_distribution"]["health"] == 2


def test_tag_hierarchy_service_status_endpoint(client: TestClient) -> None:
    """SPEC §27.4: GET /vault/tags/status."""
    res = client.get("/vault/tags/status")
    assert res.status_code == 200
    data = res.json()
    assert data["feature_enabled"] is True
    assert data["subsystem_enabled"] is True
    assert "craft" in data["valid_domains"]


def test_tag_hierarchy_service_modular_off_switches(client: TestClient) -> None:
    """SPEC §27.4: Modular off-switches returning HTTP 503."""
    config.set("locus.3_level_tag_hierarchy_semantic_indexing.enabled", False)

    res_norm = client.post("/vault/tags/normalize", json={"tags": ["#coding"]})
    assert res_norm.status_code == 503
    assert res_norm.json()["disabled"] == "locus.3_level_tag_hierarchy_semantic_indexing.enabled"

    res_val = client.post("/vault/tags/validate", json={"tag": "#coding"})
    assert res_val.status_code == 503

    res_idx = client.post("/vault/tags/index", json={"note_path": "n.md", "tags": []})
    assert res_idx.status_code == 503

    res_st = client.get("/vault/tags/status")
    assert res_st.status_code == 503
