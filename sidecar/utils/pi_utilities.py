"""
SPEC §24.1 lines 2720-2726: Pi Utilities (Clipboard, Syntax Highlighting, Frontmatter, File Watcher).
Core utilities inherited from Pi with Python sidecar parity interfaces and modular control.
"""
from __future__ import annotations

import base64
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("locus.utils.pi")


@dataclass
class ParsedDocument:
    metadata: dict[str, Any]
    body: str
    has_frontmatter: bool


class ClipboardManager:
    """
    SPEC §24.1: Cross-platform clipboard manager with OSC-52 terminal copy support.
    """

    def __init__(self) -> None:
        self._buffer: str = ""
        self._last_copied_at: float = 0.0

    def copy(self, text: str) -> dict[str, Any]:
        """Copy text to clipboard buffer."""
        self._buffer = text
        self._last_copied_at = time.time()
        # OSC 52 sequence generation simulation
        b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        osc52_seq = f"\x1b]52;c;{b64}\x07"
        return {
            "status": "ok",
            "characters_count": len(text),
            "osc52_bytes": len(osc52_seq),
            "timestamp": self._last_copied_at,
        }

    def paste(self) -> str:
        """Paste current clipboard contents."""
        return self._buffer

    def clear(self) -> None:
        """Clear clipboard buffer."""
        self._buffer = ""
        self._last_copied_at = 0.0


class FrontmatterParser:
    """
    SPEC §24.1: YAML frontmatter extractor and stripper for markdown notes and memory documents.
    """

    _FRONTMATTER_PATTERN = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", re.DOTALL)

    def parse(self, content: str) -> ParsedDocument:
        """Parse YAML frontmatter header and body."""
        content = content.lstrip("\ufeff")  # strip UTF-8 BOM
        match = self._FRONTMATTER_PATTERN.match(content)
        if not match:
            return ParsedDocument(metadata={}, body=content, has_frontmatter=False)

        yaml_str, body = match.group(1), match.group(2)
        try:
            meta = yaml.safe_load(yaml_str) or {}
            if not isinstance(meta, dict):
                meta = {"raw": meta}
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter YAML: {e}")
            meta = {"error": str(e), "raw": yaml_str}

        return ParsedDocument(metadata=meta, body=body.strip(), has_frontmatter=True)

    def strip(self, content: str) -> str:
        """Return body with frontmatter stripped."""
        return self.parse(content).body


class SyntaxHighlighter:
    """
    SPEC §24.1: Syntax highlighter tokenizing source code for CLI / terminal display.
    """

    SUPPORTED_LANGUAGES = {
        "python", "javascript", "typescript", "json", "bash", "sh", "yaml", "html", "css", "rust", "go"
    }

    def highlight(self, code: str, language: str = "text") -> dict[str, Any]:
        """Apply syntax tagging to code snippets."""
        lang = language.lower() if language else "text"
        lines = code.splitlines()

        token_counts: dict[str, int] = {"keywords": 0, "strings": 0, "comments": 0}

        # Lightweight regex token detection for diagnostics
        if lang in ("python", "bash", "sh"):
            comment_char = "#"
        else:
            comment_char = "//"

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(comment_char):
                token_counts["comments"] += 1
            if '"' in line or "'" in line:
                token_counts["strings"] += 1
            if any(w in line for w in ("def ", "class ", "import ", "function ", "const ", "let ", "return ")):
                token_counts["keywords"] += 1

        return {
            "language": lang,
            "supported": lang in self.SUPPORTED_LANGUAGES,
            "line_count": len(lines),
            "tokens": token_counts,
            "highlighted": code,
        }


class FileWatcher:
    """
    SPEC §24.1: File watcher tracking file change modifications across watched root.
    """

    def __init__(self, watch_dir: str | Path = ".") -> None:
        self.watch_dir = Path(watch_dir)
        self._snapshots: dict[str, float] = {}
        self._initialized: bool = False

    def scan(self) -> dict[str, float]:
        """Scan watched directory for files and mtime."""
        current: dict[str, float] = {}
        if not self.watch_dir.exists():
            return current

        if self.watch_dir.is_file():
            current[str(self.watch_dir)] = self.watch_dir.stat().st_mtime
            return current

        for p in self.watch_dir.rglob("*"):
            if p.is_file():
                try:
                    rel_parts = p.relative_to(self.watch_dir).parts
                    if not any(part.startswith(".") for part in rel_parts):
                        current[str(p)] = p.stat().st_mtime
                except (OSError, ValueError):
                    pass
        return current

    def poll_changes(self) -> list[dict[str, Any]]:
        """Poll for created, modified, and deleted files since last poll."""
        current = self.scan()
        changes: list[dict[str, Any]] = []

        if not self._initialized:
            self._snapshots = current
            self._initialized = True
            return changes

        # Check modified and created
        for path, mtime in current.items():
            if path not in self._snapshots:
                changes.append({"event": "created", "path": path, "mtime": mtime})
            elif mtime > self._snapshots[path]:
                changes.append({"event": "modified", "path": path, "mtime": mtime})

        # Check deleted
        for path in self._snapshots:
            if path not in current:
                changes.append({"event": "deleted", "path": path})

        self._snapshots = current
        return changes
