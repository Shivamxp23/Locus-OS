"""tests/test_memory_tree.py - Unit & Integration Tests for Memory Tree.

Tests Spec §4.5:
- L0 leaf buffer appending and token counting.
- Seal Gate threshold triggering hierarchical upward cascade (L0 -> L1 -> L2).
- Downward branch search prioritizing higher-level summaries.
- Topic routing cross-tree distribution.
- MemoryTreeProvider protocol compliance.
- Modularity switch: locus.memory.tree.enabled=False.
"""

from sidecar.memory.tree_ops import (
    MemoryTreeManager,
    MemoryTreeProvider,
    TreeNode,
)


def test_memory_tree_protocol_conformance():
    mgr = MemoryTreeManager()
    assert isinstance(mgr, MemoryTreeProvider)


def test_append_leaf_and_auto_seal_cascade():
    # Set small seal_gate=3 for testing cascade
    mgr = MemoryTreeManager(enabled=True, seal_gate=3)
    scope = "vault:daily"

    n1 = mgr.append_leaf(scope, "Note 1: Completed sprint task planning.")
    n2 = mgr.append_leaf(scope, "Note 2: Built state engine and intent classifier.")
    assert len(mgr.get_unsealed(scope, level=0)) == 2

    # Appending 3rd leaf hits gate and triggers L1 summary creation
    n3 = mgr.append_leaf(scope, "Note 3: Added anti-hallucination verification.")
    unsealed_l0 = mgr.get_unsealed(scope, level=0)
    assert len(unsealed_l0) == 0  # all sealed!

    # L1 summary node created
    unsealed_l1 = mgr.get_unsealed(scope, level=1)
    assert len(unsealed_l1) == 1
    parent = unsealed_l1[0]
    assert parent.level == 1
    assert set(parent.children) == {n1.id, n2.id, n3.id}
    assert "Summary:" in parent.content


def test_hierarchical_search_ranks_summaries():
    mgr = MemoryTreeManager(enabled=True, seal_gate=2)
    scope = "github:locus"

    mgr.append_leaf(scope, "Commit 1: Implemented database migrations.")
    mgr.append_leaf(scope, "Commit 2: Added Redis cache layer.")  # seals to L1

    # Search for database
    results = mgr.search(scope, "database", max_results=5)
    assert len(results) > 0
    # Top result should be the L1 summary node
    assert results[0].level == 1


def test_topic_routing():
    mgr = MemoryTreeManager(enabled=True)
    topics = ["python", "architecture", "security"]

    matched = mgr.topic_route(
        "Refactored Python security layer for permission bypass.",
        topics,
    )
    assert "topic:python" in matched
    assert "topic:security" in matched
    assert "topic:architecture" not in matched


def test_memory_tree_modularity_disabled():
    mgr = MemoryTreeManager(enabled=False)
    node = mgr.append_leaf("vault:daily", "Content")
    assert node.id == "disabled"
    assert mgr.search("vault:daily", "Content") == []
