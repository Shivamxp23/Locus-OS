"""
Context Compaction module re-exports (SPEC §4.16 / F-0110).
"""
from sidecar.compaction.context_engine import (
    CompactionLock,
    DefaultCompactionProvider,
    DefaultContextEngine,
    HermesContextCompressor,
    default_auxiliary_summarize,
    format_messages_for_summary,
)

__all__ = [
    "CompactionLock",
    "DefaultCompactionProvider",
    "DefaultContextEngine",
    "HermesContextCompressor",
    "default_auxiliary_summarize",
    "format_messages_for_summary",
]
