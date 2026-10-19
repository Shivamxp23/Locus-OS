"""
SPEC §19.3 line 15 / F-0050: AI Chat Archiver Unit Tests.
"""
from __future__ import annotations

import json
from pathlib import Path

from sidecar import config
from sidecar.crawlers.chat_crawler import ChatCrawler, extract_key_decisions
from sidecar.ingestion.chat_archiver import ChatArchiverProvider, sanitize_filename
from sidecar.providers.chat_archiver import (
    ArchiveResult,
    BaseChatArchiverProvider,
    ChatTurn,
    NormalizedChat,
)
from sidecar.registry import ProviderRegistry


def test_chat_archiver_implements_interface():
    """SPEC §19.3 line 15: "BaseChatArchiverProvider defines multi-platform crawl and vault archive contracts"."""
    archiver = ChatArchiverProvider()
    assert isinstance(archiver, BaseChatArchiverProvider)
    assert hasattr(archiver, "crawl_and_parse")
    assert hasattr(archiver, "archive_chat")
    assert hasattr(archiver, "archive_all")


def test_parse_chatgpt_export_format():
    """SPEC §19.3 line 25: "Scan local browser export directories: ChatGPT export archives"."""
    crawler = ChatCrawler()
    raw_chatgpt = {
        "title": "Quantum Computing Basics",
        "create_time": 1700000000,
        "model": "gpt-4",
        "mapping": {
            "node1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["Explain superposition in quantum mechanics."]},
                }
            },
            "node2": {
                "message": {
                    "author": {"role": "assistant"},
                    "content": {
                        "parts": [
                            "Superposition allows quantum states to be combined.\nDecided: Use Qiskit for practical circuit simulation."
                        ]
                    },
                }
            },
        },
    }

    chats = crawler.parse_json_data(raw_chatgpt, Path("chatgpt.json"))
    assert len(chats) == 1
    chat = chats[0]
    assert chat.title == "Quantum Computing Basics"
    assert chat.platform == "chatgpt"
    assert len(chat.turns) == 2
    assert chat.turns[0].role == "user"
    assert "superposition" in chat.turns[0].content
    assert len(chat.key_decisions) >= 1
    assert "Use Qiskit" in chat.key_decisions[0]


def test_parse_claude_export_format():
    """SPEC §19.3 line 24: "Scan local browser export directories: Claude Web / App JSON exports"."""
    crawler = ChatCrawler()
    raw_claude = {
        "name": "Distributed System Architecture",
        "created_at": "2026-11-20T14:30:00Z",
        "model": "claude-3-5-sonnet",
        "chat_messages": [
            {"sender": "human", "text": "Should we use Raft or Paxos for consensus?"},
            {
                "sender": "assistant",
                "text": "Raft is much simpler to implement and reason about.\nDecision: Adopt Raft consensus with etcd.",
            },
        ],
    }

    chats = crawler.parse_json_data(raw_claude, Path("claude.json"))
    assert len(chats) == 1
    chat = chats[0]
    assert chat.title == "Distributed System Architecture"
    assert chat.platform == "claude"
    assert chat.date == "2026-11-20"
    assert len(chat.turns) == 2
    assert chat.turns[0].role == "user"
    assert chat.turns[1].role == "assistant"
    assert len(chat.key_decisions) == 1
    assert "Adopt Raft consensus" in chat.key_decisions[0]


def test_parse_cursor_and_pi_formats():
    """SPEC §19.3 line 26: "Scan Cursor IDE conversation logs and Pi native session histories"."""
    crawler = ChatCrawler()

    # Cursor
    cursor_data = {
        "title": "Fix Database Deadlock",
        "model": "cursor-fast",
        "conversation": [
            {"role": "user", "text": "Fix postgresql deadlock on orders table."},
            {"role": "assistant", "text": "Added index and advisory lock. Decided: Use SELECT FOR UPDATE."},
        ],
    }
    cursor_chats = crawler.parse_json_data(cursor_data, Path("cursor.json"))
    assert len(cursor_chats) == 1
    assert cursor_chats[0].platform == "cursor"
    assert len(cursor_chats[0].turns) == 2

    # Pi
    pi_data = {
        "session_id": "pi-sess-100",
        "title": "Refactor Sidecar Supervisor",
        "turns": [
            {"role": "user", "content": "Split supervisor routes."},
            {"role": "assistant", "content": "Routes split. Decision: Use sub-routers."},
        ],
    }
    pi_chats = crawler.parse_json_data(pi_data, Path("pi.json"))
    assert len(pi_chats) == 1
    assert pi_chats[0].platform == "pi"
    assert len(pi_chats[0].turns) == 2


def test_parse_telegram_export_format():
    """SPEC §19.3 line 28: "Scan Telegram Locus conversation logs"."""
    crawler = ChatCrawler()
    tg_data = {
        "name": "Locus Channel Chat",
        "messages": [
            {"type": "message", "from": "Shivam", "text": "Schedule nightly backup at 23:45."},
            {"type": "message", "from": "LocusBot", "text": "Scheduled. Decided: Back up to CouchDB and S3."},
        ],
    }
    tg_chats = crawler.parse_json_data(tg_data, Path("telegram.json"))
    assert len(tg_chats) == 1
    assert tg_chats[0].platform == "telegram"
    assert len(tg_chats[0].turns) == 2
    assert tg_chats[0].turns[0].role == "user"
    assert tg_chats[0].turns[1].role == "assistant"


def test_extract_key_decisions():
    """SPEC §19.3 line 32: "Extracts Q&A pairs, code blocks, decisions"."""
    text = (
        "Here is our discussion.\n"
        "- Decided: Use CouchDB 3.3 for LiveSync multi-master replication.\n"
        "Some middle chat.\n"
        "Decision: Never bind database ports to 0.0.0.0.\n"
        "Ending thoughts."
    )
    decisions = extract_key_decisions(text)
    assert len(decisions) == 2
    assert "Use CouchDB 3.3" in decisions[0]
    assert "Never bind database ports" in decisions[1]


def test_format_markdown_note_with_frontmatter():
    """SPEC §19.3 line 30: "Convert platform-specific JSON/HTML into unified Markdown format with YAML Frontmatter"."""
    archiver = ChatArchiverProvider()
    chat = NormalizedChat(
        title="Neural Architecture Search",
        platform="claude",
        model="claude-3-5-sonnet",
        date="2026-11-25",
        turns=[
            ChatTurn(role="user", content="How does DARTS work?"),
            ChatTurn(role="assistant", content="Differentiable architecture search relaxes the discrete search space."),
        ],
        key_decisions=["Benchmark on CIFAR-10 first"],
        summary="Discussion on DARTS architecture search methodology",
        tags=["ai-chat", "nas"],
    )

    md = archiver.format_markdown_note(chat)
    assert md.startswith("---")
    assert 'title: "Neural Architecture Search"' in md
    assert "platform: claude" in md
    assert "model: claude-3-5-sonnet" in md
    assert "## Key Decisions" in md
    assert "- Benchmark on CIFAR-10 first" in md
    assert "## Transcript" in md
    assert "### User" in md
    assert "How does DARTS work?" in md
    assert "### Assistant" in md


def test_archive_chat_writes_to_vault_and_replicates(monkeypatch, tmp_path: Path):
    """SPEC §19.3 line 35: "Write generated notes to /vault/04-Captures/AI Chats/YYYY-MM-DD/{title}.md and trigger LiveSync"."""
    locus_home = tmp_path / ".locus"
    vault_dir = locus_home / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)
    monkeypatch.setattr(config, "get", lambda k, d=None: str(vault_dir) if k == "locus.vault.path" else d)

    archiver = ChatArchiverProvider()
    archiver.initialize()

    chat = NormalizedChat(
        title="LangGraph Workflow Optimization",
        platform="chatgpt",
        model="gpt-4o",
        date="2026-11-26",
        turns=[
            ChatTurn(role="user", content="Optimize state graph transitions."),
            ChatTurn(role="assistant", content="Use conditional edges with checkpointing."),
        ],
        key_decisions=["Enable SQLite persistence checkpointing"],
    )

    result = archiver.archive_chat(chat)
    assert result.status == "archived"
    assert "04-Captures/AI Chats/2026-11-26/LangGraph-Workflow-Optimization.md" in result.vault_rel_path

    expected_file = vault_dir / "04-Captures" / "AI Chats" / "2026-11-26" / "LangGraph-Workflow-Optimization.md"
    assert expected_file.is_file()
    content = expected_file.read_text(encoding="utf-8")
    assert "LangGraph Workflow Optimization" in content
    assert "conditional edges" in content


def test_chat_archiver_off_switch(monkeypatch, tmp_path: Path):
    """SPEC §03 line 35: "a disabled feature's functions no-op and routes answer 503"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)
    monkeypatch.setattr(
        config,
        "get",
        lambda k, d=None: False if k == "locus.ingestion.chat_archiver.enabled" else d,
    )

    archiver = ChatArchiverProvider()
    assert archiver.is_enabled() is False

    chat = NormalizedChat("Disabled Test", "claude", "claude-3", "2026-11-20")
    res = archiver.archive_chat(chat)
    assert res.status == "skipped"

    all_res = archiver.archive_all([tmp_path])
    assert all_res == []


def test_chat_archiver_modular_swap():
    """SPEC §03 line 12: "Universal Provider Registry allowing modular swap"."""
    registry = ProviderRegistry()

    class CustomChatArchiver(BaseChatArchiverProvider):
        def crawl_and_parse(self, source_path):
            return [NormalizedChat("Custom", "custom", "v1", "2026-01-01")]

        def archive_chat(self, chat):
            return ArchiveResult(chat.title, chat.platform, "custom/path.md", "custom_archived")

        def archive_all(self, source_dirs=None):
            return [ArchiveResult("Custom", "custom", "custom/path.md", "custom_archived")]

    registry.register("chat_archiver", "custom", CustomChatArchiver)
    active = registry.get_active_provider("chat_archiver", default_name="custom")
    assert active is CustomChatArchiver

    inst = active()
    res = inst.archive_chat(NormalizedChat("C", "custom", "v1", "2026-01-01"))
    assert res.status == "custom_archived"


def test_chat_archiver_health_check(monkeypatch, tmp_path: Path):
    """SPEC §03 line 40: "Health check for all registered providers"."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "get_locus_home", lambda: locus_home)

    archiver = ChatArchiverProvider()
    health = archiver.health_check()
    assert health["status"] == "ok"
    assert health["provider"] == "default_chat_archiver"
    assert health["enabled"] is True
    assert "04-Captures" in health["captures_dir"]
