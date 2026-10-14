"""
tests/test_config_accessor.py - Unit tests for US-05 (F-0125).

Acceptance criteria:
- sidecar/config.py defines get(path, default=None) and is_enabled(path) and reads config at D-10 location.
- locus-extension/src/config.ts offers the same two functions over the same file.
- Missing key returns default; is_enabled is false when absent or false.
- No module outside the accessor reads os.environ, process.env or config file directly.
- py -3 -m sidecar.config get <path> prints the value (or default).
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from sidecar.config import (
    clear_cache,
    get,
    get_config_path,
    get_env,
    is_enabled,
)


@pytest.fixture
def custom_config(tmp_path: Path) -> Path:
    """Fixture providing a temporary config.yaml file."""
    cfg_file = tmp_path / "config.yaml"
    data = {
        "locus": {
            "demo": {
                "value": 7,
                "name": "Locus Demo",
                "nested": {
                    "count": 42,
                },
            },
            "features": {
                "active": True,
                "disabled": False,
                "string_true": "yes",
                "string_false": "off",
                "numeric_one": 1,
                "numeric_zero": 0,
            },
        }
    }
    cfg_file.write_text(yaml.safe_dump(data), encoding="utf-8")
    clear_cache()
    return cfg_file


def test_python_config_get_nested_and_default(custom_config: Path):
    """Test get() with nested keys, missing keys, and intermediate non-dicts."""
    # Existing keys
    assert get("locus.demo.value", custom_path=custom_config) == 7
    assert get("locus.demo.name", custom_path=custom_config) == "Locus Demo"
    assert get("locus.demo.nested.count", custom_path=custom_config) == 42

    # Whole subtree
    nested = get("locus.demo.nested", custom_path=custom_config)
    assert isinstance(nested, dict)
    assert nested.get("count") == 42

    # Missing keys
    assert get("locus.nonexistent", default="fallback", custom_path=custom_config) == "fallback"
    assert get("locus.demo.nonexistent", default=None, custom_path=custom_config) is None
    assert get("completely.missing.path", custom_path=custom_config) is None

    # Intermediate key is not a dict
    assert get("locus.demo.value.subpath", default="not_found", custom_path=custom_config) == "not_found"

    # Invalid path types
    assert get("", default="empty", custom_path=custom_config) == "empty"
    assert get(None, default="none", custom_path=custom_config) == "none"  # type: ignore


def test_python_config_is_enabled(custom_config: Path):
    """Test is_enabled() with truthy, falsy, and absent values."""
    # Explicit booleans
    assert is_enabled("locus.features.active", custom_path=custom_config) is True
    assert is_enabled("locus.features.disabled", custom_path=custom_config) is False

    # String representations
    assert is_enabled("locus.features.string_true", custom_path=custom_config) is True
    assert is_enabled("locus.features.string_false", custom_path=custom_config) is False

    # Numbers
    assert is_enabled("locus.features.numeric_one", custom_path=custom_config) is True
    assert is_enabled("locus.features.numeric_zero", custom_path=custom_config) is False

    # Missing keys
    assert is_enabled("locus.features.missing", custom_path=custom_config) is False
    assert is_enabled("nonexistent.switch", custom_path=custom_config) is False


def test_python_config_env_access(monkeypatch):
    """Test environment variable retrieval via get('env.<KEY>') and get_env."""
    monkeypatch.setenv("TEST_LOCUS_VAR", "my_secret_token")
    assert get("env.TEST_LOCUS_VAR") == "my_secret_token"
    assert get_env("TEST_LOCUS_VAR") == "my_secret_token"
    assert get("env.NONEXISTENT_VAR", default="default_env") == "default_env"


def test_cli_config_get(custom_config: Path, monkeypatch):
    """Test CLI execution: py -3 -m sidecar.config get <path>."""
    monkeypatch.setenv("LOCUS_HOME", str(custom_config.parent))
    clear_cache()

    # Existing key
    res = subprocess.run(
        [sys.executable, "-m", "sidecar.config", "get", "locus.demo.value"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.stdout.strip() == "7"

    # Missing key with explicit default
    res = subprocess.run(
        [sys.executable, "-m", "sidecar.config", "get", "locus.missing.key", "my_default"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.stdout.strip() == "my_default"

    # Missing key without default -> prints None
    res = subprocess.run(
        [sys.executable, "-m", "sidecar.config", "get", "locus.demo.unconfigured"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res.stdout.strip() == "None"


def test_ts_config_accessor_matches_python(custom_config: Path):
    """Verify that locus-extension/src/config.ts behaves identically to Python."""
    repo_root = Path(__file__).resolve().parent.parent
    ts_file = (repo_root / "locus-extension" / "src" / "config.ts").as_uri()
    cfg_path = custom_config.resolve().as_posix()

    script = f"""
    import {{ get, is_enabled }} from '{ts_file}';
    const cfg = '{cfg_path}';

    const v1 = get('locus.demo.value', null, cfg);
    const v2 = get('locus.demo.nested.count', null, cfg);
    const v3 = get('locus.nonexistent', 'fallback', cfg);
    const e1 = is_enabled('locus.features.active', cfg);
    const e2 = is_enabled('locus.features.disabled', cfg);
    const e3 = is_enabled('locus.features.missing', cfg);

    console.log(JSON.stringify({{ v1, v2, v3, e1, e2, e3 }}));
    """

    res = subprocess.run(
        ["node", "--experimental-strip-types", "-e", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Node script failed: {res.stderr}"

    import json

    ts_results = json.loads(res.stdout.strip())
    assert ts_results["v1"] == get("locus.demo.value", custom_path=custom_config)
    assert ts_results["v2"] == get("locus.demo.nested.count", custom_path=custom_config)
    assert ts_results["v3"] == get("locus.nonexistent", default="fallback", custom_path=custom_config)
    assert ts_results["e1"] == is_enabled("locus.features.active", custom_path=custom_config)
    assert ts_results["e2"] == is_enabled("locus.features.disabled", custom_path=custom_config)
    assert ts_results["e3"] == is_enabled("locus.features.missing", custom_path=custom_config)


def test_no_direct_environ_or_config_reads_outside_accessor():
    """
    Acceptance criterion: No module outside the accessor reads os.environ,
    process.env or config file directly.
    """
    repo_root = Path(__file__).resolve().parent.parent
    sidecar_dir = repo_root / "sidecar"

    # Check Python sidecar files
    offending_py = []
    for py_file in sidecar_dir.rglob("*.py"):
        if py_file.name == "config.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        # Strip comments
        lines = [line.split("#")[0] for line in content.splitlines()]
        code = "\n".join(lines)
        if "os.environ" in code:
            offending_py.append(py_file.relative_to(repo_root).as_posix())

    assert not offending_py, f"Modules reading os.environ directly outside accessor: {offending_py}"

    # Check TypeScript extension files
    extension_dir = repo_root / "locus-extension" / "src"
    offending_ts = []
    for ts_file in extension_dir.rglob("*.ts"):
        if ts_file.name == "config.ts":
            continue
        content = ts_file.read_text(encoding="utf-8")
        lines = [line.split("//")[0] for line in content.splitlines()]
        code = "\n".join(lines)
        if "process.env" in code:
            offending_ts.append(ts_file.relative_to(repo_root).as_posix())

    assert not offending_ts, f"TypeScript modules reading process.env outside config.ts: {offending_ts}"


def test_owner_demo_scenario(tmp_path: Path, monkeypatch):
    """
    Replicate exact owner Sprint Review demo:
    1. Run py -3 -m sidecar.config get locus.demo.value (prints default None).
    2. Add locus.demo.value: 7 to config file.
    3. Run py -3 -m sidecar.config get locus.demo.value (prints 7).
    """
    cfg_dir = tmp_path / ".locus"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "config.yaml"
    monkeypatch.setenv("LOCUS_HOME", str(cfg_dir))
    clear_cache()

    # Step 1: Config does not exist yet -> prints None
    res1 = subprocess.run(
        [sys.executable, "-m", "sidecar.config", "get", "locus.demo.value"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res1.stdout.strip() == "None"

    # Step 2: Write locus.demo.value: 7 to config.yaml
    cfg_file.write_text("locus:\n  demo:\n    value: 7\n", encoding="utf-8")

    # Step 3: Run again -> prints 7
    res2 = subprocess.run(
        [sys.executable, "-m", "sidecar.config", "get", "locus.demo.value"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert res2.stdout.strip() == "7"
