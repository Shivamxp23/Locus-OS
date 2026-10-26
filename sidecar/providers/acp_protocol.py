"""
SPEC §9.4 lines 6057-6142:
ACP Protocol Provider Interface and Implementation (F-0033 / US-64).
Implements BaseACPClientProvider and DefaultACPClientProvider with modular off-switch.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

from sidecar.acp_server import ACPClient, ACPEvent, ACPServer
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseACPClientProvider(ABC):
    """
    SPEC §9.4: Provider Interface: ACPClientProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if ACP Protocol is enabled."""
        raise NotImplementedError

    @abstractmethod
    def initialize(self, client_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform capability negotiation handshake."""
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        target_agent_id: str,
        prompt: str,
        tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Dispatch task to target agent via ACP."""
        raise NotImplementedError

    @abstractmethod
    def cancel(self, request_id: int) -> Dict[str, Any]:
        """Send request cancellation notification."""
        raise NotImplementedError


class DefaultACPClientProvider(BaseACPClientProvider):
    """
    Default implementation of ACPClientProvider.
    Off-switch: locus.acp_protocol.enabled (default: true).
    Secondary off-switch: locus.protocols.acp.enabled (default: true).
    Off-state: endpoints return HTTP 503.
    """

    def __init__(self, client: Optional[ACPClient] = None) -> None:
        self.client = client or ACPClient()

    def is_available(self) -> bool:
        """SPEC §9.4: Modular off-switch check."""
        val1 = config.get("locus.acp_protocol.enabled")
        if val1 is not None and not config.is_enabled("locus.acp_protocol.enabled"):
            return False
        val2 = config.get("locus.protocols.acp.enabled")
        if val2 is not None and not config.is_enabled("locus.protocols.acp.enabled"):
            return False
        return True

    def initialize(self, client_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("ACPClientProvider is disabled via config")
        return self.client.initialize(client_info=client_info)

    def execute(
        self,
        target_agent_id: str,
        prompt: str,
        tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("ACPClientProvider is disabled via config")
        events = self.client.dispatch_agent_task(target_agent_id, prompt, tools)
        return {
            "status": "completed",
            "target": target_agent_id,
            "session_id": self.client.session_id,
            "events": [e.to_dict() for e in events],
        }

    def cancel(self, request_id: int) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("ACPClientProvider is disabled via config")
        return self.client.cancel_request(request_id)
