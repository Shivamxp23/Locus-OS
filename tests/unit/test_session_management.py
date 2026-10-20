"""
Unit tests for Session Management & Telegram Bridge (SPEC §5.1-5.8 / F-0027).
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from sidecar.sessions.session_manager import (
    VALID_ENTRY_TYPES,
    Session,
    SessionEntry,
    SessionManager,
    TelegramSessionBridge,
)
from sidecar.session_export import (
    export_to_markdown,
    export_to_json,
    export_to_jsonl,
    export_session,
)
from sidecar.providers.session_management import (
    BaseSessionManagementProvider,
    DefaultSessionManagementProvider,
)
import sidecar.config as config


def test_session_format_and_entry_types(tmp_path: Path) -> None:
    """SPEC §5.1-5.8 line 5738: "SESSION FORMAT (JSONL v3): Entry types: message, tool_call, tool_result, compaction_summary, branch_summary, metadata, system_event, checkpoint, marker" """
    mgr = SessionManager(sessions_dir=tmp_path)
    session = mgr.create_session(session_id="test-session-1")

    # Verify initial metadata entry
    assert len(session.entries) == 1
    assert session.entries[0].type == "metadata"

    # Append every valid entry type
    for et in VALID_ENTRY_TYPES:
        if et == "metadata":
            continue
        entry = SessionEntry(type=et, content=f"Sample content for {et}", role="user" if et == "message" else None)
        session.append(entry)

    assert len(session.entries) == len(VALID_ENTRY_TYPES)
    # Check JSONL file was written
    storage_file = tmp_path / "test-session-1.jsonl"
    assert storage_file.exists()
    lines = storage_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == len(VALID_ENTRY_TYPES)


def test_session_invalid_entry_type(tmp_path: Path) -> None:
    """SPEC §5.1-5.8 line 5739: "Entry types: message, tool_call, tool_result, compaction_summary..." """
    mgr = SessionManager(sessions_dir=tmp_path)
    session = mgr.create_session(session_id="invalid-type-session")
    with pytest.raises(ValueError, match="Invalid entry type"):
        session.append(SessionEntry(type="non_existent_type", content="bad"))


def test_session_tree_and_forking(tmp_path: Path) -> None:
    """SPEC §5.1-5.8 line 5746: "FUNCTION fork_session(parent_session_id, fork_point):" """
    mgr = SessionManager(sessions_dir=tmp_path)
    parent = mgr.create_session(session_id="parent-session")

    e1 = SessionEntry(type="message", role="user", content="Turn 1: hello")
    parent.append(e1)
    e2 = SessionEntry(type="message", role="assistant", content="Turn 1: hi there")
    parent.append(e2)
    e3 = SessionEntry(type="message", role="user", content="Turn 2: alternative universe")
    parent.append(e3)

    # Fork at e2 (before turn 2)
    forked = mgr.fork_session(parent_session_id="parent-session", fork_point=e2.id, summary="Divergence at Turn 1")

    assert forked.parent_session_id == "parent-session"
    assert forked.fork_point == e2.id
    # Should contain metadata, e1, e2, plus the new branch_summary entry
    entry_types = [e.type for e in forked.entries]
    assert "branch_summary" in entry_types
    branch_entry = [e for e in forked.entries if e.type == "branch_summary"][0]
    assert branch_entry.content == "Divergence at Turn 1"
    assert branch_entry.metadata["parent"] == "parent-session"
    assert branch_entry.metadata["fork_point"] == e2.id

    # Verify forked session was persisted to its own .jsonl file
    forked_file = tmp_path / f"{forked.session_id}.jsonl"
    assert forked_file.exists()


def test_session_resume_rebuild_context(tmp_path: Path) -> None:
    """SPEC §5.1-5.8 line 5761: "FUNCTION resume_session(session_id):" """
    mgr = SessionManager(sessions_dir=tmp_path)
    session = mgr.create_session(session_id="resume-session")

    # Add compaction summary
    compaction = SessionEntry(type="compaction_summary", content="Previous 10 turns discussed Python sidecar design.")
    session.append(compaction)

    # Add messages
    m1 = SessionEntry(type="message", role="user", content="What did we discuss earlier?")
    session.append(m1)
    m2 = SessionEntry(type="message", role="assistant", content="We discussed Python sidecar architecture.")
    session.append(m2)

    resume_res = mgr.resume_session("resume-session")
    assert resume_res["session_id"] == "resume-session"
    assert resume_res["compactions_count"] == 1
    assert resume_res["messages_count"] == 2

    # Context should place compaction summaries first, followed by replay messages
    context = resume_res["context"]
    assert len(context) == 3
    assert context[0]["role"] == "system"
    assert "[Compaction Summary]" in context[0]["content"]
    assert context[1]["role"] == "user"
    assert context[2]["role"] == "assistant"


def test_session_exports(tmp_path: Path) -> None:
    """SPEC §5.1-5.8 line 5797: "KEEP: All Pi session formats, branching, resume, export. Zero changes." """
    mgr = SessionManager(sessions_dir=tmp_path)
    session = mgr.create_session(session_id="export-session")
    session.append(SessionEntry(type="message", role="user", content="Hello export world"))
    session.append(SessionEntry(type="message", role="assistant", content="Export received"))

    # Markdown export
    md_content = export_to_markdown(session, sessions_dir=tmp_path)
    assert "# Locus Session Transcript: export-session" in md_content
    assert "Hello export world" in md_content
    assert "Export received" in md_content

    # JSON export
    json_str = export_to_json(session, sessions_dir=tmp_path)
    json_data = json.loads(json_str)
    assert json_data["session_id"] == "export-session"
    assert json_data["entries_count"] == 3

    # JSONL export
    out_jsonl = tmp_path / "exported.jsonl"
    jsonl_str = export_to_jsonl(session, output_path=out_jsonl, sessions_dir=tmp_path)
    assert out_jsonl.exists()
    assert len(jsonl_str.strip().split("\n")) == 3

    # Unified export_session
    res = export_session("export-session", format="markdown", sessions_dir=tmp_path)
    assert res["status"] == "ok"
    assert res["format"] == "markdown"


def test_telegram_session_bridge(tmp_path: Path) -> None:
    """SPEC §5.1-5.8 line 5771: "TELEGRAM SESSION BRIDGE (Locus-unique): FUNCTION bridge_telegram_to_session(telegram_chat_id, user_message):" """
    mgr = SessionManager(sessions_dir=tmp_path)
    bridge = TelegramSessionBridge(session_manager=mgr, db_path=tmp_path / "tg.db")

    chat_id = 987654321

    # First message creates session
    res1 = bridge.bridge_telegram_to_session(chat_id, "Hello from Telegram bot")
    assert res1["status"] == "ok"
    assert res1["chat_id"] == str(chat_id)
    sid1 = res1["session_id"]
    assert sid1 is not None

    # Verify session entries
    session1 = mgr.load_session(sid1)
    # metadata + user message + assistant response
    assert len(session1.entries) == 3
    assert session1.entries[1].content == "Hello from Telegram bot"
    assert session1.entries[2].role == "assistant"

    # Second message re-uses existing mapped session
    res2 = bridge.bridge_telegram_to_session(chat_id, "Second message in same chat")
    assert res2["session_id"] == sid1
    session1_reloaded = mgr.load_session(sid1)
    assert len(session1_reloaded.entries) == 5


def test_session_management_provider_off_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §03 / §5.1-5.8: Off-switch behavior: locus.session_management.enabled returning 503."""
    provider = DefaultSessionManagementProvider(sessions_dir=tmp_path, db_path=tmp_path / "tg.db")
    assert provider.is_available() is True

    # Disable via config
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "session" in key else default)
    assert provider.is_available() is False

    with pytest.raises(RuntimeError, match="Session Management is disabled"):
        provider.create_session()

    with pytest.raises(RuntimeError, match="Session Management is disabled"):
        provider.load_session("some-id")

    with pytest.raises(RuntimeError, match="Session Management is disabled"):
        provider.bridge_telegram("123", "hi")
