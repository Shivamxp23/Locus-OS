"""sidecar/ingestion/chat_archiver.py - Ingestion package entrypoint for Chat Archiver.

Maps from Spec §19.3. Re-exports ChatArchiver, ChatArchiverProvider, and scheduling utilities.
"""

from sidecar.chat_archiver import (
    ChatArchiver,
    ChatArchiverProvider,
    ChatSession,
    ChatTurn,
    schedule_nightly_archival_job,
)

__all__ = [
    "ChatArchiver",
    "ChatArchiverProvider",
    "ChatSession",
    "ChatTurn",
    "schedule_nightly_archival_job",
]
