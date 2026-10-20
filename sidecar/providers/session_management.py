"""
SPEC §5.1-5.8: Session Management Provider (F-0027).
Implements BaseSessionManagementProvider and DefaultSessionManagementProvider with modular off-switch.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.session_export import export_session
from sidecar.sessions.session_manager import (
    Session,
    SessionEntry,
    SessionManager,
    TelegramSessionBridge,
)

logger = logging.getLogger(__name__)


class BaseSessionManagementProvider(ABC):
    """
    SPEC §5.1-5.8 lines 5729-5799:
    Universal provider interface for Session Management & Telegram Bridge.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Session Management is enabled and available."""
        raise NotImplementedError

    @abstractmethod
    def create_session(
        self,
        session_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        fork_point: Optional[str] = None,
    ) -> Session:
        """Create a new JSONL v3 session."""
        raise NotImplementedError

    @abstractmethod
    def load_session(self, session_id: str) -> Session:
        """Load an existing session by ID."""
        raise NotImplementedError

    @abstractmethod
    def fork_session(
        self,
        parent_session_id: str,
        fork_point: str,
        summary: Optional[str] = None,
    ) -> Session:
        """Fork an existing session at a specific entry point."""
        raise NotImplementedError

    @abstractmethod
    def resume_session(self, session_id: str) -> Dict[str, Any]:
        """Replay messages and compacted context for session resume."""
        raise NotImplementedError

    @abstractmethod
    def export_session(
        self,
        session_id: str,
        format: str = "markdown",
    ) -> Dict[str, Any]:
        """Export session to Markdown, JSON, or JSONL."""
        raise NotImplementedError

    @abstractmethod
    def bridge_telegram(
        self,
        telegram_chat_id: str | int,
        user_message: str,
        responder: Optional[Callable[[str, Session], str]] = None,
        channel_provider: Any = None,
    ) -> Dict[str, Any]:
        """Bridge a Telegram message into a persistent session."""
        raise NotImplementedError


class DefaultSessionManagementProvider(BaseSessionManagementProvider):
    """
    Default session management provider backed by SessionManager and TelegramSessionBridge.
    Off-switch: locus.session_management.enabled (default: true) and locus.sessions.enabled (default: true).
    """

    def __init__(
        self,
        sessions_dir: Optional[Path | str] = None,
        db_path: Optional[Path | str] = None,
    ) -> None:
        self.session_manager = SessionManager(sessions_dir=sessions_dir)
        self.telegram_bridge = TelegramSessionBridge(
            session_manager=self.session_manager,
            db_path=db_path,
        )

    def is_available(self) -> bool:
        """SPEC §03 / §5.1-5.8: Modular on/off switch check."""
        sm_enabled = config.get("locus.session_management.enabled", True)
        s_enabled = config.get("locus.sessions.enabled", True)
        return bool(sm_enabled and s_enabled)

    def create_session(
        self,
        session_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        fork_point: Optional[str] = None,
    ) -> Session:
        if not self.is_available():
            raise RuntimeError("Session Management is disabled via locus.session_management.enabled")
        return self.session_manager.create_session(
            session_id=session_id,
            parent_id=parent_id,
            fork_point=fork_point,
        )

    def load_session(self, session_id: str) -> Session:
        if not self.is_available():
            raise RuntimeError("Session Management is disabled via locus.session_management.enabled")
        return self.session_manager.load_session(session_id)

    def fork_session(
        self,
        parent_session_id: str,
        fork_point: str,
        summary: Optional[str] = None,
    ) -> Session:
        if not self.is_available():
            raise RuntimeError("Session Management is disabled via locus.session_management.enabled")
        return self.session_manager.fork_session(
            parent_session_id=parent_session_id,
            fork_point=fork_point,
            summary=summary,
        )

    def resume_session(self, session_id: str) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Session Management is disabled via locus.session_management.enabled")
        return self.session_manager.resume_session(session_id)

    def export_session(
        self,
        session_id: str,
        format: str = "markdown",
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Session Management is disabled via locus.session_management.enabled")
        return export_session(
            session_id=session_id,
            format=format,
            sessions_dir=self.session_manager.sessions_dir,
        )

    def bridge_telegram(
        self,
        telegram_chat_id: str | int,
        user_message: str,
        responder: Optional[Callable[[str, Session], str]] = None,
        channel_provider: Any = None,
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Session Management is disabled via locus.session_management.enabled")
        return self.telegram_bridge.bridge_telegram_to_session(
            telegram_chat_id=telegram_chat_id,
            user_message=user_message,
            channel_provider=channel_provider,
            responder=responder,
        )


# Register default provider in universal registry
get_registry().register("session_management", "default", DefaultSessionManagementProvider)
get_registry().register("sessions", "default", DefaultSessionManagementProvider)
