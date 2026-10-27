"""
SPEC §27.1 lines 1477-1540: Vectorless Retrieval (PageIndex) (F-0059 / US-95).
Source: VectifyAI/PageIndex
Logic:
    PageIndex is vectorless, reasoning-based RAG:
    Hierarchical "table-of-contents" tree over markdown document.
    No vector DB, no chunking.
    Tree build (md_to_tree):
    1. extract_nodes_from_markdown: regex #{1,6} headers + **bold** standalone lines as level-1.
       Skips content inside fenced code blocks.
    2. extract_node_text_content: assigns text between headers.
    3. update_token_counts: cumulative token count per node bottom-up.
    4. tree_thinning_for_index: merges nodes below min_node_token into parent.
    5. build_tree_from_nodes: stack-based nesting by heading level; assigns node_id zero-padded 4-digit counter.
    6. generate_summaries_for_structure_md: summary for leaves, prefix_summary for parents.
    Retrieval (retrieve):
    Reasoning-based tree search root -> leaf presenting child summaries; returns leaf full text with citation path.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.search.pageindex")


@dataclass
class PageIndexNode:
    title: str
    node_id: str = ""
    line_num: int = 1
    level: int = 1
    text: str = ""
    token_count: int = 0
    cumulative_token_count: int = 0
    summary: Optional[str] = None
    prefix_summary: Optional[str] = None
    nodes: List[PageIndexNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "title": self.title,
            "node_id": self.node_id,
            "line_num": self.line_num,
            "level": self.level,
            "text": self.text,
            "token_count": self.token_count,
            "cumulative_token_count": self.cumulative_token_count,
            "nodes": [child.to_dict() for child in self.nodes],
        }
        if self.summary is not None:
            data["summary"] = self.summary
        if self.prefix_summary is not None:
            data["prefix_summary"] = self.prefix_summary
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageIndexNode:
        children = [cls.from_dict(c) for c in data.get("nodes", [])]
        return cls(
            title=data.get("title", ""),
            node_id=data.get("node_id", ""),
            line_num=int(data.get("line_num", 1)),
            level=int(data.get("level", 1)),
            text=data.get("text", ""),
            token_count=int(data.get("token_count", 0)),
            cumulative_token_count=int(data.get("cumulative_token_count", 0)),
            summary=data.get("summary"),
            prefix_summary=data.get("prefix_summary"),
            nodes=children,
        )


@dataclass
class PageIndexDoc:
    doc_name: str
    line_count: int
    structure: List[PageIndexNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_name": self.doc_name,
            "line_count": self.line_count,
            "structure": [node.to_dict() for node in self.structure],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PageIndexDoc:
        return cls(
            doc_name=data.get("doc_name", "document.md"),
            line_count=int(data.get("line_count", 0)),
            structure=[PageIndexNode.from_dict(n) for n in data.get("structure", [])],
        )


@dataclass
class PageIndexSearchResult:
    doc_name: str
    leaf_node_id: str
    leaf_title: str
    citation_path: List[str]
    text: str
    summary: Optional[str] = None
    hops: int = 0
    reasoning_steps: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_name": self.doc_name,
            "leaf_node_id": self.leaf_node_id,
            "leaf_title": self.leaf_title,
            "citation_path": self.citation_path,
            "text": self.text,
            "summary": self.summary,
            "hops": self.hops,
            "reasoning_steps": self.reasoning_steps,
        }


class PageIndexEngine:
    """
    SPEC §27.1: Vectorless, reasoning-based hierarchical RAG indexer and search engine.
    """

    SWITCH_KEY = "locus.retrieval.pageindex.enabled"

    def __init__(self) -> None:
        self._doc_cache: Dict[str, PageIndexDoc] = {}

    def is_engine_enabled(self) -> bool:
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def count_tokens(self, text: str) -> int:
        """Estimate token count (approx 1.3 tokens per whitespace word)."""
        words = text.strip().split()
        return max(1, int(len(words) * 1.3)) if words else 0

    def extract_nodes_from_markdown(self, content: str) -> List[PageIndexNode]:
        """
        Step 1: Extract header nodes from markdown.
        - Matches regex #{1,6} headers
        - Matches **bold** standalone lines as level-1 headings
        - SKIPS content inside fenced code blocks (``` or ~~~).
        """
        nodes: List[PageIndexNode] = []
        lines = content.splitlines()

        in_code_block = False
        code_fence_pattern = re.compile(r"^\s*(```|~~~)")
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
        bold_pattern = re.compile(r"^\*\*([^*]+)\*\*\s*$")

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Check code block toggle
            if code_fence_pattern.match(stripped):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Check markdown headers #{1,6}
            h_match = header_pattern.match(stripped)
            if h_match:
                level = len(h_match.group(1))
                title = h_match.group(2).strip()
                nodes.append(PageIndexNode(title=title, line_num=idx, level=level))
                continue

            # Check standalone **bold** lines as level-1 headers
            b_match = bold_pattern.match(stripped)
            if b_match:
                title = b_match.group(1).strip()
                nodes.append(PageIndexNode(title=title, line_num=idx, level=1))
                continue

        # If no headings exist, create a root document node
        if not nodes:
            nodes.append(PageIndexNode(title="Document Root", line_num=1, level=1))

        return nodes

    def extract_node_text_content(
        self, nodes: List[PageIndexNode], content: str
    ) -> List[PageIndexNode]:
        """
        Step 2: Assign each node the text between its header line and the next header's line.
        """
        lines = content.splitlines()
        total_lines = len(lines)

        for i, node in enumerate(nodes):
            start_line = node.line_num  # header line index (1-based)
            if i + 1 < len(nodes):
                end_line = nodes[i + 1].line_num - 1
            else:
                end_line = total_lines

            # Extract lines between start_line and end_line
            # Start slice after the header line itself
            body_lines = lines[start_line:end_line]
            node.text = "\n".join(body_lines).strip()
            node.token_count = self.count_tokens(node.text)

        return nodes

    def tree_thinning_for_index(
        self, nodes: List[PageIndexNode], min_node_token: int = 50
    ) -> List[PageIndexNode]:
        """
        Step 4: Merge any node whose text is below min_node_token into the preceding node
        if it's not a root node, keeping the index compact.
        """
        if not nodes or min_node_token <= 0:
            return nodes

        thinned: List[PageIndexNode] = []
        for node in nodes:
            if not thinned:
                thinned.append(node)
                continue

            # If node text is tiny and not a top-level header, merge into previous
            if node.token_count < min_node_token and node.level > 1:
                prev = thinned[-1]
                merged_title = f"{prev.title} / {node.title}" if prev.title else node.title
                merged_text = f"{prev.text}\n\n### {node.title}\n{node.text}".strip()
                prev.text = merged_text
                prev.token_count = self.count_tokens(prev.text)
            else:
                thinned.append(node)

        return thinned

    def build_tree_from_nodes(self, nodes: List[PageIndexNode]) -> List[PageIndexNode]:
        """
        Step 5: Stack-based nesting by heading level; assigns node_id = zero-padded 4-digit counter.
        """
        root_nodes: List[PageIndexNode] = []
        stack: List[PageIndexNode] = []
        counter = 1

        for node in nodes:
            node.node_id = f"{counter:04d}"
            counter += 1

            while stack and stack[-1].level >= node.level:
                stack.pop()

            if not stack:
                root_nodes.append(node)
            else:
                stack[-1].nodes.append(node)

            stack.append(node)

        return root_nodes

    def update_cumulative_tokens(self, node: PageIndexNode) -> int:
        """
        Step 3: Cumulative token count per node including all descendants (computed bottom-up).
        """
        children_tokens = sum(self.update_cumulative_tokens(child) for child in node.nodes)
        node.cumulative_token_count = node.token_count + children_tokens
        return node.cumulative_token_count

    def generate_summaries_for_structure(
        self,
        nodes: List[PageIndexNode],
        summary_token_threshold: int = 200,
        summarizer: Optional[Callable[[str, str], str]] = None,
    ) -> None:
        """
        Step 6: Generate summaries.
        For nodes over threshold tokens or branch nodes:
        - leaves get `summary`
        - parent nodes get `prefix_summary`
        """
        for node in nodes:
            is_parent = len(node.nodes) > 0

            # Default heuristic summarizer: first 2 sentences or first 160 characters
            summary_text = ""
            if summarizer:
                summary_text = summarizer(node.title, node.text)
            else:
                # Heuristic summary
                lines = [ln.strip() for ln in node.text.splitlines() if ln.strip()]
                first_few = " ".join(lines[:3])
                summary_text = (first_few[:200] + "...") if len(first_few) > 200 else first_few
                if not summary_text:
                    summary_text = f"Section covering {node.title}"

            if is_parent:
                node.prefix_summary = summary_text
                # Recurse children
                self.generate_summaries_for_structure(
                    node.nodes,
                    summary_token_threshold=summary_token_threshold,
                    summarizer=summarizer,
                )
            else:
                node.summary = summary_text

    def md_to_tree(
        self,
        content: str,
        doc_name: str = "document.md",
        min_node_token: int = 50,
        summary_token_threshold: int = 200,
        summarizer: Optional[Callable[[str, str], str]] = None,
    ) -> PageIndexDoc:
        """
        SPEC §27.1: Pipeline converting markdown document into hierarchical PageIndex tree.
        """
        lines = content.splitlines()
        line_count = len(lines)

        # 1. Extract nodes
        raw_nodes = self.extract_nodes_from_markdown(content)

        # 2. Extract node text
        text_nodes = self.extract_node_text_content(raw_nodes, content)

        # 3. Thinning
        thinned_nodes = self.tree_thinning_for_index(text_nodes, min_node_token=min_node_token)

        # 4. Build hierarchical tree with zero-padded node_ids
        tree = self.build_tree_from_nodes(thinned_nodes)

        # 5. Cumulative token count bottom-up
        for root in tree:
            self.update_cumulative_tokens(root)

        # 6. Generate summaries
        self.generate_summaries_for_structure(
            tree,
            summary_token_threshold=summary_token_threshold,
            summarizer=summarizer,
        )

        doc = PageIndexDoc(doc_name=doc_name, line_count=line_count, structure=tree)
        self._doc_cache[doc_name] = doc
        return doc

    def _score_relevance(self, query: str, node: PageIndexNode) -> float:
        """Score candidate node against query terms."""
        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return 0.0

        title_words = set(re.findall(r"\w+", node.title.lower()))
        summary_words = set(
            re.findall(
                r"\w+",
                ((node.summary or "") + " " + (node.prefix_summary or "")).lower(),
            )
        )

        title_match = len(query_words.intersection(title_words)) * 3.0
        summary_match = len(query_words.intersection(summary_words)) * 1.5

        return title_match + summary_match

    def retrieve(
        self,
        query: str,
        doc: Optional[PageIndexDoc] = None,
        doc_name: Optional[str] = None,
        chooser: Optional[Callable[[str, List[PageIndexNode]], PageIndexNode]] = None,
    ) -> PageIndexSearchResult:
        """
        SPEC §27.1: Reasoning-based tree traversal search.
        Starts at root; presents child summaries; descends until leaf; returns full leaf text and citation path.
        """
        target_doc = doc or (self._doc_cache.get(doc_name or "") if doc_name else None)
        if not target_doc and self._doc_cache:
            target_doc = next(iter(self._doc_cache.values()))

        if not target_doc or not target_doc.structure:
            return PageIndexSearchResult(
                doc_name=doc_name or "empty",
                leaf_node_id="0000",
                leaf_title="Not Found",
                citation_path=[],
                text="",
                hops=0,
                reasoning_steps=[],
            )

        citation_path: List[str] = [target_doc.doc_name]
        current_candidates: List[PageIndexNode] = target_doc.structure
        hops = 0
        reasoning_steps: List[Dict[str, Any]] = []

        chosen: Optional[PageIndexNode] = None

        while current_candidates:
            hops += 1

            if chooser:
                chosen = chooser(query, current_candidates)
            else:
                # Rank candidates by relevance score
                ranked = sorted(
                    current_candidates,
                    key=lambda n: self._score_relevance(query, n),
                    reverse=True,
                )
                chosen = ranked[0]

            citation_path.append(chosen.title)
            reasoning_steps.append(
                {
                    "hop": hops,
                    "chosen_id": chosen.node_id,
                    "chosen_title": chosen.title,
                    "summary": chosen.summary or chosen.prefix_summary,
                    "level": chosen.level,
                }
            )

            # If chosen has children, descend further
            if chosen.nodes:
                current_candidates = chosen.nodes
            else:
                break

        assert chosen is not None

        return PageIndexSearchResult(
            doc_name=target_doc.doc_name,
            leaf_node_id=chosen.node_id,
            leaf_title=chosen.title,
            citation_path=citation_path,
            text=chosen.text,
            summary=chosen.summary,
            hops=hops,
            reasoning_steps=reasoning_steps,
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "cached_docs": list(self._doc_cache.keys()),
            "cached_doc_count": len(self._doc_cache),
            "engine_enabled": self.is_engine_enabled(),
        }
