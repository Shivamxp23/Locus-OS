"""
Context window management and Headroom CCR token compression (SPEC §1.6 & §4.17).
"""
from __future__ import annotations

from sidecar.context.headroom_adapter import HeadroomCCRAdapter
from sidecar.context.headroom_pipeline import (
    CacheAligner,
    CCRStore,
    CodeCompressor,
    CompressConfig,
    CompressResult,
    ContentRouter,
    ContentType,
    HeadroomPipeline,
    KompressCompressor,
    SmartCrusher,
)

__all__ = [
    "HeadroomCCRAdapter",
    "HeadroomPipeline",
    "CompressConfig",
    "CompressResult",
    "ContentRouter",
    "ContentType",
    "CacheAligner",
    "SmartCrusher",
    "CodeCompressor",
    "KompressCompressor",
    "CCRStore",
]
