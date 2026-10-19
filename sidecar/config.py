"""
SPEC §03 / F-0125 / US-05: Single configuration accessor for Python sidecar.
Reads LOCUS_HOME/config.yaml (default ~/.locus/config.yaml per errata D-10).
No module outside this accessor may read os.environ or config.yaml directly.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Any

import yaml


def get_environ() -> dict[str, str]:
    """Return a copy of environment variables (encapsulated accessor)."""
    return dict(os.environ)


def get_env(key: str, default: str | None = None) -> str | None:
    """Retrieve an environment variable via the config accessor."""
    return os.environ.get(key, default)


def get_locus_home() -> Path:
    """Return canonical LOCUS_HOME path (LOCUS_HOME env var or ~/.locus)."""
    env_home = get_env("LOCUS_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / ".locus").resolve()


def get_config_path() -> Path:
    """Return path to config.yaml within LOCUS_HOME."""
    return get_locus_home() / "config.yaml"


def is_config_valid() -> bool:
    """
    Check if config.yaml is readable and syntactically valid YAML.
    If file does not exist, returns True (greenfield default).
    If file exists but fails to parse or is invalid, returns False.
    """
    cfg_path = get_config_path()
    if not cfg_path.is_file():
        return True
    try:
        content = cfg_path.read_text(encoding="utf-8")
        if not content.strip():
            return True
        parsed = yaml.safe_load(content)
        return isinstance(parsed, dict)
    except Exception:
        return False


def set_value(path: str, value: Any) -> None:
    """
    Set a configuration value by dot-separated path and atomically save to config.yaml.
    """
    if not path:
        return
    cfg_path = get_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if cfg_path.is_file():
        try:
            content = cfg_path.read_text(encoding="utf-8")
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            data = {}
    parts = path.strip().split(".")
    curr = data
    for part in parts[:-1]:
        if part not in curr or not isinstance(curr[part], dict):
            curr[part] = {}
        curr = curr[part]
    curr[parts[-1]] = value
    temp_path = cfg_path.with_suffix(".tmp")
    temp_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    temp_path.replace(cfg_path)



def _load_raw_config() -> dict[str, Any]:
    """Load config.yaml if it exists and is valid, returning parsed dict."""
    cfg_path = get_config_path()
    if not cfg_path.is_file():
        return {}
    try:
        content = cfg_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def get(path: str, default: Any = None) -> Any:
    """
    Retrieve a configuration value by dot-separated path (e.g. 'locus.demo.value').
    Returns default if key is not found or config file is missing.
    """
    if not path:
        return default

    data: Any = _load_raw_config()
    parts = path.strip().split(".")
    for part in parts:
        if isinstance(data, dict) and part in data:
            data = data[part]
        else:
            return default
    return data if data is not None else default


def is_enabled(path: str) -> bool:
    """
    Check if a boolean configuration flag is enabled.
    Returns False when absent, False, 0, or 'false'/'off'/'no'.
    """
    val = get(path, False)
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "on")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Locus configuration CLI accessor")
    subparsers = parser.add_subparsers(dest="command")

    get_parser = subparsers.add_parser("get", help="Get a configuration value")
    get_parser.add_argument("path", help="Dot-separated path (e.g. locus.demo.value)")
    get_parser.add_argument("default", nargs="?", default="", help="Optional default value")

    enabled_parser = subparsers.add_parser("is_enabled", help="Check if a configuration flag is enabled")
    enabled_parser.add_argument("path", help="Dot-separated path")

    args = parser.parse_args()
    if args.command == "get":
        val = get(args.path, default=args.default)
        if val is not None:
            print(val)
    elif args.command == "is_enabled":
        print(is_enabled(args.path))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
