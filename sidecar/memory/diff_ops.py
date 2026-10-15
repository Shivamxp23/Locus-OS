"""Memory Diff (Snapshot-Based Change Tracking) (§4.9).

Captures chunk snapshots across memory source scopes (e.g., vault, code repositories)
and computes semantic diffs (additions, removals, modifications) across sync cycles.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SnapshotTrigger(str, Enum):
    AUTO_POST_SYNC = "AutoPostSync"
    MANUAL = "Manual"
    CHECKPOINT = "Checkpoint"


class ChangeKind(str, Enum):
    ADDED = "Added"
    REMOVED = "Removed"
    MODIFIED = "Modified"


@dataclass
class SnapshotItem:
    chunk_id: str
    content_hash: str
    title: Optional[str] = None
    token_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SnapshotItem:
        return cls(
            chunk_id=str(data.get("chunk_id", "")),
            content_hash=str(data.get("content_hash", "")),
            title=data.get("title"),
            token_count=int(data.get("token_count", 0)),
        )


@dataclass
class Snapshot:
    id: str
    source_scope: str
    trigger: str
    items: List[SnapshotItem] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_scope": self.source_scope,
            "trigger": self.trigger,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Snapshot:
        items = [SnapshotItem.from_dict(it) for it in data.get("items", [])]
        return cls(
            id=str(data.get("id", uuid.uuid4())),
            source_scope=str(data.get("source_scope", "default")),
            trigger=str(data.get("trigger", SnapshotTrigger.MANUAL.value)),
            items=items,
            created_at=str(data.get("created_at", datetime.now(timezone.utc).isoformat())),
        )


@dataclass
class ItemChange:
    kind: str
    chunk_id: str
    title: Optional[str] = None
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiffSummary:
    added: int = 0
    removed: int = 0
    modified: int = 0
    unchanged: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiffResult:
    source_scope: str
    from_snapshot: str
    to_snapshot: str
    changes: List[ItemChange] = field(default_factory=list)
    summary: DiffSummary = field(default_factory=DiffSummary)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_scope": self.source_scope,
            "from_snapshot": self.from_snapshot,
            "to_snapshot": self.to_snapshot,
            "changes": [c.to_dict() for c in self.changes],
            "summary": self.summary.to_dict(),
        }


def hash_content(content: str) -> str:
    """Compute SHA-256 hash of text content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def take_snapshot(
    source_scope: str,
    chunks: List[Dict[str, Any]],
    trigger: str = SnapshotTrigger.AUTO_POST_SYNC.value,
) -> Snapshot:
    """Build a Snapshot from a list of chunk dicts (chunk_id, content, title, token_count)."""
    items: List[SnapshotItem] = []
    for chunk in chunks:
        cid = str(chunk.get("id", chunk.get("chunk_id", "")))
        content = chunk.get("content", "")
        chash = chunk.get("content_hash") or hash_content(str(content))
        title = chunk.get("title")
        t_count = int(chunk.get("token_count", max(1, len(str(content)) // 4)))
        items.append(
            SnapshotItem(
                chunk_id=cid,
                content_hash=chash,
                title=title,
                token_count=t_count,
            )
        )
    return Snapshot(
        id=str(uuid.uuid4()),
        source_scope=source_scope,
        trigger=trigger,
        items=items,
    )


def diff_snapshots(
    source_scope: str,
    from_snapshot: Optional[Snapshot],
    to_snapshot: Snapshot,
) -> DiffResult:
    """Compare two snapshots and return added, removed, modified, and unchanged items."""
    from_map: Dict[str, SnapshotItem] = (
        {it.chunk_id: it for it in from_snapshot.items} if from_snapshot else {}
    )
    to_map: Dict[str, SnapshotItem] = {it.chunk_id: it for it in to_snapshot.items}

    all_keys = set(from_map.keys()) | set(to_map.keys())
    changes: List[ItemChange] = []
    summary = DiffSummary()

    for cid in sorted(all_keys):
        if cid in to_map and cid not in from_map:
            to_item = to_map[cid]
            changes.append(
                ItemChange(
                    kind=ChangeKind.ADDED.value,
                    chunk_id=cid,
                    title=to_item.title,
                    new_hash=to_item.content_hash,
                )
            )
            summary.added += 1
        elif cid in from_map and cid not in to_map:
            from_item = from_map[cid]
            changes.append(
                ItemChange(
                    kind=ChangeKind.REMOVED.value,
                    chunk_id=cid,
                    title=from_item.title,
                    old_hash=from_item.content_hash,
                )
            )
            summary.removed += 1
        else:
            from_item = from_map[cid]
            to_item = to_map[cid]
            if from_item.content_hash != to_item.content_hash:
                changes.append(
                    ItemChange(
                        kind=ChangeKind.MODIFIED.value,
                        chunk_id=cid,
                        title=to_item.title or from_item.title,
                        old_hash=from_item.content_hash,
                        new_hash=to_item.content_hash,
                    )
                )
                summary.modified += 1
            else:
                summary.unchanged += 1

    return DiffResult(
        source_scope=source_scope,
        from_snapshot=from_snapshot.id if from_snapshot else "empty",
        to_snapshot=to_snapshot.id,
        changes=changes,
        summary=summary,
    )


class MemoryDiffManager:
    """In-memory or persistent store for snapshot timelines and checkpoint diffing."""

    def __init__(self) -> None:
        self.snapshots_by_scope: Dict[str, List[Snapshot]] = {}
        self.checkpoints_by_scope: Dict[str, Snapshot] = {}

    def record_snapshot(
        self,
        source_scope: str,
        chunks: List[Dict[str, Any]],
        trigger: str = SnapshotTrigger.AUTO_POST_SYNC.value,
    ) -> Snapshot:
        snap = take_snapshot(source_scope, chunks, trigger)
        history = self.snapshots_by_scope.setdefault(source_scope, [])
        history.append(snap)
        return snap

    def create_checkpoint(
        self,
        source_scope: str,
        chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> Snapshot:
        if chunks is not None:
            snap = self.record_snapshot(source_scope, chunks, SnapshotTrigger.CHECKPOINT.value)
        else:
            history = self.snapshots_by_scope.get(source_scope, [])
            if not history:
                snap = self.record_snapshot(source_scope, [], SnapshotTrigger.CHECKPOINT.value)
            else:
                snap = history[-1]
        self.checkpoints_by_scope[source_scope] = snap
        return snap

    def diff_latest(self, source_scope: str) -> Optional[DiffResult]:
        history = self.snapshots_by_scope.get(source_scope, [])
        if len(history) < 2:
            if len(history) == 1:
                return diff_snapshots(source_scope, None, history[0])
            return None
        return diff_snapshots(source_scope, history[-2], history[-1])

    def diff_since_checkpoint(
        self,
        source_scope: str,
        current_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> DiffResult:
        ckpt = self.checkpoints_by_scope.get(source_scope)
        if current_chunks is not None:
            current_snap = take_snapshot(source_scope, current_chunks, SnapshotTrigger.MANUAL.value)
        else:
            history = self.snapshots_by_scope.get(source_scope, [])
            current_snap = history[-1] if history else take_snapshot(source_scope, [])
        return diff_snapshots(source_scope, ckpt, current_snap)
