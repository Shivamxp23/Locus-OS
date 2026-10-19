"""
SPEC §03 / F-0125: Universal Provider Registry.
Provides ProviderRegistry and get_registry() singleton for swappable providers.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type


class ProviderRegistry:
    """Universal provider registry allowing modular swap and on/off configuration."""

    def __init__(self) -> None:
        self._providers: Dict[str, Dict[str, Type[Any]]] = {}
        self._instances: Dict[str, Any] = {}

    def register(self, area: str, name: str, provider_cls: Type[Any]) -> None:
        """Register a provider class under an area and name."""
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
        """Run health check on all instantiated providers."""
        results = {}
        for name, inst in self._instances.items():
            if hasattr(inst, "health_check"):
                try:
                    results[name] = inst.health_check()
                except Exception as ex:
                    results[name] = {"status": "error", "error": str(ex)}
            else:
                results[name] = {"status": "unknown"}
        return results


_GLOBAL_REGISTRY: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Return the global ProviderRegistry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ProviderRegistry()
    return _GLOBAL_REGISTRY
