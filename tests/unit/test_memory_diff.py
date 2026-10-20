"""
Unit tests for Memory Diff (Snapshot-Based Change Tracking).
Verifies SqliteMemoryDiffProvider per Spec §4.9 lines 1031-1165.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sidecar.memory_diff import SqliteMemoryDiffProvider, compute_content_hash
from sidecar.providers.memory_diff import (
    ChangeKind,
    MemoryDiffConfig,
    SnapshotTrigger,
)


@pytest.fixture
def temp_diff_provider() -> SqliteMemoryDiffProvider:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    cfg = MemoryDiffConfig(enabled=True)
    provider = SqliteMemoryDiffProvider(db_path=tmp.name, config=cfg)
    yield provider
    try:
        Path(tmp.name).unlink(missing_ok=True)
    except Exception:
        pass


def test_take_snapshot_and_hashing(temp_diff_provider: SqliteMemoryDiffProvider) -> None:
    """SPEC §4.9 line 1079: "FUNCTION take_snapshot(source_scope, trigger): items = store.get_all_chunks(source_scope).map(c => SnapshotItem { chunk_id: c.id, content_hash: sha256(c.content), title: c.title, token_count: c.token_count })"."""
    items = [
        {"chunk_id": "c1", "content": "alpha content", "title": "Note Alpha"},
        {"chunk_id": "c2", "content": "beta content", "title": "Note Beta"},
    ]
    snapshot = temp_diff_provider.take_snapshot(
        source_scope="vault:daily",
        trigger=SnapshotTrigger.MANUAL.value,
        items=items,
    )
    assert snapshot.id is not None
    assert snapshot.source_scope == "vault:daily"
    assert snapshot.trigger == SnapshotTrigger.MANUAL.value
    assert len(snapshot.items) == 2

    # Verify content hash matches SHA-256
    expected_hash = compute_content_hash("alpha content")
    item1 = next(it for it in snapshot.items if it.chunk_id == "c1")
    assert item1.content_hash == expected_hash
    assert item1.title == "Note Alpha"


def test_diff_added_removed_modified(temp_diff_provider: SqliteMemoryDiffProvider) -> None:
    """SPEC §4.9 line 1089: "FUNCTION diff(source_scope, from_id, to_id): from_items = store.get_snapshot(from_id).items to_items = store.get_snapshot(to_id).items changes = []"."""
    # Baseline snapshot
    items_v1 = [
        {"chunk_id": "keep", "content": "identical content"},
        {"chunk_id": "modify_me", "content": "initial version"},
        {"chunk_id": "remove_me", "content": "will be deleted"},
    ]
    snap1 = temp_diff_provider.take_snapshot("scope1", items=items_v1)

    # Modified snapshot
    items_v2 = [
        {"chunk_id": "keep", "content": "identical content"},
        {"chunk_id": "modify_me", "content": "updated version!"},
        {"chunk_id": "new_note", "content": "freshly added note"},
    ]
    snap2 = temp_diff_provider.take_snapshot("scope1", items=items_v2)

    diff_res = temp_diff_provider.diff("scope1", snap1.id, snap2.id)
    assert diff_res.source_scope == "scope1"
    assert diff_res.from_snapshot == snap1.id
    assert diff_res.to_snapshot == snap2.id

    assert diff_res.summary.added == 1
    assert diff_res.summary.removed == 1
    assert diff_res.summary.modified == 1
    assert diff_res.summary.unchanged == 1

    change_kinds = {c.chunk_id: c.kind for c in diff_res.changes}
    assert change_kinds["new_note"] == ChangeKind.ADDED.value
    assert change_kinds["remove_me"] == ChangeKind.REMOVED.value
    assert change_kinds["modify_me"] == ChangeKind.MODIFIED.value


def test_named_checkpoints(temp_diff_provider: SqliteMemoryDiffProvider) -> None:
    """SPEC §4.9 line 1104: "FUNCTION create_checkpoint(name): FOR EACH active source_scope: snap_id = take_snapshot(source_scope, Checkpoint) checkpoint.snapshot_ids[source_scope] = snap_id"."""
    scope_data = {
        "vault": [{"chunk_id": "v1", "content": "vault content"}],
        "github": [{"chunk_id": "g1", "content": "repo readme"}],
    }
    checkpoint = temp_diff_provider.create_checkpoint("weekly-baseline", scope_items=scope_data)
    assert checkpoint.name == "weekly-baseline"
    assert "vault" in checkpoint.snapshot_ids
    assert "github" in checkpoint.snapshot_ids

    fetched = temp_diff_provider.get_checkpoint("weekly-baseline")
    assert fetched is not None
    assert fetched.name == "weekly-baseline"
    assert fetched.snapshot_ids == checkpoint.snapshot_ids


def test_diff_since_checkpoint(temp_diff_provider: SqliteMemoryDiffProvider) -> None:
    """SPEC §4.9 line 1109: "FUNCTION diff_since_checkpoint(name): checkpoint = store.get_checkpoint(name) diffs = {} FOR EACH scope, snap_id IN checkpoint.snapshot_ids: current = take_snapshot(scope, Manual) diffs[scope] = diff(scope, snap_id, current)"."""
    base_data = {
        "vault": [{"chunk_id": "v1", "content": "initial vault"}],
        "github": [{"chunk_id": "g1", "content": "initial github"}],
    }
    temp_diff_provider.create_checkpoint("v1-release", scope_items=base_data)

    current_data = {
        "vault": [
            {"chunk_id": "v1", "content": "updated vault!"},
            {"chunk_id": "v2", "content": "brand new note"},
        ],
        "github": [{"chunk_id": "g1", "content": "initial github"}],
    }

    cross = temp_diff_provider.diff_since_checkpoint("v1-release", current_scope_items=current_data)
    assert cross.checkpoint_name == "v1-release"
    assert "vault" in cross.diffs
    assert "github" in cross.diffs

    vault_diff = cross.diffs["vault"]
    assert vault_diff.summary.added == 1
    assert vault_diff.summary.modified == 1
    assert vault_diff.summary.removed == 0

    github_diff = cross.diffs["github"]
    assert github_diff.summary.unchanged == 1
    assert github_diff.summary.added == 0

    assert cross.total_summary.added == 1
    assert cross.total_summary.modified == 1
    assert cross.total_summary.unchanged == 1


def test_what_changed_agent_tool_action(temp_diff_provider: SqliteMemoryDiffProvider) -> None:
    """SPEC §4.9 line 1120: "MemoryDiffTool: 'what_changed' action → diff_since_checkpoint or diff last N snapshots Returns human-readable summary: '3 notes added, 1 modified, 0 removed'"."""
    # Test diffing last 2 snapshots in a scope
    s1 = temp_diff_provider.take_snapshot(
        "notes",
        items=[
            {"chunk_id": "n1", "content": "c1"},
            {"chunk_id": "n2", "content": "c2"},
        ],
    )
    s2 = temp_diff_provider.take_snapshot(
        "notes",
        items=[
            {"chunk_id": "n1", "content": "c1 modified"},
            {"chunk_id": "n3", "content": "c3 added"},
        ],
    )

    summary_msg = temp_diff_provider.what_changed(source_scope="notes")
    assert "1 notes added, 1 modified, 1 removed" in summary_msg
    assert "0 unchanged" in summary_msg
