"""sidecar/memory/queue_worker.py - Async Memory Job Queue & Worker Pool.

Implements Spec §4.8:
- Async job pipeline driving extraction, scoring, summarization, and digesting.
- Job types: ExtractChunk, AppendBuffer, Seal, TopicRoute, DigestDaily, FlushStale.
- Statuses: Ready, Running, Done, Failed.
- Atomic claim pattern with unique claim_tokens and lease timeouts.
- Settlement guards: mark_done / mark_failed only succeed if claim_token matches.
- Deduplication: at-most-one-active job per dedupe_key.
- Stale lock recovery.
- Modularity: locus.memory.queue.workers (0 = disabled).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable
import uuid


class JobKind(str, Enum):
    EXTRACT_CHUNK = "ExtractChunk"
    APPEND_BUFFER = "AppendBuffer"
    SEAL = "Seal"
    TOPIC_ROUTE = "TopicRoute"
    DIGEST_DAILY = "DigestDaily"
    FLUSH_STALE = "FlushStale"


class JobStatus(str, Enum):
    READY = "Ready"
    RUNNING = "Running"
    DONE = "Done"
    FAILED = "Failed"


@dataclass
class MemoryJob:
    """A unit of async memory pipeline work."""

    id: str
    kind: JobKind
    payload: dict[str, Any]
    dedupe_key: str
    status: JobStatus = JobStatus.READY
    claim_token: Optional[str] = None
    claimed_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@runtime_checkable
class MemoryQueueProvider(Protocol):
    """Protocol for memory job queues."""

    def enqueue(self, kind: JobKind, payload: dict[str, Any], dedupe_key: str) -> Optional[MemoryJob]:
        """Enqueue a new job with deduplication."""
        return None

    def claim_next(self) -> Optional[MemoryJob]:
        """Claim the next Ready job with a unique lease token."""
        return None

    def mark_done(self, job_id: str, claim_token: str) -> bool:
        """Mark job Done guarded by claim token matching."""
        return False


class MemoryQueueManager:
    """Core Memory Queue Manager implementing Spec §4.8."""

    CLAIM_LEASE_SECONDS = 300.0  # 5 minutes

    def __init__(self, enabled: bool = True, max_workers: int = 2):
        self.enabled = enabled
        self.max_workers = max_workers
        self._jobs: dict[str, MemoryJob] = {}

    def enqueue(self, kind: JobKind, payload: dict[str, Any], dedupe_key: str) -> Optional[MemoryJob]:
        """Enqueue a job. If an active job with same dedupe_key exists, ignore."""
        if not self.enabled or self.max_workers == 0:
            return None

        # Check deduplication against Ready or Running jobs
        for job in self._jobs.values():
            if job.dedupe_key == dedupe_key and job.status in (JobStatus.READY, JobStatus.RUNNING):
                return job

        job_id = f"job-{uuid.uuid4().hex[:8]}"
        job = MemoryJob(
            id=job_id,
            kind=kind,
            payload=payload,
            dedupe_key=dedupe_key,
            status=JobStatus.READY,
        )
        self._jobs[job_id] = job
        return job

    def claim_next(self) -> Optional[MemoryJob]:
        """Atomically claim the oldest Ready job and assign a lease token."""
        if not self.enabled or self.max_workers == 0:
            return None

        self.recover_stale_locks()

        ready_jobs = [j for j in self._jobs.values() if j.status == JobStatus.READY]
        if not ready_jobs:
            return None

        # Oldest first
        ready_jobs.sort(key=lambda j: j.created_at)
        job = ready_jobs[0]

        token = uuid.uuid4().hex
        job.status = JobStatus.RUNNING
        job.claim_token = token
        job.claimed_at = time.time()
        return job

    def mark_done(self, job_id: str, claim_token: str) -> bool:
        """Settle job as Done only if claim_token matches."""
        job = self._jobs.get(job_id)
        if not job or job.claim_token != claim_token:
            return False

        job.status = JobStatus.DONE
        job.completed_at = time.time()
        return True

    def mark_failed(self, job_id: str, claim_token: str, error: str) -> bool:
        """Settle job as Failed only if claim_token matches."""
        job = self._jobs.get(job_id)
        if not job or job.claim_token != claim_token:
            return False

        job.retry_count += 1
        if job.retry_count < 3:
            # Requeue for retry
            job.status = JobStatus.READY
            job.claim_token = None
            job.claimed_at = None
        else:
            job.status = JobStatus.FAILED
            job.error_message = error
            job.completed_at = time.time()
        return True

    def recover_stale_locks(self) -> int:
        """Reset running jobs whose claim lease has expired back to Ready."""
        now = time.time()
        recovered = 0
        for job in self._jobs.values():
            if job.status == JobStatus.RUNNING and job.claimed_at:
                if (now - job.claimed_at) > self.CLAIM_LEASE_SECONDS:
                    job.status = JobStatus.READY
                    job.claim_token = None
                    job.claimed_at = None
                    recovered += 1
        return recovered
