"""
SPEC §29.5 lines 7613-7671: Connectivity Check Provider (F-0068 / US-106).
Modular off-switch:
- locus.connectivity_check.enabled (master toggle, returns 503 when off)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.diagnostics.connectivity import ConnectivityChecker

logger = logging.getLogger("locus.providers.connectivity")


class BaseConnectivityProvider(ABC):
    """
    Abstract contract for Connectivity Check Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def check_internet(
        self,
        timeout: Optional[float] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Check internet connectivity against probe endpoints."""

    @abstractmethod
    def check_services(
        self,
        services: List[Dict[str, Any]],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Check availability of specific internal/external services."""

    @abstractmethod
    def evaluate_gates(self) -> Dict[str, Any]:
        """Evaluate operational gates (model escalation, sync, web search, inner loop)."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get diagnostic status of connectivity checker subsystem."""


class DefaultConnectivityProvider(BaseConnectivityProvider):
    """
    Standard implementation wrapping ConnectivityChecker with configuration and 503 off-switch.
    """

    def __init__(
        self,
        checker: Optional[ConnectivityChecker] = None,
        config_prefix: str = "locus.connectivity_check",
    ) -> None:
        self._checker = checker or ConnectivityChecker()
        self._prefix = config_prefix

    @property
    def name(self) -> str:
        return "default_connectivity_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """
        Check master toggle `locus.connectivity_check.enabled`.
        """
        enabled = config.get(f"{self._prefix}.enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.lower() not in ("false", "0", "no", "off")
        elif not isinstance(enabled, bool):
            enabled = bool(enabled)

        if not enabled:
            return False, f"Feature {self._prefix} is disabled via configuration"
        return True, "Enabled"

    def check_internet(
        self,
        timeout: Optional[float] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        ok, reason = self.is_feature_enabled()
        if not ok:
            return {"error": reason, "status_code": 503, "online": False}

        cfg_timeout = float(config.get(f"{self._prefix}.timeout", 5.0))
        t = timeout if timeout is not None else cfg_timeout
        cfg_endpoints = config.get(f"{self._prefix}.endpoints", None)
        endpoints = list(cfg_endpoints) if isinstance(cfg_endpoints, list) else None

        result = self._checker.check_connectivity(timeout=t, endpoints=endpoints, force_refresh=force_refresh)
        return {
            "status": "success",
            "provider": self.name,
            **result,
        }

    def check_services(
        self,
        services: List[Dict[str, Any]],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        ok, reason = self.is_feature_enabled()
        if not ok:
            return {"error": reason, "status_code": 503, "services": {}}

        cfg_timeout = float(config.get(f"{self._prefix}.service_timeout", 3.0))
        t = timeout if timeout is not None else cfg_timeout
        results = self._checker.check_service_connectivity(services, timeout=t)
        return {
            "status": "success",
            "provider": self.name,
            "services": results,
        }

    def evaluate_gates(self) -> Dict[str, Any]:
        ok, reason = self.is_feature_enabled()
        if not ok:
            return {
                "error": reason,
                "status_code": 503,
                "skip_inner_loop_web": True,
                "force_local_model": True,
                "skip_vault_sync": True,
                "skip_web_search": True,
            }

        status = self.check_internet()
        online = bool(status.get("online", False))
        return {
            "status": "success",
            "online": online,
            "skip_inner_loop_web": self._checker.should_skip_inner_loop_web(online),
            "force_local_model": self._checker.should_force_local_model(online),
            "skip_vault_sync": self._checker.should_skip_vault_sync(online),
            "skip_web_search": self._checker.should_skip_web_search(online),
        }

    def get_status(self) -> Dict[str, Any]:
        ok, reason = self.is_feature_enabled()
        if not ok:
            return {"error": reason, "status_code": 503, "enabled": False}
        return {
            "status": "success",
            "provider": self.name,
            "enabled": True,
            "endpoints": list(self._checker.endpoints),
            "default_timeout": self._checker.default_timeout,
            "service_timeout": self._checker.service_timeout,
            "cache_ttl": self._checker.cache_ttl,
            "last_result": self._checker._last_result,
            "last_check_time": self._checker._last_check_time,
        }

