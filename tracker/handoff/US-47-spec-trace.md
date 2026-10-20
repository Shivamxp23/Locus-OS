# Spec Trace for US-47: Memory Tree (Hierarchical Summarization Cascade)

| Spec Ref | Spec Sentence | Code Implementation | Test File:Line |
|---|---|---|---|
| §4.5 line 716 | "## Feature §4.5: Memory Tree (Hierarchical Summarization Cascade)" | `sidecar/memory_tree.py:61` | `tests/unit/test_memory_tree.py:27` |
| §4.5 line 741 | "TreeNode { id: UUID, tree_scope: str, level: u32, content: str, children: [UUID], token_count: u32, created_at: DateTime, sealed: bool }" | `sidecar/providers/memory_tree.py:21`, `locus-extension/src/memory-tree.ts:13` | `tests/unit/test_memory_tree.py:38` |
| §4.5 line 755 | "FUNCTION append_leaf(tree_scope, content): node = TreeNode { level: 0, content, sealed: false }" | `sidecar/memory_tree.py:157` | `tests/unit/test_memory_tree.py:38`, `tests/integration/test_memory_tree_service.py:30` |
| §4.5 line 758 | "IF count_unsealed(tree_scope, level=0) >= SEAL_GATE: enqueue_job(JobKind::Seal, tree_scope, level=0)" | `sidecar/memory_tree.py:228` | `tests/unit/test_memory_tree.py:58` |
| §4.5 line 762 | "FUNCTION seal_level(tree_scope, level): unsealed = store.get_unsealed(tree_scope, level)" | `sidecar/memory_tree.py:236` | `tests/unit/test_memory_tree.py:58`, `tests/integration/test_memory_tree_service.py:30` |
| §4.5 line 783 | "// CASCADE: check if parent level also needs sealing" | `sidecar/memory_tree.py:317` | `tests/unit/test_memory_tree.py:90` |
| §4.5 line 787 | "FUNCTION search(tree_scope, query, max_results): Start from highest-level nodes, descend into relevant branches" | `sidecar/memory_tree.py:323` | `tests/unit/test_memory_tree.py:145`, `tests/integration/test_memory_tree_service.py:65` |
| §4.5 line 794 | "FUNCTION topic_route(chunk, topics): matched = match_topics(chunk.content, topics)" | `sidecar/memory_tree.py:358` | `tests/unit/test_memory_tree.py:165`, `tests/integration/test_memory_tree_service.py:65` |
| §4.5 line 804 | "Time-based stale flush: if L0 buffer age > 3 hours, seal regardless of count" | `sidecar/memory_tree.py:265` | `tests/unit/test_memory_tree.py:121` |
| §4.5 line 808 | "SQLite table: mem_tree_chunks" | `sidecar/memory_tree.py:84` | `tests/unit/test_memory_tree.py:205` |
| §4.5 line 816 | "Provider Interface: implements MemoryProvider — plugs into the Memory Tri-Stack alongside Neo4j and PageIndex." | `sidecar/providers/memory_tree.py:98`, `sidecar/service.py:2620` | `tests/unit/test_memory_tree.py:27` |
| §4.5 line 820 | "Swappable / off state: locus.memory.tree.enabled. Off → raw chunks stored but never summarized (flat memory only)" | `sidecar/memory_tree.py:173`, `sidecar/service.py:2648` | `tests/unit/test_memory_tree.py:186`, `tests/integration/test_memory_tree_service.py:112` |
