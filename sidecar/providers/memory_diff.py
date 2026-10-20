"""
SPEC §4.9: Memory Diff (Snapshot-Based Change Tracking) Provider Interfaces.
Defines core snapshot, item change, diff result, checkpoint, and provider interfaces.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SnapshotTrigger(str, Enum):
    """
    SPEC §4.9 line 1045:
    trigger: SnapshotTrigger // AutoPostSync | Manual | Checkpoint
    """
    AUTO_POST_SYNC = "auto_post_sync"
    MANUAL = "manual"
    CHECKPOINT = "checkpoint"


class ChangeKind(str, Enum):
    """
    SPEC §4.9 line 1064:
    kind: ChangeKind // Added | Removed | Modified
    """
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class SnapshotItem:
    """
    SPEC §4.9 line 1051:
    SnapshotItem { chunk_id: str, content_hash: str, title: Option<str>, token_count: u32 }
    """
    chunk_id: str
    content_hash: str
    title: Optional[str] = None
    token_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SnapshotItem:
        return cls(
            chunk_id=data["chunk_id"],
            content_hash=data["content_hash"],
            title=data.get("title"),
            token_count=int(data.get("token_count", 0)),
        )


@dataclass
class Snapshot:
    """
    SPEC §4.9 line 1043:
    Snapshot { id: UUID, source_scope: str, trigger: SnapshotTrigger, items: [SnapshotItem], created_at: DateTime }
    """
    id: str
    source_scope: str
    trigger: str
    items: List[SnapshotItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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
        raw_items = data.get("items", [])
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except Exception:
                raw_items = []
        items = [SnapshotItem.from_dict(it) if isinstance(it, dict) else it for it in raw_items]
        return cls(
            id=data["id"],
            source_scope=data["source_scope"],
            trigger=data.get("trigger", SnapshotTrigger.MANUAL.value),
            items=items,
            created_at=data.get("created_at", ""),
        )


@dataclass
class ItemChange:
    """
    SPEC §4.9 line 1063:
    ItemChange { kind: ChangeKind, chunk_id: str, title: Option<str>, old_hash: Option<str>, new_hash: Option<str> }
    """
    kind: str
    chunk_id: str
    title: Optional[str] = None
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiffSummary:
    """
    SPEC §4.9 line 1071:
    DiffSummary { added: u32, removed: u32, modified: u32, unchanged: u32 }
    """
    added: int = 0
    removed: int = 0
    modified: int = 0
    unchanged: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiffResult:
    """
    SPEC §4.9 line 1056:
    DiffResult { source_scope: str, from_snapshot: UUID, to_snapshot: UUID, changes: [ItemChange], summary: DiffSummary }
    """
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


@dataclass
class Checkpoint:
    """
    SPEC §4.9 line 1099:
    Checkpoint { name: str, snapshot_ids: { source_scope → snapshot_id } }
    """
    name: str
    snapshot_ids: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrossSourceDiff:
    """
    SPEC §4.9 line 1114:
    CrossSourceDiff { checkpoint_name: str, diffs: { source_scope → DiffResult }, total_summary: DiffSummary }
    """
    checkpoint_name: str
    diffs: Dict[str, DiffResult] = field(default_factory=dict)
    total_summary: DiffSummary = field(default_factory=DiffSummary)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_name": self.checkpoint_name,
            "diffs": {k: v.to_dict() for k, v in self.diffs.items()},
            "total_summary": self.total_summary.to_dict(),
        }


@dataclass
class MemoryDiffConfig:
    """
    Configuration for Memory Diff subsystem per Spec §4.9.
    """
    enabled: bool = True
    db_path: Optional[str] = None
    auto_snapshot_post_sync: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseMemoryDiffProvider(ABC):
    """
    SPEC §4.9 line 1035:
    Base provider for snapshot-based change tracking.
    """

    def __init__(self, name: str = "default", config: Optional[MemoryDiffConfig] = None) -> None:
        self.name = name
        self.config = config or MemoryDiffConfig()

    @abstractmethod
    def take_snapshot(
        self,
        source_scope: str,
        trigger: str = SnapshotTrigger.MANUAL.value,
        items: Optional[List[Dict[str, Any]]] = None,
    ) -> Snapshot:
        """
        SPEC §4.9 line 1079:
        Captures chunk store state as a snapshot and returns the created Snapshot.
        """
        raise NotImplementedError

    @abstractmethod
    def diff(
        self,
        source_scope: str,
        from_snapshot_id: str,
        to_snapshot_id: str,
    ) -> DiffResult:
        """
        SPEC §4.9 line 1089:
        Diffs two snapshots by comparing chunk_id keys and SHA-256 hashes.
        """
        raise NotImplementedError

    @abstractmethod
    def create_checkpoint(
        self,
        name: str,
        scopes: Optional[List[str]] = None,
        scope_items: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Checkpoint:
        """
        SPEC §4.9 line 1104:
        Creates a named baseline checkpoint across active source scopes.
        """
        raise NotImplementedError

    @abstractmethod
    def diff_since_checkpoint(
        self,
        name: str,
        current_scope_items: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> CrossSourceDiff:
        """
        SPEC §4.9 line 1109:
        Diffs current memory state against baseline checkpoint.
        """
        raise NotImplementedError

    @abstractmethod
    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Retrieve snapshot by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_snapshots(
        self,
        source_scope: Optional[str] = None,
        limit: int = 50,
    ) -> List[Snapshot]:
        """List snapshots optionally filtered by source scope."""
        raise NotImplementedError

    @abstractmethod
    def what_changed(
        self,
        checkpoint_name: Optional[str] = None,
        source_scope: Optional[str] = None,
    ) -> str:
        """
        SPEC §4.9 line 1120:
        Agent tool action returning concise human-readable diff summary.
        """
        raise NotImplementedError
