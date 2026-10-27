"""
SPEC §24.1 lines 2720-2726: Integration tests for Pi Utilities routes (F-0106 / US-85).
Tests FastAPI endpoints under /utils/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.providers.pi_utilities import DefaultPiUtilitiesProvider
from sidecar.service import create_app
from sidecar.utils.pi_utilities import (
    ClipboardManager,
    FileWatcher,
    FrontmatterParser,
    SyntaxHighlighter,
)


@pytest.fixture
def client(tmp_path: pytest.TempPathFactory) -> TestClient:
    app = create_app()
    clipboard = ClipboardManager()
    parser = FrontmatterParser()
    highlighter = SyntaxHighlighter()
    watcher = FileWatcher(watch_dir=tmp_path)
    provider = DefaultPiUtilitiesProvider(
        clipboard=clipboard,
        frontmatter=parser,
        highlighter=highlighter,
        watcher=watcher,
    )
    app.state.utilities_provider = provider
    return TestClient(app)


def test_utilities_service_clipboard_lifecycle(client: TestClient) -> None:
    """SPEC §24.1: POST /utils/clipboard/copy and GET /utils/clipboard/paste."""
    # Copy text
    copy_res = client.post("/utils/clipboard/copy", json={"text": "Integration test string"})
    assert copy_res.status_code == 200
    copy_data = copy_res.json()
    assert copy_data["status"] == "ok"
    assert copy_data["characters_count"] == len("Integration test string")

    # Paste text
    paste_res = client.get("/utils/clipboard/paste")
    assert paste_res.status_code == 200
    paste_data = paste_res.json()
    assert paste_data["status"] == "ok"
    assert paste_data["text"] == "Integration test string"


def test_utilities_service_frontmatter_parse(client: TestClient) -> None:
    """SPEC §24.1: POST /utils/frontmatter/parse."""
    content = """---
title: "Locus Architecture"
tags: [pi, core, utils]
status: active
---
# Main Content
Body line after frontmatter.
"""
    res = client.post("/utils/frontmatter/parse", json={"content": content})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["has_frontmatter"] is True
    assert data["metadata"]["title"] == "Locus Architecture"
    assert "active" == data["metadata"]["status"]
    assert "# Main Content" in data["body"]


def test_utilities_service_syntax_highlight(client: TestClient) -> None:
    """SPEC §24.1: POST /utils/syntax/highlight."""
    code = """
def compute_hash(val: str) -> str:
    # Hash calculation
    return "hash-" + val
"""
    res = client.post("/utils/syntax/highlight", json={"code": code, "language": "python"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["language"] == "python"
    assert data["supported"] is True
    assert data["tokens"]["keywords"] >= 2


def test_utilities_service_watcher_poll(client: TestClient) -> None:
    """SPEC §24.1: POST /utils/watcher/poll."""
    res = client.post("/utils/watcher/poll")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "count" in data
    assert isinstance(data["changes"], list)


def test_utilities_service_status(client: TestClient) -> None:
    """SPEC §24.1: GET /utils/status diagnostic route."""
    res = client.get("/utils/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provider"] == "default_pi_utilities_provider"
    assert "clipboard_length" in data
    assert "supported_languages" in data
    assert "watch_dir" in data


def test_utilities_service_off_switches(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify HTTP 503 when locus.pi_utilities.enabled or locus.pi_utilities_clipboard...enabled is disabled."""
    # Test primary switch
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.pi_utilities.enabled" else True)
    res = client.get("/utils/status")
    assert res.status_code == 503
    assert res.json()["disabled"] == "locus.pi_utilities.enabled"

    # Test full switch name
    monkeypatch.setattr(
        config,
        "get",
        lambda k, default=None: False if k == "locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled" else True,
    )
    res2 = client.post("/utils/clipboard/copy", json={"text": "test"})
    assert res2.status_code == 503
    assert res2.json()["disabled"] == "locus.pi_utilities_clipboard_syntax_highlighting_frontmatter_file_watcher.enabled"
