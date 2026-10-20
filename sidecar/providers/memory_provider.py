"""
Memory Provider definitions and provider exports (SPEC §4.18: Memory Provider Interface).
Exports MemoryProvider, DefaultMemoryProvider, and stackable MemoryManager.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import sidecar.config as config
from sidecar.memory.provider_interface import (
    DefaultMemoryProvider,
    MemoryManager,
    MemoryProvider,
)

logger = logging.getLogger(__name__)

__all__ = [
    "MemoryProvider",
    "DefaultMemoryProvider",
    "MemoryManager",
]
