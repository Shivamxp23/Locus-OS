"""
SPEC §24.1 line 2720: "## Feature §24.1: Pi Utilities (Clipboard, Syntax Highlighting, Frontmatter, File Watcher)"
Unit tests for Pi Utilities (F-0106 / US-85).
Asserts clipboard management with OSC 52, YAML frontmatter extraction,
syntax token highlighting, directory file watcher change polling,
swappable provider interface, and modular off-switches.
"""
from __future__ import annotations

from typing import Any
import pytest

import sidecar.config as config
from sidecar.providers.pi_utilities import (
    BasePiUtilitiesProvider,
    DefaultPiUtilitiesProvider,
)
from sidecar.utils.pi_utilities import (
    ClipboardManager,
    FileWatcher,
    FrontmatterParser,
    ParsedDocument,
    SyntaxHighlighter,
)


def test_clipboard_manager_operations() -> None:
    """SPEC §24.1 line 2720: Clipboard read/write and OSC-52 terminal sequence simulation."""
    clip = ClipboardManager()
    assert clip.paste() == ""

    res = clip.copy("Hello Locus Agent!")
    assert res["status"] == "ok"
    assert res["characters_count"] == 18
    assert res["osc52_bytes"] > 0
    assert clip.paste() == "Hello Locus Agent!"

    clip.clear()
    assert clip.paste() == ""


def test_frontmatter_parser() -> None:
    """SPEC §24.1 line 2720: Frontmatter parsing and stripping."""
    parser = FrontmatterParser()

    doc_with_fm = """---
title: Memory Node Alpha
tags: [architecture, locus]
priority: 5
---
# Main Content Body
This is the note body.
"""
    res = parser.parse(doc_with_fm)
    assert res.has_frontmatter is True
    assert res.metadata["title"] == "Memory Node Alpha"
    assert "architecture" in res.metadata["tags"]
    assert res.metadata["priority"] == 5
    assert "This is the note body." in res.body

    # Strip test
    stripped = parser.strip(doc_with_fm)
    assert not stripped.startswith("---")
    assert "Main Content Body" in stripped

    # Document without frontmatter
    plain = "Just plain text without headers."
    res_plain = parser.parse(plain)
    assert res_plain.has_frontmatter is False
    assert res_plain.metadata == {}
    assert res_plain.body == plain


def test_syntax_highlighter_tokenizing() -> None:
    """SPEC §24.1 line 2720: Syntax highlighting and token count metrics."""
    hl = SyntaxHighlighter()
    code = """# Python snippet
def execute_query(name: str):
    message = "running"
    return True
"""
    res = hl.highlight(code, language="python")
    assert res["language"] == "python"
    assert res["supported"] is True
    assert res["tokens"]["comments"] == 1
    assert res["tokens"]["keywords"] >= 2
    assert res["tokens"]["strings"] >= 1


def test_file_watcher_change_detection(tmp_path: Any) -> None:
    """SPEC §24.1 line 2720: FileWatcher directory monitoring and change detection."""
    watcher = FileWatcher(watch_dir=tmp_path)

    # Initial scan establishes baseline snapshot
    initial_changes = watcher.poll_changes()
    assert initial_changes == []

    # Create a new file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World", encoding="utf-8")

    changes = watcher.poll_changes()
    assert len(changes) == 1
    assert changes[0]["event"] == "created"
    assert "test.txt" in changes[0]["path"]

    # Delete the file
    test_file.unlink()
    del_changes = watcher.poll_changes()
    assert len(del_changes) == 1
    assert del_changes[0]["event"] == "deleted"


def test_swappable_utilities_provider() -> None:
    """Verify BasePiUtilitiesProvider interface and DefaultPiUtilitiesProvider swappability."""
    class CustomUtilitiesProvider(BasePiUtilitiesProvider):
        @property
        def name(self) -> str:
            return "custom_utils"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def copy_clipboard(self, text: str) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def paste_clipboard(self) -> dict[str, Any]:
            return {"status": "ok", "text": "custom-clipboard"}

        def parse_frontmatter(self, content: str) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def highlight_syntax(self, code: str, language: str = "text") -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def poll_file_changes(self) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "custom_active": True}

    custom = CustomUtilitiesProvider()
    assert custom.name == "custom_utils"
    assert custom.copy_clipboard("test")["custom"] is True

    default_prov = DefaultPiUtilitiesProvider()
    assert default_prov.name == "default_pi_utilities_provider"
    assert default_prov.paste_clipboard()["status"] == "ok"


def test_utilities_provider_off_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §24.1: Modular off-switches return HTTP 503."""
    provider = DefaultPiUtilitiesProvider()

    # Enabled when config has no setting
    enabled, switch = provider.is_feature_enabled()
    assert enabled is True

    # Disable via locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled
    long_switch = "locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled"
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == long_switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == long_switch else True)

    enabled, switch = provider.is_feature_enabled()
    assert enabled is False
    assert switch == long_switch

    res_copy = provider.copy_clipboard("hello")
    assert res_copy["status_code"] == 503
    assert res_copy["disabled"] == long_switch

    res_paste = provider.paste_clipboard()
    assert res_paste["status_code"] == 503

    res_fm = provider.parse_frontmatter("---\na: 1\n---\nbody")
    assert res_fm["status_code"] == 503

    # Disable via locus.pi_utilities.enabled
    monkeypatch.setattr(config, "get", lambda key, default=None: False if key == "locus.pi_utilities.enabled" else None)
    monkeypatch.setattr(config, "is_enabled", lambda key, default=False: False if key == "locus.pi_utilities.enabled" else True)

    enabled2, switch2 = provider.is_feature_enabled()
    assert enabled2 is False
    assert switch2 == "locus.pi_utilities.enabled"
