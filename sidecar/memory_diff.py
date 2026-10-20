"""
SPEC §4.9: Memory Diff (Snapshot-Based Change Tracking) Implementation.
Provides SqliteMemoryDiffProvider with snapshot storage, chunk hashing,
diff operations, named checkpoints, and what_changed agent tool action.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar.providers.memory_diff import (
    BaseMemoryDiffProvider,
    ChangeKind,
    Checkpoint,
    CrossSourceDiff,
    DiffResult,
    DiffSummary,
    ItemChange,
    MemoryDiffConfig,
    Snapshot,
    SnapshotItem,
    SnapshotTrigger,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".locus" / "memory" / "snapshots.db"


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of chunk content per Spec §4.9 line 1052."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class SqliteMemoryDiffProvider(BaseMemoryDiffProvider):
    """
    SPEC §4.9 line 1035:
    Snapshot-based change tracking for memory sources.
    After each sync, captures what's in the chunk store, then diffs against
    previous snapshots to surface additions, removals, and modifications.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        config: Optional[MemoryDiffConfig] = None,
    ) -> None:
        cfg = config or MemoryDiffConfig()
        super().__init__(name="sqlite_memory_diff", config=cfg)
        self.db_path = db_path or cfg.db_path or str(DEFAULT_DB_PATH)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mem_snapshots (
                        id TEXT PRIMARY KEY,
                        source_scope TEXT NOT NULL,
                        trigger TEXT NOT NULL,
                        items_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mem_checkpoints (
                        name TEXT PRIMARY KEY,
                        snapshot_ids_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_mem_snapshots_scope_created
                    ON mem_snapshots(source_scope, created_at);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def take_snapshot(
        self,
        source_scope: str,
        trigger: str = SnapshotTrigger.MANUAL.value,
        items: Optional[List[Dict[str, Any]]] = None,
    ) -> Snapshot:
        """
        SPEC §4.9 line 1079:
        FUNCTION take_snapshot(source_scope, trigger):
          items = store.get_all_chunks(source_scope)
                    .map(c => SnapshotItem {
                      chunk_id: c.id,
                      content_hash: sha256(c.content),
                      title: c.title,
                      token_count: c.token_count
                    })
          snapshot = Snapshot { source_scope, trigger, items, created_at: now() }
          store.save_snapshot(snapshot)
          RETURN snapshot.id
        """
        raw_items = items or []
        snapshot_items: List[SnapshotItem] = []

        for it in raw_items:
            chunk_id = str(it.get("chunk_id") or it.get("id") or uuid.uuid4().hex)
            content_hash = it.get("content_hash")
            if not content_hash:
                content = it.get("content", "")
                content_hash = compute_content_hash(content)
            title = it.get("title")
            token_count = int(it.get("token_count") or (len(it.get("content", "")) // 4))
            snapshot_items.append(
                SnapshotItem(
                    chunk_id=chunk_id,
                    content_hash=content_hash,
                    title=title,
                    token_count=token_count,
                )
            )

        snap_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        items_json = json.dumps([item.to_dict() for item in snapshot_items])

        snapshot = Snapshot(
            id=snap_id,
            source_scope=source_scope,
            trigger=trigger,
            items=snapshot_items,
            created_at=now_iso,
        )

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO mem_snapshots (id, source_scope, trigger, items_json, created_at)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (snap_id, source_scope, trigger, items_json, now_iso),
                )
                conn.commit()
            finally:
                conn.close()

        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Retrieve snapshot by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, source_scope, trigger, items_json, created_at FROM mem_snapshots WHERE id = ?;",
                    (snapshot_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return Snapshot.from_dict(
                    {
                        "id": row["id"],
                        "source_scope": row["source_scope"],
                        "trigger": row["trigger"],
                        "items": json.loads(row["items_json"]),
                        "created_at": row["created_at"],
                    }
                )
            finally:
                conn.close()

    def list_snapshots(
        self,
        source_scope: Optional[str] = None,
        limit: int = 50,
    ) -> List[Snapshot]:
        """List snapshots optionally filtered by source scope ordered newest first."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                if source_scope:
                    cursor.execute(
                        """
                        SELECT id, source_scope, trigger, items_json, created_at
                        FROM mem_snapshots
                        WHERE source_scope = ?
                        ORDER BY created_at DESC
                        LIMIT ?;
                        """,
                        (source_scope, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, source_scope, trigger, items_json, created_at
                        FROM mem_snapshots
                        ORDER BY created_at DESC
                        LIMIT ?;
                        """,
                        (limit,),
                    )
                rows = cursor.fetchall()
                snapshots: List[Snapshot] = []
                for r in rows:
                    snapshots.append(
                        Snapshot.from_dict(
                            {
                                "id": r["id"],
                                "source_scope": r["source_scope"],
                                "trigger": r["trigger"],
                                "items": json.loads(r["items_json"]),
                                "created_at": r["created_at"],
                            }
                        )
                    )
                return snapshots
            finally:
                conn.close()

    def diff(
        self,
        source_scope: str,
        from_snapshot_id: str,
        to_snapshot_id: str,
    ) -> DiffResult:
        """
        SPEC §4.9 line 1089:
        FUNCTION diff(source_scope, from_id, to_id):
          from_items = store.get_snapshot(from_id).items
          to_items   = store.get_snapshot(to_id).items
          
          changes = []
          FOR chunk_id IN union(from_items.keys, to_items.keys):
            IF chunk_id IN to_items AND NOT IN from_items:
              changes.push(ItemChange { kind: Added, ... })
            ELIF chunk_id IN from_items AND NOT IN to_items:
              changes.push(ItemChange { kind: Removed, ... })
            ELIF from_items[chunk_id].content_hash != to_items[chunk_id].content_hash:
              changes.push(ItemChange { kind: Modified, ... })
        """
        from_snap = self.get_snapshot(from_snapshot_id)
        to_snap = self.get_snapshot(to_snapshot_id)

        from_map = {item.chunk_id: item for item in (from_snap.items if from_snap else [])}
        to_map = {item.chunk_id: item for item in (to_snap.items if to_snap else [])}

        changes: List[ItemChange] = []
        added_count = 0
        removed_count = 0
        modified_count = 0
        unchanged_count = 0

        all_keys = set(from_map.keys()) | set(to_map.keys())

        for chunk_id in sorted(all_keys):
            in_from = chunk_id in from_map
            in_to = chunk_id in to_map

            if in_to and not in_from:
                to_item = to_map[chunk_id]
                changes.append(
                    ItemChange(
                        kind=ChangeKind.ADDED.value,
                        chunk_id=chunk_id,
                        title=to_item.title,
                        old_hash=None,
                        new_hash=to_item.content_hash,
                    )
                )
                added_count += 1
            elif in_from and not in_to:
                from_item = from_map[chunk_id]
                changes.append(
                    ItemChange(
                        kind=ChangeKind.REMOVED.value,
                        chunk_id=chunk_id,
                        title=from_item.title,
                        old_hash=from_item.content_hash,
                        new_hash=None,
                    )
                )
                removed_count += 1
            else:
                from_item = from_map[chunk_id]
                to_item = to_map[chunk_id]
                if from_item.content_hash != to_item.content_hash:
                    changes.append(
                        ItemChange(
                            kind=ChangeKind.MODIFIED.value,
                            chunk_id=chunk_id,
                            title=to_item.title or from_item.title,
                            old_hash=from_item.content_hash,
                            new_hash=to_item.content_hash,
                        )
                    )
                    modified_count += 1
                else:
                    unchanged_count += 1

        summary = DiffSummary(
            added=added_count,
            removed=removed_count,
            modified=modified_count,
            unchanged=unchanged_count,
        )

        return DiffResult(
            source_scope=source_scope,
            from_snapshot=from_snapshot_id,
            to_snapshot=to_snapshot_id,
            changes=changes,
            summary=summary,
        )

    def create_checkpoint(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        scope_items: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Checkpoint:
        """
        SPEC §4.9 line 1104:
        FUNCTION create_checkpoint(name):
          FOR EACH active source_scope:
            snap_id = take_snapshot(source_scope, Checkpoint)
            checkpoint.snapshot_ids[source_scope] = snap_id
          store.save_checkpoint(name, checkpoint)
        """
        active_scopes = scopes or (list(scope_items.keys()) if scope_items else ["default"])
        snapshot_ids: Dict[str, str] = {}

        for scope in active_scopes:
            items = scope_items.get(scope, []) if scope_items else []
            snap = self.take_snapshot(
                source_scope=scope,
                trigger=SnapshotTrigger.CHECKPOINT.value,
                items=items,
            )
            snapshot_ids[scope] = snap.id

        now_iso = datetime.now(timezone.utc).isoformat()
        checkpoint = Checkpoint(
            name=name,
            snapshot_ids=snapshot_ids,
            created_at=now_iso,
        )

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO mem_checkpoints (name, snapshot_ids_json, created_at)
                    VALUES (?, ?, ?);
                    """,
                    (name, json.dumps(snapshot_ids), now_iso),
                )
                conn.commit()
            finally:
                conn.close()

        return checkpoint

    def get_checkpoint(self, name: str) -> Optional[Checkpoint]:
        """Retrieve checkpoint by name."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name, snapshot_ids_json, created_at FROM mem_checkpoints WHERE name = ?;",
                    (name,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return Checkpoint(
                    name=row["name"],
                    snapshot_ids=json.loads(row["snapshot_ids_json"]),
                    created_at=row["created_at"],
                )
            finally:
                conn.close()

    def diff_since_checkpoint(
        self,
        name: str,
        current_scope_items: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> CrossSourceDiff:
        """
        SPEC §4.9 line 1109:
        FUNCTION diff_since_checkpoint(name):
          checkpoint = store.get_checkpoint(name)
          diffs = {}
          FOR EACH scope, snap_id IN checkpoint.snapshot_ids:
            current = take_snapshot(scope, Manual)
            diffs[scope] = diff(scope, snap_id, current)
          RETURN CrossSourceDiff { diffs }
        """
        checkpoint = self.get_checkpoint(name)
        if not checkpoint:
            raise ValueError(f"Checkpoint '{name}' not found")

        diffs: Dict[str, DiffResult] = {}
        total_added = 0
        total_removed = 0
        total_modified = 0
        total_unchanged = 0

        for scope, base_snap_id in checkpoint.snapshot_ids.items():
            curr_items = current_scope_items.get(scope, []) if current_scope_items else []
            curr_snap = self.take_snapshot(
                source_scope=scope,
                trigger=SnapshotTrigger.MANUAL.value,
                items=curr_items,
            )
            scope_diff = self.diff(
                source_scope=scope,
                from_snapshot_id=base_snap_id,
                to_snapshot_id=curr_snap.id,
            )
            diffs[scope] = scope_diff
            total_added += scope_diff.summary.added
            total_removed += scope_diff.summary.removed
            total_modified += scope_diff.summary.modified
            total_unchanged += scope_diff.summary.unchanged

        total_summary = DiffSummary(
            added=total_added,
            removed=total_removed,
            modified=total_modified,
            unchanged=total_unchanged,
        )

        return CrossSourceDiff(
            checkpoint_name=name,
            diffs=diffs,
            total_summary=total_summary,
        )

    def what_changed(
        self,
        checkpoint_name: Optional[str] = None,
        source_scope: Optional[str] = None,
    ) -> str:
        """
        SPEC §4.9 line 1120:
        MemoryDiffTool:
          "what_changed" action → diff_since_checkpoint or diff last N snapshots
          Returns human-readable summary: "3 notes added, 1 modified, 0 removed"
        """
        if checkpoint_name:
            try:
                cross = self.diff_since_checkpoint(checkpoint_name)
                ts = cross.total_summary
                return (
                    f"{ts.added} notes added, {ts.modified} modified, "
                    f"{ts.removed} removed ({ts.unchanged} unchanged) since checkpoint '{checkpoint_name}'"
                )
            except Exception as exc:
                return f"Error computing diff for checkpoint '{checkpoint_name}': {exc}"

        scope = source_scope or "default"
        snaps = self.list_snapshots(source_scope=scope, limit=2)
        if len(snaps) < 2:
            count = len(snaps[0].items) if snaps else 0
            return f"Initial baseline for scope '{scope}' contains {count} items. No previous snapshot to diff against."

        diff_res = self.diff(scope, snaps[1].id, snaps[0].id)
        s = diff_res.summary
        return f"{s.added} notes added, {s.modified} modified, {s.removed} removed ({s.unchanged} unchanged)"
