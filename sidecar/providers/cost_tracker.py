"""
SPEC §1.10 / F-0010 / US-29: Usage / Cost Tracking Provider Contracts.
Defines CanonicalUsage, PricingEntry, CostResult, and BaseCostTrackerProvider.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class CanonicalUsage:
    """
    SPEC §1.10 line 2290:
    CanonicalUsage:
        input_tokens: int
        output_tokens: int
        cache_read_tokens: int
        cache_write_tokens: int
        reasoning_tokens: int
        request_count: int = 1
        COMPUTED: prompt_tokens = input + cache_read + cache_write
        COMPUTED: total_tokens = prompt_tokens + output_tokens
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_tokens: int = 0
    request_count: int = 1

    @property
    def prompt_tokens(self) -> int:
        """SPEC §1.10 line 2297: COMPUTED: prompt_tokens = input + cache_read + cache_write"""
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    @property
    def total_tokens(self) -> int:
        """SPEC §1.10 line 2298: COMPUTED: total_tokens = prompt_tokens + output_tokens"""
        return self.prompt_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "request_count": self.request_count,
            "prompt_tokens": self.prompt_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CanonicalUsage:
        if not data:
            return cls()
        return cls(
            input_tokens=int(data.get("input_tokens", 0)),
            output_tokens=int(data.get("output_tokens", 0)),
            cache_read_tokens=int(data.get("cache_read_tokens", 0)),
            cache_write_tokens=int(data.get("cache_write_tokens", 0)),
            reasoning_tokens=int(data.get("reasoning_tokens", 0)),
            request_count=int(data.get("request_count", 1)),
        )


@dataclass
class PricingEntry:
    """
    SPEC §1.10 line 2300:
    PricingEntry:
        input_cost_per_million: Decimal     // e.g. $3.00/M for Claude Sonnet
        output_cost_per_million: Decimal    // e.g. $15.00/M
        cache_read_cost_per_million: Decimal
        cache_write_cost_per_million: Decimal
        request_cost: Decimal               // flat per-request fee (some providers)
        source: "provider_cost_api" | "official_docs_snapshot" | "user_override"
    """
    input_cost_per_million: float = 0.0
    output_cost_per_million: float = 0.0
    cache_read_cost_per_million: float = 0.0
    cache_write_cost_per_million: float = 0.0
    request_cost: float = 0.0
    source: str = "official_docs_snapshot"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_cost_per_million": self.input_cost_per_million,
            "output_cost_per_million": self.output_cost_per_million,
            "cache_read_cost_per_million": self.cache_read_cost_per_million,
            "cache_write_cost_per_million": self.cache_write_cost_per_million,
            "request_cost": self.request_cost,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PricingEntry:
        if not data:
            return cls()
        return cls(
            input_cost_per_million=float(data.get("input_cost_per_million", 0.0)),
            output_cost_per_million=float(data.get("output_cost_per_million", 0.0)),
            cache_read_cost_per_million=float(data.get("cache_read_cost_per_million", 0.0)),
            cache_write_cost_per_million=float(data.get("cache_write_cost_per_million", 0.0)),
            request_cost=float(data.get("request_cost", 0.0)),
            source=str(data.get("source", "official_docs_snapshot")),
        )


@dataclass
class CostResult:
    """
    SPEC §1.10 line 2308:
    CostResult:
        amount_usd: Decimal
        status: "actual" | "estimated" | "included" | "unknown"
        source: CostSource
        label: string                       // human-readable (e.g. "$0.0034")
    """
    amount_usd: float = 0.0
    status: str = "estimated"
    source: str = "official_docs_snapshot"
    label: str = "$0.0000"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount_usd": self.amount_usd,
            "status": self.status,
            "source": self.source,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CostResult:
        if not data:
            return cls()
        return cls(
            amount_usd=float(data.get("amount_usd", 0.0)),
            status=str(data.get("status", "estimated")),
            source=str(data.get("source", "official_docs_snapshot")),
            label=str(data.get("label", "$0.0000")),
        )


class BaseCostTrackerProvider(abc.ABC):
    """Abstract interface for usage tracking, pricing resolution, and cost accumulation."""

    @abc.abstractmethod
    def extract_usage(
        self, raw_response: Dict[str, Any], provider: str = ""
    ) -> CanonicalUsage:
        """
        SPEC §1.10 line 2314:
        Normalize provider-specific response usage into CanonicalUsage.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def resolve_pricing(
        self, model: str, provider: str = "", base_url: Optional[str] = None
    ) -> PricingEntry:
        """
        SPEC §1.10 line 2322:
        Resolve pricing entry using priority chain:
        user_override > provider_cost_api > official_docs_snapshot > unknown.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def calculate_cost(
        self, usage: CanonicalUsage, pricing: PricingEntry
    ) -> CostResult:
        """
        SPEC §1.10 line 2329:
        Calculate USD cost from usage and pricing rates.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def record_usage(
        self, usage: CanonicalUsage, model: str, provider: str = ""
    ) -> CostResult:
        """
        SPEC §1.10 line 2337:
        Calculate cost and record against session and daily totals.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_session_summary(self) -> Dict[str, Any]:
        """Return session cumulative tokens, cost, daily total, and formatted string."""
        raise NotImplementedError

    @abc.abstractmethod
    def format_usage_display(self) -> str:
        """
        SPEC §1.10 line 2346:
        Format session and daily cost for TUI/footer display.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_pricing_override(self, model: str, pricing: PricingEntry) -> None:
        """Set user pricing override for a model."""
        raise NotImplementedError

    @abc.abstractmethod
    def reset_session(self) -> None:
        """Clear session cumulative totals."""
        raise NotImplementedError
