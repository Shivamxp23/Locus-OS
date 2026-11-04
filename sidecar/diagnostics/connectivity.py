"""
SPEC §29.5 lines 7613-7671:
Connectivity Check (F-0068 / US-106).
Source: OpenHuman connectivity/checker.py + Locus-original.

Logic extracted:
    CONNECTIVITY CHECK:
        ENDPOINTS = [
            "https://httpbin.org/status/200",     // primary (neutral, fast)
            "https://1.1.1.1/cdn-cgi/trace",      // fallback (Cloudflare, minimal response)
        ]
        
        FUNCTION check_connectivity(timeout=5):
            FOR EACH endpoint IN ENDPOINTS:
                TRY:
                    response = http.head(endpoint, timeout=timeout)
                    IF response.status < 400:
                        RETURN { online: true, latency_ms: response.elapsed, endpoint: endpoint }
                CATCH timeout_or_error:
                    CONTINUE  // try next endpoint
            
            RETURN { online: false, latency_ms: null }
        
        FUNCTION check_service_connectivity(services):
            // Check specific service endpoints (Neo4j, PostgreSQL, sidecar)
            results = {}
            FOR EACH service IN services:
                TRY:
                    response = http.get(service.health_url, timeout=3)
                    results[service.name] = { healthy: response.status == 200 }
                CATCH:
                    results[service.name] = { healthy: false }
            RETURN results
        
        Used as gate before:
          - Inner Loop proactive passes (skip if offline)
          - Remote model API calls (fallback to local Ollama if offline)
          - Background vault sync (skip if offline)
          - Web search retrieval (skip, use local only)
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

logger = logging.getLogger("locus.diagnostics.connectivity")

DEFAULT_CONNECTIVITY_ENDPOINTS: List[str] = [
    "https://httpbin.org/status/200",
    "https://1.1.1.1/cdn-cgi/trace",
]


class ConnectivityChecker:
    """
    Lightweight internet connectivity and service health checker per SPEC §29.5.
    """

    def __init__(
        self,
        endpoints: Optional[List[str]] = None,
        default_timeout: float = 5.0,
        service_timeout: float = 3.0,
        cache_ttl_seconds: float = 5.0,
        http_head_fn: Optional[Callable[[str, float], Tuple[int, float]]] = None,
        http_get_fn: Optional[Callable[[str, float], Tuple[int, float]]] = None,
    ) -> None:
        self.endpoints = endpoints or list(DEFAULT_CONNECTIVITY_ENDPOINTS)
        self.default_timeout = default_timeout
        self.service_timeout = service_timeout
        self.cache_ttl = cache_ttl_seconds
        self._last_result: Optional[Dict[str, Any]] = None
        self._last_check_time: float = 0.0
        self._head_fn = http_head_fn or self._default_head
        self._get_fn = http_get_fn or self._default_get

    def _default_head(self, url: str, timeout: float) -> Tuple[int, float]:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Locus-Connectivity-Probe/1.0"})
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return int(resp.status), elapsed_ms

    def _default_get(self, url: str, timeout: float) -> Tuple[int, float]:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Locus-Service-Probe/1.0"})
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return int(resp.status), elapsed_ms

    def check_connectivity(
        self,
        timeout: Optional[float] = None,
        endpoints: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        SPEC §29.5 line 7631:
        FUNCTION check_connectivity(timeout=5):
            FOR EACH endpoint IN ENDPOINTS:
                TRY:
                    response = http.head(endpoint, timeout=timeout)
                    IF response.status < 400:
                        RETURN { online: true, latency_ms: response.elapsed, endpoint: endpoint }
                CATCH timeout_or_error:
                    CONTINUE
            RETURN { online: false, latency_ms: null }
        """
        now = time.time()
        if not force_refresh and self._last_result is not None and (now - self._last_check_time) < self.cache_ttl:
            return {**self._last_result, "cached": True}

        t = timeout if timeout is not None else self.default_timeout
        targets = endpoints or self.endpoints

        for endpoint in targets:
            try:
                status, elapsed = self._head_fn(endpoint, t)
                if status < 400:
                    res = {
                        "online": True,
                        "latency_ms": round(elapsed, 2),
                        "endpoint": endpoint,
                        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                        "cached": False,
                    }
                    self._last_result = res
                    self._last_check_time = now
                    return res
            except Exception as e:
                logger.debug("Connectivity check failed for %s: %s", endpoint, e)
                continue

        res = {
            "online": False,
            "latency_ms": None,
            "endpoint": None,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            "cached": False,
        }
        self._last_result = res
        self._last_check_time = now
        return res

    def check_service_connectivity(
        self,
        services: List[Dict[str, Any]],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        SPEC §29.5 line 7642:
        FUNCTION check_service_connectivity(services):
            results = {}
            FOR EACH service IN services:
                TRY:
                    response = http.get(service.health_url, timeout=3)
                    results[service.name] = { healthy: response.status == 200 }
                CATCH:
                    results[service.name] = { healthy: false }
            RETURN results
        """
        t = timeout if timeout is not None else self.service_timeout
        results: Dict[str, Any] = {}

        for s in services:
            s_name = str(s.get("name") or "unknown")
            health_url = s.get("health_url") or s.get("url")
            if not health_url:
                results[s_name] = {"healthy": False, "error": "missing_health_url"}
                continue

            try:
                status, elapsed = self._get_fn(str(health_url), t)
                results[s_name] = {
                    "healthy": bool(status == 200),
                    "status_code": status,
                    "latency_ms": round(elapsed, 2),
                }
            except Exception as e:
                logger.debug("Service connectivity check failed for %s (%s): %s", s_name, health_url, e)
                results[s_name] = {"healthy": False, "error": str(e)}

        return results

    # Gate helpers per SPEC §29.5 line 7660
    def should_skip_inner_loop_web(self, is_online: Optional[bool] = None, online: Optional[bool] = None) -> bool:
        """Skip Inner Loop proactive web-dependent passes if offline."""
        val = is_online if is_online is not None else online
        active = val if val is not None else self.check_connectivity()["online"]
        return not active

    def should_force_local_model(self, is_online: Optional[bool] = None, online: Optional[bool] = None) -> bool:
        """Force fallback to local Ollama if remote APIs cannot be reached."""
        val = is_online if is_online is not None else online
        active = val if val is not None else self.check_connectivity()["online"]
        return not active

    def should_skip_vault_sync(self, is_online: Optional[bool] = None, online: Optional[bool] = None) -> bool:
        """Skip background vault remote sync if offline."""
        val = is_online if is_online is not None else online
        active = val if val is not None else self.check_connectivity()["online"]
        return not active

    def should_skip_web_search(self, is_online: Optional[bool] = None, online: Optional[bool] = None) -> bool:
        """Skip web search retrieval and use local data only when offline."""
        val = is_online if is_online is not None else online
        active = val if val is not None else self.check_connectivity()["online"]
        return not active
