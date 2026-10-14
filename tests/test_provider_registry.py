"""
tests/test_provider_registry.py - Unit tests for US-06 (F-0125).

Acceptance criteria:
- sidecar/registry.py defines ProviderRegistry and get_registry().
- A provider registers under (interface, name); active provider is chosen by locus.<area>.<feature>.provider.
- When a feature's enabled switch is false:
  - its HTTP routes answer 503 with {"disabled": "<config key>"}
  - its tools are not registered
  - its jobs are not scheduled
  (one test per behaviour, using a dummy feature).
- Swap test: two dummy providers for one interface; changing config key switches behaviour with no code edit.
- Health test: every registered provider answers health_check().
- locus-extension/src/registry.ts offers the same register/get and the same off behaviour for tools.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import yaml

from sidecar.config import clear_cache
from sidecar.registry import (
    BaseProvider,
    FeatureDisabledError,
    ProviderRegistry,
    get_registry,
)


class DummyBase(BaseProvider):
    name = "dummy_base"

    def execute(self) -> str:
        return "base"


class DummyAlphaProvider(DummyBase):
    name = "alpha"

    def execute(self) -> str:
        return "alpha_result"

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "latency_ms": 1.2, "error": None}


class DummyBetaProvider(DummyBase):
    name = "beta"

    def execute(self) -> str:
        return "beta_result"

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "latency_ms": 2.5, "error": None}


class DummyDegradedProvider(DummyBase):
    name = "degraded"

    def health_check(self) -> dict[str, Any]:
        return {"status": "degraded", "latency_ms": 150.0, "error": "High latency"}


class DummyFailingProvider(DummyBase):
    name = "failing"

    def health_check(self) -> dict[str, Any]:
        raise RuntimeError("Connection refused")


@pytest.fixture
def registry() -> ProviderRegistry:
    """Fixture providing a fresh isolated ProviderRegistry."""
    reg = ProviderRegistry()
    return reg


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Fixture providing a temporary config.yaml file."""
    cfg = tmp_path / "config.yaml"
    data = {
        "locus": {
            "test": {
                "dummy": {
                    "enabled": True,
                    "provider": "alpha",
                },
                "disabled_feat": {
                    "enabled": False,
                    "provider": "alpha",
                },
            }
        }
    }
    cfg.write_text(yaml.safe_dump(data), encoding="utf-8")
    clear_cache()
    return cfg


def test_provider_registration_and_defaults(registry: ProviderRegistry):
    """Test registering providers under (interface, name) and default resolution."""
    registry.register("SearchProvider", "alpha", DummyAlphaProvider, is_default=True)
    registry.register("SearchProvider", "beta", DummyBetaProvider)

    # Default resolution
    default_prov = registry.get("SearchProvider")
    assert isinstance(default_prov, DummyAlphaProvider)
    assert default_prov.execute() == "alpha_result"

    # Explicit name resolution
    beta_prov = registry.get("SearchProvider", name="beta")
    assert isinstance(beta_prov, DummyBetaProvider)
    assert beta_prov.execute() == "beta_result"

    # Unregistered interface
    with pytest.raises(KeyError, match="No default provider registered"):
        registry.get("NonexistentInterface")

    # Unregistered provider name
    with pytest.raises(KeyError, match="Provider 'unknown' not registered"):
        registry.get("SearchProvider", name="unknown")


def test_provider_off_http_route(registry: ProviderRegistry, config_file: Path):
    """
    Acceptance criterion: When a feature's enabled switch is false:
    its HTTP routes answer 503 with {"disabled": "<config key>"}.
    """
    @registry.route_guard("locus.test.dummy", custom_config_path=config_file)
    def dummy_route_handler():
        return 200, {"message": "success"}

    @registry.route_guard("locus.test.disabled_feat", custom_config_path=config_file)
    def disabled_route_handler():
        return 200, {"message": "should not be called"}

    # Enabled route returns normal response
    status, body = dummy_route_handler()
    assert status == 200
    assert body == {"message": "success"}

    # Disabled route returns 503 with {"disabled": "<config key>"}
    status_off, body_off = disabled_route_handler()
    assert status_off == 503
    assert body_off == {"disabled": "locus.test.disabled_feat.enabled"}

    # Direct helper disabled_http_response returns 503
    res_code, res_body = registry.disabled_http_response("locus.test.disabled_feat.enabled")
    assert res_code == 503
    assert res_body == {"disabled": "locus.test.disabled_feat.enabled"}


def test_provider_off_tools_suppressed(registry: ProviderRegistry, config_file: Path):
    """
    Acceptance criterion: When a feature's enabled switch is false:
    its tools are not registered / active.
    """
    tool_enabled = {"name": "dummy_search_tool", "description": "Search active"}
    tool_disabled = {"name": "dummy_inactive_tool", "description": "Search inactive"}

    registry.register_tool("locus.test.dummy", tool_enabled)
    registry.register_tool("locus.test.disabled_feat", tool_disabled)

    active_tools = registry.get_active_tools(custom_config_path=config_file)
    assert tool_enabled in active_tools
    assert tool_disabled not in active_tools
    assert len(active_tools) == 1


def test_provider_off_jobs_suppressed(registry: ProviderRegistry, config_file: Path):
    """
    Acceptance criterion: When a feature's enabled switch is false:
    its jobs are not scheduled / active.
    """
    job_enabled = {"name": "dummy_sync_job", "cron": "*/5 * * * *"}
    job_disabled = {"name": "dummy_backup_job", "cron": "0 0 * * *"}

    registry.register_job("locus.test.dummy", job_enabled)
    registry.register_job("locus.test.disabled_feat", job_disabled)

    active_jobs = registry.get_active_jobs(custom_config_path=config_file)
    assert job_enabled in active_jobs
    assert job_disabled not in active_jobs
    assert len(active_jobs) == 1


def test_provider_off_direct_get_raises(registry: ProviderRegistry, config_file: Path):
    """Direct registry.get() with disabled config_key raises FeatureDisabledError."""
    registry.register("SearchProvider", "alpha", DummyAlphaProvider)

    # Calling with disabled key raises FeatureDisabledError
    with pytest.raises(FeatureDisabledError) as exc_info:
        registry.get("SearchProvider", config_key="locus.test.disabled_feat", custom_config_path=config_file)
    assert exc_info.value.config_key == "locus.test.disabled_feat.enabled"


def test_provider_swap_without_code_edit(registry: ProviderRegistry, tmp_path: Path):
    """
    Acceptance criterion: Swap test: two dummy providers for one interface;
    changing the config key switches behaviour with no code edit.
    """
    registry.register("SearchProvider", "alpha", DummyAlphaProvider)
    registry.register("SearchProvider", "beta", DummyBetaProvider)

    cfg = tmp_path / "config.yaml"

    # Step 1: Config points to alpha
    cfg.write_text(yaml.safe_dump({"locus": {"search": {"enabled": True, "provider": "alpha"}}}), encoding="utf-8")
    clear_cache()
    prov_1 = registry.get("SearchProvider", config_key="locus.search", custom_config_path=cfg)
    assert isinstance(prov_1, DummyAlphaProvider)
    assert prov_1.execute() == "alpha_result"

    # Step 2: Config updated to point to beta - NO code edit
    cfg.write_text(yaml.safe_dump({"locus": {"search": {"enabled": True, "provider": "beta"}}}), encoding="utf-8")
    clear_cache()
    prov_2 = registry.get("SearchProvider", config_key="locus.search", custom_config_path=cfg)
    assert isinstance(prov_2, DummyBetaProvider)
    assert prov_2.execute() == "beta_result"


def test_provider_health_checks(registry: ProviderRegistry):
    """
    Acceptance criterion: Health test: every registered provider answers health_check().
    """
    registry.register("HealthyInterface", "alpha", DummyAlphaProvider, is_default=True)
    registry.register("DegradedInterface", "degraded", DummyDegradedProvider, is_default=True)
    registry.register("FailingInterface", "failing", DummyFailingProvider, is_default=True)

    # Individual health checks
    h_ok = registry.health_check("HealthyInterface")
    assert h_ok["status"] == "ok"
    assert "latency_ms" in h_ok
    assert h_ok["error"] is None

    h_deg = registry.health_check("DegradedInterface")
    assert h_deg["status"] == "degraded"
    assert h_deg["error"] == "High latency"

    h_fail = registry.health_check("FailingInterface")
    assert h_fail["status"] == "down"
    assert "Connection refused" in h_fail["error"]

    # health_check_all aggregate report
    all_health = registry.health_check_all()
    assert all_health["status"] == "down"  # because one is down
    assert "HealthyInterface" in all_health["providers"]
    assert "DegradedInterface" in all_health["providers"]
    assert "FailingInterface" in all_health["providers"]


def test_global_singleton_get_registry():
    """Verify get_registry() returns a consistent singleton instance."""
    reg1 = get_registry()
    reg2 = get_registry()
    assert reg1 is reg2
    assert isinstance(reg1, ProviderRegistry)


def test_ts_registry_matches_python(tmp_path: Path):
    """
    Acceptance criterion: locus-extension/src/registry.ts offers the same
    register/get, swap, and off behaviour for tools.
    """
    repo_root = Path(__file__).resolve().parent.parent
    ts_reg_file = (repo_root / "locus-extension" / "src" / "registry.ts").as_uri()

    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        yaml.safe_dump({
            "locus": {
                "test": {
                    "dummy": {"enabled": True, "provider": "alpha"},
                    "disabled_feat": {"enabled": False, "provider": "alpha"},
                }
            }
        }),
        encoding="utf-8",
    )
    cfg_posix = cfg.resolve().as_posix()

    script = f"""
    import {{ ProviderRegistry, BaseProvider, FeatureDisabledError }} from '{ts_reg_file}';

    class AlphaProvider extends BaseProvider {{
      constructor() {{
        super();
        this.name = 'alpha';
      }}
      execute() {{ return 'alpha_ts_result'; }}
      async health_check() {{
        return {{ status: 'ok', latency_ms: 1.5, error: null }};
      }}
    }}

    class BetaProvider extends BaseProvider {{
      constructor() {{
        super();
        this.name = 'beta';
      }}
      execute() {{ return 'beta_ts_result'; }}
      async health_check() {{
        return {{ status: 'ok', latency_ms: 2.0, error: null }};
      }}
    }}

    async function run() {{
      const reg = new ProviderRegistry();
      reg.register('SearchProvider', 'alpha', AlphaProvider, true);
      reg.register('SearchProvider', 'beta', BetaProvider);

      const cfg = '{cfg_posix}';

      // 1. Swap test
      const p1 = reg.get('SearchProvider', undefined, 'locus.test.dummy', cfg);
      const res1 = p1.execute();

      // 2. Off behaviour for direct get
      let disabledCaught = false;
      try {{
        reg.get('SearchProvider', undefined, 'locus.test.disabled_feat', cfg);
      }} catch (err) {{
        if (err instanceof FeatureDisabledError) {{
          disabledCaught = true;
        }}
      }}

      // 3. Off behaviour for tools
      reg.register_tool('locus.test.dummy', {{ name: 'tool_active' }});
      reg.register_tool('locus.test.disabled_feat', {{ name: 'tool_inactive' }});
      const activeTools = reg.get_active_tools(cfg);

      // 4. Health check
      const health = await reg.health_check('SearchProvider', 'alpha', undefined, cfg);

      // 5. Disabled HTTP response
      const [code, body] = reg.disabled_http_response('locus.test.disabled_feat');

      console.log(JSON.stringify({{
        swapResult: res1,
        disabledCaught,
        activeToolsCount: activeTools.length,
        activeToolName: activeTools[0]?.name,
        healthStatus: health.status,
        httpCode: code,
        disabledKey: body.disabled
      }}));
    }}

    run();
    """

    res = subprocess.run(
        ["node", "--experimental-strip-types", "-e", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Node script failed: {res.stderr}"

    data = json.loads(res.stdout.strip())
    assert data["swapResult"] == "alpha_ts_result"
    assert data["disabledCaught"] is True
    assert data["activeToolsCount"] == 1
    assert data["activeToolName"] == "tool_active"
    assert data["healthStatus"] == "ok"
    assert data["httpCode"] == 503
    assert data["disabledKey"] == "locus.test.disabled_feat.enabled"
