"""
Unit tests for Memory Queue (Async Job Pipeline).
Verifies SqliteMemoryQueue per Spec §4.8 lines 925-1030.
"""
from __future__ import annotations

import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from sidecar.memory_queue import SqliteMemoryQueue, ThrottleGateStatus
from sidecar.providers.memory_queue import (
    JobKind,
    JobRecord,
    JobStatus,
    MemoryQueueConfig,
)


@pytest.fixture
def temp_queue() -> SqliteMemoryQueue:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    cfg = MemoryQueueConfig(workers=2, lock_duration_ms=500, llm_concurrency=3)
    queue = SqliteMemoryQueue(db_path=tmp.name, config=cfg)
    yield queue
    try:
        Path(tmp.name).unlink(missing_ok=True)
    except Exception:
        pass


def test_enqueue_and_deduplication(temp_queue: SqliteMemoryQueue) -> None:
    """SPEC §4.8 line 966: "INSERT OR IGNORE → at-most-one-active duplicate suppression"."""
    job_id1 = temp_queue.enqueue(
        kind=JobKind.EXTRACT_CHUNK.value,
        payload={"source_id": "file1", "content": "text"},
        dedupe_key="dedupe:file1",
    )
    assert job_id1 is not None

    # Duplicate active enqueue with same dedupe_key must be suppressed
    job_id2 = temp_queue.enqueue(
        kind=JobKind.EXTRACT_CHUNK.value,
        payload={"source_id": "file1", "content": "text_new"},
        dedupe_key="dedupe:file1",
    )
    assert job_id2 is None

    # Enqueue with different or no dedupe_key succeeds
    job_id3 = temp_queue.enqueue(
        kind=JobKind.APPEND_BUFFER.value,
        payload={"tree_scope": "global", "content": "abc"},
    )
    assert job_id3 is not None
    assert job_id3 != job_id1


def test_atomic_claim_next(temp_queue: SqliteMemoryQueue) -> None:
    """SPEC §4.8 line 973: "Single atomic UPDATE...RETURNING (no SELECT-then-UPDATE race)"."""
    job_id = temp_queue.enqueue(
        kind=JobKind.EXTRACT_CHUNK.value,
        payload={"source_id": "s1", "content": "hello world"},
    )
    assert job_id is not None

    claimed = temp_queue.claim_next(worker_id="worker-A")
    assert claimed is not None
    assert claimed.id == job_id
    assert claimed.status == JobStatus.RUNNING.value
    assert claimed.claim_token is not None
    assert claimed.claim_token.startswith("worker-A:")

    # Second claim returns None when queue is empty
    claimed_again = temp_queue.claim_next(worker_id="worker-B")
    assert claimed_again is None


def test_settlement_mark_done_token_guard(temp_queue: SqliteMemoryQueue) -> None:
    """SPEC §4.8 line 980: "mark_done(id, claim_token) → only succeeds if token matches"."""
    job_id = temp_queue.enqueue(
        kind=JobKind.SEAL.value,
        payload={"tree_scope": "global", "level": 0},
    )
    assert job_id is not None
    claimed = temp_queue.claim_next(worker_id="worker-A")
    assert claimed is not None

    # Invalid token mismatch settlement fails
    invalid_settled = temp_queue.mark_done(job_id=claimed.id, claim_token="wrong-token")
    assert invalid_settled is False

    # Valid token settlement succeeds
    valid_settled = temp_queue.mark_done(job_id=claimed.id, claim_token=claimed.claim_token)  # type: ignore[arg-type]
    assert valid_settled is True

    # Re-settlement fails (already done)
    resettled = temp_queue.mark_done(job_id=claimed.id, claim_token=claimed.claim_token)  # type: ignore[arg-type]
    assert resettled is False

    updated = temp_queue.get_job(claimed.id)
    assert updated is not None
    assert updated.status == JobStatus.DONE.value
    assert updated.claim_token is None


def test_settlement_mark_failed_token_guard(temp_queue: SqliteMemoryQueue) -> None:
    """SPEC §4.8 line 981: "mark_failed(id, claim_token) → same token guard"."""
    job_id = temp_queue.enqueue(
        kind=JobKind.TOPIC_ROUTE.value,
        payload={"chunk_content": "rust topic", "source_context": "code"},
    )
    assert job_id is not None
    claimed = temp_queue.claim_next(worker_id="worker-X")
    assert claimed is not None

    # Invalid token fails
    assert temp_queue.mark_failed(claimed.id, "bad-token", "some error") is False

    # Valid token succeeds
    assert temp_queue.mark_failed(claimed.id, claimed.claim_token, "failed to parse") is True  # type: ignore[arg-type]

    updated = temp_queue.get_job(claimed.id)
    assert updated is not None
    assert updated.status == JobStatus.FAILED.value
    assert updated.error_message == "failed to parse"
    assert updated.retry_count == 1


def test_stale_lock_recovery(temp_queue: SqliteMemoryQueue) -> None:
    """SPEC §4.8 line 996: "UPDATE mem_tree_jobs SET status='ready', claim_token=NULL WHERE status='running' AND claimed_at < now() - lock_duration"."""
    job_id = temp_queue.enqueue(
        kind=JobKind.EXTRACT_CHUNK.value,
        payload={"source_id": "file99", "content": "stale test"},
    )
    assert job_id is not None
    claimed = temp_queue.claim_next(worker_id="worker-crash")
    assert claimed is not None

    # Before lock expiration, recovery recovers 0
    recovered_early = temp_queue.recover_stale_locks(lock_duration_ms=5000)
    assert recovered_early == 0

    # Wait or pass 0 ms duration to trigger immediate recovery
    recovered = temp_queue.recover_stale_locks(lock_duration_ms=0)
    assert recovered == 1

    job_after = temp_queue.get_job(job_id)
    assert job_after is not None
    assert job_after.status == JobStatus.READY.value
    assert job_after.claim_token is None
    assert job_after.retry_count == 1

    # Now another worker can claim it
    reclaimed = temp_queue.claim_next(worker_id="worker-recovered")
    assert reclaimed is not None
    assert reclaimed.id == job_id


def test_throttle_gate_backoff(temp_queue: SqliteMemoryQueue) -> None:
    """SPEC §4.8 line 989: "IF gate == Throttled: back off without holding DB leases"."""
    temp_queue.enqueue(
        kind=JobKind.APPEND_BUFFER.value,
        payload={"tree_scope": "topic-1", "content": "data"},
    )

    # Inject throttled gate state
    temp_queue._throttle_gate_fn = lambda: ThrottleGateStatus.THROTTLED
    assert temp_queue.claim_next(worker_id="w1") is None

    # Inject paused gate state
    temp_queue._throttle_gate_fn = lambda: ThrottleGateStatus.PAUSED
    assert temp_queue.claim_next(worker_id="w1") is None

    # When capacity returns, claiming succeeds
    temp_queue._throttle_gate_fn = lambda: ThrottleGateStatus.CAPACITY
    claimed = temp_queue.claim_next(worker_id="w1")
    assert claimed is not None


def test_trigger_digest_and_backfill(temp_queue: SqliteMemoryQueue) -> None:
    """SPEC §4.8 line 1007: "trigger_digest(date) → enqueue single digest" and line 1008 "backfill_missing_digests(from, to) → batch enqueue"."""
    single_id = temp_queue.trigger_digest("2027-04-01")
    assert single_id is not None

    # Deduplication check for same date
    dup_id = temp_queue.trigger_digest("2027-04-01")
    assert dup_id is None

    # Backfill range
    backfill_ids = temp_queue.backfill_missing_digests("2027-04-02", "2027-04-04")
    assert len(backfill_ids) == 3

    # Flush stale daily
    flush_id = temp_queue.flush_stale_daily("2027-04-04")
    assert flush_id is not None


def test_daily_tick_schedule(temp_queue: SqliteMemoryQueue) -> None:
    """SPEC §4.8 line 1002: "Daily tick at UTC 00:05: 1. enqueue DigestDaily(yesterday) 2. enqueue FlushStale(today)"."""
    digest_id, flush_id = temp_queue.daily_tick("2027-04-05")
    assert digest_id is not None
    assert flush_id is not None

    digest_job = temp_queue.get_job(digest_id)
    assert digest_job is not None
    assert digest_job.payload["date"] == "2027-04-04"  # yesterday

    flush_job = temp_queue.get_job(flush_id)
    assert flush_job is not None
    assert flush_job.payload["date"] == "2027-04-05"  # today
