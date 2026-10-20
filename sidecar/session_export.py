"""
SPEC §5.1-5.8: Session Export (F-0027).
Export sessions into Markdown, JSON, and JSONL formats for review, transcripts, and backup.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from sidecar.sessions.session_manager import Session, SessionManager


def export_to_markdown(
    session: Session | str,
    sessions_dir: Optional[Path | str] = None,
) -> str:
    """Export a session transcript formatted as clean GitHub-flavored Markdown."""
    if isinstance(session, str):
        mgr = SessionManager(sessions_dir=sessions_dir)
        session = mgr.load_session(session)

    lines: list[str] = [
        f"# Locus Session Transcript: {session.session_id}",
        "",
        f"- **Session ID**: `{session.session_id}`",
        f"- **Parent Session**: `{session.parent_session_id or 'None'}`",
        f"- **Fork Point**: `{session.fork_point or 'Root'}`",
        f"- **Total Entries**: {len(session.entries)}",
        "",
        "---",
        "",
    ]

    for idx, entry in enumerate(session.entries, 1):
        if entry.type == "metadata":
            lines.append(f"<!-- Metadata: {entry.content or ''} -->\n")
        elif entry.type == "branch_summary":
            lines.append(f"> [!NOTE] **Branch Point**\n> {entry.content or ''}\n")
        elif entry.type == "compaction_summary":
            lines.append(f"> [!IMPORTANT] **Compacted Context Summary**\n> {entry.content or ''}\n")
        elif entry.type == "message":
            role_title = (entry.role or "user").capitalize()
            lines.append(f"### {role_title} (Turn #{idx})\n\n{entry.content or ''}\n")
        elif entry.type == "tool_call":
            lines.append(f"```json\n// Tool Call: {entry.content or ''}\n```\n")
        elif entry.type == "tool_result":
            lines.append(f"```text\n// Tool Result: {entry.content or ''}\n```\n")
        else:
            lines.append(f"*[{entry.type.upper()}]*: {entry.content or ''}\n")

    return "\n".join(lines)


def export_to_json(
    session: Session | str,
    sessions_dir: Optional[Path | str] = None,
    indent: int = 2,
) -> str:
    """Export a session as structured JSON string."""
    if isinstance(session, str):
        mgr = SessionManager(sessions_dir=sessions_dir)
        session = mgr.load_session(session)

    data: Dict[str, Any] = {
        "session_id": session.session_id,
        "parent_session_id": session.parent_session_id,
        "fork_point": session.fork_point,
        "entries_count": len(session.entries),
        "entries": [e.to_dict() for e in session.entries],
    }
    return json.dumps(data, indent=indent)


def export_to_jsonl(
    session: Session | str,
    output_path: Optional[Path | str] = None,
    sessions_dir: Optional[Path | str] = None,
) -> str:
    """Export a session as raw JSONL v3 lines, optionally writing to output_path."""
    if isinstance(session, str):
        mgr = SessionManager(sessions_dir=sessions_dir)
        session = mgr.load_session(session)

    lines = [json.dumps(e.to_dict()) for e in session.entries]
    content = "\n".join(lines) + ("\n" if lines else "")

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")

    return content


def export_session(
    session_id: str,
    format: str = "markdown",
    sessions_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Unified export dispatcher supporting markdown, json, and jsonl."""
    fmt = format.lower().strip()
    mgr = SessionManager(sessions_dir=sessions_dir)
    session = mgr.load_session(session_id)

    if fmt == "markdown" or fmt == "md":
        content = export_to_markdown(session)
    elif fmt == "json":
        content = export_to_json(session)
    elif fmt == "jsonl":
        content = export_to_jsonl(session)
    else:
        raise ValueError(f"Unsupported export format: {format}. Must be 'markdown', 'json', or 'jsonl'.")

    return {
        "status": "ok",
        "session_id": session_id,
        "format": fmt,
        "data": content,
    }
