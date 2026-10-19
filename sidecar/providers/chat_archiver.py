"""
SPEC §19.3 line 15 / §03 line 12: Base Chat Archiver Provider Interface.
Declares data structures and abstract contracts for multi-platform chat crawling,
markdown normalization, and vault persistence.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ChatTurn:
    """A single turn in an AI chat conversation."""
    role: str
    content: str
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class NormalizedChat:
    """Normalized multi-platform AI conversation representation."""
    title: str
    platform: str
    model: str
    date: str
    turns: List[ChatTurn] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "platform": self.platform,
            "model": self.model,
            "date": self.date,
            "turns": [turn.to_dict() for turn in self.turns],
            "key_decisions": self.key_decisions,
            "summary": self.summary,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class ArchiveResult:
    """Result of archiving a conversation into the vault."""
    title: str
    platform: str
    vault_rel_path: str
    status: str
    replicated: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "platform": self.platform,
            "vault_rel_path": self.vault_rel_path,
            "status": self.status,
            "replicated": self.replicated,
            "error": self.error,
        }


class BaseChatArchiverProvider(ABC):
    """Abstract interface for multi-platform chat ingestion and vault archival."""

    def __init__(self, name: str = "chat_archiver") -> None:
        self.name = name
        self._enabled: bool = True

    def is_enabled(self) -> bool:
        """Return whether chat archival is enabled."""
        return self._enabled

    @abstractmethod
    def crawl_and_parse(self, source_path: Path) -> List[NormalizedChat]:
        """Crawl export files and parse into normalized chat structures."""
        pass

    @abstractmethod
    def archive_chat(self, chat: NormalizedChat) -> ArchiveResult:
        """Normalize chat to markdown, write to vault, and trigger replication."""
        pass

    @abstractmethod
    def archive_all(self, source_dirs: Optional[List[Path]] = None) -> List[ArchiveResult]:
        """Discover all chat exports and archive them into the vault."""
        pass
