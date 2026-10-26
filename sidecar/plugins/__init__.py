"""
SPEC §9.9 lines 6143-6199:
Plugin LLM Sandboxing & Auxiliary Bridge package.
"""
from sidecar.plugins.llm_bridge import (
    AuxiliaryClient,
    AuxiliaryClientPool,
    AuxiliaryResponse,
    AuxiliaryTimeoutError,
    DefaultAuxiliaryClient,
    PluginLLMBridge,
    QuotaExceededError,
    TokenUsage,
)

__all__ = [
    "AuxiliaryClient",
    "AuxiliaryClientPool",
    "AuxiliaryResponse",
    "AuxiliaryTimeoutError",
    "DefaultAuxiliaryClient",
    "PluginLLMBridge",
    "QuotaExceededError",
    "TokenUsage",
]
