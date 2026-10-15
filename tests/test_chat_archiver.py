"""tests/test_chat_archiver.py - Tests for Daily AI Chat Archiver & Vault Writer.

Validates Acceptance Criteria for US-18, Spec §19.3, and Decision D-4:
- Unit: ChatCrawler file discovery and parsing
- Unit: ChatGPT, Claude, and local transcript normalization
- Unit: Secret redaction in audit markdown (S-0, D-4)
- Unit: Vault writing under vault/05-Daily/Logs/audit-YYYY-MM-DD.md
- Unit: APScheduler cron integration at 03:00
- Unit: Modularity off-test and provider protocol
- Integration: End-to-end archival from mock dump to vault markdown
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from apscheduler.schedulers.background import BackgroundScheduler

from sidecar.chat_archiver import (
    ChatArchiver,
    ChatArchiverProvider,
    ChatSession,
    ChatTurn,
    schedule_nightly_archival_job,
)
from sidecar.crawlers.chat_crawler import ChatCrawler


def test_unit_crawler_discovery(tmp_path: Path):
    """Verify ChatCrawler discovers json, jsonl, and md files in watch dirs."""
    d1 = tmp_path / "exports"
    d1.mkdir()
    (d1 / "chat1.json").write_text("{}", encoding="utf-8")
    (d1 / "chat2.jsonl").write_text("{}\n", encoding="utf-8")
    (d1 / "notes.txt").write_text("ignore", encoding="utf-8")

    crawler = ChatCrawler(watch_dirs=[d1])
    files = crawler.scan_files()
    assert len(files) == 2
    assert any(f.name == "chat1.json" for f in files)
    assert any(f.name == "chat2.jsonl" for f in files)


def test_unit_normalization_multi_platform():
    """Verify normalization of ChatGPT and Claude JSON structures."""
    archiver = ChatArchiver()

    # ChatGPT dump structure
    chatgpt_data = {
        "id": "gpt-123",
        "title": "Debug Python",
        "mapping": {
            "node1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["How to fix bug?"]},
                }
            },
            "node2": {
                "message": {
                    "author": {"role": "assistant"},
                    "content": {"parts": ["Check your imports."]},
                }
            },
        },
    }
    sess_gpt = archiver.normalize_chatgpt_export(chatgpt_data)
    assert sess_gpt is not None
    assert sess_gpt.platform == "chatgpt"
    assert len(sess_gpt.turns) == 2
    assert sess_gpt.turns[0].content == "How to fix bug?"
    assert sess_gpt.turns[1].role == "assistant"

    # Claude dump structure
    claude_data = {
        "uuid": "claude-456",
        "name": "Architecture Design",
        "chat_messages": [
            {"sender": "human", "text": "What is clean arch?"},
            {"sender": "assistant", "text": "Separation of concerns."},
        ],
    }
    sess_claude = archiver.normalize_claude_export(claude_data)
    assert sess_claude is not None
    assert sess_claude.platform == "claude"
    assert len(sess_claude.turns) == 2
    assert sess_claude.turns[0].role == "user"


def test_unit_secret_redaction_in_audit_markdown():
    """Verify secrets are redacted in generated audit markdown per S-0 and D-4."""
    archiver = ChatArchiver()
    dummy_key = "sk-" + "ant-" + "secretkey1234567890abcdef"
    dummy_gh = "gh" + "p_" + "1234567890abcdefghijklmnopqrstuvwxyz"

    session = ChatSession(
        session_id="sec-sess-1",
        platform="claude",
        title="Secret discussion",
        turns=[
            ChatTurn(role="user", content=f"Using token {dummy_key}"),
            ChatTurn(role="assistant", content=f"Stored token {dummy_gh} and password=secretpw987"),
        ],
    )

    md = archiver.render_audit_markdown("2027-04-02", [session])

    assert "secretkey1234567890abcdef" not in md
    assert "1234567890abcdefghijkl" not in md
    assert "secretpw987" not in md
    assert "date: 2027-04-02" in md
    assert "type: audit-log" in md


def test_unit_vault_markdown_persistence(tmp_path: Path):
    """Verify markdown note is saved under vault/05-Daily/Logs/audit-YYYY-MM-DD.md."""
    vault = tmp_path / "vault"
    archiver = ChatArchiver(vault_root=vault)

    out = archiver.archive_daily_chats(date_str="2027-04-02", dry_run=False)
    assert out is not None
    assert out.exists()
    assert out.name == "audit-2027-04-02.md"
    assert out.parent.name == "Logs"
    assert out.parent.parent.name == "05-Daily"

    content = out.read_text(encoding="utf-8")
    assert "---" in content
    assert "date: 2027-04-02" in content
    assert "type: audit-log" in content


def test_unit_apscheduler_cron_registration():
    """Verify integration with APScheduler as nightly cron job at 03:00."""
    sched = BackgroundScheduler()
    job = schedule_nightly_archival_job(scheduler=sched, cron_hour=3, cron_minute=0)

    assert job is not None
    assert job.id == "nightly_chat_archiver"
    trigger = str(job.trigger)
    assert "cron[hour='3', minute='0']" in trigger or "hour='3'" in trigger


def test_unit_modularity_off_and_protocol(tmp_path: Path):
    """Verify modular off toggle and protocol compliance."""
    vault = tmp_path / "vault"
    archiver_disabled = ChatArchiver(vault_root=vault, enabled=False)

    assert archiver_disabled.is_enabled is False
    res = archiver_disabled.archive_daily_chats(date_str="2027-04-02")
    assert res is None
    assert not (vault / "05-Daily" / "Logs" / "audit-2027-04-02.md").exists()

    # Protocol compliance
    assert isinstance(archiver_disabled, ChatArchiverProvider)


def test_integration_chat_archiver_pipeline(tmp_path: Path):
    """Integration: Full scan of mock export files, redaction, and vault log persistence."""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    vault = tmp_path / "vault"

    dummy_secret = "sk-" + "ant-" + "testsecret1234567890abcdef"
    chat_file = export_dir / "claude_export.json"
    chat_file.write_text(
        json.dumps(
            [
                {
                    "uuid": "sess-live-test",
                    "name": "Integration Chat",
                    "chat_messages": [
                        {"sender": "human", "text": f"Here is my secret {dummy_secret}"},
                        {"sender": "assistant", "text": "Credentials acknowledged and secured."},
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    archiver = ChatArchiver(vault_root=vault, export_dirs=[export_dir], enabled=True)
    out_file = archiver.archive_daily_chats(date_str="2027-04-02", dry_run=False)

    assert out_file is not None
    assert out_file.is_file()

    text = out_file.read_text(encoding="utf-8")
    assert "total_sessions: 1" in text
    assert "Integration Chat" in text
    assert "Credentials acknowledged and secured" in text
    # Secret must be completely masked
    assert "testsecret1234567890abcdef" not in text
