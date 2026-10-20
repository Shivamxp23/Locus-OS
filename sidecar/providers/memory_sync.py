"""Memory Sync Provider interfaces and data contracts.

Implements Spec §4.7:
- Unified SyncPipeline trait and SyncOutcome contract.
- Three pipeline kinds: Composio (Direct API), Workspace (local files/turns), MCP (third-party tools).
- Schedulers and periodic loops (20-min ticks, 3-hour queue).
- Raw-archive coverage and self-healing tree rebuilds.
- Hard layer boundaries: all writes canonicalized through ingestion pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Dict, List, Optional, Set
import uuid


class SyncPipelineKind(str, Enum):
    """Pipeline categories per Spec §4.7 line 856."""

    COMPOSIO = "composio"  # External APIs: Gmail, Slack, GitHub, Notion, Linear, ClickUp
    WORKSPACE = "workspace"  # Local files: Obsidian vault, conversation history, dictation
    MCP = "mcp"  # Third-party Model Context Protocol servers


@dataclass
class SyncOutcome:
    """Outcome of a pipeline sync tick per Spec §4.7 line 850.

    SPEC §4.7 line 850:
    SyncOutcome {
      records_ingested: u64,
      more_pending: bool,    // pagination: caller should tick again
      note: Option<String>,  // human-readable status
    }
    """

    records_ingested: int = 0
    more_pending: bool = False
    note: Optional[str] = None
    cursor: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert outcome to dictionary."""
        return {
            "records_ingested": self.records_ingested,
            "more_pending": self.more_pending,
            "note": self.note,
            "cursor": self.cursor,
            "errors": list(self.errors),
            "duration_ms": self.duration_ms,
        }


@dataclass
class SourceScope:
    """Mapping between raw archive ID and tree scope per Spec §4.7 line 899.

    SPEC §4.7 line 899:
    // GOTCHA: tree scope and raw-archive ID slugify DIFFERENTLY
    // for GitHub: "github:owner/repo" vs "github.com/owner/repo"
    // Always carry both (SourceScope struct)
    """

    tree_scope: str  # e.g. "github:owner/repo"
    raw_archive_id: str  # e.g. "github.com/owner/repo"
    provider: str = "generic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tree_scope": self.tree_scope,
            "raw_archive_id": self.raw_archive_id,
            "provider": self.provider,
        }


@dataclass
class MemorySyncConfig:
    """Configuration for Multi-Source Memory Sync subsystem per Spec §4.7 line 921."""

    enabled: bool = True
    periodic_interval_seconds: float = 1200.0  # 20 minutes (line 877)
    queue_scheduler_interval_seconds: float = 10800.0  # 3 hours (line 881)
    daily_budget_cap: int = 1000
    state_db_path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "periodic_interval_seconds": self.periodic_interval_seconds,
            "queue_scheduler_interval_seconds": self.queue_scheduler_interval_seconds,
            "daily_budget_cap": self.daily_budget_cap,
            "state_db_path": self.state_db_path,
        }


class BaseSyncPipeline(ABC):
    """Unified SyncPipeline trait per Spec §4.7 line 843.

    SPEC §4.7 line 843:
    trait SyncPipeline: Send + Sync {
      async fn init(&self, config: &Config) → Result<()>
      async fn tick(&self, config: &Config) → Result<SyncOutcome>
      fn id(&self) → &str             // unique pipeline identifier
      fn kind(&self) → SyncPipelineKind  // Composio | Workspace | Mcp
    }
    """

    def __init__(self, pipeline_id: str, kind: SyncPipelineKind, name: str = "sync_pipeline") -> None:
        self.pipeline_id = pipeline_id
        self.pipeline_kind = kind
        self.name = name

    def id(self) -> str:
        """Return unique pipeline identifier."""
        return self.pipeline_id

    def kind(self) -> SyncPipelineKind:
        """Return pipeline category."""
        return self.pipeline_kind

    @abstractmethod
    def init(self, config: MemorySyncConfig) -> bool:
        """Initialize pipeline with configuration."""
        ...

    @abstractmethod
    def tick(self, config: MemorySyncConfig) -> SyncOutcome:
        """Execute single sync step, returning ingested count and pending state."""
        ...

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Return runtime health and cursor status."""
        ...


class BaseMemorySyncProvider(ABC):
    """Provider interface for Multi-Source Ingestion Pipelines per Spec §4.7 line 914."""

    def __init__(self, name: str = "memory_sync") -> None:
        self.name = name

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return True if memory sync operations are enabled."""
        ...

    @abstractmethod
    def register_pipeline(self, pipeline: BaseSyncPipeline) -> bool:
        """Register a sync pipeline."""
        ...

    @abstractmethod
    def get_pipeline(self, pipeline_id: str) -> Optional[BaseSyncPipeline]:
        """Retrieve registered pipeline by ID."""
        ...

    @abstractmethod
    def list_pipelines(self) -> list[dict[str, Any]]:
        """List all registered pipelines and statuses."""
        ...

    @abstractmethod
    def tick_pipeline(self, pipeline_id: str) -> SyncOutcome:
        """Execute single pipeline tick."""
        ...

    @abstractmethod
    def tick_all(self) -> dict[str, SyncOutcome]:
        """Execute sync step across all active pipelines."""
        ...

    @abstractmethod
    def check_and_rebuild_tree(self, source: SourceScope, on_disk_files: list[str]) -> list[str]:
        """Self-healing raw-archive set difference reconciliation per Spec §4.7 lines 887-898."""
        ...

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return overall sync manager health and ingestion statistics."""
        ...
