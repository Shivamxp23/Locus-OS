"""
SPEC §03 / F-0125 / US-06: Unit tests for Universal ProviderRegistry.
Enforces:
- Registration under (area, name) and singleton accessor
- Active provider selection by config key locus.<area>.<feature>.provider
- Off-switch behavior: 503 for routes, tools not registered, jobs not scheduled
- Dynamic provider swap with no code edit
- Health check verification for all registered providers
"""
from __future__ import annotations

from pathlib import Path
import pytest

from sidecar import config
from sidecar.registry import ProviderRegistry, get_registry


@pytest.fixture
def clean_locus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated LOCUS_HOME for configuration testing."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    return locus_home


class DummyProviderAlpha:
    def __init__(self, options=None):
        self.options = options or {}

    def health_check(self):
        return {"status": "ok", "provider": "alpha", "latency_ms": 1.2}

    def execute(self) -> str:
        return "alpha_executed"


class DummyProviderBeta:
    def __init__(self, options=None):
        self.options = options or {}

    def health_check(self):
        return {"status": "ok", "provider": "beta", "latency_ms": 2.5}

    def execute(self) -> str:
        return "beta_executed"


def test_provider_registry_singleton():
    """SPEC 03.Modularity line 8: "register: registry.register(\"name\", ProviderClass)\""""
    r1 = get_registry()
    r2 = get_registry()
    assert isinstance(r1, ProviderRegistry)
    assert r1 is r2


def test_provider_registry_register_and_get():
    """SPEC 03.Modularity line 8: "register: registry.register(\"name\", ProviderClass)\""""
    reg = ProviderRegistry()
    reg.register("search", "alpha", DummyProviderAlpha)

    p_cls = reg.get("search", "alpha")
    assert p_cls is DummyProviderAlpha

    providers = reg.list_providers("search")
    assert "alpha" in providers


def test_provider_registry_active_by_config(clean_locus_env: Path):
    """SPEC 03.Modularity line 9: "configure under locus.<area>: provider (which one), enabled (on/off), options (provider-specific)\""""
    reg = ProviderRegistry()
    reg.register("memory", "alpha", DummyProviderAlpha)
    reg.register("memory", "beta", DummyProviderBeta)

    # Configure active provider by feature config key: locus.memory.short_term.provider
    config.set_value("locus.memory.short_term.provider", "beta")

    active_cls = reg.get_active_provider("memory", feature="short_term", default_name="alpha")
    assert active_cls is DummyProviderBeta
    assert active_cls().execute() == "beta_executed"


def test_off_switch_routes_answer_503(clean_locus_env: Path):
    """SPEC 03.Modularity line 35: "Defaults chosen here: a disabled feature's HTTP routes answer 503 with {\"disabled\": \"<config key>\"}; its Pi tools are not registered; its scheduled jobs are not scheduled; start-up still succeeds.\""""
    reg = ProviderRegistry()
    cfg_key = "locus.demo.enabled"

    # Enabled state: check returns None (allowed)
    config.set_value(cfg_key, True)
    assert reg.check_route_allowed(cfg_key) is None

    # Disabled state: check returns 503 and names disabled key
    config.set_value(cfg_key, False)
    res = reg.check_route_allowed(cfg_key)
    assert res is not None
    code, payload = res
    assert code == 503
    assert payload == {"disabled": cfg_key}


def test_off_switch_tools_not_registered(clean_locus_env: Path):
    """SPEC 03.Modularity line 35: "Defaults chosen here: a disabled feature's HTTP routes answer 503 with {\"disabled\": \"<config key>\"}; its Pi tools are not registered; its scheduled jobs are not scheduled; start-up still succeeds.\""""
    reg = ProviderRegistry()
    cfg_key = "locus.tools.calculator.enabled"

    config.set_value(cfg_key, False)
    ok = reg.register_tool("calculator", cfg_key, lambda x: x * 2)
    assert ok is False
    assert "calculator" not in reg.get_registered_tools()

    # When enabled, registration succeeds
    config.set_value(cfg_key, True)
    ok_enabled = reg.register_tool("calculator", cfg_key, lambda x: x * 2)
    assert ok_enabled is True
    assert "calculator" in reg.get_registered_tools()


def test_off_switch_jobs_not_scheduled(clean_locus_env: Path):
    """SPEC 03.Modularity line 35: "Defaults chosen here: a disabled feature's HTTP routes answer 503 with {\"disabled\": \"<config key>\"}; its Pi tools are not registered; its scheduled jobs are not scheduled; start-up still succeeds.\""""
    reg = ProviderRegistry()
    cfg_key = "locus.cron.nightly_vacuum.enabled"

    config.set_value(cfg_key, False)
    ok = reg.schedule_job("nightly_vacuum", cfg_key, lambda: "vacuumed")
    assert ok is False
    assert "nightly_vacuum" not in reg.get_scheduled_jobs()

    # When enabled, scheduling succeeds
    config.set_value(cfg_key, True)
    ok_enabled = reg.schedule_job("nightly_vacuum", cfg_key, lambda: "vacuumed")
    assert ok_enabled is True
    assert "nightly_vacuum" in reg.get_scheduled_jobs()


def test_provider_swap_via_config(clean_locus_env: Path):
    """SPEC 03.Modularity line 41: "test_<feature>_swap: register a second fake provider under another name, set provider, assert the fake is called and the default is not.\""""
    reg = ProviderRegistry()
    reg.register("tts", "edge_tts", DummyProviderAlpha)
    reg.register("tts", "elevenlabs", DummyProviderBeta)

    # Initial setting: edge_tts
    config.set_value("locus.tts.provider", "edge_tts")
    prov_1 = reg.get_active_provider("tts", default_name="edge_tts")
    assert prov_1 is DummyProviderAlpha
    assert prov_1().execute() == "alpha_executed"

    # Swap by config change with zero code edit
    config.set_value("locus.tts.provider", "elevenlabs")
    prov_2 = reg.get_active_provider("tts", default_name="edge_tts")
    assert prov_2 is DummyProviderBeta
    assert prov_2().execute() == "beta_executed"


def test_health_check_all_registered():
    """SPEC 03.Modularity line 42: "test_<feature>_health: health_check() returns status and latency, and reports a stopped dependency as not OK.\""""
    reg = ProviderRegistry()
    reg.register("test_area", "alpha", DummyProviderAlpha)
    reg.register("test_area", "beta", DummyProviderBeta)

    health_report = reg.health_check_all()
    assert "test_area.alpha" in health_report
    assert "test_area.beta" in health_report
    assert health_report["test_area.alpha"]["status"] == "ok"
    assert health_report["test_area.beta"]["status"] == "ok"
    assert health_report["test_area.alpha"]["latency_ms"] == 1.2
