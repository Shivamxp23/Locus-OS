"""
SPEC §4.8: Memory Queue (Async Job Pipeline) Provider Interfaces.
Defines JobKind, JobStatus, JobRecord, MemoryQueueConfig, and BaseMemoryQueueProvider.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class JobKind(str, Enum):
    """
    SPEC §4.8 line 948:
    Job types for async memory processing pipeline.
    """
    EXTRACT_CHUNK = "extract_chunk"
    APPEND_BUFFER = "append_buffer"
    SEAL = "seal"
    TOPIC_ROUTE = "topic_route"
    DIGEST_DAILY = "digest_daily"
    FLUSH_STALE = "flush_stale"


class JobStatus(str, Enum):
    """
    SPEC §4.8 line 964:
    Status enum: Ready, Running, Done, Failed
    """
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class JobRecord:
    """
    SPEC §4.8 line 957:
    Table: mem_tree_jobs
    Columns: id, kind, payload (JSON), status, dedupe_key,
             created_at, claimed_at, claim_token, completed_at,
             error_message, retry_count
    """
    id: int
    kind: str
    payload: Dict[str, Any]
    status: str = JobStatus.READY.value
    dedupe_key: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    claimed_at: Optional[str] = None
    claim_token: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> JobRecord:
        payload = data.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {"raw": payload}
        return cls(
            id=data["id"],
            kind=data["kind"],
            payload=payload,
            status=data.get("status", JobStatus.READY.value),
            dedupe_key=data.get("dedupe_key"),
            created_at=data.get("created_at", ""),
            claimed_at=data.get("claimed_at"),
            claim_token=data.get("claim_token"),
            completed_at=data.get("completed_at"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class MemoryQueueConfig:
    """
    Configuration for Memory Queue async job pipeline per Spec §4.8.
    """
    workers: int = 2
    enabled: bool = True
    db_path: Optional[str] = None
    lock_duration_ms: int = 300_000
    llm_concurrency: int = 3
    throttle_gate_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseMemoryQueueProvider(ABC):
    """
    SPEC §4.8 line 930:
    Async job pipeline driving extraction, scoring, summarisation,
    and digesting OFF the ingest hot path.
    """

    def __init__(self, name: str = "default", config: Optional[MemoryQueueConfig] = None) -> None:
        self.name = name
        self.config = config or MemoryQueueConfig()

    @abstractmethod
    def enqueue(
        self,
        kind: str,
        payload: Dict[str, Any],
        dedupe_key: Optional[str] = None,
    ) -> Optional[int]:
        """
        SPEC §4.8 line 966:
        Enqueues job with dedupe_key suppression. Returns job_id or None if suppressed.
        """
        raise NotImplementedError

    @abstractmethod
    def claim_next(
        self,
        worker_id: str,
        lock_duration_ms: Optional[int] = None,
    ) -> Optional[JobRecord]:
        """
        SPEC §4.8 line 973:
        Single atomic claim using UPDATE ... SET status='running', claim_token=uuid.
        """
        raise NotImplementedError

    @abstractmethod
    def mark_done(self, job_id: int, claim_token: str) -> bool:
        """
        SPEC §4.8 line 980:
        Settlement: mark_done(id, claim_token) only succeeds if token matches.
        """
        raise NotImplementedError

    @abstractmethod
    def mark_failed(self, job_id: int, claim_token: str, error_message: str = "") -> bool:
        """
        SPEC §4.8 line 981:
        Settlement: mark_failed(id, claim_token) with token guard.
        """
        raise NotImplementedError

    @abstractmethod
    def recover_stale_locks(self, lock_duration_ms: Optional[int] = None) -> int:
        """
        SPEC §4.8 line 996:
        Stale lock recovery at startup or tick: resets expired running jobs to ready.
        """
        raise NotImplementedError

    @abstractmethod
    def trigger_digest(self, date: str) -> Optional[int]:
        """
        SPEC §4.8 line 1007:
        Manual helper: enqueue single digest_daily job.
        """
        raise NotImplementedError

    @abstractmethod
    def backfill_missing_digests(self, from_date: str, to_date: str) -> List[int]:
        """
        SPEC §4.8 line 1008:
        Manual helper: batch enqueue missing digest_daily jobs for date range.
        """
        raise NotImplementedError

    @abstractmethod
    def flush_stale_daily(self, date: str) -> Optional[int]:
        """
        SPEC §4.8 line 1004:
        Enqueue FlushStale job for time-stale buffers (>3h).
        """
        raise NotImplementedError

    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """
        Queue statistics (counts per status, active locks, total jobs).
        """
        raise NotImplementedError
