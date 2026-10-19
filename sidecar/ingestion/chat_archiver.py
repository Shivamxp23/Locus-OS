"""
SPEC §19.3 line 15 / F-0050: AI Chat Archiver Ingestion Subsystem.
Parses multi-platform conversation dumps, formats them with YAML frontmatter,
persists them into the Obsidian vault under 04-Captures/AI Chats/YYYY-MM-DD/,
and triggers automated LiveSync replication.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from sidecar import config
from sidecar.crawlers.chat_crawler import ChatCrawler
from sidecar.providers.chat_archiver import (
    ArchiveResult,
    BaseChatArchiverProvider,
    NormalizedChat,
)
from sidecar.registry import get_registry

logger = logging.getLogger("locus.ingestion.chat_archiver")


def sanitize_filename(title: str) -> str:
    """Sanitize title into safe filename stem."""
    clean = re.sub(r'[\\/*?:"<>|]', "", title).strip()
    clean = re.sub(r"\s+", "-", clean)
    return clean[:80] or "untitled-chat"


class ChatArchiverProvider(BaseChatArchiverProvider):
    """
    Standard implementation of BaseChatArchiverProvider conforming to
    SPEC §19.3 and SPEC §03 modular provider lifecycle.
    """

    def __init__(self, name: str = "default_chat_archiver") -> None:
        super().__init__(name=name)
        self.crawler = ChatCrawler()

    def is_enabled(self) -> bool:
        """Modular off-switch check: locus.ingestion.chat_archiver.enabled."""
        return config.get("locus.ingestion.chat_archiver.enabled", True) is not False

    def get_vault_path(self) -> Path:
        """Resolve canonical vault root directory."""
        custom_vault = config.get("locus.vault.path")
        if custom_vault:
            p = Path(custom_vault).resolve()
        else:
            p = (config.get_locus_home() / "vault").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def initialize(self, options: Optional[Dict[str, Any]] = None) -> None:
        """Initialize provider lifecycle."""
        self.get_vault_path()

    def health_check(self) -> Dict[str, Any]:
        """Provider health check report."""
        enabled = self.is_enabled()
        vault_path = self.get_vault_path()
        return {
            "status": "ok" if enabled else "disabled",
            "provider": self.name,
            "enabled": enabled,
            "vault_path": str(vault_path),
            "captures_dir": str(vault_path / "04-Captures" / "AI Chats"),
        }

    def format_markdown_note(self, chat: NormalizedChat) -> str:
        """Format normalized conversation into Obsidian-compatible markdown with frontmatter."""
        date_str = chat.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tags = chat.tags or ["ai-chat", chat.platform]

        lines = [
            "---",
            f'title: "{chat.title}"',
            f"date: {date_str}",
            f"platform: {chat.platform}",
            f"model: {chat.model}",
            "tags:",
        ]
        for tag in tags:
            lines.append(f"  - {tag}")
        if chat.summary:
            lines.append(f'summary: "{chat.summary}"')
        lines.append("---")
        lines.append("")
        lines.append(f"# {chat.title}")
        lines.append("")

        if chat.key_decisions:
            lines.append("## Key Decisions")
            for dec in chat.key_decisions:
                lines.append(f"- {dec}")
            lines.append("")

        lines.append("## Transcript")
        lines.append("")

        for turn in chat.turns:
            role_title = "User" if turn.role.lower() == "user" else "Assistant"
            lines.append(f"### {role_title}")
            lines.append(turn.content.strip())
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def crawl_and_parse(self, source_path: Path) -> List[NormalizedChat]:
        """Crawl export files and return normalized chats."""
        if not self.is_enabled():
            return []
        if source_path.is_file():
            return self.crawler.parse_file(source_path)
        elif source_path.is_dir():
            return self.crawler.crawl_directory(source_path)
        return []

    def archive_chat(self, chat: NormalizedChat) -> ArchiveResult:
        """Write chat to vault under 04-Captures/AI Chats/YYYY-MM-DD/ and trigger LiveSync."""
        if not self.is_enabled():
            return ArchiveResult(
                title=chat.title,
                platform=chat.platform,
                vault_rel_path="",
                status="skipped",
                error="archiver_disabled",
            )

        vault_path = self.get_vault_path()
        date_folder = chat.date if (chat.date and len(chat.date) == 10) else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        dest_dir = vault_path / "04-Captures" / "AI Chats" / date_folder
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{sanitize_filename(chat.title)}.md"
        dest_file = dest_dir / filename
        rel_path = f"04-Captures/AI Chats/{date_folder}/{filename}"

        md_content = self.format_markdown_note(chat)
        dest_file.write_text(md_content, encoding="utf-8")

        replicated = False
        # Automated LiveSync CouchDB replication trigger
        if config.get("locus.vault.sync.enabled", True):
            try:
                registry = get_registry()
                sync_provider_cls = registry.get_active_provider("vault_sync", default_name="couchdb_livesync")
                if sync_provider_cls:
                    sync_inst = sync_provider_cls()
                    sync_inst.initialize()
                    res = sync_inst.push(rel_path)
                    replicated = res.get("status") in ("pushed", "skipped")
            except Exception as ex:
                logger.debug("LiveSync push notification caught: %s", ex)

        return ArchiveResult(
            title=chat.title,
            platform=chat.platform,
            vault_rel_path=rel_path,
            status="archived",
            replicated=replicated,
        )

    def archive_all(self, source_dirs: Optional[List[Path]] = None) -> List[ArchiveResult]:
        """Crawl all configured search directories and archive discovered chats."""
        if not self.is_enabled():
            return []

        search_dirs = source_dirs or self.crawler.get_default_crawl_dirs()
        results: List[ArchiveResult] = []

        for src in search_dirs:
            chats = self.crawl_and_parse(src)
            for c in chats:
                res = self.archive_chat(c)
                results.append(res)

        return results
