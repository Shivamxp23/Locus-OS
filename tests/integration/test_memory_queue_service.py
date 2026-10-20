"""Integration tests for Memory Queue FastAPI service endpoints.

Tests Spec §4.8:
- GET /memory/queue/config: Subsystem health & settings.
- GET /memory/queue/stats: Status metrics & active concurrency.
- POST /memory/queue/enqueue: Job enqueue with dedupe suppression.
- POST /memory/queue/claim: Atomic claim with token.
- POST /memory/queue/settle: Settlement with token guard.
- POST /memory/queue/recover_stale: Expired lease recovery.
- POST /memory/queue/trigger_digest & backfill_digests: Scheduler helpers.
- Modular off-switch 503 behavior when disabled or workers == 0.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    
    orig_get = config.get

    def _cfg_get(key: str, default=None):
        if key == "locus.memory.queue.db_path":
            return tmp.name
        return orig_get(key, default)

    monkeypatch.setattr(config, "get", _cfg_get)
    config._CONFIG_CACHE = None
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    config._CONFIG_CACHE = None
    try:
        Path(tmp.name).unlink(missing_ok=True)
    except Exception:
        pass


def test_service_queue_config_and_stats(client: TestClient) -> None:
    """SPEC §4.8 line 930: "PURPOSE: Async job pipeline driving extraction, scoring, summarisation, and digesting OFF the ingest hot path."

    Asserts /memory/queue/config and /memory/queue/stats return active configuration and counts.
    """
    res_cfg = client.get("/memory/queue/config")
    assert res_cfg.status_code == 200
    data_cfg = res_cfg.json()
    assert data_cfg["status"] == "ok"
    assert data_cfg["enabled"] is True
    assert "config" in data_cfg

    res_stats = client.get("/memory/queue/stats")
    assert res_stats.status_code == 200
    data_stats = res_stats.json()
    assert data_stats["status"] == "ok"
    assert "ready" in data_stats["stats"]
    assert "total" in data_stats["stats"]


def test_service_enqueue_and_deduplication(client: TestClient) -> None:
    """SPEC §4.8 line 966: "Each payload owns a dedupe_key() method Partial unique index: (dedupe_key) WHERE status IN ('ready','running')"

    Asserts enqueue suppresses duplicate active tasks with identical dedupe_key.
    """
    res1 = client.post(
        "/memory/queue/enqueue",
        json={
            "kind": "extract_chunk",
            "payload": {"source_id": "doc42", "content": "hello world"},
            "dedupe_key": "extract:doc42",
        },
    )
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["status"] == "ok"
    assert d1["job_id"] is not None
    assert d1["suppressed"] is False

    # Second enqueue with same dedupe_key must be suppressed
    res2 = client.post(
        "/memory/queue/enqueue",
        json={
            "kind": "extract_chunk",
            "payload": {"source_id": "doc42", "content": "new text"},
            "dedupe_key": "extract:doc42",
        },
    )
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["status"] == "ok"
    assert d2["job_id"] is None
    assert d2["suppressed"] is True


def test_service_claim_and_settlement_workflow(client: TestClient) -> None:
    """SPEC §4.8 line 973: "claim_next() = UPDATE ... SET status='running', claim_token=uuid WHERE status='ready' ORDER BY created_at LIMIT 1 RETURNING *" and line 980 "mark_done(id, claim_token) → only succeeds if token matches"

    Asserts end-to-end atomic claim, settlement with token verification, and job inspection.
    """
    enq_res = client.post(
        "/memory/queue/enqueue",
        json={
            "kind": "seal",
            "payload": {"tree_scope": "global", "level": 1},
        },
    )
    job_id = enq_res.json()["job_id"]
    assert job_id is not None

    # Claim next job
    claim_res = client.post("/memory/queue/claim", json={"worker_id": "int-worker"})
    assert claim_res.status_code == 200
    claimed = claim_res.json()["job"]
    assert claimed is not None
    assert claimed["id"] == job_id
    token = claimed["claim_token"]
    assert token is not None

    # Attempt invalid settlement token
    bad_settle = client.post(
        "/memory/queue/settle",
        json={"job_id": job_id, "claim_token": "fake-token", "success": True},
    )
    assert bad_settle.status_code == 200
    assert bad_settle.json()["settled"] is False

    # Settle with correct token
    good_settle = client.post(
        "/memory/queue/settle",
        json={"job_id": job_id, "claim_token": token, "success": True},
    )
    assert good_settle.status_code == 200
    assert good_settle.json()["settled"] is True

    # Verify job record reflects done
    job_res = client.get(f"/memory/queue/jobs/{job_id}")
    assert job_res.status_code == 200
    job_data = job_res.json()["job"]
    assert job_data["status"] == "done"


def test_service_scheduler_helpers_and_recovery(client: TestClient) -> None:
    """SPEC §4.8 line 1007: "trigger_digest(date) → enqueue single digest" and line 1008 "backfill_missing_digests(from, to) → batch enqueue"

    Asserts digest triggering, batch backfilling, daily ticks, and stale recovery routes.
    """
    # Trigger single digest
    d_res = client.post("/memory/queue/trigger_digest", json={"date": "2027-04-10"})
    assert d_res.status_code == 200
    assert d_res.json()["job_id"] is not None

    # Backfill digests
    bf_res = client.post(
        "/memory/queue/backfill_digests",
        json={"from_date": "2027-04-11", "to_date": "2027-04-12"},
    )
    assert bf_res.status_code == 200
    assert len(bf_res.json()["enqueued_ids"]) == 2

    # Flush stale
    fs_res = client.post("/memory/queue/flush_stale", json={"date": "2027-04-12"})
    assert fs_res.status_code == 200
    assert fs_res.json()["job_id"] is not None

    # Daily tick
    tick_res = client.post("/memory/queue/daily_tick", json={"date": "2027-04-15"})
    assert tick_res.status_code == 200
    assert tick_res.json()["digest_job_id"] is not None
    assert tick_res.json()["flush_job_id"] is not None

    # Stale recovery
    rec_res = client.post("/memory/queue/recover_stale", json={"lock_duration_ms": 0})
    assert rec_res.status_code == 200
    assert "recovered_count" in rec_res.json()


def test_service_disabled_off_switch(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §4.8 line 1025: "Swappable / off state: locus.memory.queue.workers (0 = disabled). Off → extraction happens synchronously on the ingest path"

    Asserts HTTP 503 response when queue feature is disabled or workers count is 0.
    """
    monkeypatch.setattr(
        config,
        "get",
        lambda key, default=None: (
            False
            if key in ("locus.memory_queue_async_job_pipeline.enabled", "locus.memory.queue.enabled")
            else default
        ),
    )
    config._CONFIG_CACHE = None

    res = client.get("/memory/queue/config")
    assert res.status_code == 503
    assert "disabled" in res.json()
