"""
Unit tests for Connectivity Check (F-0068 / US-106).
SPEC §29.5 lines 7613-7671.
"""
from __future__ import annotations

import time
import pytest

from sidecar import config
from sidecar.diagnostics.connectivity import (
    ConnectivityChecker,
    DEFAULT_CONNECTIVITY_ENDPOINTS,
)
from sidecar.providers.connectivity import (
    BaseConnectivityProvider,
    DefaultConnectivityProvider,
)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.connectivity_check.enabled", True)
    config.set("locus.connectivity_check.timeout", 5.0)
    config.set("locus.connectivity_check.service_timeout", 3.0)
    yield
    config.set("locus.connectivity_check.enabled", True)


def test_default_endpoints():
    """SPEC §29.5 line 7631: "ENDPOINTS = [" """
    checker = ConnectivityChecker()
    assert checker.endpoints == [
        "https://httpbin.org/status/200",
        "https://1.1.1.1/cdn-cgi/trace",
    ]
    assert checker.endpoints == DEFAULT_CONNECTIVITY_ENDPOINTS


def test_check_connectivity_success():
    """SPEC §29.5 line 7636: "FUNCTION check_connectivity(timeout=5):" """
    probed = []

    def mock_head(url: str, timeout: float):
        probed.append((url, timeout))
        return 200, 18.5

    checker = ConnectivityChecker(http_head_fn=mock_head)
    res = checker.check_connectivity(timeout=4.0)

    assert res["online"] is True
    assert res["latency_ms"] == 18.5
    assert res["endpoint"] == "https://httpbin.org/status/200"
    assert len(probed) == 1
    assert probed[0] == ("https://httpbin.org/status/200", 4.0)


def test_check_connectivity_status_code_400():
    """SPEC §29.5 line 7640: "IF response.status < 400:" """
    probed = []

    def mock_head(url: str, timeout: float):
        probed.append(url)
        if "httpbin" in url:
            return 500, 25.0
        return 204, 12.0

    checker = ConnectivityChecker(http_head_fn=mock_head)
    res = checker.check_connectivity()

    assert res["online"] is True
    assert res["endpoint"] == "https://1.1.1.1/cdn-cgi/trace"
    assert res["latency_ms"] == 12.0
    assert len(probed) == 2


def test_check_connectivity_fallback():
    """SPEC §29.5 line 7643: "CONTINUE // try next endpoint" """
    probed = []

    def mock_head(url: str, timeout: float):
        probed.append(url)
        if "httpbin" in url:
            raise TimeoutError("probe timed out")
        return 200, 15.0

    checker = ConnectivityChecker(http_head_fn=mock_head)
    res = checker.check_connectivity()

    assert res["online"] is True
    assert res["endpoint"] == "https://1.1.1.1/cdn-cgi/trace"
    assert len(probed) == 2


def test_check_connectivity_all_fail():
    """SPEC §29.5 line 7645: "RETURN { online: false, latency_ms: null }" """
    def mock_head(url: str, timeout: float):
        raise ConnectionError("host unreachable")

    checker = ConnectivityChecker(http_head_fn=mock_head)
    res = checker.check_connectivity()

    assert res["online"] is False
    assert res["latency_ms"] is None
    assert res["endpoint"] is None


def test_check_service_connectivity_healthy():
    """SPEC §29.5 line 7647: "FUNCTION check_service_connectivity(services):" """
    probed = []

    def mock_get(url: str, timeout: float):
        probed.append((url, timeout))
        return 200, 5.2

    checker = ConnectivityChecker(http_get_fn=mock_get)
    services = [
        {"name": "neo4j", "health_url": "http://localhost:7474"},
        {"name": "postgres", "health_url": "http://localhost:5432/health"},
    ]
    results = checker.check_service_connectivity(services, timeout=2.5)

    assert results["neo4j"]["healthy"] is True
    assert results["neo4j"]["status_code"] == 200
    assert results["postgres"]["healthy"] is True
    assert len(probed) == 2
    assert probed[0] == ("http://localhost:7474", 2.5)


def test_check_service_connectivity_mixed():
    """SPEC §29.5 line 7653: "results[service.name] = { healthy: response.status == 200 }" """
    def mock_get(url: str, timeout: float):
        if "neo4j" in url:
            return 200, 4.0
        if "postgres" in url:
            return 503, 8.0
        raise TimeoutError("connection timed out")

    checker = ConnectivityChecker(http_get_fn=mock_get)
    services = [
        {"name": "neo4j", "health_url": "http://localhost:7474/neo4j"},
        {"name": "postgres", "health_url": "http://localhost:5432/postgres"},
        {"name": "sidecar", "health_url": "http://localhost:8420/health"},
    ]
    results = checker.check_service_connectivity(services)

    assert results["neo4j"]["healthy"] is True
    assert results["postgres"]["healthy"] is False
    assert results["postgres"]["status_code"] == 503
    assert results["sidecar"]["healthy"] is False
    assert "timed out" in results["sidecar"]["error"]


def test_connectivity_gates():
    """SPEC §29.5 line 7659: "// Used as gate before:" """
    checker = ConnectivityChecker()

    # Online state: no operations should be skipped/forced
    assert checker.should_skip_inner_loop_web(online=True) is False
    assert checker.should_force_local_model(online=True) is False
    assert checker.should_skip_vault_sync(online=True) is False
    assert checker.should_skip_web_search(online=True) is False

    # Offline state: all web operations must be skipped, models forced local
    assert checker.should_skip_inner_loop_web(online=False) is True
    assert checker.should_force_local_model(online=False) is True
    assert checker.should_skip_vault_sync(online=False) is True
    assert checker.should_skip_web_search(online=False) is True


def test_connectivity_caching_and_refresh():
    call_count = 0

    def mock_head(url: str, timeout: float):
        nonlocal call_count
        call_count += 1
        return 200, 10.0

    checker = ConnectivityChecker(http_head_fn=mock_head, cache_ttl_seconds=10.0)

    # First probe
    r1 = checker.check_connectivity()
    assert r1["online"] is True
    assert call_count == 1
    assert r1.get("cached") is False

    # Second probe within TTL -> returns cached
    r2 = checker.check_connectivity()
    assert r2["online"] is True
    assert call_count == 1
    assert r2.get("cached") is True

    # Force refresh bypasses cache
    r3 = checker.check_connectivity(force_refresh=True)
    assert r3["online"] is True
    assert call_count == 2
    assert r3.get("cached") is False


def test_connectivity_off_switch_503():
    """SPEC §29.5 line 7668: "- **Swappable / off state**: Always available (utility function). Used as a gate by Inner Loop, model escalation, and background tasks. If offline: Inner Loop skips web-dependent operations, model escalation forces local-only, web search returns empty results." """
    config.set("locus.connectivity_check.enabled", False)

    provider = DefaultConnectivityProvider()
    assert isinstance(provider, BaseConnectivityProvider)

    enabled, reason = provider.is_feature_enabled()
    assert enabled is False
    assert "disabled" in reason.lower()

    # check_internet returns status_code 503
    res_int = provider.check_internet()
    assert res_int.get("status_code") == 503
    assert res_int.get("online") is False

    # check_services returns status_code 503
    res_srv = provider.check_services([{"name": "test", "health_url": "http://localhost"}])
    assert res_srv.get("status_code") == 503

    # evaluate_gates returns status_code 503 with conservative skip defaults
    res_gat = provider.evaluate_gates()
    assert res_gat.get("status_code") == 503
    assert res_gat["force_local_model"] is True
    assert res_gat["skip_web_search"] is True

    # get_status returns status_code 503
    res_stat = provider.get_status()
    assert res_stat.get("status_code") == 503
    assert res_stat.get("enabled") is False


def test_connectivity_provider_enabled_flow():
    def mock_head(url: str, timeout: float):
        return 200, 22.0

    checker = ConnectivityChecker(http_head_fn=mock_head)
    provider = DefaultConnectivityProvider(checker=checker)

    status = provider.get_status()
    assert status["status"] == "success"
    assert status["enabled"] is True
    assert status["provider"] == "default_connectivity_provider"

    probe = provider.check_internet()
    assert probe["status"] == "success"
    assert probe["online"] is True
    assert probe["latency_ms"] == 22.0

    gates = provider.evaluate_gates()
    assert gates["status"] == "success"
    assert gates["online"] is True
    assert gates["force_local_model"] is False
    assert gates["skip_web_search"] is False

