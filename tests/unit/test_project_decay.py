"""
SPEC §4.14: Unit tests for Project-Specific Memory Decay Engine & Cold Archiver.
Validates exponential decay calculations, lifecycle half-life tables, cold storage thresholds,
sweep mechanics, gzip JSONL cold archival, modular off-switch, provider swapping, and health checks.
"""
from __future__ import annotations

import gzip
import json
import math
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from sidecar import config, registry
from sidecar.memory.cold_archiver import (
    archive_cluster_to_cold_storage,
    get_cold_archive_dir,
    get_cold_archive_path,
    list_cold_archives,
    load_cold_archive,
)
from sidecar.memory.project_decay import (
    COLD_STORAGE_THRESHOLD,
    DEFAULT_HALF_LIFE,
    HALF_LIFE_DAYS,
    ProjectDecayEngine,
    ProjectNode,
    ProjectRecord,
    calculate_retention_strength,
)
from sidecar.providers.project_memory_decay import (
    BaseMemoryDecayProvider,
    DefaultProjectMemoryDecayProvider,
    MemoryDecayProvider,
    ProjectDecayConfig,
    ProjectMemoryDecayProvider,
)


def test_half_life_parameters():
    """SPEC §4.14 line 1430: "LIFECYCLE HALF-LIFE PARAMETERS: HALF_LIFE_DAYS = {"ACTIVE": 90.0, "MAINTENANCE": 45.0, "PAUSED": 30.0, "ABANDONED": 14.0, "ARCHIVED": 7.0}"."""
    assert HALF_LIFE_DAYS["ACTIVE"] == 90.0
    assert HALF_LIFE_DAYS["MAINTENANCE"] == 45.0
    assert HALF_LIFE_DAYS["PAUSED"] == 30.0
    assert HALF_LIFE_DAYS["ABANDONED"] == 14.0
    assert HALF_LIFE_DAYS["ARCHIVED"] == 7.0
    assert DEFAULT_HALF_LIFE == 30.0
    assert COLD_STORAGE_THRESHOLD == 0.10


def test_calculate_retention_strength_exact():
    """SPEC §4.14 line 1441: "// Exponential half-life decay formula: S(t) = S_0 * 2^(-t / T_1/2)"."""
    # At t=0, retention strength is 1.0 (s_0)
    assert calculate_retention_strength("ACTIVE", 0.0) == pytest.approx(1.0)
    assert calculate_retention_strength("ARCHIVED", 0.0) == pytest.approx(1.0)

    # At t=half_life, retention strength should be exactly 0.50
    assert calculate_retention_strength("ACTIVE", 90.0) == pytest.approx(0.50, rel=1e-4)
    assert calculate_retention_strength("MAINTENANCE", 45.0) == pytest.approx(0.50, rel=1e-4)
    assert calculate_retention_strength("PAUSED", 30.0) == pytest.approx(0.50, rel=1e-4)
    assert calculate_retention_strength("ABANDONED", 14.0) == pytest.approx(0.50, rel=1e-4)
    assert calculate_retention_strength("ARCHIVED", 7.0) == pytest.approx(0.50, rel=1e-4)

    # At t=2*half_life, retention strength should be 0.25
    assert calculate_retention_strength("ACTIVE", 180.0) == pytest.approx(0.25, rel=1e-4)
    assert calculate_retention_strength("ARCHIVED", 14.0) == pytest.approx(0.25, rel=1e-4)

    # Fallback to default 30.0 days for unknown lifecycle state
    assert calculate_retention_strength("UNKNOWN_STATE", 30.0) == pytest.approx(0.50, rel=1e-4)


def test_retention_strength_bounds_and_clamping():
    """SPEC §4.14 line 1442: "strength = 1.0 * (2.0 ** (-days_since_last_touch / half_life))"."""
    # Negative days clamped to 0 -> strength = 1.0
    assert calculate_retention_strength("ACTIVE", -10.0) == 1.0

    # Very large days approaches 0.0, bounded above 0.0
    s_far = calculate_retention_strength("ARCHIVED", 1000.0)
    assert 0.0 <= s_far < 0.0001

    # Custom initial strength s_0
    assert calculate_retention_strength("ACTIVE", 90.0, s_0=2.0) == pytest.approx(1.0)


def test_cold_storage_threshold_trigger():
    """SPEC §4.14 line 1437: "COLD_STORAGE_THRESHOLD = 0.10 // Retention strength S(t) < 0.10 triggers cold archive"."""
    # For ARCHIVED (half_life=7): 2^(-t/7) < 0.10 => -t/7 < log2(0.10) => t > -7 * (-3.3219) ~ 23.25 days
    assert calculate_retention_strength("ARCHIVED", 20.0) > COLD_STORAGE_THRESHOLD
    assert calculate_retention_strength("ARCHIVED", 25.0) < COLD_STORAGE_THRESHOLD


def test_cold_archiver_roundtrip(tmp_path):
    """SPEC §4.14 line 1471: "cold archived memory clusters compressed in .locus/memory/cold_archive/{project_id}.jsonl.gz"."""
    nodes = [
        {"node_id": "node_1", "project_id": "proj_alpha", "content": "Initial architecture proposal"},
        {"node_id": "node_2", "project_id": "proj_alpha", "content": "Database migration script"},
    ]

    archive_path = archive_cluster_to_cold_storage(
        project_id="proj_alpha",
        nodes=nodes,
        override_dir=tmp_path,
        metadata={"project_status": "ARCHIVED", "reason": "decay"},
    )

    assert archive_path.is_file()
    assert archive_path.name == "proj_alpha.jsonl.gz"

    # Verify it is genuine valid gzip
    with gzip.open(archive_path, "rt", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        assert len(lines) == 3  # header + 2 nodes
        header = json.loads(lines[0])
        assert header.get("_locus_cold_archive") is True
        assert header.get("project_id") == "proj_alpha"

    # Load back using load_cold_archive
    loaded = load_cold_archive(project_id="proj_alpha", override_dir=tmp_path)
    assert loaded["project_id"] == "proj_alpha"
    assert loaded["node_count"] == 2
    assert loaded["nodes"][0]["node_id"] == "node_1"
    assert loaded["nodes"][1]["node_id"] == "node_2"


def test_cold_archiver_listing_and_missing(tmp_path):
    """SPEC §4.14 line 1424: "Serializes and moves deeply decayed memory nodes from active Neo4j graph to compressed storage"."""
    # Empty directory
    assert list_cold_archives(override_dir=tmp_path) == []

    # Missing project raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        load_cold_archive("nonexistent_project", override_dir=tmp_path)

    # Archive two projects
    archive_cluster_to_cold_storage("p1", [{"node_id": "n1"}], override_dir=tmp_path)
    archive_cluster_to_cold_storage("p2", [{"node_id": "n2"}], override_dir=tmp_path)

    archives = list_cold_archives(override_dir=tmp_path)
    assert len(archives) == 2
    proj_ids = [a["project_id"] for a in archives]
    assert "p1" in proj_ids
    assert "p2" in proj_ids


def test_nightly_project_decay_sweep(tmp_path):
    """SPEC §4.14 lines 1445-1466: "NIGHTLY PROJECT DECAY SWEEP (03:00 IST): FUNCTION sweep_project_memories():"."""
    engine = ProjectDecayEngine(storage_dir=tmp_path)

    t0 = 1000000.0  # reference time

    # Project 1: ACTIVE, touched recently (2 days ago) -> strength ~ 2^(-2/90) ~ 0.9847
    p1 = ProjectRecord(project_id="p_active", name="Active Project", status="ACTIVE", last_touched_at=t0 - (2 * 86400))
    engine.register_project(p1)
    engine.add_node(ProjectNode(node_id="n1", project_id="p_active", content="active task 1"))
    engine.add_node(ProjectNode(node_id="n2", project_id="p_active", content="active task 2"))

    # Project 2: ARCHIVED, touched long ago (30 days ago) -> strength ~ 2^(-30/7) ~ 0.051 < 0.10 (TRIGGERS COLD ARCHIVE)
    p2 = ProjectRecord(project_id="p_archived", name="Old Archive", status="ARCHIVED", last_touched_at=t0 - (30 * 86400))
    engine.register_project(p2)
    engine.add_node(ProjectNode(node_id="n3", project_id="p_archived", content="old subtask 1"))
    engine.add_node(ProjectNode(node_id="n4", project_id="p_archived", content="old subtask 2"))

    sweep_res = engine.sweep_project_memories(current_timestamp=t0)

    assert sweep_res["projects_evaluated"] == 2
    assert "p_archived" in sweep_res["projects_archived"]
    assert sweep_res["nodes_archived"] == 2

    # Active project nodes remain in memory with updated retention strength
    active_nodes = engine.get_project_nodes("p_active")
    assert len(active_nodes) == 2
    for node in active_nodes:
        assert node.retention_strength > 0.90
        assert node.last_decay_sweep == t0

    # Archived project nodes have been evicted from active set
    archived_nodes = engine.get_project_nodes("p_archived")
    assert len(archived_nodes) == 0

    # Cold archive file exists and contains the 2 nodes
    archive_file = tmp_path / "p_archived.jsonl.gz"
    assert archive_file.exists()
    loaded = load_cold_archive("p_archived", override_dir=tmp_path)
    assert loaded["node_count"] == 2


def test_sweep_dry_run(tmp_path):
    """SPEC §4.14 line 1455: "MATCH (n)-[:BELONGS_TO|SUBTASK_OF]->(p:Project {id: $proj_id}) SET n.retention_strength = $strength"."""
    engine = ProjectDecayEngine(storage_dir=tmp_path)
    t0 = 1000000.0

    p = ProjectRecord(project_id="p_archived", name="Old Archive", status="ARCHIVED", last_touched_at=t0 - (40 * 86400))
    engine.register_project(p)
    engine.add_node(ProjectNode(node_id="n1", project_id="p_archived", content="decaying item"))

    # Dry run should identify archive candidate but not remove nodes or create archive file
    res = engine.sweep_project_memories(current_timestamp=t0, dry_run=True)
    assert res["nodes_archived"] == 1
    assert "p_archived" in res["projects_archived"]

    # In active memory still
    assert len(engine.get_project_nodes("p_archived")) == 1
    # File not created
    assert not (tmp_path / "p_archived.jsonl.gz").exists()


def test_provider_interface_implementation(tmp_path):
    """SPEC §4.14 line 1470: "Provider Interface: MemoryDecayProvider"."""
    provider = DefaultProjectMemoryDecayProvider(
        name="test_decay",
        config=ProjectDecayConfig(storage_dir=str(tmp_path)),
    )
    assert isinstance(provider, MemoryDecayProvider)

    # Calculate
    s = provider.calculate_retention("PAUSED", 30.0)
    assert s == pytest.approx(0.50, rel=1e-3)

    # Health check
    health = provider.health_check()
    assert health["status"] == "healthy"
    assert "latency_ms" in health
    assert health["latency_ms"] >= 0.0


def test_project_decay_swap():
    """SPEC §4.14 line 1470: "Provider Interface: MemoryDecayProvider"."""
    reg = registry.ProviderRegistry()

    class CustomDecayProvider(MemoryDecayProvider):
        def calculate_retention(self, project_state: str, days_since_last_touch: float, s_0: float = 1.0) -> float:
            return 0.42

        def register_project(self, project: ProjectRecord) -> None:
            pass

        def add_project_node(self, node: ProjectNode) -> None:
            pass

        def sweep(self, current_timestamp: Optional[float] = None, dry_run: bool = False) -> Dict[str, Any]:
            return {"status": "custom"}

        def get_archive(self, project_id: str) -> Dict[str, Any]:
            return {"status": "custom"}

        def list_archives(self) -> List[Dict[str, Any]]:
            return []

        def health_check(self) -> Dict[str, Any]:
            return {"status": "custom_healthy"}

    reg.register("memory_decay", "default", DefaultProjectMemoryDecayProvider)
    reg.register("memory_decay", "custom", CustomDecayProvider)

    # Default provider returns normal exponential decay
    default_cls = reg.get("memory_decay", "default")
    assert default_cls is DefaultProjectMemoryDecayProvider
    def_inst = default_cls()
    assert def_inst.calculate_retention("ACTIVE", 0.0) == 1.0

    # Swapped provider returns custom value
    custom_cls = reg.get("memory_decay", "custom")
    assert custom_cls is CustomDecayProvider
    cust_inst = custom_cls()
    assert cust_inst.calculate_retention("ACTIVE", 0.0) == 0.42
    assert cust_inst.health_check()["status"] == "custom_healthy"


def test_project_decay_health():
    """SPEC §4.14 line 1470: "Provider Interface: MemoryDecayProvider"."""
    provider = DefaultProjectMemoryDecayProvider()
    health = provider.health_check()
    assert health["status"] in ("healthy", "degraded")
    assert "latency_ms" in health
    assert isinstance(health["latency_ms"], float)
    assert health["latency_ms"] >= 0.0


def test_project_decay_config_off_switch():
    """SPEC §4.14 line 1472: "Swappable / off state: locus.memory.decay.enabled. Off -> memory nodes never decay; all historical projects remain permanently active in Neo4j."."""
    cfg = ProjectDecayConfig(enabled=False)
    assert cfg.enabled is False
    assert cfg.cold_storage_threshold == COLD_STORAGE_THRESHOLD
    d = cfg.to_dict()
    assert d["enabled"] is False
