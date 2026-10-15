"""sidecar/crawlers/chat_crawler.py - Directory & export watcher for conversation dumps.

Implements Spec §19.3 Step 2:
- Discovers chat export files (ChatGPT, Claude, Cursor, Telegram, Pi session transcripts).
- Scans configured export directories and returns raw source payloads for normalization.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger("sidecar.crawlers.chat")


class ChatCrawler:
    """Discovers and reads conversation export dumps and local transcripts."""

    def __init__(self, watch_dirs: Sequence[Path | str] | None = None):
        self.watch_dirs = [Path(d) for d in watch_dirs] if watch_dirs else []

    def add_watch_dir(self, directory: Path | str) -> None:
        p = Path(directory)
        if p not in self.watch_dirs:
            self.watch_dirs.append(p)

    def scan_files(self) -> list[Path]:
        """Find candidate conversation export files in watched directories."""
        candidates: list[Path] = []
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists() or not watch_dir.is_dir():
                continue
            for ext in ("*.json", "*.jsonl", "*.md"):
                candidates.extend(watch_dir.rglob(ext))
        return sorted(set(candidates))

    def read_export(self, file_path: Path) -> Optional[dict[str, Any] | list[Any]]:
        """Safely read and parse a JSON or JSONL export file."""
        if not file_path.is_file():
            return None

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            if file_path.suffix.lower() == ".json":
                return json.loads(content)
            elif file_path.suffix.lower() == ".jsonl":
                lines = [json.loads(line) for line in content.splitlines() if line.strip()]
                return lines
            else:
                return {"path": str(file_path), "text": content}
        except Exception as exc:
            logger.warning("Failed to parse chat export file %s: %s", file_path, exc)
            return None
