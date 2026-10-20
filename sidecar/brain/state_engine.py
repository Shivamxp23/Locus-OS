"""
SPEC §4.10 / §2.4: sidecar/brain/state_engine.py
Canonical bridge re-exporting Locus state engine for cognitive modules.
"""
from sidecar.state_engine import (
    DEFAULT_BASELINE,
    StateEngineProvider,
)

__all__ = [
    "DEFAULT_BASELINE",
    "StateEngineProvider",
]
