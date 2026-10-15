import pytest
from datetime import datetime, timedelta, timezone
from sidecar.memory.project_decay import (
    HALF_LIFE_DAYS,
    COLD_STORAGE_THRESHOLD,
    calculate_retention_strength,
    ProjectMemoryCluster,
    ProjectDecayManager,
)


def test_half_life_exact_calculations():
    # 0 days inactive -> 1.0
    assert calculate_retention_strength("ACTIVE", 0) == 1.0

    # Exactly 1 half-life (90 days for ACTIVE) -> 0.50
    assert pytest.approx(calculate_retention_strength("ACTIVE", 90.0), rel=1e-3) == 0.50

    # Exactly 2 half-lives (180 days for ACTIVE) -> 0.25
    assert pytest.approx(calculate_retention_strength("ACTIVE", 180.0), rel=1e-3) == 0.25

    # Archived project (half-life = 7 days). At 28 days (4 half-lives) -> (0.5)^4 = 0.0625
    archived_strength = calculate_retention_strength("ARCHIVED", 28.0)
    assert pytest.approx(archived_strength, rel=1e-3) == 0.0625
    assert archived_strength < COLD_STORAGE_THRESHOLD


def test_project_decay_manager_sweep_and_cold_storage():
    mgr = ProjectDecayManager()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    t_sweep = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)  # ~60 days later

    # Project 1: ACTIVE (half-life 90 days, 60 days inactive -> (0.5)^(60/90) ≈ 0.63 -> stays active)
    mgr.register_project("proj_active", status="ACTIVE", last_touched=t0)

    # Project 2: ARCHIVED (half-life 7 days, 60 days inactive -> strength << 0.10 -> archived)
    mgr.register_project("proj_archived", status="ARCHIVED", last_touched=t0)

    res = mgr.sweep_project_memories(current_time=t_sweep)
    assert res["total_swept"] == 2
    assert res["newly_archived"] == 1
    assert "proj_archived" in mgr.cold_archive
    assert not mgr.clusters["proj_active"].is_cold_archived
    assert mgr.clusters["proj_archived"].is_cold_archived


def test_touch_project_restores_from_cold_storage():
    mgr = ProjectDecayManager()
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    mgr.register_project("proj1", status="ARCHIVED", last_touched=t0)
    mgr.sweep_project_memories(current_time=datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc))

    assert mgr.clusters["proj1"].is_cold_archived

    # Touch project
    restored = mgr.touch_project("proj1")
    assert not restored.is_cold_archived
    assert restored.retention_strength == 1.0
    assert "proj1" not in mgr.cold_archive
