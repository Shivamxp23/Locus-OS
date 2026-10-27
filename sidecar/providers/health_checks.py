"""
SPEC §29.3 lines 7501-7530: Health Checks Provider (F-0066 / US-104).
Modular off-switches:
- locus.health_checks.enabled (master toggle, returns 503 when off)
- locus.diagnostics.health_checks.enabled (subsystem toggle)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Optional, Tuple

from sidecar import config
from sidecar.diagnostics.health_checker import HealthChecker, SystemHealthReport

logger = logging.getLogger("locus.providers.health_checks")


class BaseHealthChecksProvider(ABC):
    """
    Abstract contract for Health Checks Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def health_check_all(self, providers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute health checks across all registered providers."""

    @abstractmethod
    def get_report(self, providers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get aggregate system health report."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Self-diagnostic probe."""


class DefaultHealthChecksProvider(BaseHealthChecksProvider):
    """
    Default provider wrapping HealthChecker with modular off-switch enforcement.
    """

    FEATURE_SWITCH = "locus.health_checks.enabled"

    def __init__(self, checker: Optional[HealthChecker] = None) -> None:
        self._checker = checker or HealthChecker()

    @property
    def name(self) -> str:
        return "default_health_checks"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Modular off-switch check: locus.health_checks.enabled."""
        val = config.get(self.FEATURE_SWITCH)
        if val is not None and not config.is_enabled(self.FEATURE_SWITCH):
            return False, self.FEATURE_SWITCH
        return True, ""

    def health_check_all(self, providers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute health check across all providers or return 503 if disabled."""
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": f"Health checks feature is disabled by {switch}",
                "disabled": switch,
            }
        results = self._checker.health_check_all(providers=providers)
        return {
            "status": "ok",
            "results": results,
            "count": len(results),
        }

    def get_report(self, providers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Aggregate report or 503 if disabled."""
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": f"Health checks feature is disabled by {switch}",
                "disabled": switch,
            }
        report = self._checker.build_report(providers=providers)
        return report.to_dict()

    def get_status(self) -> Dict[str, Any]:
        """Diagnostic status or 503 if disabled."""
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": f"Health checks feature is disabled by {switch}",
                "disabled": switch,
            }
        return {
            "name": self.name,
            "feature_enabled": True,
            "subsystem_enabled": self._checker.is_enabled(),
            "switch": self.FEATURE_SWITCH,
            "subsystem_switch": self._checker.SWITCH_KEY,
        }

    def health_check(self) -> Dict[str, Any]:
        """Self-diagnostic probe."""
        enabled, _ = self.is_feature_enabled()
        return {
            "status": "ok" if enabled else "disabled",
            "provider": self.name,
            "subsystem_active": self._checker.is_enabled(),
        }
