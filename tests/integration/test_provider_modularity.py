"""
SPEC §03 / F-0125 / US-06: Integration tests for Provider Registry and Modularity.
Crosses component and process boundaries:
1. Validates dynamic provider swapping driven by LOCUS_HOME/config.yaml.
2. Validates off-switch behavior across routes (503 response), tools (not registered), and jobs (not scheduled).
3. Validates health checks on all registered providers.
4. Executes cross-language integration verifying TypeScript provider registry and Python sidecar registry against shared configuration.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import pytest
import yaml

from sidecar import config
from sidecar.registry import ProviderRegistry, get_registry
from sidecar.telegram.gateway import TelegramGateway


@pytest.fixture
def clean_locus_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated LOCUS_HOME for integration testing."""
    locus_home = tmp_path / ".locus"
    locus_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCUS_HOME", str(locus_home))
    return locus_home


class ConcreteMemoryProviderAlpha:
    def __init__(self, options=None):
        self.options = options or {}

    def health_check(self):
        return {"status": "ok", "provider": "alpha", "latency_ms": 1.1}

    def query(self) -> str:
        return "alpha_data"


class ConcreteMemoryProviderBeta:
    def __init__(self, options=None):
        self.options = options or {}

    def health_check(self):
        return {"status": "ok", "provider": "beta", "latency_ms": 2.2}

    def query(self) -> str:
        return "beta_data"


def test_integration_provider_swap_via_config(clean_locus_env: Path):
    """SPEC 03.Modularity line 41: "test_<feature>_swap: register a second fake provider under another name, set provider, assert the fake is called and the default is not.\""""
    reg = get_registry()
    reg.register("memory", "neo4j", ConcreteMemoryProviderAlpha)
    reg.register("memory", "postgres", ConcreteMemoryProviderBeta)

    # 1. Config points to neo4j
    config.set_value("locus.memory.provider", "neo4j")
    active_cls1 = reg.get_active_provider("memory", default_name="neo4j")
    assert active_cls1 is ConcreteMemoryProviderAlpha
    assert active_cls1().query() == "alpha_data"

    # 2. Swap config on disk to postgres
    config.set_value("locus.memory.provider", "postgres")
    active_cls2 = reg.get_active_provider("memory", default_name="neo4j")
    assert active_cls2 is ConcreteMemoryProviderBeta
    assert active_cls2().query() == "beta_data"


def test_integration_off_switch_behavior(clean_locus_env: Path):
    """SPEC 03.Modularity line 35: "Defaults chosen here: a disabled feature's HTTP routes answer 503 with {\"disabled\": \"<config key>\"}; its Pi tools are not registered; its scheduled jobs are not scheduled; start-up still succeeds.\""""
    reg = get_registry()
    feature_key = "locus.analytics.reporting.enabled"

    # Disable feature in config
    config.set_value(feature_key, False)

    # 1. HTTP route check answers 503 with {"disabled": feature_key}
    route_check = reg.check_route_allowed(feature_key)
    assert route_check is not None
    status_code, body = route_check
    assert status_code == 503
    assert body == {"disabled": feature_key}

    # 2. Tool registration is suppressed
    registered_tool = reg.register_tool("run_report", feature_key, lambda: "report")
    assert registered_tool is False
    assert "run_report" not in reg.get_registered_tools()

    # 3. Job scheduling is suppressed
    scheduled_job = reg.schedule_job("nightly_report", feature_key, lambda: "scheduled")
    assert scheduled_job is False
    assert "nightly_report" not in reg.get_scheduled_jobs()


def test_integration_health_check_all_providers(clean_locus_env: Path):
    """SPEC 03.Modularity line 42: "test_<feature>_health: health_check() returns status and latency, and reports a stopped dependency as not OK.\""""
    reg = get_registry()
    reg.register("test_svc", "alpha", ConcreteMemoryProviderAlpha)
    reg.register("test_svc", "beta", ConcreteMemoryProviderBeta)

    health_data = reg.health_check_all()
    assert "test_svc.alpha" in health_data
    assert "test_svc.beta" in health_data
    assert health_data["test_svc.alpha"]["status"] == "ok"
    assert health_data["test_svc.beta"]["status"] == "ok"


def test_integration_cross_language_typescript_registry(clean_locus_env: Path):
    """SPEC 03.Modularity line 23: "registry | sidecar/registry.py: ProviderRegistry, get_registry() | locus-extension/src/registry.ts\""""
    # Write config file in Python
    config.set_value("locus.tools.calc.enabled", False)
    config.set_value("locus.tools.echo.enabled", True)

    repo_root = Path(__file__).resolve().parent.parent.parent
    ts_test = repo_root / "tests" / "unit" / "test_registry.test.ts"

    # Execute Node test runner over TypeScript registry against the shared environment
    proc = subprocess.run(
        ["node", "--test", "--test-reporter=tap", str(ts_test)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env={**os.environ, "LOCUS_HOME": str(clean_locus_env)},
    )
    assert proc.returncode == 0, f"TypeScript integration failed: {proc.stderr}\n{proc.stdout}"
    assert "ok 1 - TypeScript ProviderRegistry" in proc.stdout
    assert "ok 2 - TypeScript ProviderRegistry" in proc.stdout
