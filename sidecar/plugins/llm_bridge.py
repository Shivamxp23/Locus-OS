"""Locus Plugin LLM Sandboxing & Auxiliary Bridge (§9.9).

Provides third-party and workspace plugins with scoped, rate-limited, and quota-capped
LLM generation capabilities while preventing prompt injection, leaking master context,
or exceeding tenant budgets.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PluginQuotaPolicy:
    max_requests_per_minute: int = 30
    max_tokens_per_hour: int = 50000
    allowed_models: List[str] = field(default_factory=lambda: ["mock-small-fast", "claude-3-haiku"])
    require_approval_above_tokens: int = 2000


class PluginLLMBridge:
    """Brokers LLM requests from plugins through security and quota checkpoints."""

    def __init__(self, default_policy: Optional[PluginQuotaPolicy] = None):
        self.default_policy = default_policy or PluginQuotaPolicy()
        self.plugin_policies: Dict[str, PluginQuotaPolicy] = {}
        self.plugin_usage: Dict[str, Dict[str, Any]] = {}

    def register_plugin(self, plugin_id: str, policy: Optional[PluginQuotaPolicy] = None) -> None:
        self.plugin_policies[plugin_id] = policy or self.default_policy
        self.plugin_usage[plugin_id] = {
            "tokens_used": 0,
            "requests_count": 0,
            "last_request_time": 0.0,
        }

    def generate_completion(
        self,
        plugin_id: str,
        prompt: str,
        model: str = "mock-small-fast",
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        if plugin_id not in self.plugin_policies:
            self.register_plugin(plugin_id)

        policy = self.plugin_policies[plugin_id]
        usage = self.plugin_usage[plugin_id]
        now = time.time()

        # Check model whitelist
        if model not in policy.allowed_models:
            return {
                "success": False,
                "error": f"Model '{model}' not permitted for plugin. Allowed: {policy.allowed_models}",
            }

        # Check rate limit
        if now - usage["last_request_time"] < (60.0 / policy.max_requests_per_minute):
            return {
                "success": False,
                "error": "Rate limit exceeded for plugin",
            }

        # Check token quota
        est_tokens = len(prompt.split()) + max_tokens
        if usage["tokens_used"] + est_tokens > policy.max_tokens_per_hour:
            return {
                "success": False,
                "error": "Hourly token quota exceeded for plugin",
            }

        # Sanitize prompt against system escape sequences
        sanitized_prompt = prompt.replace("<<SYS>>", "").replace("<|im_start|>", "")

        # Execute completion (simulated)
        completion_text = f"Plugin [{plugin_id}] LLM Response for: {sanitized_prompt[:40]}..."
        actual_tokens = len(prompt.split()) + len(completion_text.split())

        usage["tokens_used"] += actual_tokens
        usage["requests_count"] += 1
        usage["last_request_time"] = now

        return {
            "success": True,
            "plugin_id": plugin_id,
            "model": model,
            "completion": completion_text,
            "tokens_consumed": actual_tokens,
        }
