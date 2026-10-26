"""
SPEC §7.1-7.9: TUI / Dashboard Provider Interface and Implementation (F-0030).
Implements BaseTUIDashboardProvider and DefaultTUIDashboardProvider with modular off-switch.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Optional

import sidecar.config as config
from sidecar.display.dashboard import DashboardState, TUIDashboardEngine
from sidecar.registry import get_registry

logger = logging.getLogger(__name__)


class BaseTUIDashboardProvider(ABC):
    """
    SPEC §7.1-7.9 lines 5808-5810:
    Provider Interface: TUIProvider / TUIDashboardProvider
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if TUI dashboard provider is enabled."""
        raise NotImplementedError

    @abstractmethod
    def get_dashboard_state(self) -> DashboardState:
        """Retrieve the current dashboard metrics state."""
        raise NotImplementedError

    @abstractmethod
    def format_footer(self, width: int = 80) -> str:
        """Format 3-column footer widget layout."""
        raise NotImplementedError

    @abstractmethod
    def format_dashboard(self, width: int = 80) -> str:
        """Format full status monitor dashboard panel."""
        raise NotImplementedError


class DefaultTUIDashboardProvider(BaseTUIDashboardProvider):
    """
    Default implementation of TUIDashboardProvider.
    Off-switch: locus.tui_dashboard.enabled (default: true).
    Off-state: TUI dashboard endpoints return 503; footer formatting returns empty string.
    """

    def __init__(self, engine: Optional[TUIDashboardEngine] = None) -> None:
        self.engine = engine or TUIDashboardEngine()

    def is_available(self) -> bool:
        """SPEC §7.1-7.9: Modular off-switch check."""
        return bool(config.get("locus.tui_dashboard.enabled", True))

    def get_dashboard_state(self) -> DashboardState:
        if not self.is_available():
            return DashboardState(dcs=0.0, mode="OFF", active_faction="None", sidecar_latency_ms=0)
        return self.engine.get_state()

    def format_footer(self, width: int = 80) -> str:
        if not self.is_available():
            return ""
        return self.engine.format_footer(width=width)

    def format_dashboard(self, width: int = 80) -> str:
        if not self.is_available():
            return ""
        return self.engine.format_dashboard(width=width)


# Register default provider in universal registry
get_registry().register("tui_dashboard", "default_tui_dashboard", DefaultTUIDashboardProvider)
get_registry().register("tui_dashboard", "default", DefaultTUIDashboardProvider)
