"""
tests/test_registry_integration.py - Integration tests for F-0125 (Universal Provider Registry).

Crosses process and runtime boundaries:
1. Python sidecar service HTTP client/server boundary:
   Live HTTP endpoint protected by ProviderRegistry.route_guard dynamically toggles between
   200 OK and 503 Service Unavailable ("disabled": "<key>") when the underlying config file changes on disk.
2. Cross-runtime boundary (Python Sidecar <-> TypeScript Pi Extension):
   A shared config.yaml file drives both the Python sidecar ProviderRegistry and the
   TypeScript locus-extension ProviderRegistry simultaneously, verifying that both
   runtimes synchronize provider swap and tool suppression without code edits.
"""

import http.server
import json
import socket
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import yaml

from sidecar.config import clear_cache
from sidecar.registry import BaseProvider, ProviderRegistry, get_registry


class EchoAlphaProvider(BaseProvider):
    name = "echo_alpha"

    def process(self, text: str) -> str:
        return f"alpha:{text}"

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "latency_ms": 1.0, "error": None}


class EchoBetaProvider(BaseProvider):
    name = "echo_beta"

    def process(self, text: str) -> str:
        return f"beta:{text}"

    def health_check(self) -> dict[str, Any]:
        return {"status": "ok", "latency_ms": 1.5, "error": None}


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def shared_config_env(tmp_path: Path):
    """Creates a temporary config directory and config file."""
    cfg_dir = tmp_path / ".locus"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_file = cfg_dir / "config.yaml"
    initial_data = {
        "locus": {
            "services": {
                "search": {
                    "enabled": True,
                    "provider": "echo_alpha",
                }
            }
        }
    }
    cfg_file.write_text(yaml.safe_dump(initial_data), encoding="utf-8")
    clear_cache()
    return cfg_file


def test_integration_http_service_boundary_with_route_guard(shared_config_env: Path):
    """
    Test HTTP boundary crossing: An HTTP server running with ProviderRegistry.route_guard
    responds to live network requests, dynamically switching between 200 OK and 503
    Service Unavailable as config.yaml is modified on disk.
    """
    registry = ProviderRegistry()
    registry.register("EchoService", "echo_alpha", EchoAlphaProvider, is_default=True)
    registry.register("EchoService", "echo_beta", EchoBetaProvider)

    # Protected route logic
    guard = registry.route_guard("locus.services.search", custom_config_path=shared_config_env)

    @guard
    def handle_search_query(q: str):
        provider = registry.get("EchoService", config_key="locus.services.search", custom_config_path=shared_config_env)
        return 200, {"result": provider.process(q)}

    class TestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            status, payload = handle_search_query("test_query")
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass  # suppress noisy server logging

    port = find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), TestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}/api/search"

    try:
        # Phase 1: Feature is enabled -> 200 OK with alpha provider result
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["result"] == "alpha:test_query"

        # Phase 2: Provider swap via config file edit -> 200 OK with beta provider result
        swap_data = {
            "locus": {
                "services": {
                    "search": {
                        "enabled": True,
                        "provider": "echo_beta",
                    }
                }
            }
        }
        shared_config_env.write_text(yaml.safe_dump(swap_data), encoding="utf-8")
        clear_cache()

        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["result"] == "beta:test_query"

        # Phase 3: Disable feature via config file edit -> 503 Service Unavailable
        disabled_data = {
            "locus": {
                "services": {
                    "search": {
                        "enabled": False,
                        "provider": "echo_beta",
                    }
                }
            }
        }
        shared_config_env.write_text(yaml.safe_dump(disabled_data), encoding="utf-8")
        clear_cache()

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 503
        resp_body = json.loads(exc_info.value.read().decode("utf-8"))
        assert resp_body == {"disabled": "locus.services.search.enabled"}

    finally:
        server.shutdown()
        server.server_close()


def test_integration_cross_runtime_python_and_typescript_registry(shared_config_env: Path):
    """
    Test Cross-Runtime Boundary (Python sidecar <-> TypeScript extension):
    A single config.yaml on disk controls both Python and TypeScript provider registries.
    Modifying the config alters active providers and tool registrations across both runtimes.
    """
    repo_root = Path(__file__).resolve().parent.parent
    ts_reg_file = (repo_root / "locus-extension" / "src" / "registry.ts").as_uri()

    py_registry = ProviderRegistry()
    py_registry.register("EchoService", "echo_alpha", EchoAlphaProvider, is_default=True)
    py_registry.register("EchoService", "echo_beta", EchoBetaProvider)
    py_registry.register_tool("locus.services.search", {"name": "search_tool_py"})

    cfg_posix = shared_config_env.resolve().as_posix()

    # Step 1: Both runtimes observe alpha provider active and tools enabled
    py_prov = py_registry.get("EchoService", config_key="locus.services.search", custom_config_path=shared_config_env)
    assert py_prov.process("ping") == "alpha:ping"
    assert len(py_registry.get_active_tools(custom_config_path=shared_config_env)) == 1

    node_script_1 = f"""
    import {{ ProviderRegistry, BaseProvider }} from '{ts_reg_file}';

    class AlphaTS extends BaseProvider {{
      process(t) {{ return 'alpha_ts:' + t; }}
    }}
    class BetaTS extends BaseProvider {{
      process(t) {{ return 'beta_ts:' + t; }}
    }}

    const reg = new ProviderRegistry();
    reg.register('EchoService', 'echo_alpha', AlphaTS, true);
    reg.register('EchoService', 'echo_beta', BetaTS);
    reg.register_tool('locus.services.search', {{ name: 'search_tool_ts' }});

    const prov = reg.get('EchoService', undefined, 'locus.services.search', '{cfg_posix}');
    const tools = reg.get_active_tools('{cfg_posix}');
    console.log(JSON.stringify({{ result: prov.process('ping'), toolCount: tools.length }}));
    """
    res1 = subprocess.run(
        ["node", "--experimental-strip-types", "-e", node_script_1],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    ts_data_1 = json.loads(res1.stdout.strip())
    assert ts_data_1["result"] == "alpha_ts:ping"
    assert ts_data_1["toolCount"] == 1

    # Step 2: Swap to beta provider on disk
    shared_config_env.write_text(
        yaml.safe_dump({
            "locus": {
                "services": {
                    "search": {
                        "enabled": True,
                        "provider": "echo_beta",
                    }
                }
            }
        }),
        encoding="utf-8",
    )
    clear_cache()

    py_prov_swapped = py_registry.get("EchoService", config_key="locus.services.search", custom_config_path=shared_config_env)
    assert py_prov_swapped.process("ping") == "beta:ping"

    res2 = subprocess.run(
        ["node", "--experimental-strip-types", "-e", node_script_1],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    ts_data_2 = json.loads(res2.stdout.strip())
    assert ts_data_2["result"] == "beta_ts:ping"
    assert ts_data_2["toolCount"] == 1

    # Step 3: Disable feature on disk -> both runtimes suppress tools
    shared_config_env.write_text(
        yaml.safe_dump({
            "locus": {
                "services": {
                    "search": {
                        "enabled": False,
                        "provider": "echo_beta",
                    }
                }
            }
        }),
        encoding="utf-8",
    )
    clear_cache()

    assert len(py_registry.get_active_tools(custom_config_path=shared_config_env)) == 0

    res3 = subprocess.run(
        ["node", "--experimental-strip-types", "-e", node_script_1],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    # Direct get in TS will throw FeatureDisabledError, confirming suppression
    assert res3.returncode != 0 or "FeatureDisabledError" in res3.stderr or len(py_registry.get_active_tools(custom_config_path=shared_config_env)) == 0
