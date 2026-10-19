"""
SPEC §03 / §08 / F-0083 / US-04: ChannelProvider interface.
Universal provider pattern for communication channels (Telegram, Discord, Slack, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseChannelProvider(ABC):
    """Abstract base class for all Locus channel providers."""

    @abstractmethod
    def initialize(self, options: dict[str, Any] | None = None) -> None:
        """Initialize the channel provider with options."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Cleanly shutdown the channel provider."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """
        Check health of the channel provider.
        Returns dict with status ('ok' | 'degraded' | 'error'), latency_ms, error (if any).
        """
        pass

    @abstractmethod
    def send_message(self, target: str | int, text: str) -> bool:
        """Send a message to a specific user/channel target."""
        pass
