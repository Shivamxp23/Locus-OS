"""
SPEC §03 / F-0125 / US-06: Universal Provider Registry.
Provides ProviderRegistry and get_registry() singleton for swappable providers.
Enforces:
1. Registration under (area/interface, name)
2. Active provider selection via config key locus.<area>.<feature>.provider (or locus.<area>.provider)
3. Off-switch behavior:
   - HTTP routes answer 503 with {"disabled": "<config key>"}
   - Tools are not registered
   - Jobs are not scheduled
4. Health check for all registered providers
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type

from sidecar import config


class ProviderRegistry:
    """Universal provider registry allowing modular swap and on/off configuration."""

    def __init__(self) -> None:
        self._providers: Dict[str, Dict[str, Type[Any]]] = {}
        self._instances: Dict[str, Any] = {}
        self._tools: Dict[str, Any] = {}
        self._jobs: Dict[str, Callable[..., Any]] = {}

    def register(self, area: str, name: str, provider_cls: Type[Any]) -> None:
        """Register a provider class under an area/interface and name."""
        if area not in self._providers:
            self._providers[area] = {}
        self._providers[area][name] = provider_cls

    def get(self, area: str, name: Optional[str] = None) -> Optional[Type[Any]]:
        """Retrieve a registered provider class."""
        area_providers = self._providers.get(area, {})
        if name:
            return area_providers.get(name)
        # Return first or default if name not given
        return next(iter(area_providers.values()), None)

    def get_active_provider(
        self, area: str, feature: Optional[str] = None, default_name: Optional[str] = None
    ) -> Optional[Type[Any]]:
        """
        Retrieve active provider determined by configuration:
        Checks locus.<area>.<feature>.provider then locus.<area>.provider,
        falling back to default_name.
        """
        chosen_name: Optional[str] = None
        if feature:
            chosen_name = config.get(f"locus.{area}.{feature}.provider")
        if not chosen_name:
            chosen_name = config.get(f"locus.{area}.provider")
        if not chosen_name:
            chosen_name = default_name

        return self.get(area, chosen_name)

    def is_feature_enabled(self, area: str, feature: Optional[str] = None) -> bool:
        """
        Check if a feature area is enabled.
        Checks locus.<area>.<feature>.enabled or locus.<area>.enabled (default True).
        """
        if feature:
            val = config.get(f"locus.{area}.{feature}.enabled")
            if val is not None:
                return config.is_enabled(f"locus.{area}.{feature}.enabled")

        val = config.get(f"locus.{area}.enabled")
        if val is not None:
            return config.is_enabled(f"locus.{area}.enabled")

        return True

    def check_route_allowed(self, config_key: str) -> tuple[int, dict[str, str]] | None:
        """
        Check if an HTTP route is allowed.
        If the feature's enabled switch is false, returns (503, {"disabled": "<config key>"}).
        If allowed, returns None.
        """
        if not config.is_enabled(config_key):
            return 503, {"disabled": config_key}
        return None

    def register_tool(self, tool_name: str, config_key: str, tool_fn: Any) -> bool:
        """
        Register a tool if its feature switch is enabled.
        If enabled switch is false, tool is NOT registered.
        Returns True if registered, False if suppressed.
        """
        if not config.is_enabled(config_key):
            return False
        self._tools[tool_name] = tool_fn
        return True

    def get_registered_tools(self) -> list[str]:
        """Return names of currently registered tools."""
        return list(self._tools.keys())

    def schedule_job(self, job_id: str, config_key: str, job_fn: Callable[..., Any]) -> bool:
        """
        Schedule a job if its feature switch is enabled.
        If enabled switch is false, job is NOT scheduled.
        Returns True if scheduled, False if suppressed.
        """
        if not config.is_enabled(config_key):
            return False
        self._jobs[job_id] = job_fn
        return True

    def get_scheduled_jobs(self) -> list[str]:
        """Return IDs of currently scheduled jobs."""
        return list(self._jobs.keys())

    def list_providers(self, area: Optional[str] = None) -> list[str]:
        """List provider names in an area (or all areas if area is None)."""
        if area:
            return list(self._providers.get(area, {}).keys())
        out = []
        for a, pmap in self._providers.items():
            for name in pmap.keys():
                out.append(f"{a}.{name}")
        return out

    def health_check_all(self) -> dict[str, Any]:
        """
        Run health check on all registered providers.
        Instantiates providers without arguments if needed.
        """
        results: dict[str, Any] = {}
        for area, pmap in self._providers.items():
            for name, pcls in pmap.items():
                key = f"{area}.{name}"
                try:
                    inst = self._instances.get(key)
                    if inst is None:
                        inst = pcls()
                        self._instances[key] = inst
                    if hasattr(inst, "health_check"):
                        results[key] = inst.health_check()
                    else:
                        results[key] = {"status": "ok", "provider": key}
                except Exception as ex:
                    results[key] = {"status": "error", "provider": key, "error": str(ex)}
        return results


_GLOBAL_REGISTRY: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Return the global ProviderRegistry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ProviderRegistry()
    return _GLOBAL_REGISTRY
