"""
SPEC §5.1-5.8: Session Management & Telegram Bridge (F-0027).
Implements tree-structured sessions in JSONL v3, session branching,
compaction-aware resume, and Telegram-to-session bridge.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("locus.sessions")

# SPEC §5.1-5.8 lines 5738-5740: Entry types: message, tool_call, tool_result,
# compaction_summary, branch_summary, metadata, system_event, checkpoint, marker
VALID_ENTRY_TYPES = {
    "message",
    "tool_call",
    "tool_result",
    "compaction_summary",
    "branch_summary",
    "metadata",
    "system_event",
    "checkpoint",
    "marker",
}


@dataclass
class SessionEntry:
    """SPEC §5.1-5.8 lines 5738-5741: Single JSONL v3 entry."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    type: str = "message"
    role: Optional[str] = None  # user | assistant | system | tool
    content: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionEntry:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            parent_id=data.get("parent_id"),
            type=data.get("type", "message"),
            role=data.get("role"),
            content=data.get("content"),
            timestamp=float(data.get("timestamp", time.time())),
            metadata=data.get("metadata") or {},
        )


class Session:
    """
    SPEC §5.1-5.8 lines 5742-5743:
    Structure: tree-based (sessions can fork into branches)
    Storage: one .jsonl file per session, named by session_id.
    """

    def __init__(
        self,
        session_id: str,
        storage_path: Path,
        parent_session_id: Optional[str] = None,
        fork_point: Optional[str] = None,
    ) -> None:
        self.session_id = session_id
        self.storage_path = storage_path
        self.parent_session_id = parent_session_id
        self.fork_point = fork_point
        self.entries: List[SessionEntry] = []
        self._entries_by_id: Dict[str, SessionEntry] = {}

    def append(self, entry: SessionEntry) -> None:
        """Append an entry to in-memory state and persist to JSONL v3."""
        if entry.type not in VALID_ENTRY_TYPES:
            raise ValueError(f"Invalid entry type: {entry.type}. Must be one of {VALID_ENTRY_TYPES}")
        if not entry.parent_id and self.entries:
            entry.parent_id = self.entries[-1].id
        self.entries.append(entry)
        self._entries_by_id[entry.id] = entry
        self._write_entry(entry)

    def _write_entry(self, entry: SessionEntry) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def flush(self) -> None:
        """SPEC §5.1-5.8 line 5791: Ensure all entries are persisted."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(json.dumps(entry.to_dict()) + "\n")

    def replay_entries(self) -> List[SessionEntry]:
        """SPEC §5.1-5.8 line 5764: Restore full message history."""
        return [e for e in self.entries if e.type in ("message", "tool_call", "tool_result")]

    def get_compaction_entries(self) -> List[SessionEntry]:
        """SPEC §5.1-5.8 line 5766: Restore compacted summaries."""
        return [e for e in self.entries if e.type == "compaction_summary"]

    def rebuild_context(self) -> List[Dict[str, Any]]:
        """
        SPEC §5.1-5.8 lines 5767-5768:
        Rebuild context: summaries first, then recent messages.
        """
        context: List[Dict[str, Any]] = []
        compactions = self.get_compaction_entries()
        for c in compactions:
            context.append({
                "role": "system",
                "content": f"[Compaction Summary]: {c.content or ''}",
                "entry_id": c.id,
            })
        messages = self.replay_entries()
        for m in messages:
            context.append({
                "role": m.role or "user",
                "content": m.content or "",
                "entry_id": m.id,
                "type": m.type,
            })
        return context


class SessionManager:
    """
    SPEC §5.1-5.8: Manages session creation, branching, resuming, and persistence.
    """

    def __init__(self, sessions_dir: Optional[Path | str] = None) -> None:
        if sessions_dir is None:
            self.sessions_dir = Path.home() / ".locus" / "sessions"
        else:
            self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.jsonl"

    def create_session(
        self,
        session_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        fork_point: Optional[str] = None,
    ) -> Session:
        """Create and initialize a new JSONL v3 session."""
        sid = session_id or str(uuid.uuid4())
        path = self._path_for(sid)
        session = Session(session_id=sid, storage_path=path, parent_session_id=parent_id, fork_point=fork_point)
        # Append initial metadata entry
        meta = SessionEntry(
            type="metadata",
            content=f"Session {sid} initialized",
            metadata={"session_id": sid, "parent_id": parent_id, "fork_point": fork_point},
        )
        session.append(meta)
        return session

    def load_session(self, session_id: str) -> Session:
        """SPEC §5.1-5.8 line 5762: session = load_session(session_id)."""
        path = self._path_for(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"Session file not found: {path}")
        session = Session(session_id=session_id, storage_path=path)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = SessionEntry.from_dict(data)
                    session.entries.append(entry)
                    session._entries_by_id[entry.id] = entry
                    if entry.type == "metadata":
                        session.parent_session_id = entry.metadata.get("parent_id")
                        session.fork_point = entry.metadata.get("fork_point")
                except json.JSONDecodeError:
                    continue
        return session

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all available session IDs and their entry counts."""
        res: List[Dict[str, Any]] = []
        for p in self.sessions_dir.glob("*.jsonl"):
            sid = p.stem
            try:
                with open(p, "r", encoding="utf-8") as f:
                    count = sum(1 for line in f if line.strip())
                res.append({"session_id": sid, "path": str(p), "entries_count": count})
            except Exception:
                continue
        return res

    def fork_session(
        self,
        parent_session_id: str,
        fork_point: str,
        summary: Optional[str] = None,
    ) -> Session:
        """
        SPEC §5.1-5.8 lines 5746-5758:
        FUNCTION fork_session(parent_session_id, fork_point):
            new_session = create_session()
            new_session.parent = parent_session_id
            new_session.fork_point = fork_point
            copy_entries(parent_session_id, new_session.id, up_to=fork_point)
            new_session.append(BranchSummaryEntry { ... })
            RETURN new_session
        """
        parent = self.load_session(parent_session_id)
        new_sid = str(uuid.uuid4())
        new_session = Session(
            session_id=new_sid,
            storage_path=self._path_for(new_sid),
            parent_session_id=parent_session_id,
            fork_point=fork_point,
        )

        # Copy all entries up to fork_point
        copied: List[SessionEntry] = []
        reached_fork = False
        for entry in parent.entries:
            copied.append(entry)
            if entry.id == fork_point:
                reached_fork = True
                break

        if not reached_fork and fork_point:
            logger.warning(f"Fork point {fork_point} not found in parent {parent_session_id}; copying all entries.")

        for entry in copied:
            new_session.entries.append(entry)
            new_session._entries_by_id[entry.id] = entry

        # Branch summary entry marks the divergence point
        branch_summary = summary or f"Branched from session {parent_session_id} at {fork_point}"
        branch_entry = SessionEntry(
            parent_id=fork_point if reached_fork else (copied[-1].id if copied else None),
            type="branch_summary",
            role="system",
            content=branch_summary,
            metadata={"parent": parent_session_id, "fork_point": fork_point, "summary": branch_summary},
        )
        new_session.entries.append(branch_entry)
        new_session._entries_by_id[branch_entry.id] = branch_entry
        new_session.flush()
        return new_session

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        """
        SPEC §5.1-5.8 lines 5761-5769:
        FUNCTION resume_session(session_id):
            session = load_session(session_id)
            messages = session.replay_entries()
            compactions = session.get_compaction_entries()
            context = rebuild_context(compactions, messages)
            RETURN context
        """
        session = self.load_session(session_id)
        messages = session.replay_entries()
        compactions = session.get_compaction_entries()
        context = session.rebuild_context()
        return {
            "session_id": session_id,
            "messages_count": len(messages),
            "compactions_count": len(compactions),
            "context": context,
        }


class TelegramSessionBridge:
    """
    SPEC §5.1-5.8 lines 5771-5799:
    Telegram↔Session bridge maps Telegram chat IDs to Pi session IDs.
    State stored in PostgreSQL/SQLite telegram_sessions table.
    """

    def __init__(
        self,
        session_manager: SessionManager,
        db_path: Optional[Path | str] = None,
    ) -> None:
        self.session_manager = session_manager
        if db_path is None:
            self.db_path = self.session_manager.sessions_dir / "telegram_sessions.db"
        else:
            self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_sessions (
                    chat_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def get_session_id(self, chat_id: str | int) -> Optional[str]:
        cid = str(chat_id).strip()
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT session_id FROM telegram_sessions WHERE chat_id = ?", (cid,))
            row = cur.fetchone()
            return row[0] if row else None

    def set_session_id(self, chat_id: str | int, session_id: str) -> None:
        cid = str(chat_id).strip()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO telegram_sessions (chat_id, session_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET session_id=excluded.session_id, updated_at=excluded.updated_at
                """,
                (cid, session_id, time.time()),
            )
            conn.commit()

    def bridge_telegram_to_session(
        self,
        telegram_chat_id: str | int,
        user_message: str,
        channel_provider: Any = None,
        responder: Optional[Callable[[str, Session], str]] = None,
    ) -> Dict[str, Any]:
        """
        SPEC §5.1-5.8 lines 5771-5792:
        FUNCTION bridge_telegram_to_session(telegram_chat_id, user_message):
            session_id = session_map.get(telegram_chat_id)
            IF session_id is None:
                session_id = create_new_session()
                session_map.set(telegram_chat_id, session_id)
            session = load_session(session_id)
            session.append(MessageEntry { role: "user", content: user_message })
            response = run_reactive_loop(session, user_message)
            channel_provider.send_message(telegram_chat_id, response)
            session.append(MessageEntry { role: "assistant", content: response })
            session.flush()
        """
        cid = str(telegram_chat_id).strip()
        session_id = self.get_session_id(cid)
        if session_id is None:
            new_session = self.session_manager.create_session()
            session_id = new_session.session_id
            self.set_session_id(cid, session_id)
            session = new_session
        else:
            try:
                session = self.session_manager.load_session(session_id)
            except FileNotFoundError:
                session = self.session_manager.create_session(session_id=session_id)

        # Inject message into Pi session
        user_entry = SessionEntry(role="user", content=user_message, type="message")
        session.append(user_entry)

        # Run reactive pipeline or default responder
        if responder:
            response_text = responder(user_message, session)
        else:
            response_text = f"Acknowledged: {user_message}"

        # Send response back via channel provider if provided
        if channel_provider and hasattr(channel_provider, "send_message"):
            try:
                channel_provider.send_message(cid, response_text)
            except Exception as e:
                logger.error(f"Failed to send telegram message to {cid}: {e}")

        # Persist assistant response
        assistant_entry = SessionEntry(role="assistant", content=response_text, type="message")
        session.append(assistant_entry)
        session.flush()

        return {
            "status": "ok",
            "chat_id": cid,
            "session_id": session_id,
            "response": response_text,
        }
