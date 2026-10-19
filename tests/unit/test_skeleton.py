"""
SPEC §1.12 / F-0084: Architecture lock and skeleton structure tests.
Asserts importlib.util.find_spec('core') is None and no forbidden top-level directories exist.
"""
import importlib.util
import json
import pathlib
import pytest


def test_core_package_does_not_exist():
    """Verify that the removed `core` package does not exist and cannot be imported."""
    assert importlib.util.find_spec("core") is None


def test_no_forbidden_top_level_directories():
    """Verify that no forbidden top-level directory (core, locus, locus-os, src) exists."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    forbidden = ["core", "locus", "locus-os", "src"]
    for name in forbidden:
        path = repo_root / name
        assert not path.exists(), f"Forbidden top-level directory '{name}' exists at {path}"


def test_sidecar_package_version():
    """Verify that sidecar/__init__.py defines __version__."""
    import sidecar
    assert hasattr(sidecar, "__version__")
    assert isinstance(sidecar.__version__, str)


def test_upstream_lock_baseline_recorded():
    """Verify that tools/guard/upstream.lock.json baseline is present and valid."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent
    lock_file = repo_root / "tools" / "guard" / "upstream.lock.json"
    assert lock_file.exists(), f"Upstream lock file missing at {lock_file}"
    data = json.loads(lock_file.read_text(encoding="utf-8"))
    assert "baseline_commit" in data or "baseline" in data
    commit = data.get("baseline_commit") or data.get("baseline")
    assert len(commit) >= 7
