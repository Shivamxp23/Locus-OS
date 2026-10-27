"""
SPEC §29.3 lines 7501-7530:
Health Checks diagnostic engine (F-0066 / US-104).
Source: Hermes gateway/status.py + OpenHuman health

Logic extracted:
    HEALTH CHECKS:
        FUNCTION health_check_all():
            results = {}
            FOR EACH provider IN all_registered_providers:
                start = now()
                try:
                    status = provider.health_check()
                    results[provider.name] = { status: "ok", latency_ms: now()-start, details: status }
                except error:
                    results[provider.name] = { status: "error", latency_ms: now()-start, error: str(error) }
            RETURN results

Locus adaptation:
    - Component: locus-extension/src/health/
    - Called by locus doctor CLI command and sidecar diagnostics
    - Off-switch: locus.diagnostics.health_checks.enabled
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.diagnostics.health_checker")


@dataclass
class ProviderHealthResult:
    """Diagnostic outcome for a single provider probe."""
    name: str
    status: str  # "ok" or "error"
    latency_ms: float
    details: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
        }
        if self.details is not None:
            d["details"] = self.details
        if self.error is not None:
            d["error"] = self.error
        return d


@dataclass
class SystemHealthReport:
    """Aggregate health summary across all probed providers."""
    overall_status: str  # "ok", "degraded", "error"
    timestamp: float
    total_providers: int
    healthy_providers: int
    failing_providers: int
    results: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "timestamp": self.timestamp,
            "total_providers": self.total_providers,
            "healthy_providers": self.healthy_providers,
            "failing_providers": self.failing_providers,
            "results": self.results,
        }


class HealthChecker:
    """
    SPEC §29.3: Centralized health check executor across all registered providers
    and diagnostic subsystems.
    """

    SWITCH_KEY = "locus.diagnostics.health_checks.enabled"

    def __init__(self) -> None:
        pass

    def is_enabled(self) -> bool:
        """Check subsystem toggle."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def check_provider(self, name: str, provider: Any) -> ProviderHealthResult:
        """
        Probe a single provider with latency measurement and exception containment.
        Supports provider.health_check(), provider.get_status(), or callable probe.
        """
        start = time.perf_counter()
        try:
            if hasattr(provider, "health_check") and callable(provider.health_check):
                status = provider.health_check()
            elif hasattr(provider, "get_status") and callable(provider.get_status):
                status = provider.get_status()
            elif callable(provider):
                status = provider()
            else:
                status = {"status": "present", "type": type(provider).__name__}

            latency_ms = (time.perf_counter() - start) * 1000.0
            return ProviderHealthResult(
                name=name,
                status="ok",
                latency_ms=latency_ms,
                details=status,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000.0
            logger.warning("Provider %s health check failed: %s", name, exc)
            return ProviderHealthResult(
                name=name,
                status="error",
                latency_ms=latency_ms,
                error=str(exc),
            )

    def health_check_all(
        self,
        providers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        SPEC §29.3 lines 7512-7521:
        FUNCTION health_check_all():
            results = {}
            FOR EACH provider IN all_registered_providers:
                start = now()
                try:
                    status = provider.health_check()
                    results[provider.name] = { status: "ok", latency_ms: now()-start, details: status }
                except error:
                    results[provider.name] = { status: "error", latency_ms: now()-start, error: str(error) }
            RETURN results
        """
        if not self.is_enabled():
            return {
                "_subsystem": {
                    "status": "disabled",
                    "latency_ms": 0.0,
                    "details": "Health checks diagnostic engine is disabled",
                }
            }

        targets: Dict[str, Any] = {}
        if providers is not None:
            targets = dict(providers)
        else:
            try:
                from sidecar.providers.registry import default_registry
                targets = default_registry.list_active_providers()
            except Exception:
                targets = {}

        results: Dict[str, Dict[str, Any]] = {}
        for name, prov in targets.items():
            probe_res = self.check_provider(name, prov)
            results[name] = probe_res.to_dict()

        return results

    def build_report(
        self,
        providers: Optional[Dict[str, Any]] = None,
    ) -> SystemHealthReport:
        """Produce an aggregated SystemHealthReport summarizing provider statuses."""
        res_dict = self.health_check_all(providers=providers)
        total = len(res_dict)
        healthy = sum(1 for v in res_dict.values() if v.get("status") == "ok")
        failing = sum(1 for v in res_dict.values() if v.get("status") == "error")

        if failing == 0:
            overall = "ok"
        elif healthy > 0:
            overall = "degraded"
        else:
            overall = "error" if total > 0 else "ok"

        return SystemHealthReport(
            overall_status=overall,
            timestamp=time.time(),
            total_providers=total,
            healthy_providers=healthy,
            failing_providers=failing,
            results=res_dict,
        )


def health_check_all(
    providers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Functional convenience entrypoint per SPEC §29.3 line 7512."""
    checker = HealthChecker()
    return checker.health_check_all(providers=providers)
