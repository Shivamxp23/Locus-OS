"""Canonical Usage & Cost Tracking Engine (§1.10).

Tracks granular token usage (input, output, cache-read, cache-write, reasoning)
and calculates USD expenditures per model tier and session timeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional


@dataclass
class CanonicalUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def prompt_tokens(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens + self.reasoning_tokens


@dataclass
class PricingEntry:
    input_per_million: float = 0.0
    output_per_million: float = 0.0
    cache_read_per_million: float = 0.0
    cache_write_per_million: float = 0.0
    source: str = "official_docs_snapshot"


# Standard reference pricing (per 1M tokens)
DEFAULT_PRICING: Dict[str, PricingEntry] = {
    "deepseek-chat": PricingEntry(0.14, 0.28, 0.014, 0.14),
    "gemini-2.5-pro": PricingEntry(1.25, 5.00, 0.30, 1.25),
    "gemini-2.5-flash": PricingEntry(0.075, 0.30, 0.018, 0.075),
    "claude-3-5-sonnet": PricingEntry(3.00, 15.00, 0.30, 3.75),
    "gpt-4o": PricingEntry(2.50, 10.00, 1.25, 2.50),
}


@dataclass
class CostResult:
    amount_usd: float
    status: str = "actual"  # "actual" | "estimated" | "included" | "unknown"
    usage: CanonicalUsage = field(default_factory=CanonicalUsage)


def calculate_request_cost(
    usage: CanonicalUsage,
    pricing: Optional[PricingEntry] = None,
) -> CostResult:
    p = pricing or PricingEntry(1.0, 3.0)
    cost = (
        (usage.input_tokens / 1_000_000.0) * p.input_per_million
        + (usage.output_tokens / 1_000_000.0) * p.output_per_million
        + (usage.cache_read_tokens / 1_000_000.0) * p.cache_read_per_million
        + (usage.cache_write_tokens / 1_000_000.0) * p.cache_write_per_million
    )
    rounded = float(Decimal(str(cost)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
    return CostResult(amount_usd=rounded, status="actual", usage=usage)


class CostTracker:
    """Aggregates usage and expenditures across sessions, days, and models."""

    def __init__(self, pricing_catalog: Optional[Dict[str, PricingEntry]] = None) -> None:
        self.pricing = pricing_catalog or dict(DEFAULT_PRICING)
        self.total_cost_usd: float = 0.0
        self.total_usage = CanonicalUsage()
        self.cost_by_model: Dict[str, float] = {}
        self.history: List[Dict[str, Any]] = []

    def record_usage(
        self,
        model: str,
        usage: CanonicalUsage,
        session_id: str = "default",
    ) -> CostResult:
        entry = self.pricing.get(model, PricingEntry(0.50, 1.50))
        result = calculate_request_cost(usage, entry)

        self.total_cost_usd = round(self.total_cost_usd + result.amount_usd, 6)
        self.cost_by_model[model] = round(self.cost_by_model.get(model, 0.0) + result.amount_usd, 6)

        self.total_usage.input_tokens += usage.input_tokens
        self.total_usage.output_tokens += usage.output_tokens
        self.total_usage.cache_read_tokens += usage.cache_read_tokens
        self.total_usage.cache_write_tokens += usage.cache_write_tokens
        self.total_usage.reasoning_tokens += usage.reasoning_tokens

        self.history.append({
            "session_id": session_id,
            "model": model,
            "cost_usd": result.amount_usd,
            "tokens": usage.total_tokens,
        })
        return result

    def format_usage_summary(self) -> str:
        lines = [
            f"Total Spend: ${self.total_cost_usd:.4f}",
            f"Tokens: {self.total_usage.total_tokens:,} (Prompt: {self.total_usage.prompt_tokens:,}, Output: {self.total_usage.output_tokens:,})",
        ]
        if self.cost_by_model:
            lines.append("By Model: " + ", ".join(f"{m}: ${c:.4f}" for m, c in self.cost_by_model.items()))
        return " | ".join(lines)
