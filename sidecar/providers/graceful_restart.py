"""
SPEC §17.10 lines 3855-3926:
Graceful Restart Provider Interface and Implementation (F-0047 / US-80).

Implements BaseGracefulRestartProvider and DefaultGracefulRestartProvider with modular off-switches:
- locus.graceful_restart.enabled
- locus.gateway.graceful_restart.enabled
Returning HTTP 503 when disabled.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import sidecar.config as config
from sidecar.gateway.lifecycle import (
    ForensicRecord,
    GatewayLifecycleManager,
    SessionSnapshot,
)

logger = logging.getLogger(__name__)


class BaseGracefulRestartProvider(ABC):
    """
    SPEC §17.10: Provider Interface: GatewayLifecycleProvider / GracefulRestartProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if graceful restart subsystem is enabled."""
        raise NotImplementedError

    @abstractmethod
    def initiate_shutdown(
        self,
        signal_type: str = "SIGTERM",
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Initiate graceful drain and shutdown sequence."""
        raise NotImplementedError

    @abstractmethod
    def drain_connections(self) -> int:
        """Drain in-flight connections."""
        raise NotImplementedError

    @abstractmethod
    def snapshot_sessions(self) -> List[str]:
        """Snapshot active in-memory sessions to disk."""
        raise NotImplementedError

    @abstractmethod
    def recover_sessions(self) -> List[Dict[str, Any]]:
        """Recover previously saved sessions from recovery directory."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get diagnostic status of gateway lifecycle."""
        raise NotImplementedError


class DefaultGracefulRestartProvider(BaseGracefulRestartProvider):
    """
    SPEC §17.10: Default implementation of GracefulRestartProvider.
    Wraps GatewayLifecycleManager with modular off-switch enforcement.
    """

    def __init__(self, manager: Optional[GatewayLifecycleManager] = None) -> None:
        self.manager = manager or GatewayLifecycleManager()

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.graceful_restart.enabled
        - locus.gateway.graceful_restart.enabled
        """
        v1 = config.get("locus.graceful_restart.enabled")
        if v1 is not None and not config.is_enabled("locus.graceful_restart.enabled"):
            return False

        v2 = config.get("locus.gateway.graceful_restart.enabled")
        if v2 is not None and not config.is_enabled("locus.gateway.graceful_restart.enabled"):
            return False

        return True

    def initiate_shutdown(
        self,
        signal_type: str = "SIGTERM",
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Graceful restart is disabled by modular off-switch.")
        return self.manager.handle_shutdown_signal(signal_type=signal_type, dry_run=dry_run)

    def drain_connections(self) -> int:
        if not self.is_available():
            raise RuntimeError("Graceful restart is disabled by modular off-switch.")
        return self.manager.drain_connections()

    def snapshot_sessions(self) -> List[str]:
        if not self.is_available():
            raise RuntimeError("Graceful restart is disabled by modular off-switch.")
        return self.manager.snapshot_sessions()

    def recover_sessions(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("Graceful restart is disabled by modular off-switch.")
        snaps = self.manager.recover_sessions()
        return [s.to_dict() for s in snaps]

    def get_status(self) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("Graceful restart is disabled by modular off-switch.")
        return {
            "available": True,
            **self.manager.get_status(),
        }
