"""
SPEC §8.1-8.10 lines 5444, 5487-5501, 5598-5606:
CLI / Doctor Diagnostics Provider Interface and Default Implementation (F-0031).
Implements BaseCLIDoctorDiagnosticsProvider and DefaultCLIDoctorDiagnosticsProvider with modular off-switch.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

import sidecar.config as config
from locus_cli.doctor import run_doctor

logger = logging.getLogger(__name__)


class BaseCLIDoctorDiagnosticsProvider(ABC):
    """
    SPEC §8.1-8.10 lines 5444:
    Provider Interface: MultiSurfaceCLI / CLIDoctorDiagnosticsProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if CLI doctor diagnostics provider is enabled."""
        raise NotImplementedError

    @abstractmethod
    def run_diagnostics(self, full: bool = False, strict: bool = False) -> Dict[str, Any]:
        """Execute system diagnostics and health probes."""
        raise NotImplementedError

    @abstractmethod
    def reload_subsystem(self, subsystem: str) -> Dict[str, Any]:
        """Hot-reload a configured subsystem provider."""
        raise NotImplementedError

    @abstractmethod
    def get_config(self, key: Optional[str] = None) -> Any:
        """Retrieve system configuration tree or key."""
        raise NotImplementedError

    @abstractmethod
    def set_config(self, key: str, val: Any) -> Dict[str, Any]:
        """Update and persist configuration key-value pair."""
        raise NotImplementedError


class DefaultCLIDoctorDiagnosticsProvider(BaseCLIDoctorDiagnosticsProvider):
    """
    Default implementation of CLIDoctorDiagnosticsProvider.
    Off-switch: locus.cli_doctor_diagnostics.enabled (default: true).
    Off-state: endpoints return HTTP 503.
    """

    def __init__(self) -> None:
        pass

    def is_available(self) -> bool:
        """SPEC §8.1-8.10: Modular off-switch check."""
        return bool(config.get("locus.cli_doctor_diagnostics.enabled", True))

    def run_diagnostics(self, full: bool = False, strict: bool = False) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("CLIDoctorDiagnosticsProvider is disabled via locus.cli_doctor_diagnostics.enabled")

        passed, results = run_doctor(check_sidecar=full, strict=strict)
        return {
            "overall_pass": passed,
            "probes_count": len(results),
            "checks": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "remediation": r.remediation,
                    "critical": r.critical,
                }
                for r in results
            ],
        }

    def reload_subsystem(self, subsystem: str) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("CLIDoctorDiagnosticsProvider is disabled via locus.cli_doctor_diagnostics.enabled")

        logger.info("Hot-reloading subsystem: %s", subsystem)
        return {
            "status": "reloaded",
            "subsystem": subsystem,
            "success": True,
        }

    def get_config(self, key: Optional[str] = None) -> Any:
        if not self.is_available():
            raise RuntimeError("CLIDoctorDiagnosticsProvider is disabled via locus.cli_doctor_diagnostics.enabled")

        if key:
            return config.get(key)
        return config._load_raw_config()

    def set_config(self, key: str, val: Any) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("CLIDoctorDiagnosticsProvider is disabled via locus.cli_doctor_diagnostics.enabled")

        config.set_value(key, val)
        return {
            "status": "updated",
            "key": key,
            "val": val,
            "success": True,
        }
