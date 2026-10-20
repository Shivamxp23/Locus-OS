"""
SPEC §4.8: Memory Queue (Async Job Pipeline) Implementation.
Provides SqliteMemoryQueue with atomic claim leases, deduplication,
settlement guards, LLM semaphore, scheduler gate throttle checks, and worker pool.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sidecar.providers.memory_queue import (
    BaseMemoryQueueProvider,
    JobKind,
    JobRecord,
    JobStatus,
    MemoryQueueConfig,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path.home() / ".locus" / "memory" / "jobs.db"


class ThrottleGateStatus:
    CAPACITY = "capacity"
    THROTTLED = "throttled"
    PAUSED = "paused"


class SqliteMemoryQueue(BaseMemoryQueueProvider):
    """
    SPEC §4.8 line 955:
    Persistence (SQLite) Table: mem_tree_jobs
    Columns: id, kind, payload (JSON), status, dedupe_key,
             created_at, claimed_at, claim_token, completed_at,
             error_message, retry_count
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        config: Optional[MemoryQueueConfig] = None,
        throttle_gate_fn: Optional[Callable[[], str]] = None,
    ) -> None:
        cfg = config or MemoryQueueConfig()
        super().__init__(name="sqlite_memory_queue", config=cfg)
        self.db_path = db_path or cfg.db_path or str(DEFAULT_DB_PATH)
        self._lock = threading.Lock()
        self._llm_semaphore = threading.Semaphore(cfg.llm_concurrency)
        self._throttle_gate_fn = throttle_gate_fn or (lambda: ThrottleGateStatus.CAPACITY)
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
                    CREATE TABLE IF NOT EXISTS mem_tree_jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        kind TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'ready',
                        dedupe_key TEXT,
                        created_at TEXT NOT NULL,
                        claimed_at TEXT,
                        claim_token TEXT,
                        completed_at TEXT,
                        error_message TEXT,
                        retry_count INTEGER NOT NULL DEFAULT 0
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_mem_tree_jobs_dedupe_active
                    ON mem_tree_jobs(dedupe_key)
                    WHERE status IN ('ready', 'running') AND dedupe_key IS NOT NULL;
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_mem_tree_jobs_status_created
                    ON mem_tree_jobs(status, created_at);
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def enqueue(
        self,
        kind: str,
        payload: Dict[str, Any],
        dedupe_key: Optional[str] = None,
    ) -> Optional[int]:
        """
        SPEC §4.8 line 966:
        DEDUPLICATION:
          Each payload owns a dedupe_key() method
          Partial unique index: (dedupe_key) WHERE status IN ('ready','running')
          INSERT OR IGNORE → at-most-one-active duplicate suppression
        """
        payload_json = json.dumps(payload)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO mem_tree_jobs (kind, payload, status, dedupe_key, created_at)
                    VALUES (?, ?, 'ready', ?, ?)
                    RETURNING id;
                    """,
                    (kind, payload_json, dedupe_key, now_iso),
                )
                row = cursor.fetchone()
                conn.commit()
                if row:
                    return int(row["id"])
                return None
            finally:
                conn.close()

    def claim_next(
        self,
        worker_id: str,
        lock_duration_ms: Optional[int] = None,
    ) -> Optional[JobRecord]:
        """
        SPEC §4.8 line 973:
        CLAIM PATTERN:
          claim_next() = UPDATE ... SET status='running', claim_token=uuid
                         WHERE status='ready' ORDER BY created_at LIMIT 1
                         RETURNING *
          → Single atomic UPDATE...RETURNING (no SELECT-then-UPDATE race)
        """
        # Throttle integration per line 989: scheduler_gate check before claiming
        gate = self._throttle_gate_fn()
        if gate in (ThrottleGateStatus.THROTTLED, ThrottleGateStatus.PAUSED):
            return None

        token = f"{worker_id}:{uuid.uuid4().hex}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE mem_tree_jobs
                    SET status = 'running',
                        claimed_at = ?,
                        claim_token = ?
                    WHERE id = (
                        SELECT id FROM mem_tree_jobs
                        WHERE status = 'ready'
                        ORDER BY created_at ASC, id ASC
                        LIMIT 1
                    )
                    RETURNING id, kind, payload, status, dedupe_key, created_at,
                              claimed_at, claim_token, completed_at, error_message, retry_count;
                    """,
                    (now_iso, token),
                )
                row = cursor.fetchone()
                conn.commit()
                if not row:
                    return None
                return JobRecord.from_dict(dict(row))
            finally:
                conn.close()

    def mark_done(self, job_id: int, claim_token: str) -> bool:
        """
        SPEC §4.8 line 980:
        SETTLEMENT:
          mark_done(id, claim_token) → only succeeds if token matches
          Stale worker settlements are no-ops (token mismatch)
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE mem_tree_jobs
                    SET status = 'done',
                        completed_at = ?,
                        claim_token = NULL
                    WHERE id = ? AND claim_token = ? AND status = 'running';
                    """,
                    (now_iso, job_id, claim_token),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def mark_failed(self, job_id: int, claim_token: str, error_message: str = "") -> bool:
        """
        SPEC §4.8 line 981:
        SETTLEMENT:
          mark_failed(id, claim_token) → same token guard
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE mem_tree_jobs
                    SET status = 'failed',
                        completed_at = ?,
                        error_message = ?,
                        retry_count = retry_count + 1,
                        claim_token = NULL
                    WHERE id = ? AND claim_token = ? AND status = 'running';
                    """,
                    (now_iso, error_message, job_id, claim_token),
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def recover_stale_locks(self, lock_duration_ms: Optional[int] = None) -> int:
        """
        SPEC §4.8 line 996:
        STALE LOCK RECOVERY (startup):
          UPDATE mem_tree_jobs SET status='ready', claim_token=NULL
          WHERE status='running' AND claimed_at < now() - lock_duration
        """
        duration = self.config.lock_duration_ms if lock_duration_ms is None else lock_duration_ms
        cutoff = (datetime.now(timezone.utc) - timedelta(milliseconds=duration)).isoformat()

        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE mem_tree_jobs
                    SET status = 'ready',
                        claim_token = NULL,
                        retry_count = retry_count + 1
                    WHERE status = 'running' AND claimed_at <= ?;
                    """,
                    (cutoff,),
                )
                conn.commit()
                return cursor.rowcount
            finally:
                conn.close()

    def get_job(self, job_id: int) -> Optional[JobRecord]:
        """Retrieve job record by ID."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM mem_tree_jobs WHERE id = ?;", (job_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return JobRecord.from_dict(dict(row))
            finally:
                conn.close()

    def list_jobs(self, status: Optional[str] = None, limit: int = 50) -> List[JobRecord]:
        """List jobs optionally filtered by status."""
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                if status:
                    cursor.execute(
                        "SELECT * FROM mem_tree_jobs WHERE status = ? ORDER BY id DESC LIMIT ?;",
                        (status, limit),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM mem_tree_jobs ORDER BY id DESC LIMIT ?;",
                        (limit,),
                    )
                rows = cursor.fetchall()
                return [JobRecord.from_dict(dict(r)) for r in rows]
            finally:
                conn.close()

    def trigger_digest(self, date_str: str) -> Optional[int]:
        """
        SPEC §4.8 line 1007:
        Manual helper: trigger_digest(date) → enqueue single digest
        """
        return self.enqueue(
            kind=JobKind.DIGEST_DAILY.value,
            payload={"date": date_str},
            dedupe_key=f"digest_daily:{date_str}",
        )

    def backfill_missing_digests(self, from_date_str: str, to_date_str: str) -> List[int]:
        """
        SPEC §4.8 line 1008:
        Manual helper: backfill_missing_digests(from, to) → batch enqueue
        """
        start = date.fromisoformat(from_date_str)
        end = date.fromisoformat(to_date_str)
        if start > end:
            return []

        enqueued_ids: List[int] = []
        cur = start
        while cur <= end:
            d_str = cur.isoformat()
            job_id = self.trigger_digest(d_str)
            if job_id is not None:
                enqueued_ids.append(job_id)
            cur += timedelta(days=1)
        return enqueued_ids

    def flush_stale_daily(self, date_str: str) -> Optional[int]:
        """
        SPEC §4.8 line 1004:
        Enqueue FlushStale for time-stale buffers (>3h).
        """
        return self.enqueue(
            kind=JobKind.FLUSH_STALE.value,
            payload={"date": date_str},
            dedupe_key=f"flush_stale:{date_str}",
        )

    def daily_tick(self, today_date_str: Optional[str] = None) -> Tuple[Optional[int], Optional[int]]:
        """
        SPEC §4.8 line 1002:
        Daily tick at UTC 00:05:
          1. enqueue DigestDaily(yesterday)
          2. enqueue FlushStale(today)
        """
        today = date.fromisoformat(today_date_str) if today_date_str else datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        digest_id = self.trigger_digest(yesterday.isoformat())
        flush_id = self.flush_stale_daily(today.isoformat())
        return digest_id, flush_id

    def stats(self) -> Dict[str, Any]:
        """
        Queue metrics: count per status, active lease locks, total jobs.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT status, count(*) as cnt FROM mem_tree_jobs GROUP BY status;
                    """
                )
                counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}
                cursor.execute("SELECT count(*) as total FROM mem_tree_jobs;")
                total = cursor.fetchone()["total"]
                return {
                    "total": total,
                    "ready": counts.get(JobStatus.READY.value, 0),
                    "running": counts.get(JobStatus.RUNNING.value, 0),
                    "done": counts.get(JobStatus.DONE.value, 0),
                    "failed": counts.get(JobStatus.FAILED.value, 0),
                    "llm_concurrency": self.config.llm_concurrency,
                    "workers": self.config.workers,
                }
            finally:
                conn.close()

    def process_one_job(
        self,
        worker_id: str,
        job_handler: Optional[Callable[[JobRecord], Tuple[bool, Optional[str]]]] = None,
    ) -> Optional[Tuple[JobRecord, bool]]:
        """
        Execute one unit of work through worker pool.
        Integrates LLM semaphore (3 permits) for LLM-bound jobs.
        """
        job = self.claim_next(worker_id)
        if not job:
            return None

        is_llm_bound = job.kind in (
            JobKind.EXTRACT_CHUNK.value,
            JobKind.SEAL.value,
            JobKind.DIGEST_DAILY.value,
        )

        def _execute() -> Tuple[bool, Optional[str]]:
            if job_handler:
                return job_handler(job)
            # Default mock handler for pipeline progression
            return True, None

        success = False
        error_msg: Optional[str] = None

        try:
            if is_llm_bound:
                with self._llm_semaphore:
                    success, error_msg = _execute()
            else:
                success, error_msg = _execute()
        except Exception as exc:
            success = False
            error_msg = str(exc)

        if success:
            assert job.claim_token is not None
            self.mark_done(job.id, job.claim_token)
        else:
            assert job.claim_token is not None
            self.mark_failed(job.id, job.claim_token, error_message=error_msg or "Execution failed")

        return job, success
