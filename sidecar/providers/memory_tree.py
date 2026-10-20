"""Memory Tree Provider interfaces and data contracts.

Implements Spec §4.5:
- Level hierarchy: L0 leaf buffer -> L1-LN progressive summaries -> Root.
- TreeNode structure: id, tree_scope, level, content, children, token_count, created_at, sealed.
- BaseMemoryTreeProvider protocol and abstract base class.
- Config contracts for tree scopes and seal gates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, List, Optional
import uuid


@dataclass
class TreeNode:
    """Node in the hierarchical summarization tree per Spec §4.5 line 741.

    SPEC §4.5 line 741:
    TreeNode {
      id: UUID,
      tree_scope: str,       // e.g. "vault:daily", "github:owner/repo"
      level: u32,            // 0 = leaf buffer, higher = summary
      content: str,          // raw text (L0) or LLM summary (L1+)
      children: [UUID],      // child node refs
      token_count: u32,
      created_at: DateTime,
      sealed: bool,          // L0 only: true when gate threshold met
    }
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tree_scope: str = "default"
    level: int = 0  # 0 = leaf buffer, 1+ = summary
    content: str = ""
    children: list[str] = field(default_factory=list)
    token_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    sealed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert tree node to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "tree_scope": self.tree_scope,
            "level": self.level,
            "content": self.content,
            "children": list(self.children),
            "token_count": self.token_count,
            "created_at": self.created_at,
            "sealed": self.sealed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TreeNode:
        """Create tree node from dictionary representation."""
        return cls(
            id=str(data.get("id") or uuid.uuid4()),
            tree_scope=str(data.get("tree_scope", "default")),
            level=int(data.get("level", 0)),
            content=str(data.get("content", "")),
            children=list(data.get("children") or []),
            token_count=int(data.get("token_count", 0)),
            created_at=float(data.get("created_at", time.time())),
            sealed=bool(data.get("sealed", False)),
        )


@dataclass
class TreeScopeConfig:
    """Configuration for a specific tree scope per Spec §4.5 line 800."""

    tree_scope: str = "default"
    seal_gate: int = 8  # Default: 8 items per level before seal trigger
    stale_flush_seconds: float = 3.0 * 3600.0  # 3 hours
    max_depth: int = 5


@dataclass
class MemoryTreeConfig:
    """Subsystem configuration for Memory Tree per Spec §4.5 line 820."""

    enabled: bool = True
    default_seal_gate: int = 8
    stale_flush_seconds: float = 3.0 * 3600.0
    db_path: Optional[str] = None
    max_context_tokens: int = 250


class BaseMemoryTreeProvider(ABC):
    """Abstract Base Class for Memory Tree Provider per Spec §4.5 line 816.

    SPEC §4.5 line 816:
    Provider Interface: implements MemoryProvider — plugs into the Memory Tri-Stack alongside Neo4j and PageIndex.
    """

    def __init__(self, name: str = "memory_tree") -> None:
        self.name = name

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return True if memory tree operations are enabled."""
        ...

    @abstractmethod
    def append_leaf(
        self,
        tree_scope: str,
        content: str,
        source_id: Optional[str] = None,
        source_kind: Optional[str] = None,
    ) -> TreeNode:
        """Append raw chunk to L0 buffer and auto-seal if gate threshold met."""
        ...

    @abstractmethod
    def seal_level(
        self,
        tree_scope: str,
        level: int = 0,
        force: bool = False,
    ) -> Optional[TreeNode]:
        """Combine unsealed nodes at level into a parent summary node at level + 1."""
        ...

    @abstractmethod
    def search(
        self,
        tree_scope: str,
        query: str,
        max_results: int = 5,
    ) -> list[TreeNode]:
        """Perform top-down relevance search descending into relevant tree branches."""
        ...

    @abstractmethod
    def topic_route(
        self,
        content: str,
        topics: list[str],
    ) -> list[str]:
        """Route content chunk into matching topic tree scopes."""
        ...

    @abstractmethod
    def get_nodes(
        self,
        tree_scope: Optional[str] = None,
        level: Optional[int] = None,
    ) -> list[TreeNode]:
        """Retrieve stored tree nodes matching optional filters."""
        ...

    @abstractmethod
    def get_unsealed(
        self,
        tree_scope: str,
        level: int = 0,
    ) -> list[TreeNode]:
        """Retrieve all unsealed nodes for a given scope and level."""
        ...

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return health status and node metrics."""
        ...
