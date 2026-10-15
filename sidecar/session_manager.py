"""Session Management & Branching Engine (§5.1-§5.4).

Maintains JSONL-backed tree structured conversation sessions supporting:
- Multi-entry types: message, tool_call, tool_result, compaction_summary, branch_summary.
- Session branching / forking from arbitrary checkpoints.
- Replay and context restoration across pauses and resumes.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionEntryType(str, Enum):
    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMPACTION_SUMMARY = "compaction_summary"
    BRANCH_SUMMARY = "branch_summary"
    METADATA = "metadata"
    CHECKPOINT = "checkpoint"


@dataclass
class SessionEntry:
    id: str
    entry_type: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionMetadata:
    session_id: str
    title: str = "New Session"
    parent_session_id: Optional[str] = None
    fork_point_entry_id: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Session:
    """In-memory and JSONL-persisted representation of a conversation branch."""

    def __init__(self, metadata: SessionMetadata) -> None:
        self.metadata = metadata
        self.entries: List[SessionEntry] = []

    def append(self, entry_type: str, payload: Dict[str, Any]) -> SessionEntry:
        entry = SessionEntry(
            id=str(uuid.uuid4())[:12],
            entry_type=entry_type,
            payload=payload,
        )
        self.entries.append(entry)
        return entry

    def append_message(self, role: str, content: str) -> SessionEntry:
        return self.append(SessionEntryType.MESSAGE.value, {"role": role, "content": content})

    def replay_messages(self) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        for e in self.entries:
            if e.entry_type == SessionEntryType.MESSAGE.value:
                messages.append(e.payload)
            elif e.entry_type == SessionEntryType.COMPACTION_SUMMARY.value:
                messages.append({
                    "role": "system",
                    "content": f"[Compacted Summary]: {e.payload.get('summary', '')}",
                    "compressed": True,
                })
        return messages


class SessionManager:
    """Manages active sessions, tree branching, and persistence."""

    def __init__(self) -> None:
        self.sessions: Dict[str, Session] = {}

    def create_session(
        self,
        title: str = "New Session",
        session_id: Optional[str] = None,
    ) -> Session:
        sid = session_id or ("sess_" + str(uuid.uuid4())[:8])
        meta = SessionMetadata(session_id=sid, title=title)
        sess = Session(meta)
        self.sessions[sid] = sess
        return sess

    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def fork_session(
        self,
        parent_session_id: str,
        fork_point_entry_id: Optional[str] = None,
        new_title: Optional[str] = None,
    ) -> Session:
        parent = self.get_session(parent_session_id)
        if not parent:
            raise KeyError(f"Parent session {parent_session_id} not found")

        child_id = "sess_" + str(uuid.uuid4())[:8]
        child_title = new_title or f"Branch of {parent.metadata.title}"
        meta = SessionMetadata(
            session_id=child_id,
            title=child_title,
            parent_session_id=parent_session_id,
            fork_point_entry_id=fork_point_entry_id,
        )
        child = Session(meta)

        # Copy entries up to fork_point
        copied = 0
        for entry in parent.entries:
            child.entries.append(entry)
            copied += 1
            if fork_point_entry_id and entry.id == fork_point_entry_id:
                break

        # Append branch summary entry marking divergence
        child.append(
            SessionEntryType.BRANCH_SUMMARY.value,
            {
                "parent_session_id": parent_session_id,
                "fork_point": fork_point_entry_id,
                "copied_entries": copied,
            },
        )

        self.sessions[child_id] = child
        return child
