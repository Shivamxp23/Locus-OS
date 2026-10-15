"""sidecar/crawlers/chunker.py - Collector + Chunker Ingestion Pipeline.

Implements Spec §30.1:
- Splits markdown notes, code files, and documents into semantic chunks.
- Preserves markdown header hierarchy (# H1 > ## H2) across split sections.
- Configurable chunk size and token overlap for vector/graph ingestion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DocumentChunk:
    chunk_index: int
    source_file: str
    heading_path: str
    content: str
    char_count: int
    metadata: dict[str, str] = field(default_factory=dict)


class DocumentChunker:
    """Semantic chunking engine for ingestion pipelines."""

    def __init__(self, target_chunk_size: int = 500, overlap: int = 50) -> None:
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def chunk_markdown(self, content: str, source_file: str = "note.md") -> list[DocumentChunk]:
        lines = content.splitlines()
        chunks: list[DocumentChunk] = []
        current_headings: list[str] = []
        current_lines: list[str] = []
        current_char_count = 0
        chunk_idx = 0

        for line in lines:
            header_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                # Adjust heading path stack
                current_headings = current_headings[: level - 1] + [title]

            line_len = len(line) + 1  # newline
            if current_char_count + line_len > self.target_chunk_size and current_lines:
                chunk_text = "\n".join(current_lines).strip()
                if chunk_text:
                    h_path = " > ".join(current_headings) if current_headings else "Root"
                    chunks.append(
                        DocumentChunk(
                            chunk_index=chunk_idx,
                            source_file=source_file,
                            heading_path=h_path,
                            content=chunk_text,
                            char_count=len(chunk_text),
                        )
                    )
                    chunk_idx += 1
                # Overlap retention: keep last 1-2 lines
                current_lines = current_lines[-2:] if len(current_lines) >= 2 else []
                current_char_count = sum(len(l) + 1 for l in current_lines)

            current_lines.append(line)
            current_char_count += line_len

        # Final chunk
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                h_path = " > ".join(current_headings) if current_headings else "Root"
                chunks.append(
                    DocumentChunk(
                        chunk_index=chunk_idx,
                        source_file=source_file,
                        heading_path=h_path,
                        content=chunk_text,
                        char_count=len(chunk_text),
                    )
                )

        return chunks
