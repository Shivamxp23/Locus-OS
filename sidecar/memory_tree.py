"""Hierarchical Memory Tree Provider implementation.

Implements Spec §4.5: Memory Tree (Hierarchical Summarization Cascade):
- Generic multi-level summarization tree over text corpora.
- Level hierarchy: L0 leaf buffer (raw chunks) -> L1-LN progressive summaries -> Root.
- Auto-sealing cascade: threshold of N items (default 8) triggers upward summarization.
- Stale flush: unsealed nodes older than 3 hours seal automatically.
- Top-down relevance search: ranks higher-level summary nodes first, descending to leaves.
- Topic routing: cross-tree distribution into scoped topic trees (topic:<name>).
- SQLite persistence: mem_tree_chunks and mem_tree_ingested_sources.
- Modularity switch: locus.memory.tree.enabled (or locus.memory_tree_hierarchical_summarization_cascade.enabled).
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional
import uuid

from sidecar.providers.memory_tree import (
    BaseMemoryTreeProvider,
    MemoryTreeConfig,
    TreeNode,
    TreeScopeConfig,
)

logger = logging.getLogger("locus.memory_tree")


def default_extractive_summarizer(combined_text: str, level: int = 1) -> str:
    """Default extractive summarizer for hierarchically cascading tree nodes.

    Extracts salient lines and produces a dense, structured hierarchical summary.
    """
    clean_lines = [
        line.strip()
        for line in combined_text.splitlines()
        if line.strip() and not line.strip().startswith("---")
    ]
    if not clean_lines:
        return f"Summary L{level}: [Empty content]"

    key_takeaways: list[str] = []
    seen: set[str] = set()
    for line in clean_lines:
        norm = line.lower()
        if norm not in seen:
            seen.add(norm)
            key_takeaways.append(line)
        if len(key_takeaways) >= 6:
            break

    summary_body = " | ".join(key_takeaways)
    return f"Summary L{level}: {summary_body}"


class HierarchicalMemoryTreeProvider(BaseMemoryTreeProvider):
    """Core Memory Tree Manager implementing Spec §4.5."""

    def __init__(
        self,
        config: Optional[MemoryTreeConfig] = None,
        summarizer: Optional[Callable[[str, int], str]] = None,
        scope_configs: Optional[dict[str, TreeScopeConfig]] = None,
    ) -> None:
        super().__init__(name="memory_tree")
        self.config = config or MemoryTreeConfig()
        self._summarizer = summarizer or default_extractive_summarizer
        self._scope_configs: dict[str, TreeScopeConfig] = scope_configs or {}
        self._db_path = self.config.db_path or ":memory:"
        self._conn: Optional[sqlite3.Connection] = None
        self._init_sqlite()

    def _init_sqlite(self) -> None:
        """Initialize SQLite database and required schema per Spec §4.5 lines 808-812."""
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mem_tree_chunks (
                    id TEXT PRIMARY KEY,
                    tree_scope TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    children_json TEXT NOT NULL,
                    token_count INTEGER NOT NULL,
                    sealed INTEGER NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mem_tree_ingested_sources (
                    id TEXT PRIMARY KEY,
                    source_kind TEXT,
                    source_id TEXT,
                    tree_scope TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    ingested_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tree_scope_level ON mem_tree_chunks(tree_scope, level, sealed)"
            )

    def is_enabled(self) -> bool:
        """Return True if memory tree operations are enabled."""
        return bool(self.config.enabled)

    def set_enabled(self, enabled: bool) -> None:
        """Update enabled state."""
        self.config.enabled = bool(enabled)

    def get_scope_config(self, tree_scope: str) -> TreeScopeConfig:
        """Retrieve scope-specific configuration or default."""
        if tree_scope in self._scope_configs:
            return self._scope_configs[tree_scope]
        return TreeScopeConfig(
            tree_scope=tree_scope,
            seal_gate=self.config.default_seal_gate,
            stale_flush_seconds=self.config.stale_flush_seconds,
        )

    def configure_scope(self, scope_config: TreeScopeConfig) -> None:
        """Register custom scope configuration."""
        self._scope_configs[scope_config.tree_scope] = scope_config

    def _row_to_node(self, row: sqlite3.Row) -> TreeNode:
        """Map SQLite row to TreeNode domain model."""
        children: list[str] = []
        if row["children_json"]:
            try:
                children = json.loads(row["children_json"])
            except Exception:
                children = []
        return TreeNode(
            id=str(row["id"]),
            tree_scope=str(row["tree_scope"]),
            level=int(row["level"]),
            content=str(row["content"]),
            children=children,
            token_count=int(row["token_count"]),
            sealed=bool(row["sealed"]),
            created_at=float(row["created_at"]),
        )

    def append_leaf(
        self,
        tree_scope: str,
        content: str,
        source_id: Optional[str] = None,
        source_kind: Optional[str] = None,
    ) -> TreeNode:
        """Append raw chunk to L0 buffer per Spec §4.5 line 755.

        SPEC §4.5 line 755:
        FUNCTION append_leaf(tree_scope, content):
          node = TreeNode { level: 0, content, sealed: false }
          store.insert(node)
          IF count_unsealed(tree_scope, level=0) >= SEAL_GATE:
            enqueue_job(JobKind::Seal, tree_scope, level=0)
        """
        if not self.config.enabled:
            return TreeNode(
                id="disabled",
                tree_scope=tree_scope,
                level=0,
                content=content,
                token_count=max(1, len(content.split())),
                sealed=False,
            )

        node_id = str(uuid.uuid4())
        token_count = max(1, len(content.split()))
        created_at = time.time()
        node = TreeNode(
            id=node_id,
            tree_scope=tree_scope,
            level=0,
            content=content,
            children=[],
            token_count=token_count,
            created_at=created_at,
            sealed=False,
        )

        assert self._conn is not None
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO mem_tree_chunks (
                    id, tree_scope, level, content, children_json, token_count, sealed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.tree_scope,
                    node.level,
                    node.content,
                    json.dumps(node.children),
                    node.token_count,
                    1 if node.sealed else 0,
                    node.created_at,
                ),
            )
            if source_id or source_kind:
                self._conn.execute(
                    """
                    INSERT INTO mem_tree_ingested_sources (
                        id, source_kind, source_id, tree_scope, node_id, ingested_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        source_kind or "generic",
                        source_id or "unspecified",
                        tree_scope,
                        node.id,
                        created_at,
                    ),
                )

        # Check seal gate threshold for L0
        scope_cfg = self.get_scope_config(tree_scope)
        unsealed = self.get_unsealed(tree_scope, level=0)
        if len(unsealed) >= scope_cfg.seal_gate:
            self.seal_level(tree_scope, level=0)

        return node

    def seal_level(
        self,
        tree_scope: str,
        level: int = 0,
        force: bool = False,
    ) -> Optional[TreeNode]:
        """Combine unsealed nodes at level and cascade upward per Spec §4.5 line 762.

        SPEC §4.5 line 762:
        FUNCTION seal_level(tree_scope, level):
          unsealed = store.get_unsealed(tree_scope, level)
          IF unsealed.count < SEAL_GATE: RETURN
          combined_text = unsealed.map(n => n.content).join("\n---\n")
          summary = llm.summarize(combined_text)
          parent = TreeNode { level: level + 1, content: summary, children: unsealed.map(n => n.id), sealed: false }
          store.insert(parent)
          FOR EACH child IN unsealed: child.sealed = true; store.update(child)
          IF count_unsealed(tree_scope, level+1) >= SEAL_GATE: enqueue_job(JobKind::Seal, tree_scope, level+1)
        """
        if not self.config.enabled:
            return None

        scope_cfg = self.get_scope_config(tree_scope)
        unsealed = self.get_unsealed(tree_scope, level=level)
        if not unsealed:
            return None

        # Check seal threshold vs stale flush
        now = time.time()
        is_stale = (now - unsealed[0].created_at) >= scope_cfg.stale_flush_seconds
        if not force and len(unsealed) < scope_cfg.seal_gate and not is_stale:
            return None

        combined_text = "\n---\n".join(n.content for n in unsealed)
        target_level = level + 1
        summary_text = self._summarizer(combined_text, target_level)

        parent_id = str(uuid.uuid4())
        token_count = max(1, len(summary_text.split()))
        parent = TreeNode(
            id=parent_id,
            tree_scope=tree_scope,
            level=target_level,
            content=summary_text,
            children=[n.id for n in unsealed],
            token_count=token_count,
            created_at=now,
            sealed=False,
        )

        assert self._conn is not None
        with self._conn:
            # Insert parent
            self._conn.execute(
                """
                INSERT INTO mem_tree_chunks (
                    id, tree_scope, level, content, children_json, token_count, sealed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parent.id,
                    parent.tree_scope,
                    parent.level,
                    parent.content,
                    json.dumps(parent.children),
                    parent.token_count,
                    0,
                    parent.created_at,
                ),
            )
            # Mark children as sealed
            for child in unsealed:
                self._conn.execute(
                    "UPDATE mem_tree_chunks SET sealed = 1 WHERE id = ?",
                    (child.id,),
                )
                child.sealed = True

        # Upward Cascade: check if parent level now meets seal gate threshold
        parent_level_unsealed = self.get_unsealed(tree_scope, level=target_level)
        if len(parent_level_unsealed) >= scope_cfg.seal_gate and target_level < scope_cfg.max_depth:
            self.seal_level(tree_scope, level=target_level)

        return parent

    def search(
        self,
        tree_scope: str,
        query: str,
        max_results: int = 5,
    ) -> list[TreeNode]:
        """Perform top-down relevance search per Spec §4.5 line 787.

        Higher-level summary nodes are scored with hierarchical priority.
        """
        if not self.config.enabled:
            return []

        assert self._conn is not None
        cur = self._conn.execute(
            "SELECT * FROM mem_tree_chunks WHERE tree_scope = ? ORDER BY level DESC, created_at DESC",
            (tree_scope,),
        )
        nodes = [self._row_to_node(row) for row in cur.fetchall()]
        if not nodes:
            return []

        q_terms = [t.lower() for t in query.strip().split() if len(t) >= 2]
        if not q_terms or query.strip() in ("*", ""):
            # Sort by level descending (highest summaries first), then recency
            nodes.sort(key=lambda n: (n.level, n.created_at), reverse=True)
            return nodes[:max_results]

        scored_nodes: list[tuple[float, TreeNode]] = []
        for n in nodes:
            text_lower = n.content.lower()
            matches = sum(1 for term in q_terms if term in text_lower)
            if matches > 0:
                # Level weighting: summaries provide dense relevance, boosted by 1.5 per level
                score = (matches / len(q_terms)) * (1.0 + (n.level * 0.5))
                scored_nodes.append((score, n))

        scored_nodes.sort(key=lambda item: (item[0], item[1].level, item[1].created_at), reverse=True)
        return [node for _, node in scored_nodes[:max_results]]

    def topic_route(
        self,
        content: str,
        topics: list[str],
    ) -> list[str]:
        """Route content chunk into matching topic tree scopes per Spec §4.5 line 794.

        SPEC §4.5 line 794:
        FUNCTION topic_route(chunk, topics):
          matched = match_topics(chunk.content, topics)
          FOR EACH topic IN matched:
            target_scope = "topic:{topic.name}"
            append_leaf(target_scope, chunk.content)
        """
        if not self.config.enabled:
            return []

        matched_scopes: list[str] = []
        c_lower = content.lower()
        for t in topics:
            clean_topic = t.strip()
            if not clean_topic:
                continue
            if clean_topic.lower() in c_lower:
                target_scope = f"topic:{clean_topic.lower()}"
                self.append_leaf(target_scope, content)
                matched_scopes.append(target_scope)

        return matched_scopes

    def get_nodes(
        self,
        tree_scope: Optional[str] = None,
        level: Optional[int] = None,
    ) -> list[TreeNode]:
        """Retrieve stored tree nodes matching optional filters."""
        if not self.config.enabled:
            return []

        assert self._conn is not None
        query = "SELECT * FROM mem_tree_chunks WHERE 1=1"
        params: list[Any] = []
        if tree_scope is not None:
            query += " AND tree_scope = ?"
            params.append(tree_scope)
        if level is not None:
            query += " AND level = ?"
            params.append(level)
        query += " ORDER BY level DESC, created_at DESC"

        cur = self._conn.execute(query, params)
        return [self._row_to_node(row) for row in cur.fetchall()]

    def get_unsealed(
        self,
        tree_scope: str,
        level: int = 0,
    ) -> list[TreeNode]:
        """Retrieve all unsealed nodes for a given scope and level."""
        assert self._conn is not None
        cur = self._conn.execute(
            "SELECT * FROM mem_tree_chunks WHERE tree_scope = ? AND level = ? AND sealed = 0 ORDER BY created_at ASC",
            (tree_scope, level),
        )
        return [self._row_to_node(row) for row in cur.fetchall()]

    def health(self) -> dict[str, Any]:
        """Return operational health status and database statistics."""
        assert self._conn is not None
        total_chunks = self._conn.execute("SELECT COUNT(*) FROM mem_tree_chunks").fetchone()[0]
        unsealed_count = self._conn.execute(
            "SELECT COUNT(*) FROM mem_tree_chunks WHERE sealed = 0"
        ).fetchone()[0]
        scopes_count = self._conn.execute(
            "SELECT COUNT(DISTINCT tree_scope) FROM mem_tree_chunks"
        ).fetchone()[0]
        max_level = self._conn.execute("SELECT MAX(level) FROM mem_tree_chunks").fetchone()[0] or 0

        return {
            "status": "healthy" if self.config.enabled else "disabled",
            "enabled": self.config.enabled,
            "db_path": self._db_path,
            "total_chunks": total_chunks,
            "unsealed_chunks": unsealed_count,
            "unique_scopes": scopes_count,
            "max_level": max_level,
            "default_seal_gate": self.config.default_seal_gate,
            "stale_flush_seconds": self.config.stale_flush_seconds,
        }
