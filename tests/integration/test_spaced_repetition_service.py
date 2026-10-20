"""
SPEC §4.13: Spaced Repetition Memory Consolidation Integration Tests.
Verifies FastAPI sidecar endpoints for calculating intervals, recording reviews,
fetching due nodes, running nightly consolidation, and the modular off-switch.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sidecar.memory.memory_scheduler import SpacedRepetitionMemoryScheduler
from sidecar.providers.spaced_repetition import MemoryNodeState, SpacedRepetitionConfig
from sidecar.service import create_app


@pytest.fixture
def client_and_scheduler() -> Generator[tuple[TestClient, SpacedRepetitionMemoryScheduler, str], None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_sr_service.db")
        scheduler = SpacedRepetitionMemoryScheduler(db_path=db_path)
        app = create_app()
        app.state.registry.register("spaced_repetition", "default", lambda **kw: scheduler)
        app.state.registry.register("memory_consolidation", "default", lambda **kw: scheduler)
        client = TestClient(app)
        yield client, scheduler, db_path


def test_service_get_config(client_and_scheduler: tuple[TestClient, SpacedRepetitionMemoryScheduler, str]) -> None:
    """SPEC §4.13 line 1406: "Swappable / off state: locus.memory.spaced_repetition.enabled. Off -> nodes do not decay or schedule reviews"."""
    client, _, _ = client_and_scheduler
    res = client.get("/memory/spaced_repetition/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["config"]["default_ease_factor"] == 2.50
    assert data["config"]["min_ease_factor"] == 1.30


def test_service_calculate_stateless(client_and_scheduler: tuple[TestClient, SpacedRepetitionMemoryScheduler, str]) -> None:
    """SPEC §4.13 line 1355: "FUNCTION calculate_next_review(state: MemoryNodeState, quality_grade: int) -> MemoryNodeState"."""
    client, _, _ = client_and_scheduler
    body = {
        "state": {
            "node_id": "concept:gravity",
            "repetition_count": 0,
            "ease_factor": 2.50,
            "interval_days": 1,
            "stability": 1.0,
        },
        "quality_grade": 4,
        "timestamp": 1000000.0,
    }
    res = client.post("/memory/spaced_repetition/calculate", json=body)
    assert res.status_code == 200
    data = res.json()
    assert data["repetition_count"] == 1
    assert data["interval_days"] == 1
    assert data["due_date"] == 1000000.0 + 86400.0


def test_service_node_crud_and_review(client_and_scheduler: tuple[TestClient, SpacedRepetitionMemoryScheduler, str]) -> None:
    """SPEC §4.13 line 1395: "neo4j.save_node_state(node.id, updated_state)"."""
    client, _, _ = client_and_scheduler
    node_id = "concept:relativity"

    # Save initial node state
    save_res = client.post(
        f"/memory/spaced_repetition/nodes/{node_id}",
        json={"repetition_count": 1, "interval_days": 6, "ease_factor": 2.50},
    )
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "ok"

    # Fetch node state
    get_res = client.get(f"/memory/spaced_repetition/nodes/{node_id}")
    assert get_res.status_code == 200
    assert get_res.json()["repetition_count"] == 1

    # Record review with grade 5 (ease factor increases, interval advances)
    review_res = client.post(
        "/memory/spaced_repetition/review",
        json={"node_id": node_id, "quality_grade": 5, "timestamp": 2000000.0},
    )
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert review_data["repetition_count"] == 2
    assert review_data["ease_factor"] == 2.60


def test_service_due_nodes_and_consolidation(client_and_scheduler: tuple[TestClient, SpacedRepetitionMemoryScheduler, str]) -> None:
    """SPEC §4.13 line 1381: "NIGHTLY MEMORY CONSOLIDATION WORKER (02:30 IST): FUNCTION run_spaced_repetition_consolidation():"."""
    client, _, _ = client_and_scheduler
    now = 500000.0

    # Create due node
    client.post(
        "/memory/spaced_repetition/nodes/node_overdue",
        json={"due_date": now - 100.0, "repetition_count": 4, "ease_factor": 2.50},
    )
    # Create future node
    client.post(
        "/memory/spaced_repetition/nodes/node_future",
        json={"due_date": now + 50000.0, "repetition_count": 1, "ease_factor": 2.50},
    )

    # Check due nodes
    due_res = client.get(f"/memory/spaced_repetition/due?limit=10&timestamp={now}")
    assert due_res.status_code == 200
    due_nodes = [n["node_id"] for n in due_res.json()["nodes"]]
    assert "node_overdue" in due_nodes
    assert "node_future" not in due_nodes

    # Run consolidation with simulated grade 5, promoting node_overdue (rep 4 -> 5, ease 2.60) to CORE_FACT
    cons_res = client.post(
        "/memory/spaced_repetition/consolidate",
        json={"limit": 10, "simulated_grades": {"node_overdue": 5}, "timestamp": now},
    )
    assert cons_res.status_code == 200
    cons_data = cons_res.json()["result"]
    assert cons_data["processed_count"] == 1
    assert "node_overdue" in cons_data["promoted_core_facts"]

    # Verify via core facts endpoint
    core_res = client.get("/memory/spaced_repetition/core_facts")
    assert core_res.status_code == 200
    core_ids = [n["node_id"] for n in core_res.json()["core_facts"]]
    assert "node_overdue" in core_ids


def test_service_modular_off_switch() -> None:
    """SPEC §4.13 line 1406: "Registers as a provider in sidecar/providers/ with modular off-switch locus.spaced_repetition.enabled returning 503"."""
    app = create_app()
    client = TestClient(app)

    with patch("sidecar.config.get", return_value=False):
        res1 = client.get("/memory/spaced_repetition/config")
        assert res1.status_code == 503
        assert res1.json() == {"disabled": "locus.spaced_repetition.enabled"}

        res2 = client.post("/memory/spaced_repetition/calculate", json={"quality_grade": 4})
        assert res2.status_code == 503
        assert res2.json() == {"disabled": "locus.spaced_repetition.enabled"}

        res3 = client.get("/memory/spaced_repetition/due")
        assert res3.status_code == 503
        assert res3.json() == {"disabled": "locus.spaced_repetition.enabled"}

        res4 = client.post("/memory/spaced_repetition/consolidate", json={})
        assert res4.status_code == 503
        assert res4.json() == {"disabled": "locus.spaced_repetition.enabled"}
