"""
SPEC §5.1-5.8: Session Management & Telegram Bridge (F-0027).
Package re-exports for session management, tree structures, and Telegram bridge.
"""
from __future__ import annotations

from sidecar.sessions.session_manager import (
    VALID_ENTRY_TYPES,
    Session,
    SessionEntry,
    SessionManager,
    TelegramSessionBridge,
)

__all__ = [
    "VALID_ENTRY_TYPES",
    "SessionEntry",
    "Session",
    "SessionManager",
    "TelegramSessionBridge",
]
