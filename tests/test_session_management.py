import pytest
from sidecar.session_manager import (
    SessionEntryType,
    SessionEntry,
    SessionMetadata,
    Session,
    SessionManager,
)
from sidecar.session_export import SessionExporter


def test_session_create_and_append():
    mgr = SessionManager()
    session = mgr.create_session(title="Unit Test Session")
    assert session.metadata.title == "Unit Test Session"

    session.append_message("user", "Hello world")
    session.append_message("assistant", "Hi there!")

    msgs = session.replay_messages()
    assert len(msgs) == 2
    assert msgs[0]["content"] == "Hello world"
    assert msgs[1]["content"] == "Hi there!"


def test_session_forking_branch():
    mgr = SessionManager()
    parent = mgr.create_session(title="Parent Session")
    e1 = parent.append_message("user", "Turn 1")
    e2 = parent.append_message("assistant", "Response 1")
    parent.append_message("user", "Turn 2")

    # Fork at e2
    child = mgr.fork_session(parent.metadata.session_id, fork_point_entry_id=e2.id)
    assert child.metadata.parent_session_id == parent.metadata.session_id
    assert child.metadata.fork_point_entry_id == e2.id

    # Should have e1, e2, plus the branch summary entry
    assert len(child.entries) == 3
    assert child.entries[-1].entry_type == SessionEntryType.BRANCH_SUMMARY.value


def test_session_export_markdown_and_jsonl():
    mgr = SessionManager()
    sess = mgr.create_session(title="Export Test")
    sess.append_message("user", "What is Locus?")
    sess.append(SessionEntryType.TOOL_CALL.value, {"tool": "locus_checkin", "arguments": {"dcs": 90}})

    md = SessionExporter.to_markdown(sess)
    assert "# Session: Export Test" in md
    assert "### User" in md
    assert "Tool Call" in md

    jsonl = SessionExporter.to_jsonl(sess)
    lines = jsonl.strip().split("\n")
    assert len(lines) == 3  # metadata + 2 entries
