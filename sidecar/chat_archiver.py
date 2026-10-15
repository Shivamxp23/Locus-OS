"""sidecar/chat_archiver.py - Daily AI Chat Archiver & Audit Log Generator.

Implements Spec §19.3 and Errata Decision D-4:
- Scans external chat dumps (ChatGPT, Claude, Cursor) and local transcripts (Pi, Telegram).
- Extracts user prompts, assistant completions, tool calls, and session metadata.
- Sanitizes all secrets using security.redact_patterns (S-0, D-4).
- Generates daily markdown audit logs under vault/05-Daily/Logs/audit-YYYY-MM-DD.md.
- Integrates with APScheduler for nightly execution at 03:00 local time.
- Modular switch: locus.ingestion.chat_archiver.enabled (True | False).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Protocol, Sequence, runtime_checkable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from sidecar.config import get as config_get, is_enabled as config_is_enabled
from sidecar.crawlers.chat_crawler import ChatCrawler
from sidecar.security.redact import redact_patterns

logger = logging.getLogger("sidecar.chat_archiver")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT_DIR = REPO_ROOT / "vault"
DEFAULT_EXPORT_DIR = Path.home() / ".locus" / "chat_exports"
DEFAULT_TRAJECTORY_DIR = Path.home() / ".locus" / "trajectories"


@dataclass
class ChatTurn:
    """Normalized single turn from any chat platform."""

    role: str
    content: str
    timestamp: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model: str = ""


@dataclass
class ChatSession:
    """Normalized multi-turn chat session."""

    session_id: str
    platform: str
    title: str = "Chat Session"
    started_at: str = ""
    turns: list[ChatTurn] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ChatArchiverProvider(Protocol):
    """Protocol for AI Chat Archiver providers."""

    def archive_daily_chats(
        self, date_str: str | None = None, dry_run: bool = False
    ) -> Optional[Path]:
        """Aggregate and persist daily chat logs into the vault."""
        return None

    def scan_sources(
        self, source_dirs: Sequence[Path | str] | None = None
    ) -> list[ChatSession]:
        """Scan and normalize chat sessions from input sources."""
        return []


class ChatArchiver:
    """Main implementation of Spec §19.3 Daily AI Chat Archiver."""

    def __init__(
        self,
        vault_root: Path | str | None = None,
        export_dirs: Sequence[Path | str] | None = None,
        trajectory_dir: Path | str | None = None,
        enabled: Optional[bool] = None,
    ):
        self.vault_root = Path(vault_root) if vault_root else DEFAULT_VAULT_DIR
        self.export_dirs = [Path(d) for d in export_dirs] if export_dirs else [DEFAULT_EXPORT_DIR]
        self.trajectory_dir = Path(trajectory_dir) if trajectory_dir else DEFAULT_TRAJECTORY_DIR
        self._enabled_override = enabled
        self.crawler = ChatCrawler(watch_dirs=self.export_dirs)
        if self.trajectory_dir.exists():
            self.crawler.add_watch_dir(self.trajectory_dir)

    @property
    def is_enabled(self) -> bool:
        if self._enabled_override is not None:
            return self._enabled_override
        return bool(config_get("locus.ingestion.chat_archiver.enabled", default=True))

    def normalize_trajectory_record(self, record: dict[str, Any]) -> Optional[ChatSession]:
        """Convert a local trajectory turn or session into a ChatSession."""
        sid = record.get("session_id", "unknown-session")
        prompt = record.get("prompt", "")
        response = record.get("response", "")
        tools = record.get("tool_calls", [])
        ts = str(record.get("timestamp", ""))

        turns: list[ChatTurn] = []
        if prompt:
            turns.append(ChatTurn(role="user", content=prompt, timestamp=ts))
        if response or tools:
            turns.append(ChatTurn(role="assistant", content=response, timestamp=ts, tool_calls=tools))

        if not turns:
            return None

        return ChatSession(
            session_id=sid,
            platform="locus-pi",
            title=f"Locus Session {sid[:8]}",
            started_at=ts,
            turns=turns,
            metadata=record.get("metadata", {}),
        )

    def normalize_chatgpt_export(self, item: dict[str, Any]) -> Optional[ChatSession]:
        """Parse ChatGPT export structure."""
        sid = item.get("id") or item.get("conversation_id") or "chatgpt-session"
        title = item.get("title") or "ChatGPT Conversation"
        mapping = item.get("mapping", {})

        turns: list[ChatTurn] = []
        for node_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue
            author_role = msg.get("author", {}).get("role", "unknown")
            if author_role not in ("user", "assistant", "system"):
                continue

            parts = msg.get("content", {}).get("parts", [])
            text = " ".join(str(p) for p in parts if isinstance(p, str))
            if text.strip():
                turns.append(ChatTurn(role=author_role, content=text))

        if not turns:
            return None

        return ChatSession(
            session_id=sid,
            platform="chatgpt",
            title=title,
            turns=turns,
        )

    def normalize_claude_export(self, item: dict[str, Any]) -> Optional[ChatSession]:
        """Parse Claude export structure."""
        sid = item.get("uuid") or item.get("id") or "claude-session"
        title = item.get("name") or "Claude Conversation"
        raw_messages = item.get("chat_messages", [])

        turns: list[ChatTurn] = []
        for msg in raw_messages:
            sender = msg.get("sender", "unknown")
            text = msg.get("text", "")
            if text.strip():
                role = "user" if sender == "human" else "assistant"
                turns.append(ChatTurn(role=role, content=text))

        if not turns:
            return None

        return ChatSession(
            session_id=sid,
            platform="claude",
            title=title,
            turns=turns,
        )

    def scan_sources(
        self, source_dirs: Sequence[Path | str] | None = None
    ) -> list[ChatSession]:
        """Scan watched directories and extract all normalized ChatSessions."""
        if source_dirs:
            crawler = ChatCrawler(watch_dirs=source_dirs)
        else:
            crawler = self.crawler

        files = crawler.scan_files()
        sessions: list[ChatSession] = []

        for f in files:
            data = crawler.read_export(f)
            if not data:
                continue

            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict):
                        # Try trajectory turn format
                        if "prompt" in entry or "turn_id" in entry:
                            sess = self.normalize_trajectory_record(entry)
                            if sess:
                                sessions.append(sess)
                        # Try ChatGPT / Claude conversation list
                        elif "mapping" in entry:
                            sess = self.normalize_chatgpt_export(entry)
                            if sess:
                                sessions.append(sess)
                        elif "chat_messages" in entry:
                            sess = self.normalize_claude_export(entry)
                            if sess:
                                sessions.append(sess)
            elif isinstance(data, dict):
                if "mapping" in data:
                    sess = self.normalize_chatgpt_export(data)
                    if sess:
                        sessions.append(sess)
                elif "chat_messages" in data:
                    sess = self.normalize_claude_export(data)
                    if sess:
                        sessions.append(sess)
                elif "prompt" in data or "turn_id" in data:
                    sess = self.normalize_trajectory_record(data)
                    if sess:
                        sessions.append(sess)

        return sessions

    def render_audit_markdown(self, target_date: str, sessions: list[ChatSession]) -> str:
        """Render complete audit markdown with YAML frontmatter and redacted turns (D-4)."""
        total_turns = sum(len(s.turns) for s in sessions)
        now_iso = datetime.now().isoformat()

        lines: list[str] = [
            "---",
            f"date: {target_date}",
            "type: audit-log",
            f"archived_at: {now_iso}",
            f"total_sessions: {len(sessions)}",
            f"total_turns: {total_turns}",
            "---",
            "",
            f"# Daily AI Chat & Inner Loop Audit Log: {target_date}",
            "",
            f"Aggregated {len(sessions)} sessions ({total_turns} turns). All secrets masked per Law S-0.",
            "",
        ]

        if not sessions:
            lines.append("_No chat interactions recorded for this date._\n")
            return "\n".join(lines)

        for idx, sess in enumerate(sessions, 1):
            clean_title = redact_patterns(sess.title)
            lines.append(f"## {idx}. [{sess.platform.upper()}] {clean_title} (`{sess.session_id}`)")
            if sess.started_at:
                lines.append(f"- **Timestamp**: `{sess.started_at}`")
            lines.append("")

            for t_idx, turn in enumerate(sess.turns, 1):
                clean_content = redact_patterns(turn.content)
                role_label = turn.role.capitalize()
                lines.append(f"### Turn {t_idx} — {role_label}")
                lines.append(f"> {clean_content}")
                lines.append("")

                if turn.tool_calls:
                    lines.append("**Tools Executed**:")
                    for tool in turn.tool_calls:
                        clean_tool = redact_patterns(tool)
                        lines.append(f"- `{json.dumps(clean_tool, ensure_ascii=False)}`")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def archive_daily_chats(
        self, date_str: str | None = None, dry_run: bool = False
    ) -> Optional[Path]:
        """Aggregate chat sources, sanitize secrets, and write to vault/05-Daily/Logs/audit-YYYY-MM-DD.md."""
        if not self.is_enabled:
            logger.info("Chat archiver is disabled by configuration. Skipping.")
            return None

        target_date = date_str or date.today().isoformat()
        sessions = self.scan_sources()
        markdown_text = self.render_audit_markdown(target_date, sessions)

        logs_dir = self.vault_root / "05-Daily" / "Logs"
        out_file = logs_dir / f"audit-{target_date}.md"

        if dry_run:
            logger.info("[DRY RUN] Generated audit log for %s (%d chars)", target_date, len(markdown_text))
            return out_file

        logs_dir.mkdir(parents=True, exist_ok=True)
        out_file.write_text(markdown_text, encoding="utf-8")
        logger.info("Saved daily audit log to %s (%d sessions)", out_file, len(sessions))
        return out_file


def schedule_nightly_archival_job(
    scheduler: BackgroundScheduler | None = None,
    cron_hour: int = 3,
    cron_minute: int = 0,
    archiver: ChatArchiver | None = None,
) -> Any:
    """Register the nightly chat archiver job with APScheduler (03:00 local time)."""
    sched = scheduler or BackgroundScheduler()
    active_archiver = archiver or ChatArchiver()

    def _nightly_job_fn():
        logger.info("Starting scheduled nightly chat archival...")
        active_archiver.archive_daily_chats()

    trigger = CronTrigger(hour=cron_hour, minute=cron_minute)
    job = sched.add_job(
        _nightly_job_fn,
        trigger=trigger,
        id="nightly_chat_archiver",
        name="Nightly AI Chat & Telemetry Archiver",
        replace_existing=True,
    )
    logger.info("Scheduled nightly chat archiver job at %02d:%02d", cron_hour, cron_minute)
    return job


def main() -> int:
    """CLI runner supporting `python -m sidecar.chat_archiver --dry-run`."""
    parser = argparse.ArgumentParser(description="Locus OS Daily AI Chat Archiver")
    parser.add_argument("--dry-run", action="store_true", help="Preview output without writing to vault")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--vault-dir", type=str, default=None, help="Custom vault root directory")
    parser.add_argument("--export-dir", type=str, default=None, help="Custom export directory")
    args = parser.parse_args()

    export_dirs = [Path(args.export_dir)] if args.export_dir else None
    archiver = ChatArchiver(vault_root=args.vault_dir, export_dirs=export_dirs)

    res = archiver.archive_daily_chats(date_str=args.date, dry_run=args.dry_run)
    if res:
        print(f"Archive completed successfully: {res} (dry_run={args.dry_run})")
        return 0
    else:
        print("Archive disabled or no output produced.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
