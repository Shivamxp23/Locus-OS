"""sidecar/memory/tree_ops.py - Hierarchical Memory Tree Cascade.

Implements Spec §4.5:
- Generic multi-level summarization tree over text corpora.
- Level hierarchy: L0 buffer (raw text) -> L1+ (summaries) -> Root.
- TreeNode data model with seal gating and upward cascade.
- Seal Gate: threshold of N unsealed items (default 4 for tests, 8 in production) or stale flush (>3h).
- Search: hierarchical descending relevance search across tree scopes.
- Topic Routing: cross-tree distribution into scoped topics.
- Modularity: locus.memory.tree.enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable
import uuid


@dataclass
class TreeNode:
    """Node in the hierarchical summarization tree."""

    id: str
    tree_scope: str
    level: int  # 0 = leaf buffer, 1+ = summary
    content: str
    children: list[str] = field(default_factory=list)
    token_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    sealed: bool = False

    def to_dict(self) -> dict[str, Any]:
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


@runtime_checkable
class MemoryTreeProvider(Protocol):
    """Protocol for memory tree operations."""

    def append_leaf(self, tree_scope: str, content: str) -> TreeNode:
        """Append raw text node to L0 buffer."""
        return TreeNode(id="default", tree_scope=tree_scope, level=0, content=content)

    def seal_level(self, tree_scope: str, level: int = 0, force: bool = False) -> Optional[TreeNode]:
        """Summarize unsealed nodes at level and cascade upward."""
        return None

    def search(self, tree_scope: str, query: str, max_results: int = 5) -> list[TreeNode]:
        """Search relevant nodes across levels in tree scope."""
        return []


class MemoryTreeManager:
    """Core Memory Tree Manager implementing Spec §4.5."""

    DEFAULT_SEAL_GATE = 4  # items required before automatic seal
    STALE_FLUSH_SECONDS = 3 * 3600  # 3 hours

    def __init__(
        self,
        enabled: bool = True,
        seal_gate: int = DEFAULT_SEAL_GATE,
        summarizer: Optional[Callable[[str], str]] = None,
    ):
        self.enabled = enabled
        self.seal_gate = seal_gate
        self._summarizer = summarizer or self._default_summarizer
        self._nodes: dict[str, TreeNode] = {}
        # index by (tree_scope, level) -> list of node_ids
        self._scope_level_index: dict[tuple[str, int], list[str]] = {}

    @staticmethod
    def _default_summarizer(combined_text: str) -> str:
        """Fallback extractive/extensible summarizer."""
        lines = [line.strip() for line in combined_text.splitlines() if line.strip() and not line.startswith("---")]
        if not lines:
            return "Empty summary"
        key_points = lines[:5]
        return "Summary: " + " | ".join(key_points)

    def append_leaf(self, tree_scope: str, content: str) -> TreeNode:
        """Append raw chunk to L0 buffer and auto-seal if gate threshold met."""
        if not self.enabled:
            return TreeNode(id="disabled", tree_scope=tree_scope, level=0, content=content)

        node_id = f"node-{uuid.uuid4().hex[:8]}"
        tokens = max(1, len(content.split()))
        node = TreeNode(
            id=node_id,
            tree_scope=tree_scope,
            level=0,
            content=content,
            token_count=tokens,
            sealed=False,
        )

        self._nodes[node_id] = node
        self._scope_level_index.setdefault((tree_scope, 0), []).append(node_id)

        # Check if L0 seal gate threshold reached
        unsealed = self.get_unsealed(tree_scope, level=0)
        if len(unsealed) >= self.seal_gate:
            self.seal_level(tree_scope, level=0)

        return node

    def get_unsealed(self, tree_scope: str, level: int) -> list[TreeNode]:
        """Retrieve all unsealed nodes for a given scope and level."""
        ids = self._scope_level_index.get((tree_scope, level), [])
        return [self._nodes[nid] for nid in ids if not self._nodes[nid].sealed]

    def seal_level(self, tree_scope: str, level: int = 0, force: bool = False) -> Optional[TreeNode]:
        """Combine unsealed nodes at level into a parent summary node at level + 1."""
        if not self.enabled:
            return None

        unsealed = self.get_unsealed(tree_scope, level)
        if not force and len(unsealed) < self.seal_gate:
            # Check stale flush timer (3 hours)
            now = time.time()
            if not unsealed or (now - unsealed[0].created_at) < self.STALE_FLUSH_SECONDS:
                return None

        if not unsealed:
            return None

        # Concatenate content and summarize
        combined = "\n---\n".join(n.content for n in unsealed)
        summary_text = self._summarizer(combined)

        parent_id = f"summary-L{level+1}-{uuid.uuid4().hex[:8]}"
        tokens = max(1, len(summary_text.split()))
        parent = TreeNode(
            id=parent_id,
            tree_scope=tree_scope,
            level=level + 1,
            content=summary_text,
            children=[n.id for n in unsealed],
            token_count=tokens,
            sealed=False,
        )

        self._nodes[parent_id] = parent
        self._scope_level_index.setdefault((tree_scope, level + 1), []).append(parent_id)

        # Mark children as sealed
        for child in unsealed:
            child.sealed = True

        # Upward Cascade: check if parent level reached seal gate
        parent_level_unsealed = self.get_unsealed(tree_scope, level + 1)
        if len(parent_level_unsealed) >= self.seal_gate:
            self.seal_level(tree_scope, level + 1)

        return parent

    def search(self, tree_scope: str, query: str, max_results: int = 5) -> list[TreeNode]:
        """Search top-level nodes first and descend into relevant branches."""
        if not self.enabled:
            return []

        q_terms = [t.lower() for t in query.split() if len(t) >= 3]
        matches: list[TreeNode] = []

        for node in self._nodes.values():
            if node.tree_scope != tree_scope:
                continue
            content_lower = node.content.lower()
            if any(term in content_lower for term in q_terms) or not q_terms:
                matches.append(node)

        # Higher level nodes (summaries) take precedence
        matches.sort(key=lambda n: (n.level, n.created_at), reverse=True)
        return matches[:max_results]

    def topic_route(self, content: str, topics: list[str]) -> list[str]:
        """Route content chunk into matching topic tree scopes."""
        if not self.enabled:
            return []
        matched_scopes: list[str] = []
        c_lower = content.lower()
        for t in topics:
            if t.lower() in c_lower:
                scope = f"topic:{t.lower()}"
                self.append_leaf(scope, content)
                matched_scopes.append(scope)
        return matched_scopes
