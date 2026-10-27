"""
SPEC §19.3 & §27.5: Ingestion Subsystem.
"""
from __future__ import annotations

from sidecar.ingestion.chat_archiver import ChatArchiverProvider
from sidecar.ingestion.rough_note_parser import (
    ParseRoughNoteResult,
    RoughNote,
    RoughNoteParser,
    slugify,
)

__all__ = [
    "ChatArchiverProvider",
    "ParseRoughNoteResult",
    "RoughNote",
    "RoughNoteParser",
    "slugify",
]
