"""tests/test_memory_sync.py - Unit & Integration Tests for Memory Sync Pipelines.

Tests Spec §4.7:
- WorkspaceSyncPipeline scanning markdown files and computing MD5 cursors.
- Incremental tick detection: only new or modified files yield records_ingested > 0.
- Self-healing raw-archive set difference check (check_uncovered_files).
- SyncPipeline protocol compliance.
- Modularity switch: WorkspaceSyncPipeline(enabled=False).
"""

from pathlib import Path
import pytest

from sidecar.memory.sync_pipeline import (
    SyncOutcome,
    SyncPipeline,
    SyncPipelineKind,
    WorkspaceSyncPipeline,
)


def test_sync_pipeline_protocol_conformance(tmp_path):
    pipeline = WorkspaceSyncPipeline(vault_dir=tmp_path)
    assert isinstance(pipeline, SyncPipeline)
    assert pipeline.kind() == SyncPipelineKind.WORKSPACE
    assert "workspace-vault:" in pipeline.id()


def test_workspace_sync_incremental_tick(tmp_path):
    pipeline = WorkspaceSyncPipeline(vault_dir=tmp_path, enabled=True)

    # Initial state: 0 files
    outcome1 = pipeline.tick()
    assert outcome1.records_ingested == 0

    # Add 2 markdown files
    (tmp_path / "Note1.md").write_text("# Note 1\nContent", encoding="utf-8")
    (tmp_path / "Subfolder").mkdir()
    (tmp_path / "Subfolder" / "Note2.md").write_text("# Note 2\nContent", encoding="utf-8")

    # Tick 2: Ingests 2 files
    outcome2 = pipeline.tick()
    assert outcome2.records_ingested == 2

    # Tick 3: No changes -> 0 files ingested
    outcome3 = pipeline.tick()
    assert outcome3.records_ingested == 0

    # Modify 1 file -> Tick 4 ingests exactly 1 file
    (tmp_path / "Note1.md").write_text("# Note 1\nUpdated Content", encoding="utf-8")
    outcome4 = pipeline.tick()
    assert outcome4.records_ingested == 1


def test_self_healing_uncovered_files_check(tmp_path):
    pipeline = WorkspaceSyncPipeline(vault_dir=tmp_path, enabled=True)
    f1 = tmp_path / "docA.md"
    f2 = tmp_path / "docB.md"
    f1.write_text("Doc A", encoding="utf-8")
    f2.write_text("Doc B", encoding="utf-8")

    # Before tick, both are uncovered
    uncovered = pipeline.check_uncovered_files()
    assert set(uncovered) == {"docA.md", "docB.md"}

    # After tick, none are uncovered
    pipeline.tick()
    assert pipeline.check_uncovered_files() == []


def test_sync_pipeline_modularity_disabled(tmp_path):
    pipeline = WorkspaceSyncPipeline(vault_dir=tmp_path, enabled=False)
    (tmp_path / "test.md").write_text("Hello", encoding="utf-8")
    outcome = pipeline.tick()

    assert outcome.records_ingested == 0
    assert "disabled" in outcome.note.lower()
