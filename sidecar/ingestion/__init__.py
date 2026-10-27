"""
SPEC §19.3, §27.5, & §27.6: Ingestion Subsystem.
"""
from __future__ import annotations

from sidecar.ingestion.chat_archiver import ChatArchiverProvider
from sidecar.ingestion.rough_note_parser import (
    ParseRoughNoteResult,
    RoughNote,
    RoughNoteParser,
    slugify,
)
from sidecar.ingestion.link_logger import (
    LinkDumpLogger,
    LinkResourceSummary,
    ProcessLinkDumpResult,
    extract_readable_text,
)

__all__ = [
    "ChatArchiverProvider",
    "ParseRoughNoteResult",
    "RoughNote",
    "RoughNoteParser",
    "LinkDumpLogger",
    "LinkResourceSummary",
    "ProcessLinkDumpResult",
    "extract_readable_text",
    "slugify",
]
