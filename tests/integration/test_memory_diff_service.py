"""Integration tests for Memory Diff FastAPI service endpoints.

Tests Spec §4.9:
- GET /memory/diff/config: Subsystem health & settings.
- POST /memory/diff/snapshot: Take new snapshot.
- GET /memory/diff/snapshots & /snapshots/{id}: Inspect snapshot records.
- POST /memory/diff/compare: Compare two snapshots for diff result.
- POST /memory/diff/checkpoint: Create named baseline checkpoint.
- POST /memory/diff/checkpoint/diff: Cross-source diff since checkpoint.
- GET /memory/diff/what_changed: Agent tool summary endpoint.
- Modular off-switch 503 behavior when disabled.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()

    orig_get = config.get

    def _cfg_get(key: str, default=None):
        if key == "locus.memory.diff.db_path":
            return tmp.name
        return orig_get(key, default)

    monkeypatch.setattr(config, "get", _cfg_get)
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None
    try:
        Path(tmp.name).unlink(missing_ok=True)
    except Exception:
        pass


def test_service_snapshot_creation_and_retrieval(client: TestClient) -> None:
    """SPEC §4.9 line 1079: "FUNCTION take_snapshot(source_scope, trigger): items = store.get_all_chunks(source_scope)... snapshot = Snapshot { source_scope, trigger, items, created_at: now() }"

    Asserts snapshot creation, listing, and single-record retrieval endpoints.
    """
    res_cfg = client.get("/memory/diff/config")
    assert res_cfg.status_code == 200
    assert res_cfg.json()["enabled"] is True

    snap_res = client.post(
        "/memory/diff/snapshot",
        json={
            "source_scope": "vault:notes",
            "trigger": "manual",
            "items": [
                {"chunk_id": "doc1", "content": "first document"},
                {"chunk_id": "doc2", "content": "second document"},
            ],
        },
    )
    assert snap_res.status_code == 200
    snap = snap_res.json()["snapshot"]
    assert snap["id"] is not None
    assert snap["source_scope"] == "vault:notes"
    assert len(snap["items"]) == 2

    # List snapshots
    list_res = client.get("/memory/diff/snapshots?source_scope=vault:notes")
    assert list_res.status_code == 200
    assert len(list_res.json()["snapshots"]) == 1

    # Get single snapshot
    get_res = client.get(f"/memory/diff/snapshots/{snap['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["snapshot"]["id"] == snap["id"]


def test_service_compare_snapshots(client: TestClient) -> None:
    """SPEC §4.9 line 1089: "FUNCTION diff(source_scope, from_id, to_id): from_items = store.get_snapshot(from_id).items to_items = store.get_snapshot(to_id).items changes = []"

    Asserts comparison between two snapshots computes item additions and modifications.
    """
    s1 = client.post(
        "/memory/diff/snapshot",
        json={
            "source_scope": "workspace",
            "items": [
                {"chunk_id": "fileA", "content": "version 1"},
                {"chunk_id": "fileB", "content": "unmodified"},
            ],
        },
    ).json()["snapshot"]

    s2 = client.post(
        "/memory/diff/snapshot",
        json={
            "source_scope": "workspace",
            "items": [
                {"chunk_id": "fileA", "content": "version 2 (changed)"},
                {"chunk_id": "fileB", "content": "unmodified"},
                {"chunk_id": "fileC", "content": "newly created file"},
            ],
        },
    ).json()["snapshot"]

    diff_res = client.post(
        "/memory/diff/compare",
        json={
            "source_scope": "workspace",
            "from_snapshot_id": s1["id"],
            "to_snapshot_id": s2["id"],
        },
    )
    assert diff_res.status_code == 200
    diff_data = diff_res.json()["diff"]
    summary = diff_data["summary"]
    assert summary["added"] == 1
    assert summary["modified"] == 1
    assert summary["unchanged"] == 1
    assert summary["removed"] == 0


def test_service_checkpoint_and_cross_diff(client: TestClient) -> None:
    """SPEC §4.9 line 1104: "FUNCTION create_checkpoint(name): FOR EACH active source_scope: snap_id = take_snapshot(source_scope, Checkpoint)" and line 1109 "diff_since_checkpoint(name)"

    Asserts creation of named checkpoint and cross-source diff computation.
    """
    chk_res = client.post(
        "/memory/diff/checkpoint",
        json={
            "name": "release-1.0",
            "scopes": ["docs", "code"],
            "scope_items": {
                "docs": [{"chunk_id": "d1", "content": "documentation"}],
                "code": [{"chunk_id": "c1", "content": "source code"}],
            },
        },
    )
    assert chk_res.status_code == 200
    chk = chk_res.json()["checkpoint"]
    assert chk["name"] == "release-1.0"
    assert "docs" in chk["snapshot_ids"]
    assert "code" in chk["snapshot_ids"]

    # Compute diff since checkpoint with updated code
    diff_res = client.post(
        "/memory/diff/checkpoint/diff",
        json={
            "name": "release-1.0",
            "current_scope_items": {
                "docs": [{"chunk_id": "d1", "content": "documentation"}],
                "code": [
                    {"chunk_id": "c1", "content": "source code v2"},
                    {"chunk_id": "c2", "content": "new test suite"},
                ],
            },
        },
    )
    assert diff_res.status_code == 200
    cross = diff_res.json()["cross_diff"]
    assert cross["checkpoint_name"] == "release-1.0"
    assert cross["total_summary"]["modified"] == 1
    assert cross["total_summary"]["added"] == 1
    assert cross["total_summary"]["unchanged"] == 1


def test_service_what_changed_tool_endpoint(client: TestClient) -> None:
    """SPEC §4.9 line 1120: "MemoryDiffTool: 'what_changed' action → diff_since_checkpoint or diff last N snapshots Returns human-readable summary: '3 notes added, 1 modified, 0 removed'"

    Asserts /memory/diff/what_changed returns readable summary string.
    """
    client.post(
        "/memory/diff/snapshot",
        json={
            "source_scope": "daily",
            "items": [{"chunk_id": "entry1", "content": "Monday"}],
        },
    )
    client.post(
        "/memory/diff/snapshot",
        json={
            "source_scope": "daily",
            "items": [
                {"chunk_id": "entry1", "content": "Monday"},
                {"chunk_id": "entry2", "content": "Tuesday entry"},
            ],
        },
    )

    res = client.get("/memory/diff/what_changed?source_scope=daily")
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert "1 notes added, 0 modified, 0 removed" in summary


def test_service_disabled_off_switch(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §4.9 line 1135: "Swappable / off state: locus.memory.diff.enabled. Off → no snapshot tracking; agents cannot query 'what changed'"

    Asserts HTTP 503 response when memory diff subsystem is disabled.
    """
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: (
            False
            if key in ("locus.memory_diff_snapshot_based_change_tracking.enabled", "locus.memory.diff.enabled")
            else default
        ),
    )
    config._CONFIG_CACHE = None

    res = client.get("/memory/diff/config")
    assert res.status_code == 503
    assert "disabled" in res.json()
