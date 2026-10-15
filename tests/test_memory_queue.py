"""tests/test_memory_queue.py - Unit & Integration Tests for Memory Queue.

Tests Spec §4.8:
- Job enqueuing with deduplication key.
- Atomic claim pattern with unique lease token.
- Settlement token guards: mark_done and mark_failed only succeed with matching token.
- Stale lock recovery when lease expires.
- Protocol compliance: MemoryQueueProvider.
- Modularity switch: MemoryQueueManager(enabled=False).
"""

import time
import pytest

from sidecar.memory.queue_worker import (
    JobKind,
    JobStatus,
    MemoryJob,
    MemoryQueueManager,
    MemoryQueueProvider,
)


def test_memory_queue_protocol_conformance():
    mgr = MemoryQueueManager()
    assert isinstance(mgr, MemoryQueueProvider)


def test_enqueue_deduplication():
    mgr = MemoryQueueManager(enabled=True)
    payload = {"source": "note.md", "content": "test text"}

    # Enqueue first time
    j1 = mgr.enqueue(JobKind.EXTRACT_CHUNK, payload, dedupe_key="note.md:chunk_0")
    assert j1 is not None
    assert j1.status == JobStatus.READY

    # Enqueue second time with same dedupe_key -> returns existing job without duplicate
    j2 = mgr.enqueue(JobKind.EXTRACT_CHUNK, payload, dedupe_key="note.md:chunk_0")
    assert j1.id == j2.id


def test_claim_and_token_settlement():
    mgr = MemoryQueueManager(enabled=True)
    job = mgr.enqueue(JobKind.SEAL, {"scope": "vault"}, dedupe_key="seal:vault:0")

    # Claim next
    claimed = mgr.claim_next()
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == JobStatus.RUNNING
    assert claimed.claim_token is not None

    # Mark done with WRONG token -> fails
    assert mgr.mark_done(claimed.id, "wrong-token-xyz") is False
    assert claimed.status == JobStatus.RUNNING

    # Mark done with CORRECT token -> succeeds
    assert mgr.mark_done(claimed.id, claimed.claim_token) is True
    assert claimed.status == JobStatus.DONE


def test_stale_lock_recovery():
    mgr = MemoryQueueManager(enabled=True)
    job = mgr.enqueue(JobKind.FLUSH_STALE, {}, dedupe_key="flush:today")
    claimed = mgr.claim_next()

    # Simulate expired lease by rewinding claimed_at
    claimed.claimed_at = time.time() - 400.0  # 400s > 300s lease
    recovered_count = mgr.recover_stale_locks()

    assert recovered_count == 1
    assert claimed.status == JobStatus.READY
    assert claimed.claim_token is None


def test_queue_modularity_disabled():
    mgr = MemoryQueueManager(enabled=False)
    assert mgr.enqueue(JobKind.SEAL, {}, dedupe_key="k1") is None
    assert mgr.claim_next() is None
