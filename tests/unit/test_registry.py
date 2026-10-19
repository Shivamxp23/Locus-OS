"""
SPEC §03 / F-0125: Unit tests for ProviderRegistry and get_registry.
"""
from __future__ import annotations

import pytest
from sidecar.registry import ProviderRegistry, get_registry


class FakeProvider:
    def __init__(self, options=None):
        self.options = options or {}

    def health_check(self):
        return {"status": "ok", "latency": 1.2}


def test_provider_registry_singleton():
    """Verify get_registry returns ProviderRegistry singleton."""
    r1 = get_registry()
    r2 = get_registry()
    assert isinstance(r1, ProviderRegistry)
    assert r1 is r2


def test_provider_registry_register_and_get():
    """Verify provider registration and lookup."""
    reg = ProviderRegistry()
    reg.register("channel", "fake", FakeProvider)

    p_cls = reg.get("channel", "fake")
    assert p_cls is FakeProvider

    providers = reg.list_providers("channel")
    assert "fake" in providers
