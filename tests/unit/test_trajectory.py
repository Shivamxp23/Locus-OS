"""
SPEC §19.2 line 10 / F-0049: Trajectory Recording and Batch Evaluation Unit Tests.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from sidecar import config
from sidecar.learning.trajectory import TrajectoryRecorder, redact_text
from sidecar.providers.trajectory import (
    BaseTrajectoryRecorder,
    TrajectorySession,
    TurnRecord,
)
from sidecar.registry import ProviderRegistry


def test_trajectory_recorder_implements_interface():
    """SPEC §19.2 line 10: "TRAJECTORY RECORDING — Full conversation recording for batch evaluation"."""
    recorder = TrajectoryRecorder()
    assert isinstance(recorder, BaseTrajectoryRecorder)
    assert hasattr(recorder, "record_turn")
    assert hasattr(recorder, "flush_session")
    assert hasattr(recorder, "get_trajectory")
    assert hasattr(recorder, "batch_evaluate")


def test_trajectory_record_turns_and_flush(monkeypatch, tmp_path: Path):
    """SPEC §19.2 line 15: "FOR EACH turn IN session.turns: trajectory.messages.append(...); write_json(session.trajectory_path, compressed)"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    recorder = TrajectoryRecorder()
    recorder.initialize()

    session_id = "test-session-001"
    recorder.start_session(session_id=session_id, model="pi-model", platform="locus-tui")

    turn1 = recorder.record_turn(
        session_id=session_id,
        role="user",
        content="What is the weather today?",
        tokens={"prompt": 8, "completion": 0, "total": 8},
    )
    assert turn1 is not None
    assert turn1.role == "user"
    assert turn1.content == "What is the weather today?"

    turn2 = recorder.record_turn(
        session_id=session_id,
        role="assistant",
        content="Let me check the tools.",
        tool_calls=[{"name": "get_weather", "args": {"location": "San Francisco"}}],
        tokens={"prompt": 12, "completion": 6, "total": 18},
    )
    assert turn2 is not None
    assert turn2.role == "assistant"
    assert len(turn2.tool_calls) == 1

    out_file = recorder.flush_session(session_id)
    assert out_file is not None
    assert out_file.is_file()
    assert out_file.name == f"{session_id}.json"

    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["session_id"] == session_id
    assert data["model"] == "pi-model"
    assert len(data["turns"]) == 2
    assert data["turns"][0]["role"] == "user"
    assert data["turns"][1]["role"] == "assistant"


def test_trajectory_redacts_sensitive_keys_and_tokens(monkeypatch, tmp_path: Path):
    """SPEC §19.2 line 25: "Trajectory recording writes one record per turn, redacted"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    (locus_home / ".env").write_text(
        "COUCHDB_PASSWORD=super_secret_couch_pass\nTELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    recorder = TrajectoryRecorder()
    recorder.initialize()

    session_id = "test-secret-session"
    raw_content = (
        "Here is my OpenAI key sk-1234567890abcdef1234567890 and GitHub token ghp_1234567890abcdef1234567890 "
        "and bearer token Bearer secret_bearer_token_xyz_123. Also password is super_secret_couch_pass."
    )

    turn = recorder.record_turn(
        session_id=session_id,
        role="user",
        content=raw_content,
        tool_calls=[
            {
                "name": "connect_db",
                "args": {"url": "http://127.0.0.1:5984", "pass": "super_secret_couch_pass"},
            }
        ],
    )
    assert turn is not None
    assert "sk-" not in turn.content
    assert "ghp_" not in turn.content
    assert "super_secret_couch_pass" not in turn.content
    assert "[REDACTED]" in turn.content
    assert turn.tool_calls[0]["args"]["pass"] == "[REDACTED]"

    out_file = recorder.flush_session(session_id)
    saved_text = out_file.read_text(encoding="utf-8")
    assert "super_secret_couch_pass" not in saved_text
    assert "sk-1234567890" not in saved_text


def test_trajectory_batch_evaluation_metrics(monkeypatch, tmp_path: Path):
    """SPEC §19.2 line 35: "BATCH EVALUATION: FUNCTION batch_evaluate(trajectories, eval_prompt)"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    recorder = TrajectoryRecorder()
    recorder.initialize()

    # Session 1
    recorder.start_session("s1", model="model-a")
    recorder.record_turn("s1", "user", "Hello", tokens={"prompt": 5, "completion": 0, "total": 5})
    recorder.record_turn(
        "s1",
        "assistant",
        "Hi there",
        tool_calls=[{"name": "search", "args": {"q": "python"}}],
        tokens={"prompt": 5, "completion": 10, "total": 15},
    )
    recorder.flush_session("s1")

    # Session 2
    recorder.start_session("s2", model="model-b")
    recorder.record_turn("s2", "user", "Run code", tokens={"prompt": 10, "completion": 0, "total": 10})
    recorder.record_turn(
        "s2",
        "assistant",
        "Error running code",
        tool_calls=[{"name": "execute", "error": "command failed"}],
        tokens={"prompt": 10, "completion": 15, "total": 25},
    )
    recorder.flush_session("s2")

    eval_result = recorder.batch_evaluate(eval_prompt="Assess tool reliability")
    assert eval_result["total_trajectories"] == 2
    assert eval_result["total_turns"] == 4
    assert eval_result["avg_turns_per_session"] == 2.0
    assert eval_result["token_usage"]["total"] == 55
    assert eval_result["tool_call_frequencies"]["search"] == 1
    assert eval_result["tool_call_frequencies"]["execute"] == 1
    assert eval_result["role_distribution"]["user"] == 2
    assert eval_result["role_distribution"]["assistant"] == 2
    assert eval_result["evaluation_metrics"]["error_count"] == 1


def test_trajectory_off_switch(monkeypatch, tmp_path: Path):
    """SPEC §03 line 35: "a disabled feature's functions no-op and routes answer 503"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)
    monkeypatch.setattr(config, "get", lambda k, d=None: False if k == "locus.learning.trajectory.enabled" else d)

    recorder = TrajectoryRecorder()
    recorder.initialize()
    assert recorder.is_enabled() is False

    turn = recorder.record_turn("sess-off", "user", "Do something")
    assert turn is None
    flush_res = recorder.flush_session("sess-off")
    assert flush_res is None


def test_trajectory_compression(monkeypatch, tmp_path: Path):
    """SPEC §19.2 line 22: "Compress for storage: compressed = trajectory_compressor.compress(trajectory)"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)
    monkeypatch.setattr(
        config,
        "get",
        lambda k, d=None: True if k == "locus.learning.trajectory.compress" else d,
    )

    recorder = TrajectoryRecorder()
    recorder.initialize()

    recorder.record_turn("compressed-session", "user", "Test compression content")
    out_file = recorder.flush_session("compressed-session")
    assert out_file is not None
    assert str(out_file).endswith(".json.gz")

    decompressed = gzip.decompress(out_file.read_bytes()).decode("utf-8")
    data = json.loads(decompressed)
    assert data["session_id"] == "compressed-session"

    # Reading back via get_trajectory also decompresses
    read_back = recorder.get_trajectory("compressed-session")
    assert read_back is not None
    assert read_back["session_id"] == "compressed-session"


def test_trajectory_modular_swap():
    """SPEC §03 line 12: "Universal Provider Registry allowing modular swap"."""
    registry = ProviderRegistry()

    class CustomTrajectoryRecorder(BaseTrajectoryRecorder):
        def start_session(self, session_id: str, model="unknown", platform="locus", metadata=None):
            return TrajectorySession(session_id, model, platform, "2026-01-01T00:00:00Z")

        def record_turn(self, session_id: str, role: str, content: str, tool_calls=None, tokens=None, metadata=None):
            return TurnRecord(role, "custom:" + content, "2026-01-01T00:00:00Z")

        def flush_session(self, session_id: str):
            return Path("/tmp/custom.json")

        def get_trajectory(self, session_id: str):
            return {"session_id": session_id, "custom": True}

        def batch_evaluate(self, session_ids=None, eval_prompt=None):
            return {"custom_score": 100}

    registry.register("trajectory_recorder", "custom", CustomTrajectoryRecorder)
    active = registry.get_active_provider("trajectory_recorder", default_name="custom")
    assert active is CustomTrajectoryRecorder

    inst = active()
    res = inst.record_turn("s", "user", "hi")
    assert res.content == "custom:hi"


def test_trajectory_health_check(monkeypatch, tmp_path: Path):
    """SPEC §03 line 40: "Health check for all registered providers"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    recorder = TrajectoryRecorder()
    health = recorder.health_check()
    assert health["status"] == "ok"
    assert health["provider"] == "default_trajectory_recorder"
    assert health["enabled"] is True
