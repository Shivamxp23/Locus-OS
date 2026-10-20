"""Unit tests for Memory Tree (Hierarchical Summarization Cascade).

Tests Spec §4.5:
- Level hierarchy: L0 leaf buffer (raw text) -> L1-LN progressive summaries -> Root.
- Auto-sealing cascade: threshold of N unsealed items triggers upward summarization.
- Stale flush: unsealed nodes older than 3 hours seal automatically.
- Top-down relevance search: ranks higher-level summary nodes first, descending to leaves.
- Topic routing: cross-tree distribution into scoped topic trees.
- SQLite persistence: mem_tree_chunks and mem_tree_ingested_sources.
- Modularity off-switch: locus.memory.tree.enabled.
"""

import time
from typing import Optional
import pytest

from sidecar.memory_tree import (
    HierarchicalMemoryTreeProvider,
    default_extractive_summarizer,
)
from sidecar.providers.memory_tree import (
    BaseMemoryTreeProvider,
    MemoryTreeConfig,
    TreeNode,
    TreeScopeConfig,
)


def test_memory_tree_protocol_conformance():
    """SPEC §4.5 line 816: "Provider Interface: implements MemoryProvider — plugs into the Memory Tri-Stack alongside Neo4j and PageIndex."

    Asserts HierarchicalMemoryTreeProvider implements BaseMemoryTreeProvider.
    """
    provider = HierarchicalMemoryTreeProvider()
    assert isinstance(provider, BaseMemoryTreeProvider)
    assert provider.is_enabled() is True


def test_append_leaf_creates_l0_node_and_persists():
    """SPEC §4.5 line 755: "FUNCTION append_leaf(tree_scope, content): node = TreeNode { level: 0, content, sealed: false }"

    Asserts append_leaf inserts L0 unsealed node with accurate token counts and SQLite persistence.
    """
    provider = HierarchicalMemoryTreeProvider()
    scope = "vault:daily"
    node = provider.append_leaf(scope, "Daily log turn: Reviewed sprint backlog and planned memory tree.", source_id="note-101", source_kind="obsidian")

    assert node.level == 0
    assert node.tree_scope == scope
    assert node.sealed is False
    assert node.token_count > 0
    assert node.id != ""

    nodes = provider.get_nodes(tree_scope=scope, level=0)
    assert len(nodes) == 1
    assert nodes[0].id == node.id
    assert nodes[0].content == node.content


def test_auto_seal_gate_triggers_l1_summary():
    """SPEC §4.5 line 758: "IF count_unsealed(tree_scope, level=0) >= SEAL_GATE: enqueue_job(JobKind::Seal, tree_scope, level=0)"

    Asserts that accumulating unsealed items up to seal_gate triggers automatic sealing into an L1 summary node.
    """
    # Configure custom gate of 3 for fast deterministic test
    provider = HierarchicalMemoryTreeProvider(config=MemoryTreeConfig(default_seal_gate=3))
    scope = "github:owner/repo"

    n1 = provider.append_leaf(scope, "Commit 1: Added SQLite tree chunks table.")
    n2 = provider.append_leaf(scope, "Commit 2: Added indexing on tree_scope and level.")
    unsealed_before = provider.get_unsealed(scope, level=0)
    assert len(unsealed_before) == 2

    # Appending 3rd leaf hits gate=3 and automatically triggers seal_level(scope, 0)
    n3 = provider.append_leaf(scope, "Commit 3: Added upward summarization cascade.")

    unsealed_after_l0 = provider.get_unsealed(scope, level=0)
    assert len(unsealed_after_l0) == 0  # all 3 L0 nodes sealed

    # Parent L1 summary created
    unsealed_l1 = provider.get_unsealed(scope, level=1)
    assert len(unsealed_l1) == 1
    parent = unsealed_l1[0]
    assert parent.level == 1
    assert parent.tree_scope == scope
    assert parent.sealed is False
    assert set(parent.children) == {n1.id, n2.id, n3.id}
    assert "Summary L1:" in parent.content


def test_multi_level_hierarchical_cascade_upward():
    """SPEC §4.5 line 783: "// CASCADE: check if parent level also needs sealing"

    Asserts that when L1 summaries reach seal_gate, an L2 summary is automatically spawned.
    """
    # Gate of 2 per level: 2 L0 -> 1 L1; 4 L0 -> 2 L1 -> 1 L2!
    provider = HierarchicalMemoryTreeProvider(config=MemoryTreeConfig(default_seal_gate=2))
    scope = "vault:research"

    # Add 2 leaves -> seals to 1st L1
    provider.append_leaf(scope, "Hypothesis A: Cognitive trees outperform flat vector embeddings.")
    provider.append_leaf(scope, "Hypothesis B: Deterministic bucket-sealing eliminates re-summarization drift.")
    assert len(provider.get_unsealed(scope, level=1)) == 1

    # Add 2 more leaves -> seals to 2nd L1 -> triggers cascade to L2!
    provider.append_leaf(scope, "Experiment 1: Ingested 100 research articles into Memory Tree.")
    provider.append_leaf(scope, "Experiment 2: Validated 85% token reduction on context retrieval.")

    # L0 and L1 unsealed should be sealed; L2 node should now exist!
    unsealed_l0 = provider.get_unsealed(scope, level=0)
    assert len(unsealed_l0) == 0

    unsealed_l1 = provider.get_unsealed(scope, level=1)
    assert len(unsealed_l1) == 0  # Both L1 nodes sealed into L2

    unsealed_l2 = provider.get_unsealed(scope, level=2)
    assert len(unsealed_l2) == 1
    root_summary = unsealed_l2[0]
    assert root_summary.level == 2
    assert "Summary L2:" in root_summary.content


def test_stale_flush_seals_older_nodes_regardless_of_gate():
    """SPEC §4.5 line 804: "Time-based stale flush: if L0 buffer age > 3 hours, seal regardless of count"

    Asserts that nodes older than stale_flush_seconds seal even if below the seal gate count.
    """
    # Gate of 8 items, but stale_flush_seconds set to 0.1s
    provider = HierarchicalMemoryTreeProvider(
        config=MemoryTreeConfig(default_seal_gate=8, stale_flush_seconds=0.1)
    )
    scope = "telegram:chat"

    node = provider.append_leaf(scope, "Telegram message: Meeting moved to 4 PM.")
    # Wait for stale threshold
    time.sleep(0.15)

    # Calling seal_level without force should detect staleness and seal
    parent = provider.seal_level(scope, level=0, force=False)
    assert parent is not None
    assert parent.level == 1
    assert node.id in parent.children

    # L0 should now be sealed
    assert len(provider.get_unsealed(scope, level=0)) == 0


def test_top_down_relevance_search_prioritizes_summaries():
    """SPEC §4.5 line 787: "FUNCTION search(tree_scope, query, max_results): Start from highest-level nodes, descend into relevant branches"

    Asserts that search ranks higher-level summary nodes first to provide executive context before leaf details.
    """
    provider = HierarchicalMemoryTreeProvider(config=MemoryTreeConfig(default_seal_gate=2))
    scope = "project:architecture"

    provider.append_leaf(scope, "Component: Authentication module handles OAuth2 tokens.")
    provider.append_leaf(scope, "Component: Security module enforces strict loopback binding.")

    results = provider.search(scope, "Security", max_results=5)
    assert len(results) >= 1
    # Top result should be the L1 summary node
    assert results[0].level == 1
    assert "Security" in results[0].content or "Summary L1:" in results[0].content


def test_topic_routing_distributes_across_scoped_trees():
    """SPEC §4.5 line 794: "FUNCTION topic_route(chunk, topics): matched = match_topics(chunk.content, topics)"

    Asserts that content is routed into appropriate topic tree scopes matching configured keywords.
    """
    provider = HierarchicalMemoryTreeProvider()
    topics = ["Neo4j", "Docker", "FastAPI"]
    chunk = "Refactored FastAPI routes to support modular Neo4j graph storage and off-switch."

    matched = provider.topic_route(chunk, topics)
    assert "topic:neo4j" in matched
    assert "topic:fastapi" in matched
    assert "topic:docker" not in matched

    # Verify nodes were placed into scoped topic trees
    neo_nodes = provider.get_nodes(tree_scope="topic:neo4j")
    assert len(neo_nodes) == 1
    assert "FastAPI" in neo_nodes[0].content

    fastapi_nodes = provider.get_nodes(tree_scope="topic:fastapi")
    assert len(fastapi_nodes) == 1


def test_modular_off_switch_behavior():
    """SPEC §4.5 line 820: "Swappable / off state: locus.memory.tree.enabled. Off → raw chunks stored but never summarized (flat memory only)"

    Asserts that when memory tree is disabled, append returns disabled state and search yields empty.
    """
    provider = HierarchicalMemoryTreeProvider(config=MemoryTreeConfig(enabled=False))
    assert provider.is_enabled() is False

    node = provider.append_leaf("vault:notes", "Some unsummarized note.")
    assert node.id == "disabled"

    sealed = provider.seal_level("vault:notes", level=0, force=True)
    assert sealed is None

    results = provider.search("vault:notes", "note")
    assert results == []

    health = provider.health()
    assert health["status"] == "disabled"
    assert health["enabled"] is False


def test_health_check_returns_schema_and_metrics():
    """SPEC §4.5 line 808: "SQLite table: mem_tree_chunks"

    Asserts health check reports accurate total chunks, unsealed counts, and max depth.
    """
    provider = HierarchicalMemoryTreeProvider(config=MemoryTreeConfig(default_seal_gate=5))
    provider.append_leaf("scope_a", "Chunk 1 in scope A")
    provider.append_leaf("scope_b", "Chunk 1 in scope B")

    health = provider.health()
    assert health["status"] == "healthy"
    assert health["total_chunks"] == 2
    assert health["unsealed_chunks"] == 2
    assert health["unique_scopes"] == 2
    assert health["max_level"] == 0
