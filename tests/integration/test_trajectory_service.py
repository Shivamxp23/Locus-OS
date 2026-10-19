"""
SPEC §19.2 / §03 line 35: Trajectory Recording Service Integration Tests.
Tests HTTP endpoints on the sidecar service for turn recording, session flushing,
retrieval, batch evaluation, and modular 503 off-switch behavior.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from sidecar import config
from sidecar.learning.trajectory import TrajectoryRecorder
from sidecar.registry import ProviderRegistry
from sidecar.service import create_app


def test_trajectory_service_endpoints(monkeypatch, tmp_path: Path):
    """SPEC §19.2 line 10: "Full conversation recording for batch evaluation"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    registry = ProviderRegistry()
    registry.register("trajectory_recorder", "default_trajectory_recorder", TrajectoryRecorder)

    app = create_app(registry=registry)
    client = TestClient(app)

    session_id = "integration-session-42"

    # 1. Record User Turn
    res1 = client.post(
        "/trajectories/record",
        json={
            "session_id": session_id,
            "role": "user",
            "content": "Secret key is sk-1234567890abcdef1234567890 please check.",
            "tokens": {"prompt": 10, "completion": 0, "total": 10},
        },
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "ok"
    assert "sk-" not in data1["turn"]["content"]
    assert "[REDACTED]" in data1["turn"]["content"]

    # 2. Record Assistant Turn with Tool Call
    res2 = client.post(
        "/trajectories/record",
        json={
            "session_id": session_id,
            "role": "assistant",
            "content": "Querying status",
            "tool_calls": [{"name": "read_vault", "args": {"path": "01-Projects/Locus.md"}}],
            "tokens": {"prompt": 15, "completion": 8, "total": 23},
        },
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "ok"

    # 3. Flush Session
    res_flush = client.post(f"/trajectories/sessions/{session_id}/flush")
    assert res_flush.status_code == 200
    flush_data = res_flush.json()
    assert flush_data["status"] == "ok"
    saved_path = Path(flush_data["path"])
    assert saved_path.is_file()

    # 4. Get Trajectory
    res_get = client.get(f"/trajectories/sessions/{session_id}")
    assert res_get.status_code == 200
    traj_data = res_get.json()["trajectory"]
    assert traj_data["session_id"] == session_id
    assert len(traj_data["turns"]) == 2

    # 5. Batch Evaluate
    res_eval = client.post(
        "/trajectories/evaluate",
        json={"eval_prompt": "Evaluate agent reasoning quality"},
    )
    assert res_eval.status_code == 200
    eval_data = res_eval.json()["evaluation"]
    assert eval_data["total_trajectories"] >= 1
    assert eval_data["total_turns"] >= 2
    assert "read_vault" in eval_data["tool_call_frequencies"]


def test_trajectory_service_off_switch_returns_503(monkeypatch, tmp_path: Path):
    """SPEC §03 line 35: "a disabled feature's HTTP routes answer 503 with {'disabled': '<config key>'}"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)
    monkeypatch.setattr(
        config,
        "get",
        lambda k, d=None: False if k == "locus.learning.trajectory.enabled" else d,
    )

    registry = ProviderRegistry()
    registry.register("trajectory_recorder", "default_trajectory_recorder", TrajectoryRecorder)

    app = create_app(registry=registry)
    client = TestClient(app)

    res_record = client.post(
        "/trajectories/record",
        json={"session_id": "s1", "role": "user", "content": "hi"},
    )
    assert res_record.status_code == 503
    assert res_record.json() == {"disabled": "locus.learning.trajectory.enabled"}

    res_flush = client.post("/trajectories/sessions/s1/flush")
    assert res_flush.status_code == 503
    assert res_flush.json() == {"disabled": "locus.learning.trajectory.enabled"}

    res_get = client.get("/trajectories/sessions/s1")
    assert res_get.status_code == 503
    assert res_get.json() == {"disabled": "locus.learning.trajectory.enabled"}

    res_eval = client.post("/trajectories/evaluate", json={})
    assert res_eval.status_code == 503
    assert res_eval.json() == {"disabled": "locus.learning.trajectory.enabled"}
