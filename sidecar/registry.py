"""
sidecar/registry.py - Universal Provider Registry for Locus OS.

Implements the Universal Provider Pattern (modularity spec):
- registry.register(interface, name, provider, is_default=False)
- registry.get(interface, name=None, config_key=None)
- Dynamic provider swap driven by config: locus.<area>.<feature>.provider
- Off behavior:
  - HTTP routes return 503 {"disabled": "<config key>"}
  - Tools from disabled features are suppressed
  - Jobs from disabled features are suppressed
- Health checks: provider.health_check() -> {status, latency_ms, error}
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from sidecar.config import get as config_get, is_enabled as config_is_enabled


class FeatureDisabledError(Exception):
    """Raised when attempting to access a disabled feature provider directly."""

    def __init__(self, config_key: str):
        super().__init__(f"Feature is disabled by config: {config_key}")
        self.config_key = config_key


class BaseProvider:
    """Base interface for all Locus providers."""

    name: str = "base"

    def initialize(self, options: Optional[dict[str, Any]] = None) -> None:
        """Initialize provider with options from config."""
        pass

    def shutdown(self) -> None:
        """Clean up provider resources."""
        pass

    def health_check(self) -> dict[str, Any]:
        """
        Check provider health.
        Must return a dict with at least 'status' ('ok', 'degraded', or 'down'),
        'latency_ms' (float), and 'error' (Optional[str]).
        """
        return {"status": "ok", "latency_ms": 0.0, "error": None}


class ProviderRegistry:
    """Central registry for interfaces, active providers, tools, and scheduled jobs."""

    def __init__(self) -> None:
        self._providers: dict[tuple[str, str], Any] = {}
        self._defaults: dict[str, str] = {}
        self._tools: dict[str, list[dict[str, Any]]] = {}
        self._jobs: dict[str, list[dict[str, Any]]] = {}

    def clear(self) -> None:
        """Reset registry contents (useful in testing)."""
        self._providers.clear()
        self._defaults.clear()
        self._tools.clear()
        self._jobs.clear()

    def register(
        self,
        interface: str,
        name: str,
        provider: Any,
        is_default: bool = False,
    ) -> None:
        """
        Register a provider implementation under an interface name.
        `provider` may be a class, a factory function, or an instance.
        """
        key = (interface, name)
        self._providers[key] = provider
        if is_default or interface not in self._defaults:
            self._defaults[interface] = name

    def get(
        self,
        interface: str,
        name: Optional[str] = None,
        config_key: Optional[str] = None,
        custom_config_path: Any = None,
    ) -> Any:
        """
        Resolve active provider instance.
        If config_key is given and disabled: raises FeatureDisabledError.
        If name is not specified: checks config_key.provider, then falls back to interface default.
        """
        if config_key is not None:
            enabled_key = config_key if config_key.endswith(".enabled") else f"{config_key}.enabled"
            if not config_is_enabled(enabled_key, custom_path=custom_config_path):
                raise FeatureDisabledError(enabled_key)

        provider_name = name
        if provider_name is None and config_key is not None:
            base_key = config_key[:-8] if config_key.endswith(".enabled") else config_key
            provider_name = config_get(f"{base_key}.provider", custom_path=custom_config_path)

        if provider_name is None:
            provider_name = self._defaults.get(interface)

        if provider_name is None:
            raise KeyError(f"No default provider registered for interface '{interface}'")

        key = (interface, provider_name)
        if key not in self._providers:
            raise KeyError(f"Provider '{provider_name}' not registered for interface '{interface}'")

        entry = self._providers[key]
        if isinstance(entry, type):
            # Instantiate class if not already instantiated
            instance = entry()
            self._providers[key] = instance
            return instance
        elif callable(entry) and not hasattr(entry, "health_check"):
            # Factory function
            instance = entry()
            self._providers[key] = instance
            return instance
        return entry

    def register_tool(self, config_key: str, tool_def: dict[str, Any]) -> None:
        """Register a tool associated with a feature toggle key."""
        self._tools.setdefault(config_key, []).append(tool_def)

    def get_active_tools(self, custom_config_path: Any = None) -> list[dict[str, Any]]:
        """Return all tools belonging to currently enabled features."""
        active: list[dict[str, Any]] = []
        for config_key, tool_list in self._tools.items():
            enabled_key = config_key if config_key.endswith(".enabled") else f"{config_key}.enabled"
            if config_is_enabled(enabled_key, custom_path=custom_config_path):
                active.extend(tool_list)
        return active

    def register_job(self, config_key: str, job_def: dict[str, Any]) -> None:
        """Register a scheduled job associated with a feature toggle key."""
        self._jobs.setdefault(config_key, []).append(job_def)

    def get_active_jobs(self, custom_config_path: Any = None) -> list[dict[str, Any]]:
        """Return all jobs belonging to currently enabled features."""
        active: list[dict[str, Any]] = []
        for config_key, job_list in self._jobs.items():
            enabled_key = config_key if config_key.endswith(".enabled") else f"{config_key}.enabled"
            if config_is_enabled(enabled_key, custom_path=custom_config_path):
                active.extend(job_list)
        return active

    def disabled_http_response(self, config_key: str) -> tuple[int, dict[str, str]]:
        """Standard 503 response for disabled feature HTTP endpoints."""
        key = config_key if config_key.endswith(".enabled") else f"{config_key}.enabled"
        return 503, {"disabled": key}

    def route_guard(
        self,
        config_key: str,
        custom_config_path: Any = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator for route handlers that short-circuits with 503 if feature is disabled."""
        enabled_key = config_key if config_key.endswith(".enabled") else f"{config_key}.enabled"

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if not config_is_enabled(enabled_key, custom_path=custom_config_path):
                    return self.disabled_http_response(enabled_key)
                return fn(*args, **kwargs)

            return wrapper

        return decorator

    def health_check(
        self,
        interface: str,
        name: Optional[str] = None,
        config_key: Optional[str] = None,
        custom_config_path: Any = None,
    ) -> dict[str, Any]:
        """Perform health check on active or specified provider."""
        try:
            prov = self.get(interface, name=name, config_key=config_key, custom_config_path=custom_config_path)
            if hasattr(prov, "health_check") and callable(prov.health_check):
                t0 = time.time()
                res = prov.health_check()
                latency = round((time.time() - t0) * 1000, 2)
                if isinstance(res, dict):
                    res.setdefault("latency_ms", latency)
                    res.setdefault("error", None)
                    return res
                return {"status": "ok", "latency_ms": latency, "error": None}
            return {"status": "ok", "latency_ms": 0.0, "error": None}
        except FeatureDisabledError as e:
            return {"status": "disabled", "latency_ms": 0.0, "error": str(e)}
        except Exception as e:
            return {"status": "down", "latency_ms": 0.0, "error": str(e)}

    def health_check_all(self, custom_config_path: Any = None) -> dict[str, Any]:
        """Run health check across all registered interfaces."""
        results: dict[str, Any] = {}
        overall = "ok"
        for interface in list(self._defaults.keys()):
            res = self.health_check(interface, custom_config_path=custom_config_path)
            results[interface] = res
            if res.get("status") == "down":
                overall = "down"
            elif res.get("status") == "degraded" and overall != "down":
                overall = "degraded"
        return {"status": overall, "providers": results}


_registry_instance: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Return the global ProviderRegistry singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ProviderRegistry()
    return _registry_instance
