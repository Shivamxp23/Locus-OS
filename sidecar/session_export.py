"""Session Export Engine (§5.1-§5.4).

Exports JSONL session logs to markdown transcripts, JSON representations, or HTML archives.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from sidecar.session_manager import Session, SessionEntryType


class SessionExporter:
    """Exports conversation sessions to structured formats."""

    @staticmethod
    def to_markdown(session: Session) -> str:
        lines: List[str] = [
            f"# Session: {session.metadata.title}",
            f"- **Session ID**: `{session.metadata.session_id}`",
            f"- **Created At**: {session.metadata.created_at}",
        ]
        if session.metadata.parent_session_id:
            lines.append(f"- **Parent Session**: `{session.metadata.parent_session_id}` (Fork at `{session.metadata.fork_point_entry_id}`)")

        lines.append("\n---\n")

        for entry in session.entries:
            etype = entry.entry_type
            if etype == SessionEntryType.MESSAGE.value:
                role = entry.payload.get("role", "unknown").capitalize()
                content = entry.payload.get("content", "")
                lines.append(f"### {role} ({entry.created_at[:19]})\n\n{content}\n")
            elif etype == SessionEntryType.TOOL_CALL.value:
                tool = entry.payload.get("tool", "")
                args = json.dumps(entry.payload.get("arguments", {}), indent=2)
                lines.append(f"> **Tool Call**: `{tool}`\n```json\n{args}\n```\n")
            elif etype == SessionEntryType.COMPACTION_SUMMARY.value:
                summary = entry.payload.get("summary", "")
                lines.append(f"> [!NOTE]\n> **Context Compaction**: {summary}\n")
            elif etype == SessionEntryType.BRANCH_SUMMARY.value:
                parent_id = entry.payload.get("parent_session_id")
                lines.append(f"> [!TIP]\n> **Branched from `{parent_id}`**\n")

        return "\n".join(lines)

    @staticmethod
    def to_jsonl(session: Session) -> str:
        records: List[str] = [json.dumps({"type": "metadata", **session.metadata.__dict__})]
        for entry in session.entries:
            records.append(json.dumps(entry.to_dict()))
        return "\n".join(records)
