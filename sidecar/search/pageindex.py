"""Locus Vectorless Retrieval (PageIndex) Engine (§27.1).

Fast hierarchical table-of-contents and page tree indexer that retrieves document
sections using structural headers, keywords, and metadata without dense vector embeddings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PageIndexEntry:
    doc_id: str
    section_title: str
    level: int  # Header level: 1 = H1, 2 = H2, etc.
    start_char: int
    end_char: int
    summary: str
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "section_title": self.section_title,
            "level": self.level,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "summary": self.summary,
            "keywords": self.keywords,
        }


class PageIndexEngine:
    """Indexes and queries documents through hierarchical structural metadata."""

    def __init__(self):
        self.entries: Dict[str, List[PageIndexEntry]] = {}

    def index_markdown(self, doc_id: str, markdown_text: str) -> List[PageIndexEntry]:
        lines = markdown_text.splitlines()
        entries: List[PageIndexEntry] = []
        char_offset = 0

        current_header: Optional[str] = None
        current_level: int = 1
        current_start: int = 0
        current_body_lines: List[str] = []

        header_regex = re.compile(r"^(#{1,6})\s+(.*)$")

        for line in lines:
            line_len = len(line) + 1  # include newline
            m = header_regex.match(line)
            if m:
                if current_header is not None:
                    summary = " ".join(current_body_lines)[:120]
                    words = [w.lower() for w in re.findall(r"\b\w{3,}\b", summary)]
                    entries.append(
                        PageIndexEntry(
                            doc_id=doc_id,
                            section_title=current_header,
                            level=current_level,
                            start_char=current_start,
                            end_char=char_offset,
                            summary=summary,
                            keywords=list(set(words))[:10],
                        )
                    )
                current_level = len(m.group(1))
                current_header = m.group(2).strip()
                current_start = char_offset
                current_body_lines = []
            else:
                current_body_lines.append(line)

            char_offset += line_len

        # Flush final section
        if current_header is not None:
            summary = " ".join(current_body_lines)[:120]
            words = [w.lower() for w in re.findall(r"\b\w{3,}\b", summary)]
            entries.append(
                PageIndexEntry(
                    doc_id=doc_id,
                    section_title=current_header,
                    level=current_level,
                    start_char=current_start,
                    end_char=char_offset,
                    summary=summary,
                    keywords=list(set(words))[:10],
                )
            )

        self.entries[doc_id] = entries
        return entries

    def search_index(self, query: str, limit: int = 5) -> List[PageIndexEntry]:
        query_words = set(query.lower().split())
        scored: List[tuple[float, PageIndexEntry]] = []

        for doc_entries in self.entries.values():
            for e in doc_entries:
                score = 0.0
                title_words = set(e.section_title.lower().split())
                score += len(query_words.intersection(title_words)) * 3.0
                score += len(query_words.intersection(set(e.keywords))) * 1.5
                if query.lower() in e.summary.lower():
                    score += 2.0
                if score > 0:
                    scored.append((score, e))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]
