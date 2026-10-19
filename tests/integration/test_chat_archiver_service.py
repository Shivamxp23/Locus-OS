"""
SPEC §19.3 / §03 line 35: Chat Archiver Service Integration Tests.
Tests HTTP endpoints on the sidecar service for chat crawling, vault archival,
and modular 503 off-switch behavior.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from sidecar import config
from sidecar.ingestion.chat_archiver import ChatArchiverProvider
from sidecar.registry import ProviderRegistry
from sidecar.service import create_app


def test_chat_archiver_service_endpoints(monkeypatch, tmp_path: Path):
    """SPEC §19.3 line 15: "Chat Archiver Service endpoints crawl, format and archive into vault"."""
    locus_home = tmp_path / ".locus"
    vault_dir = locus_home / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)
    monkeypatch.setattr(config, "get", lambda k, d=None: str(vault_dir) if k == "locus.vault.path" else d)

    # Create dummy export file in temp directory
    export_dir = tmp_path / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    claude_dump = {
        "name": "Integration Test Chat",
        "created_at": "2026-11-27T10:00:00Z",
        "chat_messages": [
            {"sender": "human", "text": "Can we test chat archival end-to-end?"},
            {"sender": "assistant", "text": "Yes, verified! Decided: Enable auto-archiving."},
        ],
    }
    (export_dir / "claude_chat.json").write_text(json.dumps(claude_dump), encoding="utf-8")

    registry = ProviderRegistry()
    registry.register("chat_archiver", "default_chat_archiver", ChatArchiverProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    # 1. Crawl test
    res_crawl = client.post("/ingestion/chats/crawl", json={"source_dir": str(export_dir)})
    assert res_crawl.status_code == 200
    crawl_data = res_crawl.json()
    assert crawl_data["status"] == "ok"
    assert crawl_data["count"] == 1
    assert crawl_data["chats"][0]["title"] == "Integration Test Chat"
    assert crawl_data["chats"][0]["platform"] == "claude"

    # 2. Archive test
    res_archive = client.post("/ingestion/chats/archive", json={"source_dir": str(export_dir)})
    assert res_archive.status_code == 200
    archive_data = res_archive.json()
    assert archive_data["status"] == "ok"
    assert archive_data["count"] == 1
    rel_path = archive_data["results"][0]["vault_rel_path"]
    assert "04-Captures/AI Chats/2026-11-27/Integration-Test-Chat.md" in rel_path

    # Verify vault file on disk
    dest_file = vault_dir / rel_path
    assert dest_file.is_file()
    text = dest_file.read_text(encoding="utf-8")
    assert "title: \"Integration Test Chat\"" in text
    assert "## Key Decisions" in text
    assert "Enable auto-archiving" in text


def test_chat_archiver_service_off_switch_returns_503(monkeypatch, tmp_path: Path):
    """SPEC §03 line 35: "a disabled feature's HTTP routes answer 503 with {'disabled': '<config key>'}"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)
    monkeypatch.setattr(
        config,
        "get",
        lambda k, d=None: False if k == "locus.ingestion.chat_archiver.enabled" else d,
    )

    registry = ProviderRegistry()
    registry.register("chat_archiver", "default_chat_archiver", ChatArchiverProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    res_crawl = client.post("/ingestion/chats/crawl", json={})
    assert res_crawl.status_code == 503
    assert res_crawl.json() == {"disabled": "locus.ingestion.chat_archiver.enabled"}

    res_archive = client.post("/ingestion/chats/archive", json={})
    assert res_archive.status_code == 503
    assert res_archive.json() == {"disabled": "locus.ingestion.chat_archiver.enabled"}
