"""
SPEC §03 / F-0125 / US-05: Unit tests for configuration accessor.
Asserts:
- get(path, default) returns default when absent or file missing.
- is_enabled(path) returns True for truthy values, False when absent or falsy.
- CLI execution via `python -m sidecar.config get <path>` prints value or default.
- No module outside sidecar/config.py and locus-extension/src/config.ts reads os.environ or process.env directly.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import pytest

from sidecar.config import get, is_enabled, get_locus_home, get_config_path


@pytest.fixture
def temp_locus_home(tmp_path, monkeypatch):
    """Set LOCUS_HOME to a clean temporary directory for isolated config testing."""
    monkeypatch.setenv("LOCUS_HOME", str(tmp_path))
    return tmp_path


def test_config_missing_file_returns_default(temp_locus_home):
    """SPEC §03: A missing key returns the default when config.yaml does not exist."""
    assert get("locus.nonexistent.key") is None
    assert get("locus.nonexistent.key", default="fallback") == "fallback"
    assert is_enabled("locus.nonexistent.flag") is False


def test_config_get_nested_values(temp_locus_home):
    """SPEC §03: get() retrieves nested values from config.yaml."""
    cfg_file = temp_locus_home / "config.yaml"
    cfg_file.write_text(
        "locus:\n"
        "  demo:\n"
        "    value: 7\n"
        "    name: 'test_node'\n"
        "    active: true\n"
        "    disabled_flag: false\n",
        encoding="utf-8"
    )

    assert get("locus.demo.value") == 7
    assert get("locus.demo.name") == "test_node"
    assert get("locus.demo.active") is True
    assert get("locus.demo.disabled_flag") is False
    assert get("locus.demo.missing", default="default_val") == "default_val"


def test_config_is_enabled(temp_locus_home):
    """SPEC §03: is_enabled() correctly parses boolean, integer, and string flags."""
    cfg_file = temp_locus_home / "config.yaml"
    cfg_file.write_text(
        "flags:\n"
        "  b_true: true\n"
        "  b_false: false\n"
        "  s_true: 'true'\n"
        "  s_yes: 'yes'\n"
        "  s_on: 'on'\n"
        "  s_1: '1'\n"
        "  s_false: 'false'\n"
        "  num_1: 1\n"
        "  num_0: 0\n",
        encoding="utf-8"
    )

    assert is_enabled("flags.b_true") is True
    assert is_enabled("flags.b_false") is False
    assert is_enabled("flags.s_true") is True
    assert is_enabled("flags.s_yes") is True
    assert is_enabled("flags.s_on") is True
    assert is_enabled("flags.s_1") is True
    assert is_enabled("flags.s_false") is False
    assert is_enabled("flags.num_1") is True
    assert is_enabled("flags.num_0") is False
    assert is_enabled("flags.not_found") is False


def test_config_cli_get(temp_locus_home):
    """SPEC §03: py -3 -m sidecar.config get <path> prints the value or default."""
    cfg_file = temp_locus_home / "config.yaml"
    cfg_file.write_text("locus:\n  demo:\n    value: 7\n", encoding="utf-8")

    env = {**os.environ, "LOCUS_HOME": str(temp_locus_home)}
    res = subprocess.run(
        [sys.executable, "-m", "sidecar.config", "get", "locus.demo.value"],
        capture_output=True,
        text=True,
        env=env,
        check=True
    )
    assert res.stdout.strip() == "7"

    res_default = subprocess.run(
        [sys.executable, "-m", "sidecar.config", "get", "locus.demo.missing", "fallback_cli"],
        capture_output=True,
        text=True,
        env=env,
        check=True
    )
    assert res_default.stdout.strip() == "fallback_cli"


def test_no_direct_env_or_config_reads_outside_accessor():
    """
    SPEC §03 / US-05: No module outside sidecar/config.py and locus-extension/src/config.ts
    reads os.environ, process.env or config.yaml directly.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent

    # Check sidecar python files
    sidecar_dir = repo_root / "sidecar"
    for py_file in sidecar_dir.rglob("*.py"):
        if py_file.name == "config.py":
            continue
        content = py_file.read_text(encoding="utf-8", errors="replace")
        assert "os.environ" not in content, f"Direct os.environ access in {py_file}"
        assert "config.yaml" not in content, f"Direct config.yaml reference in {py_file}"

    # Check locus-extension typescript files
    ext_src_dir = repo_root / "locus-extension" / "src"
    for ts_file in ext_src_dir.rglob("*.ts"):
        if ts_file.name == "config.ts":
            continue
        content = ts_file.read_text(encoding="utf-8", errors="replace")
        assert "process.env" not in content, f"Direct process.env access in {ts_file}"
        assert "config.yaml" not in content, f"Direct config.yaml reference in {ts_file}"
