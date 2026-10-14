"""
sidecar/config.py - Canonical configuration accessor for Locus OS (Python side).

Implements single source of truth for configuration (errata D-10):
- Reads LOCUS_HOME/config.yaml.
- get(path: str, default: Any = None) -> Any
- is_enabled(path: str) -> bool
- CLI: python -m sidecar.config get <path> [<default>]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

_cached_data: Optional[dict[str, Any]] = None
_cached_mtime: float = 0.0


def get_config_path() -> Path:
    """Determine the canonical config.yaml path in LOCUS_HOME."""
    home_env = os.environ.get("LOCUS_HOME")
    home = Path(home_env) if home_env and home_env.strip() else (Path.home() / ".locus")
    return home / "config.yaml"


def get_env(key: str, default: Any = None) -> Any:
    """Access environment variables through the config accessor boundary."""
    return os.environ.get(key, default)


def clear_cache() -> None:
    """Clear internal configuration cache (useful for tests)."""
    global _cached_data, _cached_mtime
    _cached_data = None
    _cached_mtime = 0.0


def _load_config_data(custom_path: Optional[Path] = None) -> dict[str, Any]:
    """Load configuration from config.yaml with mtime caching."""
    global _cached_data, _cached_mtime
    cfg_file = custom_path or get_config_path()

    if not cfg_file.is_file():
        return {}

    try:
        stat = cfg_file.stat()
        if stat.st_mtime != _cached_mtime or _cached_data is None:
            raw = cfg_file.read_text(encoding="utf-8")
            loaded = yaml.safe_load(raw)
            _cached_data = loaded if isinstance(loaded, dict) else {}
            _cached_mtime = stat.st_mtime
        return _cached_data
    except Exception:
        return {}


def get(path: str, default: Any = None, custom_path: Optional[Path] = None) -> Any:
    """
    Retrieve a configuration value using dot notation (e.g. 'locus.channels.telegram.enabled').
    Special prefix 'env.' retrieves environment variables through the accessor boundary.
    Missing keys or unreadable files return default.
    """
    if not path or not isinstance(path, str):
        return default

    if path.startswith("env."):
        env_var = path[4:]
        return os.environ.get(env_var, default)

    data = _load_config_data(custom_path=custom_path)
    parts = path.split(".")
    cur: Any = data
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]

    return cur if cur is not None else default


def is_enabled(path: str, custom_path: Optional[Path] = None) -> bool:
    """
    Determine if a feature toggle is enabled.
    Returns False if key is absent or evaluates to False.
    """
    val = get(path, default=False, custom_path=custom_path)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on")
    if isinstance(val, (int, float)):
        return val != 0
    return False


def main() -> None:
    """CLI entry point: python -m sidecar.config get <path> [<default>]"""
    if len(sys.argv) >= 3 and sys.argv[1] == "get":
        dot_path = sys.argv[2]
        default_val = sys.argv[3] if len(sys.argv) >= 4 else None
        result = get(dot_path, default=default_val)
        print(result if result is not None else default_val)
    else:
        print("Usage: python -m sidecar.config get <dot.path> [default]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
