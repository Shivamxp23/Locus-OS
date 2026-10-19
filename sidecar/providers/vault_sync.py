"""
SPEC §03 / §27.2 / F-0060 / US-16: VaultSyncProvider interface.
Universal provider pattern for Obsidian vault synchronization engines (LiveSync/CouchDB, local_only, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class SyncState:
    """State of vault synchronization."""
    connected: bool
    sync_engine: str
    database: str
    last_synced: Optional[int] = None
    pending_changes: int = 0
    error: Optional[str] = None


class BaseVaultSyncProvider(ABC):
    """Abstract base class for vault sync providers."""

    def __init__(self, name: str = "vault_sync") -> None:
        self.name = name
        self._connected: bool = False

    def is_connected(self) -> bool:
        """Return connectivity status."""
        return self._connected

    @abstractmethod
    def initialize(self, options: Optional[dict[str, Any]] = None) -> None:
        """Initialize sync provider with options."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Cleanly shutdown the sync provider."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """
        Check health of the vault sync provider.
        Returns dict with status ('ok' | 'degraded' | 'error'), latency_ms, error (if any).
        """
        pass

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Return sync engine status details."""
        pass

    @abstractmethod
    def push(self, rel_path: str, mtime: Optional[int] = None) -> dict[str, Any]:
        """Push a local vault note to remote synchronization store."""
        pass

    @abstractmethod
    def pull(self, rel_path: Optional[str] = None) -> dict[str, Any]:
        """Pull remote changes for a specific path or process changes feed."""
        pass

    @abstractmethod
    def resolve_conflicts(
        self, disk_path: Path, remote_doc: dict[str, Any], remote_bytes: bytes
    ) -> dict[str, Any]:
        """
        Deterministically resolve concurrent edit conflicts between disk and remote revision.
        Guarantees both revisions are preserved without inserting conflict markers into notes.
        """
        pass
