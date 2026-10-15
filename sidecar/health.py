"""sidecar/health.py - Health Probes and Heartbeat Monitoring.

Implements Spec §29.3:
- Liveness (/healthz) and readiness (/readyz) probe endpoints.
- Component health status registry: Sidecar, Database, Cache, Extension Bridge.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = "OK"
    last_check_timestamp: float = field(default_factory=time.time)


class HealthMonitor:
    """Monitors service liveness, readiness, and subsystem component statuses."""

    def __init__(self) -> None:
        self.components: dict[str, ComponentHealth] = {
            "sidecar": ComponentHealth(name="sidecar", status=HealthStatus.HEALTHY),
            "memory": ComponentHealth(name="memory", status=HealthStatus.HEALTHY),
            "storage": ComponentHealth(name="storage", status=HealthStatus.HEALTHY),
        }

    def register_status(
        self,
        component_name: str,
        status: HealthStatus,
        latency_ms: float = 0.0,
        message: str = "OK",
    ) -> None:
        self.components[component_name] = ComponentHealth(
            name=component_name,
            status=status,
            latency_ms=latency_ms,
            message=message,
            last_check_timestamp=time.time(),
        )

    def is_alive(self) -> bool:
        """Liveness check: Sidecar core process is functional."""
        return self.components.get("sidecar", ComponentHealth("sidecar", HealthStatus.UNHEALTHY)).status != HealthStatus.UNHEALTHY

    def is_ready(self) -> bool:
        """Readiness check: All critical components are healthy or degraded."""
        for comp in self.components.values():
            if comp.status == HealthStatus.UNHEALTHY:
                return False
        return True

    def get_health_report(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.is_ready() else "degraded",
            "is_alive": self.is_alive(),
            "is_ready": self.is_ready(),
            "components": {
                name: {
                    "status": c.status.value,
                    "latency_ms": c.latency_ms,
                    "message": c.message,
                }
                for name, c in self.components.items()
            },
        }
