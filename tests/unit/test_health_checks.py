"""
Unit tests for Health Checks (F-0066 / US-104).
SPEC §29.3 lines 7501-7530.
"""
from __future__ import annotations

import time
import pytest

from sidecar import config
from sidecar.diagnostics.health_checker import (
    HealthChecker,
    ProviderHealthResult,
    SystemHealthReport,
    health_check_all,
)
from sidecar.providers.health_checks import (
    BaseHealthChecksProvider,
    DefaultHealthChecksProvider,
)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.health_checks.enabled", True)
    config.set("locus.diagnostics.health_checks.enabled", True)
    yield
    config.set("locus.health_checks.enabled", True)
    config.set("locus.diagnostics.health_checks.enabled", True)


class MockHealthyProvider:
    def health_check(self):
        return {"status": "operational", "version": "1.0.0"}


class MockSlowHealthyProvider:
    def health_check(self):
        time.sleep(0.01)
        return {"status": "ok", "ping": "pong"}


class MockFailingProvider:
    def health_check(self):
        raise ConnectionResetError("Connection refused by remote daemon")


class MockStatusOnlyProvider:
    def get_status(self):
        return {"active": True, "mode": "standalone"}


def test_health_check_all_healthy_providers():
    """SPEC §29.3 line 7512: 'FUNCTION health_check_all():'"""
    checker = HealthChecker()
    providers = {
        "p_alpha": MockHealthyProvider(),
        "p_beta": MockSlowHealthyProvider(),
    }
    results = checker.health_check_all(providers=providers)

    assert "p_alpha" in results
    assert results["p_alpha"]["status"] == "ok"
    assert results["p_alpha"]["latency_ms"] >= 0.0
    assert results["p_alpha"]["details"]["version"] == "1.0.0"

    assert "p_beta" in results
    assert results["p_beta"]["status"] == "ok"
    assert results["p_beta"]["latency_ms"] >= 8.0  # Slept 10ms


def test_health_check_all_error_containment():
    """SPEC §29.3 line 7520: 'except error: results[provider.name] = { status: \"error\", latency_ms: now()-start, error: str(error) }'"""
    checker = HealthChecker()
    providers = {
        "good": MockHealthyProvider(),
        "bad": MockFailingProvider(),
    }
    results = checker.health_check_all(providers=providers)

    assert results["good"]["status"] == "ok"
    assert results["bad"]["status"] == "error"
    assert "Connection refused" in results["bad"]["error"]
    assert results["bad"]["latency_ms"] >= 0.0


def test_health_check_fallback_get_status():
    """SPEC §29.3 line 7517: 'status = provider.health_check()'"""
    checker = HealthChecker()
    providers = {
        "status_prov": MockStatusOnlyProvider(),
    }
    results = checker.health_check_all(providers=providers)
    assert results["status_prov"]["status"] == "ok"
    assert results["status_prov"]["details"]["active"] is True


def test_build_system_health_report():
    """SPEC §29.3 line 7512: 'FUNCTION health_check_all(): results = {}'"""
    checker = HealthChecker()
    providers = {
        "healthy": MockHealthyProvider(),
        "unhealthy": MockFailingProvider(),
    }
    report = checker.build_report(providers=providers)
    assert isinstance(report, SystemHealthReport)
    assert report.total_providers == 2
    assert report.healthy_providers == 1
    assert report.failing_providers == 1
    assert report.overall_status == "degraded"

    report_dict = report.to_dict()
    assert report_dict["overall_status"] == "degraded"
    assert report_dict["total_providers"] == 2


def test_subsystem_off_switch():
    """SPEC §29.3 line 7527: 'Swappable / off state: N/A (diagnostic utility, always available via locus doctor)'"""
    config.set("locus.diagnostics.health_checks.enabled", False)
    checker = HealthChecker()
    results = checker.health_check_all({"p1": MockHealthyProvider()})
    assert "_subsystem" in results
    assert results["_subsystem"]["status"] == "disabled"


def test_provider_modular_off_switch():
    """SPEC §29.3 line 7527: 'Swappable / off state: locus.health_checks.enabled.'"""
    config.set("locus.health_checks.enabled", False)
    provider = DefaultHealthChecksProvider()
    res = provider.health_check_all()
    assert res.get("status_code") == 503
    assert "disabled by locus.health_checks.enabled" in res.get("detail", "")


def test_provider_normal_delegation():
    """SPEC §29.3 line 7514: 'FOR EACH provider IN all_registered_providers:'"""
    provider = DefaultHealthChecksProvider()
    res = provider.health_check_all(providers={"mock": MockHealthyProvider()})
    assert res["status"] == "ok"
    assert "mock" in res["results"]
    assert res["results"]["mock"]["status"] == "ok"


def test_provider_polymorphism():
    """SPEC §29.3 line 7512: Provider polymorphism and swappability."""
    class CustomHealthProvider(BaseHealthChecksProvider):
        @property
        def name(self) -> str:
            return "custom_health"

        def is_feature_enabled(self):
            return True, ""

        def health_check_all(self, providers=None):
            return {"status": "ok", "custom": True, "count": 1}

        def get_report(self, providers=None):
            return {"overall_status": "ok", "custom": True}

        def get_status(self):
            return {"name": self.name, "active": True}

        def health_check(self):
            return {"status": "ok"}

    custom = CustomHealthProvider()
    assert isinstance(custom, BaseHealthChecksProvider)
    assert custom.name == "custom_health"
    assert custom.health_check_all()["custom"] is True


def test_functional_convenience_entrypoint():
    """SPEC §29.3 line 7512: 'FUNCTION health_check_all():'"""
    res = health_check_all(providers={"unit": MockHealthyProvider()})
    assert "unit" in res
    assert res["unit"]["status"] == "ok"
