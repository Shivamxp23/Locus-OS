"""Unit tests for Multi-Source Ingestion Pipelines (Memory Sync).

Tests Spec §4.7:
- Unified SyncPipeline trait and SyncOutcome contract.
- Three pipeline kinds: Composio (Direct API), Workspace (local), MCP.
- Periodic sync loops and cursor pagination.
- Self-healing raw-archive set difference reconciliation (check_and_rebuild_tree).
- Modularity off-switch: locus.memory.sync.enabled.
"""

from typing import Optional
import pytest

from sidecar.memory_sync import (
    DirectAPISyncPipeline,
    McpSyncPipeline,
    MemorySyncManager,
    WorkspaceSyncPipeline,
)
from sidecar.providers.memory_sync import (
    BaseMemorySyncProvider,
    BaseSyncPipeline,
    MemorySyncConfig,
    SourceScope,
    SyncOutcome,
    SyncPipelineKind,
)


def test_memory_sync_protocol_and_manager_conformance():
    """SPEC §4.7 line 843: "trait SyncPipeline: Send + Sync { async fn init(&self, config: &Config) → Result<()> async fn tick(&self, config: &Config) → Result<SyncOutcome> fn id(&self) → &str fn kind(&self) → SyncPipelineKind }"

    Asserts all pipeline classes conform to BaseSyncPipeline and manager implements BaseMemorySyncProvider.
    """
    mgr = MemorySyncManager()
    assert isinstance(mgr, BaseMemorySyncProvider)
    assert mgr.is_enabled() is True

    ws = WorkspaceSyncPipeline()
    assert isinstance(ws, BaseSyncPipeline)
    assert ws.kind() == SyncPipelineKind.WORKSPACE

    api = DirectAPISyncPipeline()
    assert isinstance(api, BaseSyncPipeline)
    assert api.kind() == SyncPipelineKind.COMPOSIO

    mcp = McpSyncPipeline()
    assert isinstance(mcp, BaseSyncPipeline)
    assert mcp.kind() == SyncPipelineKind.MCP


def test_workspace_pipeline_md5_change_detection():
    """SPEC §4.7 line 863: "Vault file watch (Obsidian .md files)"

    Asserts WorkspaceSyncPipeline ingests new files and detects changes via MD5 hashes without duplicating unchanged files.
    """
    ws = WorkspaceSyncPipeline(pipeline_id="test_vault")
    cfg = MemorySyncConfig()

    ws.stage_file("notes/arch.md", "# Architecture\nInitial draft of system.")
    ws.stage_file("notes/todo.md", "# Todo\n- Write unit tests.")

    outcome1 = ws.tick(cfg)
    assert outcome1.records_ingested == 2
    assert outcome1.more_pending is False

    # Second tick without modifications -> 0 ingested
    outcome2 = ws.tick(cfg)
    assert outcome2.records_ingested == 0

    # Modify one file -> exactly 1 ingested
    ws.stage_file("notes/arch.md", "# Architecture\nUpdated with memory tree sync.")
    outcome3 = ws.tick(cfg)
    assert outcome3.records_ingested == 1


def test_direct_api_pipeline_cursor_pagination():
    """SPEC §4.7 line 860: "Each provider has its own ingest.rs + pagination cursor + retry policy"

    Asserts DirectAPISyncPipeline batches items, returns cursor, and indicates more_pending until exhausted.
    """
    api = DirectAPISyncPipeline(pipeline_id="test_github", provider="github")
    api.batch_size = 3
    cfg = MemorySyncConfig()

    # Enqueue 7 remote items
    mock_items = [{"id": f"gh-issue-{i}", "title": f"Issue {i}"} for i in range(1, 8)]
    api.enqueue_remote_items(mock_items)

    # Tick 1: ingests 3 items, more_pending=True, cursor present
    out1 = api.tick(cfg)
    assert out1.records_ingested == 3
    assert out1.more_pending is True
    assert out1.cursor is not None

    # Tick 2: ingests 3 items, more_pending=True
    out2 = api.tick(cfg)
    assert out2.records_ingested == 3
    assert out2.more_pending is True

    # Tick 3: ingests remaining 1 item, more_pending=False, cursor=None
    out3 = api.tick(cfg)
    assert out3.records_ingested == 1
    assert out3.more_pending is False
    assert out3.cursor is None


def test_mcp_pipeline_resource_ingestion():
    """SPEC §4.7 line 868: "One pipeline per connected MCP server"

    Asserts McpSyncPipeline drains pending resource URIs and resets pending queue.
    """
    mcp = McpSyncPipeline(pipeline_id="mcp_fs", server_name="filesystem")
    cfg = MemorySyncConfig()

    mcp.add_resource("file:///workspace/project/spec.md")
    mcp.add_resource("file:///workspace/project/schema.sql")

    out = mcp.tick(cfg)
    assert out.records_ingested == 2
    assert "filesystem" in (out.note or "")

    # Queue emptied
    out_empty = mcp.tick(cfg)
    assert out_empty.records_ingested == 0


def test_self_healing_raw_archive_set_difference():
    """SPEC §4.7 line 887: "FUNCTION check_and_rebuild_tree(source): on_disk = list_raw_files(source.raw_archive_path) uncovered = on_disk - ingested IF uncovered.is_not_empty(): FOR EACH file IN uncovered: enqueue_job(JobKind::ExtractChunk, file)"

    Asserts check_and_rebuild_tree computes the exact set difference between on-disk files and ingested records, self-healing missed files.
    """
    mgr = MemorySyncManager()
    source = SourceScope(
        tree_scope="github:owner/repo",
        raw_archive_id="github.com/owner/repo",
        provider="github",
    )

    on_disk = ["file1.md", "file2.md", "file3.md", "file4.md"]

    # Initial check: all 4 are uncovered and self-healed
    healed1 = mgr.check_and_rebuild_tree(source, on_disk)
    assert set(healed1) == set(on_disk)

    # Next check with the same files: 0 uncovered
    healed2 = mgr.check_and_rebuild_tree(source, on_disk)
    assert healed2 == []

    # New file appears on disk: self-heals only the new file
    on_disk_extended = on_disk + ["file5.md"]
    healed3 = mgr.check_and_rebuild_tree(source, on_disk_extended)
    assert healed3 == ["file5.md"]


def test_tick_all_executes_all_registered_pipelines():
    """SPEC §4.7 line 874: "THREE BACKGROUND LOOPS: Composio periodic (20-min tick) Workspace periodic (20-min tick) Queue scheduler (3 h)"

    Asserts tick_all executes each registered pipeline and aggregates outcomes.
    """
    mgr = MemorySyncManager()
    ws: WorkspaceSyncPipeline = mgr.get_pipeline("workspace_vault")  # type: ignore
    ws.stage_file("doc1.md", "Content of doc 1")

    outcomes = mgr.tick_all()
    assert "workspace_vault" in outcomes
    assert "direct_api_github" in outcomes
    assert "mcp_default" in outcomes
    assert outcomes["workspace_vault"].records_ingested == 1


def test_modular_off_switch_halts_sync():
    """SPEC §4.7 line 921: "Swappable / off state: locus.memory.sync.enabled (global) + per-pipeline toggles. Off → no automatic ingestion"

    Asserts that disabling memory sync halts ticking and returns 0 ingested records.
    """
    mgr = MemorySyncManager(config=MemorySyncConfig(enabled=False))
    assert mgr.is_enabled() is False

    outcome = mgr.tick_pipeline("workspace_vault")
    assert outcome.records_ingested == 0
    assert "disabled" in (outcome.note or "").lower()

    source = SourceScope(tree_scope="test", raw_archive_id="test", provider="test")
    healed = mgr.check_and_rebuild_tree(source, ["file1.txt"])
    assert healed == []


def test_health_check_returns_pipeline_metrics():
    """SPEC §4.7 line 919: "sync state + cursors in .locus/memory/sync_state.db"

    Asserts health check reports accurate registered pipeline counts and sync tick history.
    """
    mgr = MemorySyncManager()
    mgr.tick_all()

    health = mgr.health()
    assert health["status"] == "healthy"
    assert health["enabled"] is True
    assert health["pipelines_count"] >= 3
    assert health["total_sync_ticks"] >= 3
