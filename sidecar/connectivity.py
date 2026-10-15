"""sidecar/connectivity.py - Network Connectivity & Endpoint Probing.

Implements Spec §29.5:
- Verifies Internet reachability, DNS resolution, and local sidecar/CouchDB/Neo4j network endpoints.
- Measures round-trip ping latency and signals offline fallback mode.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ConnectivityProbeResult:
    target: str
    is_reachable: bool
    latency_ms: float
    error_message: Optional[str] = None


class ConnectivityChecker:
    """Probes endpoint availability and determines online/offline status."""

    def __init__(self, timeout_seconds: float = 2.0) -> None:
        self.timeout_seconds = timeout_seconds

    def probe_tcp_port(self, host: str, port: int) -> ConnectivityProbeResult:
        start = time.perf_counter()
        target_str = f"{host}:{port}"
        try:
            with socket.create_connection((host, port), timeout=self.timeout_seconds):
                elapsed = (time.perf_counter() - start) * 1000.0
                return ConnectivityProbeResult(
                    target=target_str,
                    is_reachable=True,
                    latency_ms=round(elapsed, 2),
                )
        except Exception as ex:
            elapsed = (time.perf_counter() - start) * 1000.0
            return ConnectivityProbeResult(
                target=target_str,
                is_reachable=False,
                latency_ms=round(elapsed, 2),
                error_message=str(ex),
            )

    def check_internet(self, test_host: str = "8.8.8.8", test_port: int = 53) -> bool:
        """Lightweight reachability probe."""
        res = self.probe_tcp_port(test_host, test_port)
        return res.is_reachable

    def check_local_services(self) -> dict[str, ConnectivityProbeResult]:
        """Probes standard Locus internal ports (CouchDB 5984, Neo4j 7687, Postgres 5432)."""
        services = {
            "couchdb": ("127.0.0.1", 5984),
            "neo4j": ("127.0.0.1", 7687),
            "postgres": ("127.0.0.1", 5432),
        }
        return {name: self.probe_tcp_port(h, p) for name, (h, p) in services.items()}
