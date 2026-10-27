"""
SPEC §24.1 lines 2720-2726: Pi Utilities Provider.
Provides BasePiUtilitiesProvider and DefaultPiUtilitiesProvider with modular off-switches:
- locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled
- locus.pi_utilities.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

import abc
import logging
from typing import Any

import sidecar.config as config
from sidecar.utils.pi_utilities import (
    ClipboardManager,
    FileWatcher,
    FrontmatterParser,
    SyntaxHighlighter,
)

logger = logging.getLogger("locus.providers.pi_utilities")


class BasePiUtilitiesProvider(abc.ABC):
    """Abstract base provider for Pi inherited utility subsystems."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name."""
        raise NotImplementedError

    @abc.abstractmethod
    def is_feature_enabled(self) -> tuple[bool, str]:
        """Check if utility subsystem is enabled via config."""
        raise NotImplementedError

    @abc.abstractmethod
    def copy_clipboard(self, text: str) -> dict[str, Any]:
        """Copy text to clipboard."""
        raise NotImplementedError

    @abc.abstractmethod
    def paste_clipboard(self) -> dict[str, Any]:
        """Paste text from clipboard."""
        raise NotImplementedError

    @abc.abstractmethod
    def parse_frontmatter(self, content: str) -> dict[str, Any]:
        """Parse YAML frontmatter header from content."""
        raise NotImplementedError

    @abc.abstractmethod
    def highlight_syntax(self, code: str, language: str = "text") -> dict[str, Any]:
        """Highlight code source tokens."""
        raise NotImplementedError

    @abc.abstractmethod
    def poll_file_changes(self) -> dict[str, Any]:
        """Poll watched directory for file change events."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Return diagnostic runtime state."""
        raise NotImplementedError


class DefaultPiUtilitiesProvider(BasePiUtilitiesProvider):
    """
    Default utilities provider wrapping ClipboardManager, FrontmatterParser, SyntaxHighlighter, and FileWatcher.
    Enforces modular off-switches:
    - locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled
    - locus.pi_utilities.enabled
    Returning HTTP 503 when disabled.
    """

    def __init__(
        self,
        clipboard: ClipboardManager | None = None,
        frontmatter: FrontmatterParser | None = None,
        highlighter: SyntaxHighlighter | None = None,
        watcher: FileWatcher | None = None,
    ) -> None:
        self.clipboard = clipboard or ClipboardManager()
        self.frontmatter = frontmatter or FrontmatterParser()
        self.highlighter = highlighter or SyntaxHighlighter()
        self.watcher = watcher or FileWatcher()

    @property
    def name(self) -> str:
        return "default_pi_utilities_provider"

    def is_feature_enabled(self) -> tuple[bool, str]:
        """Evaluate modular off-switches."""
        for switch in (
            "locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled",
            "locus.pi_utilities.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def copy_clipboard(self, text: str) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        res = self.clipboard.copy(text)
        return {"status": "ok", **res}

    def paste_clipboard(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        val = self.clipboard.paste()
        return {"status": "ok", "text": val}

    def parse_frontmatter(self, content: str) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        doc = self.frontmatter.parse(content)
        return {
            "status": "ok",
            "has_frontmatter": doc.has_frontmatter,
            "metadata": doc.metadata,
            "body": doc.body,
        }

    def highlight_syntax(self, code: str, language: str = "text") -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        res = self.highlighter.highlight(code, language=language)
        return {"status": "ok", **res}

    def poll_file_changes(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        changes = self.watcher.poll_changes()
        return {"status": "ok", "changes": changes, "count": len(changes)}

    def get_status(self) -> dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return {
            "status": "ok",
            "provider": self.name,
            "clipboard_length": len(self.clipboard.paste()),
            "supported_languages": sorted(self.highlighter.SUPPORTED_LANGUAGES),
            "watch_dir": str(self.watcher.watch_dir),
        }
