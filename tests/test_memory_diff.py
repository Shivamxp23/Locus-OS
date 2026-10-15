import pytest
from sidecar.memory.diff_ops import (
    take_snapshot,
    diff_snapshots,
    MemoryDiffManager,
    SnapshotTrigger,
    ChangeKind,
)


def test_take_snapshot_and_hash():
    chunks = [
        {"id": "c1", "content": "Hello World", "title": "Doc 1"},
        {"id": "c2", "content": "Second Chunk", "token_count": 10},
    ]
    snap = take_snapshot("test_scope", chunks)
    assert snap.source_scope == "test_scope"
    assert len(snap.items) == 2
    assert snap.items[0].chunk_id == "c1"
    assert len(snap.items[0].content_hash) == 64


def test_diff_snapshots_add_remove_modify():
    chunks_v1 = [
        {"id": "c1", "content": "Initial content"},
        {"id": "c2", "content": "To be removed"},
    ]
    chunks_v2 = [
        {"id": "c1", "content": "Updated content"},
        {"id": "c3", "content": "Newly added"},
    ]
    snap1 = take_snapshot("scope1", chunks_v1)
    snap2 = take_snapshot("scope1", chunks_v2)

    res = diff_snapshots("scope1", snap1, snap2)
    assert res.summary.added == 1
    assert res.summary.removed == 1
    assert res.summary.modified == 1
    assert res.summary.unchanged == 0

    kinds = {c.chunk_id: c.kind for c in res.changes}
    assert kinds["c3"] == ChangeKind.ADDED.value
    assert kinds["c2"] == ChangeKind.REMOVED.value
    assert kinds["c1"] == ChangeKind.MODIFIED.value


def test_memory_diff_manager_checkpoint():
    manager = MemoryDiffManager()
    scope = "project:vault"
    manager.record_snapshot(scope, [{"id": "doc1", "content": "Version 1"}])
    manager.create_checkpoint(scope)

    # Make updates
    manager.record_snapshot(
        scope,
        [
            {"id": "doc1", "content": "Version 1"},
            {"id": "doc2", "content": "New file"},
        ],
    )

    diff = manager.diff_since_checkpoint(scope)
    assert diff.summary.added == 1
    assert diff.summary.unchanged == 1
    assert diff.summary.modified == 0
    assert diff.changes[0].chunk_id == "doc2"
