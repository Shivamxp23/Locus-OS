"""sidecar/trajectory.py - Trajectory recording engine for Locus OS.

Implements Spec §19.2 and Security Law S-0:
- Captures turns from run_pi_turn containing prompt, tools called, response,
  token counts, duration, and session metadata.
- Sanitizes every record using security.redact_patterns before persisting,
  preventing secret keys or credentials from leaking into storage (S-0).
- Modular storage providers: JSONL (default) and SQLite, retrievable by session_id.
- Modular switch: locus.trajectory.enabled (True | False).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import logging
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional, Protocol, Sequence
import uuid

from sidecar.security.redact import redact_patterns

logger = logging.getLogger("sidecar.trajectory")

DEFAULT_STORAGE_DIR = Path.home() / ".locus" / "trajectories"


@dataclass
class TrajectoryTurn:
    """A single turn within a conversation trajectory."""

    session_id: str
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    prompt: str = ""
    response: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    token_counts: dict[str, int] = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrajectoryTurn:
        return cls(
            session_id=data.get("session_id", ""),
            turn_id=data.get("turn_id", str(uuid.uuid4())),
            timestamp=float(data.get("timestamp", time.time())),
            prompt=data.get("prompt", ""),
            response=data.get("response", ""),
            tool_calls=list(data.get("tool_calls", [])),
            token_counts=dict(data.get("token_counts", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})),
            duration_ms=float(data.get("duration_ms", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


def sanitize_turn(turn: TrajectoryTurn) -> TrajectoryTurn:
    """Sanitize all string and structured fields in a turn using redact_patterns (S-0)."""
    sanitized_prompt = redact_patterns(turn.prompt)
    sanitized_response = redact_patterns(turn.response)
    sanitized_tool_calls = redact_patterns(turn.tool_calls)
    sanitized_metadata = redact_patterns(turn.metadata)

    return TrajectoryTurn(
        session_id=turn.session_id,
        turn_id=turn.turn_id,
        timestamp=turn.timestamp,
        prompt=sanitized_prompt,
        response=sanitized_response,
        tool_calls=sanitized_tool_calls,
        token_counts=dict(turn.token_counts),
        duration_ms=turn.duration_ms,
        metadata=sanitized_metadata,
    )


class TrajectoryStorageProvider(Protocol):
    """Protocol for trajectory storage providers."""

    def record_turn(self, turn: TrajectoryTurn) -> None:
        """Record a single trajectory turn."""
        ...

    def get_session_turns(self, session_id: str) -> list[TrajectoryTurn]:
        """Retrieve all recorded turns for a session."""
        ...

    def list_sessions(self) -> list[str]:
        """List all session IDs present in storage."""
        ...


class JsonlTrajectoryRecorder:
    """Appends sanitized trajectory turns to JSONL file storage."""

    def __init__(self, storage_dir: Path | str | None = None):
        self.storage_dir = Path(storage_dir) if storage_dir else DEFAULT_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / "trajectories.jsonl"

    def record_turn(self, turn: TrajectoryTurn) -> None:
        """Persist a turn after redacting secrets."""
        clean_turn = sanitize_turn(turn)
        line = json.dumps(clean_turn.to_dict(), ensure_ascii=False) + "\n"
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(line)

    def get_session_turns(self, session_id: str) -> list[TrajectoryTurn]:
        """Read all turns matching the given session_id."""
        if not self.file_path.exists():
            return []

        turns: list[TrajectoryTurn] = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get("session_id") == session_id:
                        turns.append(TrajectoryTurn.from_dict(data))
                except Exception as exc:
                    logger.warning("Corrupt JSONL trajectory line skipped: %s", exc)
        return turns

    def list_sessions(self) -> list[str]:
        """Return unique session IDs recorded in JSONL."""
        if not self.file_path.exists():
            return []

        sessions: set[str] = set()
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    sid = data.get("session_id")
                    if sid:
                        sessions.add(sid)
                except Exception:
                    continue
        return sorted(sessions)


class SQLiteTrajectoryRecorder:
    """Stores sanitized trajectory turns in an SQLite relational database."""

    def __init__(self, storage_dir: Path | str | None = None):
        self.storage_dir = Path(storage_dir) if storage_dir else DEFAULT_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_dir / "trajectories.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    tool_calls TEXT NOT NULL,
                    token_counts TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON turns(session_id)")
            conn.commit()

    def record_turn(self, turn: TrajectoryTurn) -> None:
        """Persist a turn after redacting secrets."""
        clean = sanitize_turn(turn)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO turns (
                    turn_id, session_id, timestamp, prompt, response,
                    tool_calls, token_counts, duration_ms, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean.turn_id,
                    clean.session_id,
                    clean.timestamp,
                    clean.prompt,
                    clean.response,
                    json.dumps(clean.tool_calls, ensure_ascii=False),
                    json.dumps(clean.token_counts, ensure_ascii=False),
                    clean.duration_ms,
                    json.dumps(clean.metadata, ensure_ascii=False),
                ),
            )
            conn.commit()

    def get_session_turns(self, session_id: str) -> list[TrajectoryTurn]:
        """Retrieve turns for session_id ordered by timestamp."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                SELECT turn_id, session_id, timestamp, prompt, response,
                       tool_calls, token_counts, duration_ms, metadata
                FROM turns
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

        turns: list[TrajectoryTurn] = []
        for r in rows:
            turns.append(
                TrajectoryTurn(
                    turn_id=r[0],
                    session_id=r[1],
                    timestamp=r[2],
                    prompt=r[3],
                    response=r[4],
                    tool_calls=json.loads(r[5]),
                    token_counts=json.loads(r[6]),
                    duration_ms=r[7],
                    metadata=json.loads(r[8]),
                )
            )
        return turns

    def list_sessions(self) -> list[str]:
        """List distinct session IDs."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT DISTINCT session_id FROM turns ORDER BY session_id ASC")
            return [row[0] for row in cursor.fetchall()]


def get_trajectory_recorder(
    provider: str | None = None, storage_dir: Path | str | None = None
) -> TrajectoryStorageProvider:
    """Factory creating the configured TrajectoryStorageProvider."""
    provider_name = (provider or "jsonl").lower()
    if provider_name == "sqlite":
        return SQLiteTrajectoryRecorder(storage_dir=storage_dir)
    return JsonlTrajectoryRecorder(storage_dir=storage_dir)


def parse_turn_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse tool call invocations from Pi output or formatted text."""
    tools: list[dict[str, Any]] = []
    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if "tool call:" in lower or "[tool call]" in lower or lower.startswith("tool:"):
            tools.append({"raw": stripped})
    return tools


def capture_pi_turn(
    prompt: str,
    session_id: str | None = None,
    cwd: Path | str | None = None,
    timeout: int = 300,
    recorder: TrajectoryStorageProvider | None = None,
    enabled: bool = True,
    storage_dir: Path | str | None = None,
) -> tuple[Any, TrajectoryTurn]:
    """Execute a Pi turn with execution telemetry and sanitized trajectory recording.

    Captures prompt, duration, stdout response, parsed tool calls, and persists
    to recorder if enabled (per locus.trajectory.enabled).
    """
    from sidecar.pi_bridge import run_pi_turn

    sid = session_id or str(uuid.uuid4())
    start_time = time.time()

    turn_result = run_pi_turn(
        prompt=prompt,
        session_id=sid,
        cwd=cwd,
        timeout=timeout,
    )
    duration_ms = (time.time() - start_time) * 1000.0

    tool_calls = parse_turn_tool_calls(turn_result.stdout)
    est_prompt_tokens = max(1, len(prompt.split()))
    est_completion_tokens = max(1, len(turn_result.stdout.split()))

    turn = TrajectoryTurn(
        session_id=sid,
        timestamp=start_time,
        prompt=prompt,
        response=turn_result.stdout,
        tool_calls=tool_calls,
        token_counts={
            "prompt_tokens": est_prompt_tokens,
            "completion_tokens": est_completion_tokens,
            "total_tokens": est_prompt_tokens + est_completion_tokens,
        },
        duration_ms=duration_ms,
        metadata={
            "ok": turn_result.ok,
            "returncode": turn_result.returncode,
            "stderr": turn_result.stderr[:200] if turn_result.stderr else "",
        },
    )

    if enabled:
        active_recorder = recorder or get_trajectory_recorder(storage_dir=storage_dir)
        active_recorder.record_turn(turn)

    return turn_result, turn
