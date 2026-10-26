"""
SPEC §8.1-8.10 lines 5480-5485, 5612-5656:
Configuration management for Locus CLI, managing ~/.locus/config.yaml and secrets in .env.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

import sidecar.config as sidecar_cfg


def get_config(key: str, default: Any = None) -> Any:
    """Retrieve configuration value by dot-separated path."""
    return sidecar_cfg.get(key, default)


def set_config(key: str, val: Any) -> None:
    """Persist configuration key-value pair."""
    sidecar_cfg.set_value(key, val)


def check_config_integrity() -> bool:
    """Validate that configuration file is valid YAML/JSON and readable."""
    return sidecar_cfg.is_config_valid()


def export_config() -> Dict[str, Any]:
    """Export complete configuration tree as dictionary."""
    return sidecar_cfg._load_raw_config()


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve secret from environment or ~/.locus/.env file."""
    return sidecar_cfg.get_env(key, default)
