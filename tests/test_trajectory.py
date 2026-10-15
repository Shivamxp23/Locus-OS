"""tests/test_trajectory.py - Tests for trajectory recording and redaction.

Validates Acceptance Criteria for US-17 and Spec §19.2:
- Unit: TrajectoryTurn data structures and JSON serialization
- Unit: Secret redaction in prompt, response, tool calls, and metadata (S-0)
- Unit: JsonlTrajectoryRecorder persistence and session_id retrieval
- Unit: SQLiteTrajectoryRecorder persistence and session_id retrieval
- Unit: Modularity off-test and swap-test
- Integration: capture_pi_turn execution with redaction verification
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from sidecar.pi_bridge import PiTurnResult
from sidecar.security.redact import redact_patterns
from sidecar.trajectory import (
    JsonlTrajectoryRecorder,
    SQLiteTrajectoryRecorder,
    TrajectoryTurn,
    capture_pi_turn,
    get_trajectory_recorder,
    sanitize_turn,
)


def test_unit_trajectory_turn_structure():
    """Verify TrajectoryTurn serialization round-trip."""
    turn = TrajectoryTurn(
        session_id="test-session-1",
        turn_id="turn-101",
        timestamp=1700000000.0,
        prompt="Tell me a joke",
        response="Why did the chicken cross the road?",
        tool_calls=[{"name": "search", "query": "chicken"}],
        token_counts={"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        duration_ms=250.5,
        metadata={"platform": "telegram", "model": "gpt-4"},
    )

    data = turn.to_dict()
    assert data["session_id"] == "test-session-1"
    assert data["duration_ms"] == 250.5
    assert len(data["tool_calls"]) == 1

    restored = TrajectoryTurn.from_dict(data)
    assert restored.session_id == turn.session_id
    assert restored.prompt == turn.prompt
    assert restored.token_counts == turn.token_counts


def test_unit_trajectory_redaction_secrets():
    """Verify sensitive credentials are completely masked per Security Law S-0."""
    dummy_ant = "sk-" + "ant-" + "api03-abcdef1234567890abcdef"
    dummy_gh = "gh" + "p_" + "1234567890abcdefghijklmnopqrstuvwxyz"
    dummy_oa = "sk-" + "1234567890abcdef1234567890abcdef"
    raw_prompt = f"Here is my key: {dummy_ant} and password=mysecretpassword123"
    raw_response = f"Found github token {dummy_gh}"
    raw_tool_calls = [
        {"name": "fetch_data", "headers": {"Authorization": "Bearer 1234567890abcdef1234567890abcdef"}}
    ]
    raw_metadata = {"api_key": dummy_oa}

    turn = TrajectoryTurn(
        session_id="sec-session",
        prompt=raw_prompt,
        response=raw_response,
        tool_calls=raw_tool_calls,
        metadata=raw_metadata,
    )

    clean = sanitize_turn(turn)

    # Assert secret tokens are masked
    assert "abcdef1234567890abcdef" not in clean.prompt
    assert "mysecretpassword123" not in clean.prompt
    assert "1234567890abcdefghijkl" not in clean.response
    assert "Bearer 1234567890abcdef" not in clean.tool_calls[0]["headers"]["Authorization"]
    assert "1234567890abcdef1234" not in clean.metadata["api_key"]


def test_unit_jsonl_recorder(tmp_path: Path):
    """Verify JsonlTrajectoryRecorder stores and retrieves turns by session_id."""
    recorder = JsonlTrajectoryRecorder(storage_dir=tmp_path)

    turn1 = TrajectoryTurn(session_id="session-a", prompt="Turn A1", response="Resp A1")
    turn2 = TrajectoryTurn(session_id="session-b", prompt="Turn B1", response="Resp B1")
    turn3 = TrajectoryTurn(session_id="session-a", prompt="Turn A2", response="Resp A2")

    recorder.record_turn(turn1)
    recorder.record_turn(turn2)
    recorder.record_turn(turn3)

    turns_a = recorder.get_session_turns("session-a")
    assert len(turns_a) == 2
    assert turns_a[0].prompt == "Turn A1"
    assert turns_a[1].prompt == "Turn A2"

    turns_b = recorder.get_session_turns("session-b")
    assert len(turns_b) == 1
    assert turns_b[0].response == "Resp B1"

    sessions = recorder.list_sessions()
    assert sorted(sessions) == ["session-a", "session-b"]


def test_unit_sqlite_recorder(tmp_path: Path):
    """Verify SQLiteTrajectoryRecorder stores and queries turns relational schema."""
    recorder = SQLiteTrajectoryRecorder(storage_dir=tmp_path)

    turn1 = TrajectoryTurn(
        session_id="sess-sql-1",
        prompt="SQL query question",
        response="Result table",
        tool_calls=[{"name": "sql", "query": "SELECT *"}],
        token_counts={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        duration_ms=120.0,
    )
    recorder.record_turn(turn1)

    turns = recorder.get_session_turns("sess-sql-1")
    assert len(turns) == 1
    assert turns[0].prompt == "SQL query question"
    assert turns[0].tool_calls == [{"name": "sql", "query": "SELECT *"}]
    assert turns[0].duration_ms == 120.0

    assert recorder.list_sessions() == ["sess-sql-1"]


def test_unit_modularity_off_and_swap(tmp_path: Path):
    """Test modular off-switch and provider swap test."""
    jsonl_rec = get_trajectory_recorder(provider="jsonl", storage_dir=tmp_path / "j")
    sqlite_rec = get_trajectory_recorder(provider="sqlite", storage_dir=tmp_path / "s")

    assert isinstance(jsonl_rec, JsonlTrajectoryRecorder)
    assert isinstance(sqlite_rec, SQLiteTrajectoryRecorder)

    # Swap test: both fulfill identical interface
    t = TrajectoryTurn(session_id="swap-test", prompt="Hello", response="World")
    jsonl_rec.record_turn(t)
    sqlite_rec.record_turn(t)

    assert len(jsonl_rec.get_session_turns("swap-test")) == 1
    assert len(sqlite_rec.get_session_turns("swap-test")) == 1

    # Off test: enabled=False does not persist
    with patch("sidecar.pi_bridge.run_pi_turn") as mock_pi:
        mock_pi.return_value = PiTurnResult(stdout="Response off", stderr="", returncode=0)
        res, turn = capture_pi_turn(
            prompt="Hello off",
            session_id="off-sess",
            recorder=jsonl_rec,
            enabled=False,
        )
        assert len(jsonl_rec.get_session_turns("off-sess")) == 0


def test_integration_capture_pi_turn_redacted(tmp_path: Path):
    """Integration: Execute a Pi turn with sensitive dummy credentials and verify redacted recording."""
    dummy_ant = "sk-" + "ant-" + "api03-abcdef1234567890abcdef"
    dummy_gh = "gh" + "p_" + "1234567890abcdefghijklmnopqrstuvwxyz"
    sensitive_prompt = f"Deploy with key: {dummy_ant}"
    mock_stdout = f"Deploy complete. Tool call: database_sync\nCreated access_token={dummy_gh}"

    with patch("sidecar.pi_bridge.run_pi_turn") as mock_pi:
        mock_pi.return_value = PiTurnResult(stdout=mock_stdout, stderr="", returncode=0)

        recorder = JsonlTrajectoryRecorder(storage_dir=tmp_path)
        res, turn = capture_pi_turn(
            prompt=sensitive_prompt,
            session_id="test-integration-sess",
            recorder=recorder,
            enabled=True,
        )

        assert res.ok is True
        assert turn.session_id == "test-integration-sess"
        assert turn.duration_ms >= 0

        # Retrieve from storage to verify persistent redaction
        recorded_turns = recorder.get_session_turns("test-integration-sess")
        assert len(recorded_turns) == 1
        saved = recorded_turns[0]

        # Verify raw keys are NOT in persistent storage
        assert "abcdef1234567890abcdef" not in saved.prompt
        assert "1234567890abcdefghijkl" not in saved.response
        assert len(saved.tool_calls) == 1
        assert saved.token_counts["total_tokens"] > 0
