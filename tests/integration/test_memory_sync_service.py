"""Integration tests for Memory Sync FastAPI service endpoints.

Tests Spec §4.7:
- GET /memory/sync/pipelines: List active ingestion pipelines.
- POST /memory/sync/tick/{pipeline_id}: Tick specific pipeline.
- POST /memory/sync/tick_all: Tick all active pipelines.
- POST /memory/sync/heal: Self-healing set difference reconciliation.
- GET /memory/sync/config: Subsystem health & metrics.
- Modular off-switch 503 behavior on locus.memory_sync_multi_source_ingestion_pipelines.enabled.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client():
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None


def test_service_list_pipelines_endpoint(client):
    """SPEC §4.7 line 856: "THREE PIPELINE KINDS: COMPOSIO PIPELINES WORKSPACE PIPELINES MCP PIPELINES"

    Asserts /memory/sync/pipelines returns registered pipelines of all three kinds.
    """
    res = client.get("/memory/sync/pipelines")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    pipelines = data["pipelines"]
    assert len(pipelines) >= 3
    kinds = {p["kind"] for p in pipelines}
    assert "workspace" in kinds
    assert "composio" in kinds
    assert "mcp" in kinds


def test_service_tick_single_and_all_endpoints(client):
    """SPEC §4.7 line 845: "async fn tick(&self, config: &Config) → Result<SyncOutcome>"

    Asserts /memory/sync/tick/{pipeline_id} and /memory/sync/tick_all operate end-to-end.
    """
    # Tick single pipeline
    res_single = client.post("/memory/sync/tick/workspace_vault")
    assert res_single.status_code == 200
    data_single = res_single.json()
    assert data_single["status"] == "ok"
    assert "records_ingested" in data_single["outcome"]

    # Tick all pipelines
    res_all = client.post("/memory/sync/tick_all")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["status"] == "ok"
    assert "workspace_vault" in data_all["outcomes"]
    assert "direct_api_github" in data_all["outcomes"]
    assert "mcp_default" in data_all["outcomes"]


def test_service_heal_source_endpoint(client):
    """SPEC §4.7 line 887: "FUNCTION check_and_rebuild_tree(source): on_disk = list_raw_files(source.raw_archive_path) uncovered = on_disk - ingested"

    Asserts /memory/sync/heal reconciles set difference and heals uncovered files.
    """
    payload = {
        "source": {
            "tree_scope": "github:test/repo",
            "raw_archive_id": "github.com/test/repo",
            "provider": "github",
        },
        "on_disk_files": ["README.md", "CONTRIBUTING.md", "LICENSE"],
    }
    res = client.post("/memory/sync/heal", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["healed_count"] == 3
    assert set(data["healed_files"]) == {"README.md", "CONTRIBUTING.md", "LICENSE"}

    # Repeated heal should show 0 uncovered
    res_repeat = client.post("/memory/sync/heal", json=payload)
    assert res_repeat.status_code == 200
    assert res_repeat.json()["healed_count"] == 0


def test_service_config_and_health_endpoint(client):
    """SPEC §4.7 line 919: "sync state + cursors in .locus/memory/sync_state.db"

    Asserts /memory/sync/config reports operational status, registered pipelines, and health.
    """
    res = client.get("/memory/sync/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert "MemorySyncManager" in data["provider"]
    assert data["health"]["status"] == "healthy"


def test_service_modular_off_switch_returns_503(client, monkeypatch):
    """SPEC §4.7 line 921: "Swappable / off state: locus.memory.sync.enabled (global) + per-pipeline toggles. Off → no automatic ingestion"

    Asserts endpoints return HTTP 503 when locus.memory_sync_multi_source_ingestion_pipelines.enabled is False.
    """
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: False
        if key in (
            "locus.memory.sync.enabled",
            "locus.memory_sync_multi_source_ingestion_pipelines.enabled",
        )
        else default,
    )

    # Config endpoint
    res_cfg = client.get("/memory/sync/config")
    assert res_cfg.status_code == 503
    assert res_cfg.json()["disabled"] == "locus.memory_sync_multi_source_ingestion_pipelines.enabled"

    # Pipelines endpoint
    res_pipes = client.get("/memory/sync/pipelines")
    assert res_pipes.status_code == 503

    # Tick single endpoint
    res_tick = client.post("/memory/sync/tick/workspace_vault")
    assert res_tick.status_code == 503

    # Tick all endpoint
    res_all = client.post("/memory/sync/tick_all")
    assert res_all.status_code == 503

    # Heal endpoint
    res_heal = client.post(
        "/memory/sync/heal",
        json={"source": {"tree_scope": "test"}, "on_disk_files": []},
    )
    assert res_heal.status_code == 503
