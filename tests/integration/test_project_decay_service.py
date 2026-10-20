"""
SPEC §4.14: Project Memory Decay Integration Tests.
Validates FastAPI sidecar endpoints for calculating retention strengths, registering projects and nodes,
executing nightly sweeps, reading cold archives, and the modular off-switch (503).
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sidecar.memory.project_decay import ProjectDecayEngine
from sidecar.providers.project_memory_decay import (
    DefaultProjectMemoryDecayProvider,
    ProjectDecayConfig,
)
from sidecar.service import create_app


@pytest.fixture
def client_and_provider() -> Generator[tuple[TestClient, DefaultProjectMemoryDecayProvider, str], None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = ProjectDecayConfig(storage_dir=tmpdir)
        provider = DefaultProjectMemoryDecayProvider(config=cfg)
        app = create_app()
        app.state.registry.register("project_memory_decay", "default", lambda **kw: provider)
        app.state.registry.register("memory_decay", "default", lambda **kw: provider)
        client = TestClient(app)
        yield client, provider, tmpdir


def test_service_decay_config(client_and_provider: tuple[TestClient, DefaultProjectMemoryDecayProvider, str]) -> None:
    """SPEC §4.14 line 1472: "Swappable / off state: locus.memory.decay.enabled. Off -> memory nodes never decay"."""
    client, _, _ = client_and_provider
    res = client.get("/memory/decay/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["config"]["cold_storage_threshold"] == 0.10
    assert data["config"]["half_life_days"]["ACTIVE"] == 90.0
    assert data["config"]["half_life_days"]["ARCHIVED"] == 7.0


def test_service_decay_calculate(client_and_provider: tuple[TestClient, DefaultProjectMemoryDecayProvider, str]) -> None:
    """SPEC §4.14 line 1439: "FUNCTION calculate_retention_strength(project_state: string, days_since_last_touch: float) -> float"."""
    client, _, _ = client_and_provider
    # Active touched 90 days ago -> 0.50
    res = client.post("/memory/decay/calculate", json={"project_state": "ACTIVE", "days_since_last_touch": 90.0})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["retention_strength"] == pytest.approx(0.50, rel=1e-3)
    assert data["cold_archive_candidate"] is False

    # Archived touched 30 days ago -> 2^(-30/7) < 0.10 -> candidate
    res_arch = client.post("/memory/decay/calculate", json={"project_state": "ARCHIVED", "days_since_last_touch": 30.0})
    assert res_arch.status_code == 200
    data_arch = res_arch.json()
    assert data_arch["cold_archive_candidate"] is True
    assert data_arch["retention_strength"] < 0.10


def test_service_decay_projects_and_sweep(client_and_provider: tuple[TestClient, DefaultProjectMemoryDecayProvider, str]) -> None:
    """SPEC §4.14 lines 1445-1466: "NIGHTLY PROJECT DECAY SWEEP (03:00 IST): FUNCTION sweep_project_memories():"."""
    client, _, tmpdir = client_and_provider
    t0 = 2000000.0

    # Register an active project
    p1 = {
        "project_id": "proj_phoenix",
        "name": "Project Phoenix",
        "status": "ACTIVE",
        "last_touched_at": t0 - (5 * 86400),
        "nodes": [
            {"node_id": "phoenix:task1", "content": "Phase 1 specs"},
            {"node_id": "phoenix:task2", "content": "Architecture doc"},
        ],
    }
    res1 = client.post("/memory/decay/projects", json=p1)
    assert res1.status_code == 200
    assert res1.json()["node_count"] == 2

    # Register an archived project ready for cold storage
    p2 = {
        "project_id": "proj_legacy",
        "name": "Legacy System",
        "status": "ARCHIVED",
        "last_touched_at": t0 - (35 * 86400),
        "nodes": [
            {"node_id": "legacy:n1", "content": "Deprecated schema"},
            {"node_id": "legacy:n2", "content": "Old config dump"},
        ],
    }
    res2 = client.post("/memory/decay/projects", json=p2)
    assert res2.status_code == 200
    assert res2.json()["node_count"] == 2

    # Run sweep
    sweep_res = client.post("/memory/decay/sweep", json={"timestamp": t0})
    assert sweep_res.status_code == 200
    res_data = sweep_res.json()["result"]
    assert res_data["projects_evaluated"] == 2
    assert "proj_legacy" in res_data["projects_archived"]
    assert res_data["nodes_archived"] == 2

    # List archives
    archives_res = client.get("/memory/decay/archives")
    assert archives_res.status_code == 200
    archives = archives_res.json()["archives"]
    assert len(archives) == 1
    assert archives[0]["project_id"] == "proj_legacy"

    # Get specific archive
    arch_detail = client.get("/memory/decay/archives/proj_legacy")
    assert arch_detail.status_code == 200
    detail_data = arch_detail.json()["archive"]
    assert detail_data["node_count"] == 2
    assert detail_data["project_id"] == "proj_legacy"


def test_service_decay_modular_off_switch() -> None:
    """SPEC §4.14 line 1472: "Registers as a provider in sidecar/providers/ with modular off-switch locus.project_memory_decay.enabled returning 503"."""
    app = create_app()
    client = TestClient(app)

    with patch("sidecar.config.get", return_value=False):
        res1 = client.get("/memory/decay/config")
        assert res1.status_code == 503
        assert res1.json() == {"disabled": "locus.project_memory_decay.enabled"}

        res2 = client.post("/memory/decay/calculate", json={"project_state": "ACTIVE"})
        assert res2.status_code == 503
        assert res2.json() == {"disabled": "locus.project_memory_decay.enabled"}

        res3 = client.post("/memory/decay/projects", json={"project_id": "p1"})
        assert res3.status_code == 503
        assert res3.json() == {"disabled": "locus.project_memory_decay.enabled"}

        res4 = client.post("/memory/decay/sweep", json={})
        assert res4.status_code == 503
        assert res4.json() == {"disabled": "locus.project_memory_decay.enabled"}

        res5 = client.get("/memory/decay/archives")
        assert res5.status_code == 503
        assert res5.json() == {"disabled": "locus.project_memory_decay.enabled"}
