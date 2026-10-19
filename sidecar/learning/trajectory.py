"""
SPEC §19.2 line 10 / F-0049: Trajectory Recording and Batch Evaluation.
Records full conversational and tool-call turns for agent sessions,
applies sensitive token/credential redaction, persists trajectories to disk,
and performs batch evaluation aggregation across sessions.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

from sidecar import config
from sidecar.providers.trajectory import (
    BaseTrajectoryRecorder,
    TrajectorySession,
    TurnRecord,
)

logger = logging.getLogger("locus.learning.trajectory")

# Common API key and credential regex patterns for automatic redaction
REDACTION_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),                       # OpenAI / Anthropic-style keys
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),                          # GitHub Personal Access Tokens
    re.compile(r"glpat-[A-Za-z0-9_\-]{20,}"),                     # GitLab tokens
    re.compile(r"Bearer\s+[A-Za-z0-9._~+\-/]+=*", re.IGNORECASE),  # Bearer tokens
    re.compile(r"COUCHDB_PASSWORD=[^\s\n]+", re.IGNORECASE),      # CouchDB env values
    re.compile(r"TELEGRAM_BOT_TOKEN=[^\s\n]+", re.IGNORECASE),    # Telegram token env values
]


def redact_text(text: str, custom_secrets: Optional[Set[str]] = None) -> str:
    """
    SPEC §19.2: Redact sensitive tokens, passwords, and API keys to [REDACTED].
    """
    if not isinstance(text, str) or not text:
        return text

    redacted = text
    for pattern in REDACTION_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)

    if custom_secrets:
        for secret in custom_secrets:
            if secret and len(secret) >= 4 and secret in redacted:
                redacted = redacted.replace(secret, "[REDACTED]")

    return redacted


def redact_data(data: Any, custom_secrets: Optional[Set[str]] = None) -> Any:
    """Recursively redact nested structures (dicts, lists, strings)."""
    if isinstance(data, str):
        return redact_text(data, custom_secrets)
    elif isinstance(data, dict):
        return {k: redact_data(v, custom_secrets) for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_data(item, custom_secrets) for item in data]
    return data


class TrajectoryRecorder(BaseTrajectoryRecorder):
    """
    Standard implementation of BaseTrajectoryRecorder conforming to
    SPEC §19.2 and SPEC §03 modular provider lifecycle.
    """

    _shared_sessions: Dict[str, TrajectorySession] = {}

    def __init__(self, name: str = "default_trajectory_recorder") -> None:
        self.name = name
        self._active_sessions = self._shared_sessions
        self._custom_secrets: Set[str] = set()
        self._refresh_secrets()

    def _refresh_secrets(self) -> None:
        """Collect secrets from .env file, SECRETS_KEYS, and environment."""
        self._custom_secrets.clear()
        # 1. From .env file in LOCUS_HOME
        try:
            env_dict = config._load_env_file()
            for k, v in env_dict.items():
                if v and len(v) >= 4:
                    self._custom_secrets.add(v)
        except Exception:
            pass

        # 2. From config accessor / os.environ for known secrets
        try:
            for k, v in config.get_environ().items():
                k_upper = k.upper()
                if any(term in k_upper for term in ("SECRET", "KEY", "PASS", "TOKEN", "AUTH")):
                    if v and len(v) >= 4:
                        self._custom_secrets.add(v)
        except Exception:
            pass

    def _get_storage_dir(self) -> Path:
        """Resolve storage directory for persisted session trajectories."""
        custom_dir = config.get("locus.learning.trajectory.dir")
        if custom_dir:
            p = Path(custom_dir).resolve()
        else:
            p = (config.get_locus_home() / "trajectories").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def is_enabled(self) -> bool:
        """Modular off-switch check: locus.learning.trajectory.enabled."""
        return config.get("locus.learning.trajectory.enabled", True) is not False

    def initialize(self, options: Optional[Dict[str, Any]] = None) -> None:
        """Initialize provider lifecycle."""
        self._refresh_secrets()
        self._get_storage_dir()

    def health_check(self) -> Dict[str, Any]:
        """Provider health check status."""
        enabled = self.is_enabled()
        storage_dir = self._get_storage_dir()
        return {
            "status": "ok" if enabled else "disabled",
            "provider": self.name,
            "enabled": enabled,
            "storage_dir": str(storage_dir),
            "active_sessions": len(self._active_sessions),
        }

    def start_session(
        self, session_id: str, model: str = "unknown", platform: str = "locus", metadata: Optional[Dict[str, Any]] = None
    ) -> TrajectorySession:
        """Start or initialize a session trajectory."""
        now_iso = datetime.now(timezone.utc).isoformat()
        session = TrajectorySession(
            session_id=session_id,
            model=model,
            platform=platform,
            start_time=now_iso,
            metadata=metadata or {},
        )
        self._active_sessions[session_id] = session
        return session

    def record_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tokens: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TurnRecord]:
        """Record a single conversational turn with redaction."""
        if not self.is_enabled():
            return None

        self._refresh_secrets()
        clean_content = redact_text(content, self._custom_secrets)
        clean_tool_calls = redact_data(tool_calls or [], self._custom_secrets)
        clean_metadata = redact_data(metadata or {}, self._custom_secrets)

        turn = TurnRecord(
            role=role,
            content=clean_content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tokens=tokens or {},
            tool_calls=clean_tool_calls,
            metadata=clean_metadata,
        )

        session = self._active_sessions.get(session_id)
        if not session:
            session = self.start_session(session_id=session_id)

        session.turns.append(turn)
        return turn

    def flush_session(self, session_id: str) -> Optional[Path]:
        """
        Persist session trajectory to LOCUS_HOME/trajectories/{session_id}.json.
        Returns file Path or None if disabled or session missing.
        """
        if not self.is_enabled():
            return None

        session = self._active_sessions.get(session_id)
        if not session:
            # Check if already persisted
            existing = self._get_storage_dir() / f"{session_id}.json"
            if existing.is_file():
                return existing
            return None

        if not session.end_time:
            session.end_time = datetime.now(timezone.utc).isoformat()

        payload = session.to_dict()
        storage_dir = self._get_storage_dir()
        use_compression = config.get("locus.learning.trajectory.compress", False)

        if use_compression:
            out_file = storage_dir / f"{session_id}.json.gz"
            compressed_bytes = gzip.compress(json.dumps(payload, indent=2).encode("utf-8"))
            out_file.write_bytes(compressed_bytes)
        else:
            out_file = storage_dir / f"{session_id}.json"
            out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return out_file

    def get_trajectory(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored trajectory for a session."""
        session = self._active_sessions.get(session_id)
        if session:
            return session.to_dict()

        storage_dir = self._get_storage_dir()
        json_file = storage_dir / f"{session_id}.json"
        if json_file.is_file():
            return json.loads(json_file.read_text(encoding="utf-8"))

        gz_file = storage_dir / f"{session_id}.json.gz"
        if gz_file.is_file():
            decompressed = gzip.decompress(gz_file.read_bytes()).decode("utf-8")
            return json.loads(decompressed)

        return None

    def batch_evaluate(
        self, session_ids: Optional[List[str]] = None, eval_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        SPEC §19.2: Batch evaluation across recorded trajectories.
        Aggregates token usage, tool call frequencies, role distributions, and error signals.
        """
        storage_dir = self._get_storage_dir()
        target_ids = session_ids

        if target_ids is None:
            # Discover all sessions in storage dir (or in-memory if no disk files)
            found: Set[str] = set()
            for path in storage_dir.glob("*.json"):
                found.add(path.stem)
            for path in storage_dir.glob("*.json.gz"):
                found.add(path.stem)
            if not found:
                found = set(self._active_sessions.keys())
            target_ids = sorted(list(found))

        trajectories: List[Dict[str, Any]] = []
        for sid in target_ids:
            traj = self.get_trajectory(sid)
            if traj:
                trajectories.append(traj)

        total_trajectories = len(trajectories)
        total_turns = sum(len(t.get("turns", [])) for t in trajectories)
        avg_turns = (total_turns / total_trajectories) if total_trajectories > 0 else 0.0

        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        tool_counts: Dict[str, int] = {}
        role_counts: Dict[str, int] = {}
        error_count = 0

        for t in trajectories:
            for turn in t.get("turns", []):
                role = turn.get("role", "unknown")
                role_counts[role] = role_counts.get(role, 0) + 1

                t_tokens = turn.get("tokens", {})
                p_tok = t_tokens.get("prompt", 0)
                c_tok = t_tokens.get("completion", 0)
                tot_tok = t_tokens.get("total", p_tok + c_tok)
                prompt_tokens += p_tok
                completion_tokens += c_tok
                total_tokens += tot_tok

                for tc in turn.get("tool_calls", []):
                    name = tc.get("name") or tc.get("tool", "unknown_tool")
                    tool_counts[name] = tool_counts.get(name, 0) + 1
                    if tc.get("error") or "error" in str(tc.get("result", "")).lower():
                        error_count += 1

        avg_tokens = (total_tokens / total_trajectories) if total_trajectories > 0 else 0.0

        return {
            "eval_prompt": eval_prompt,
            "total_trajectories": total_trajectories,
            "total_turns": total_turns,
            "avg_turns_per_session": round(avg_turns, 2),
            "token_usage": {
                "total": total_tokens,
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "avg_per_session": round(avg_tokens, 2),
            },
            "tool_call_frequencies": tool_counts,
            "role_distribution": role_counts,
            "evaluation_metrics": {
                "error_count": error_count,
                "tool_error_rate": round(error_count / max(1, sum(tool_counts.values())), 4),
            },
        }
