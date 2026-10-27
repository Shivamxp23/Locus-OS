"""
Unit tests for PageIndex Vectorless Retrieval (F-0059 / US-95).
"""
import pytest
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.search.pageindex import (
    PageIndexDoc,
    PageIndexEngine,
    PageIndexNode,
    PageIndexSearchResult,
)
from sidecar.providers.pageindex import (
    BasePageIndexRetrievalProvider,
    DefaultPageIndexRetrievalProvider,
)


SAMPLE_MARKDOWN = """
# Introduction to Locus

Locus is a personal cognitive operating system.

```python
# This is a comment inside code fence
# Not a heading
def fake_header():
    pass
```

## System Architecture

The architecture consists of three layers: client, sidecar, and daemon.

### Client Layer

Obsidian extension and TUI interfaces.

### Sidecar Layer

FastAPI background daemon managing memory and life OS.

## Memory Systems

Hierarchical memory with Neo4j and vector indices.

**Obsidian Vault Structure**

The single source of truth for daily operations.
"""


def test_markdown_tree_construction_and_code_fence_skipping():
    """
    SPEC §27.1 line 1496: "extract_nodes_from_markdown — regex #{1,6} headers + **bold** standalone lines as level-1 headings; skips content inside fenced code blocks."
    """
    engine = PageIndexEngine()
    nodes = engine.extract_nodes_from_markdown(SAMPLE_MARKDOWN)

    titles = [n.title for n in nodes]
    # Check that headers inside code fences are NOT extracted
    assert not any("This is a comment" in t for t in titles)
    assert not any("Not a heading" in t for t in titles)

    # Check that regular headers are extracted
    assert "Introduction to Locus" in titles
    assert "System Architecture" in titles
    assert "Client Layer" in titles
    assert "Sidecar Layer" in titles
    assert "Memory Systems" in titles

    # Check that standalone **bold** line is treated as level 1 heading
    assert "Obsidian Vault Structure" in titles
    bold_node = next(n for n in nodes if n.title == "Obsidian Vault Structure")
    assert bold_node.level == 1


def test_cumulative_token_counting_bottom_up():
    """
    SPEC §27.1 line 1498: "update_node_list_with_text_token_count — cumulative token count per node including all descendants (computed bottom-up)."
    """
    engine = PageIndexEngine()
    doc = engine.md_to_tree(SAMPLE_MARKDOWN, doc_name="locus_intro.md", min_node_token=1)

    # Find "System Architecture" child node under root "Introduction to Locus"
    root_node = doc.structure[0]
    assert root_node.title == "Introduction to Locus"
    arch_node = next(n for n in root_node.nodes if n.title == "System Architecture")
    assert len(arch_node.nodes) >= 2  # Has children Client Layer & Sidecar Layer

    # Cumulative tokens must be strictly greater than own text token count
    assert arch_node.cumulative_token_count > arch_node.token_count
    # Cumulative tokens must equal own tokens + sum of children cumulative tokens
    expected = arch_node.token_count + sum(c.cumulative_token_count for c in arch_node.nodes)
    assert arch_node.cumulative_token_count == expected


def test_tree_thinning_for_compactness():
    """
    SPEC §27.1 line 1499: "tree_thinning_for_index — merge any node whose subtree is below min_node_token into its parent (keeps index compact)."
    """
    engine = PageIndexEngine()
    # If min_node_token is high, small leaf sections get merged into preceding node
    raw_nodes = engine.extract_nodes_from_markdown(SAMPLE_MARKDOWN)
    text_nodes = engine.extract_node_text_content(raw_nodes, SAMPLE_MARKDOWN)

    # Thin with a threshold of 100 tokens (most sample sections are short)
    thinned = engine.tree_thinning_for_index(text_nodes, min_node_token=100)
    assert len(thinned) < len(text_nodes)


def test_stack_based_nesting_and_padded_node_ids():
    """
    SPEC §27.1 line 1500: "build_tree_from_nodes — stack-based nesting by heading level; assigns node_id = zero-padded 4-digit counter."
    """
    engine = PageIndexEngine()
    doc = engine.md_to_tree(SAMPLE_MARKDOWN, doc_name="locus_intro.md", min_node_token=1)

    # All node IDs must be zero-padded 4-digit strings
    def check_node_ids(nodes: List[PageIndexNode]):
        for node in nodes:
            assert len(node.node_id) == 4
            assert node.node_id.isdigit()
            check_node_ids(node.nodes)

    check_node_ids(doc.structure)
    assert doc.structure[0].node_id == "0001"


def test_reasoning_tree_retrieval_and_citation_path():
    """
    SPEC §27.1 line 1504: "Retrieval (agent_tools.py): start at root; present child summaries to the LLM; it picks the most relevant child; descend; return the leaf's full text."
    """
    engine = PageIndexEngine()
    doc = engine.md_to_tree(SAMPLE_MARKDOWN, doc_name="locus_intro.md", min_node_token=1)

    # Search for sidecar architecture
    res = engine.retrieve(query="FastAPI background daemon sidecar", doc=doc)
    assert res.doc_name == "locus_intro.md"
    assert res.leaf_title == "Sidecar Layer"
    assert "FastAPI background daemon" in res.text
    # Citation path should trace from doc -> Introduction to Locus -> System Architecture -> Sidecar Layer
    assert res.citation_path == ["locus_intro.md", "Introduction to Locus", "System Architecture", "Sidecar Layer"]
    assert res.hops >= 3
    assert len(res.reasoning_steps) >= 3


def test_modular_subsystem_off_switch(monkeypatch):
    """
    SPEC §27.1 line 1530: "Swappable / off state: locus.retrieval.provider (pageindex | pgvector | BM25 | custom); off = semantic retrieval relies on pgvector only."
    """
    engine = PageIndexEngine()
    switch = "locus.retrieval.pageindex.enabled"

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    assert engine.is_engine_enabled() is False


def test_provider_master_off_switch_503(monkeypatch):
    """
    SPEC §27.1 line 1530: "Registers as a provider in sidecar/providers/ with modular off-switch locus.pageindex_retrieval.enabled returning 503."
    """
    provider = DefaultPageIndexRetrievalProvider()
    switch = "locus.pageindex_retrieval.enabled"

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    enabled, sw = provider.is_feature_enabled()
    assert enabled is False
    assert sw == switch

    res_tree = provider.build_tree(content="# Test\nBody")
    assert res_tree.get("status_code") == 503

    res_ret = provider.retrieve(query="Test query")
    assert res_ret.get("status_code") == 503

    res_st = provider.get_status()
    assert res_st.get("status_code") == 503


def test_provider_swap_polymorphism():
    """
    SPEC §27.1 line 1530: "Registers as a provider in sidecar/providers/ with modular off-switch locus.pageindex_retrieval.enabled returning 503."
    """
    class MockCustomPageIndexProvider(BasePageIndexRetrievalProvider):
        @property
        def name(self) -> str:
            return "mock_pageindex_provider"

        def is_feature_enabled(self) -> Tuple[bool, str]:
            return True, ""

        def build_tree(
            self,
            content: str,
            doc_name: str = "document.md",
            min_node_token: int = 50,
            summary_token_threshold: int = 200,
        ) -> Dict[str, Any]:
            return {"mock": True, "doc_name": doc_name}

        def retrieve(
            self,
            query: str,
            doc_name: Optional[str] = None,
            tree_data: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            return {"mock": True, "query": query}

        def get_status(self) -> Dict[str, Any]:
            return {"mock": True, "name": self.name}

    prov: BasePageIndexRetrievalProvider = MockCustomPageIndexProvider()
    assert prov.name == "mock_pageindex_provider"
    assert prov.build_tree("# Doc")["mock"] is True
    assert prov.retrieve("hello")["query"] == "hello"
