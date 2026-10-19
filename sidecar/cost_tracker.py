"""
SPEC §1.10 / F-0010 / US-29: Usage / Cost Tracking Implementation.
Extracts canonical usage from provider responses, resolves model pricing rates,
calculates USD costs per request, and maintains session and daily usage totals.
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
import threading
from typing import Any, Dict, Optional, Tuple

from sidecar import config
from sidecar.providers.cost_tracker import (
    BaseCostTrackerProvider,
    CanonicalUsage,
    CostResult,
    PricingEntry,
)
from sidecar.registry import get_registry

# Official pricing database snapshot (USD per million tokens)
OFFICIAL_PRICING_SNAPSHOT: Dict[str, Dict[str, float]] = {
    # Anthropic
    "claude-3-5-sonnet": {
        "input": 3.00,
        "output": 15.00,
        "cache_read": 0.30,
        "cache_write": 3.75,
    },
    "claude-3-7-sonnet": {
        "input": 3.00,
        "output": 15.00,
        "cache_read": 0.30,
        "cache_write": 3.75,
    },
    "claude-3-opus": {
        "input": 15.00,
        "output": 75.00,
        "cache_read": 1.50,
        "cache_write": 18.75,
    },
    "claude-3-5-haiku": {
        "input": 0.80,
        "output": 4.00,
        "cache_read": 0.08,
        "cache_write": 1.00,
    },
    "claude-3-haiku": {
        "input": 0.25,
        "output": 1.25,
        "cache_read": 0.03,
        "cache_write": 0.30,
    },
    # OpenAI
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
        "cache_read": 1.25,
        "cache_write": 0.0,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
        "cache_read": 0.075,
        "cache_write": 0.0,
    },
    "o1": {
        "input": 15.00,
        "output": 60.00,
        "cache_read": 7.50,
        "cache_write": 0.0,
    },
    "o1-mini": {
        "input": 1.10,
        "output": 4.40,
        "cache_read": 0.55,
        "cache_write": 0.0,
    },
    "o3-mini": {
        "input": 1.10,
        "output": 4.40,
        "cache_read": 0.55,
        "cache_write": 0.0,
    },
    # Google
    "gemini-1.5-pro": {
        "input": 3.50,
        "output": 10.50,
        "cache_read": 0.875,
        "cache_write": 0.0,
    },
    "gemini-1.5-flash": {
        "input": 0.075,
        "output": 0.30,
        "cache_read": 0.01875,
        "cache_write": 0.0,
    },
    "gemini-2.0-flash": {
        "input": 0.10,
        "output": 0.40,
        "cache_read": 0.025,
        "cache_write": 0.0,
    },
    "gemini-2.0-pro": {
        "input": 2.50,
        "output": 10.00,
        "cache_read": 0.625,
        "cache_write": 0.0,
    },
}


def extract_canonical_usage(
    raw_response: Dict[str, Any], provider: str = ""
) -> CanonicalUsage:
    """
    SPEC §1.10 line 2314:
    FUNCTION extract_canonical_usage(raw_response, provider):
        // Normalize provider-specific usage formats into CanonicalUsage
        // Anthropic: usage.input_tokens, usage.output_tokens, usage.cache_creation_input_tokens
        // OpenAI: usage.prompt_tokens, usage.completion_tokens, usage.prompt_tokens_details.cached_tokens
        // Google: usageMetadata.promptTokenCount, candidatesTokenCount
    """
    if not raw_response or not isinstance(raw_response, dict):
        return CanonicalUsage()

    prov = (provider or "").strip().lower()

    # 1. Direct or Pi format check
    usage_block = raw_response.get("usage")
    if not isinstance(usage_block, dict):
        # Check google style metadata
        usage_block = raw_response.get("usageMetadata") or raw_response.get("usage_metadata") or raw_response

    input_tok = 0
    output_tok = 0
    cache_read = 0
    cache_write = 0
    reasoning_tok = 0

    if isinstance(usage_block, dict):
        # Anthropic format
        if "input_tokens" in usage_block or "output_tokens" in usage_block:
            input_tok = int(usage_block.get("input_tokens", 0))
            output_tok = int(usage_block.get("output_tokens", 0))
            cache_write = int(usage_block.get("cache_creation_input_tokens", 0))
            cache_read = int(usage_block.get("cache_read_input_tokens", 0))

        # OpenAI format
        elif "prompt_tokens" in usage_block or "completion_tokens" in usage_block:
            raw_prompt = int(usage_block.get("prompt_tokens", 0))
            output_tok = int(usage_block.get("completion_tokens", 0))
            p_details = usage_block.get("prompt_tokens_details") or {}
            if isinstance(p_details, dict):
                cache_read = int(p_details.get("cached_tokens", 0))
            c_details = usage_block.get("completion_tokens_details") or {}
            if isinstance(c_details, dict):
                reasoning_tok = int(c_details.get("reasoning_tokens", 0))
            # Base input without cached tokens
            input_tok = max(0, raw_prompt - cache_read)

        # Google / Gemini format
        elif "promptTokenCount" in usage_block or "prompt_token_count" in usage_block:
            input_tok = int(usage_block.get("promptTokenCount", usage_block.get("prompt_token_count", 0)))
            output_tok = int(usage_block.get("candidatesTokenCount", usage_block.get("candidates_token_count", 0)))
            cache_read = int(usage_block.get("cachedContentTokenCount", usage_block.get("cached_content_token_count", 0)))
            if cache_read > 0 and input_tok >= cache_read:
                input_tok = max(0, input_tok - cache_read)

        # Pi response metadata format
        elif "input" in usage_block or "output" in usage_block:
            input_tok = int(usage_block.get("input", 0))
            output_tok = int(usage_block.get("output", 0))
            cache_read = int(usage_block.get("cacheRead", 0))
            cache_write = int(usage_block.get("cacheWrite", 0))

    return CanonicalUsage(
        input_tokens=max(0, input_tok),
        output_tokens=max(0, output_tok),
        cache_read_tokens=max(0, cache_read),
        cache_write_tokens=max(0, cache_write),
        reasoning_tokens=max(0, reasoning_tok),
        request_count=1,
    )


def resolve_pricing(
    model: str,
    provider: str = "",
    base_url: Optional[str] = None,
    user_overrides: Optional[Dict[str, PricingEntry]] = None,
) -> PricingEntry:
    """
    SPEC §1.10 line 2322:
    FUNCTION resolve_pricing(provider, model, base_url):
        // Priority: user_override > provider_cost_api > official_docs_snapshot > unknown
    """
    normalized_model = (model or "").strip().lower()

    # Priority 1: User override
    if user_overrides and normalized_model in user_overrides:
        return user_overrides[normalized_model]
    config_override = config.get(f"locus.pricing.overrides.{normalized_model}")
    if isinstance(config_override, dict):
        return PricingEntry.from_dict({**config_override, "source": "user_override"})

    # Priority 2: Match against official docs snapshot
    # Try exact match first
    if normalized_model in OFFICIAL_PRICING_SNAPSHOT:
        data = OFFICIAL_PRICING_SNAPSHOT[normalized_model]
        return PricingEntry(
            input_cost_per_million=data["input"],
            output_cost_per_million=data["output"],
            cache_read_cost_per_million=data.get("cache_read", 0.0),
            cache_write_cost_per_million=data.get("cache_write", 0.0),
            source="official_docs_snapshot",
        )

    # Prefix / family substring match (e.g. claude-3-5-sonnet-20241022 -> claude-3-5-sonnet)
    for key, data in OFFICIAL_PRICING_SNAPSHOT.items():
        if normalized_model.startswith(key) or key in normalized_model:
            return PricingEntry(
                input_cost_per_million=data["input"],
                output_cost_per_million=data["output"],
                cache_read_cost_per_million=data.get("cache_read", 0.0),
                cache_write_cost_per_million=data.get("cache_write", 0.0),
                source="official_docs_snapshot",
            )

    # Priority 3: Unknown / default free or zero
    return PricingEntry(
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        source="unknown",
    )


def calculate_cost(usage: CanonicalUsage, pricing: PricingEntry) -> CostResult:
    """
    SPEC §1.10 line 2329:
    FUNCTION calculate_cost(usage: CanonicalUsage, pricing: PricingEntry):
        cost = 0
        cost += (usage.input_tokens / 1_000_000) * pricing.input_cost_per_million
        cost += (usage.output_tokens / 1_000_000) * pricing.output_cost_per_million
        IF pricing.cache_read_cost_per_million:
            cost += (usage.cache_read_tokens / 1_000_000) * pricing.cache_read_cost_per_million
        IF pricing.request_cost:
            cost += pricing.request_cost * usage.request_count
        RETURN CostResult(amount_usd=cost, ...)
    """
    cost = 0.0
    cost += (usage.input_tokens / 1_000_000.0) * pricing.input_cost_per_million
    cost += (usage.output_tokens / 1_000_000.0) * pricing.output_cost_per_million

    if pricing.cache_read_cost_per_million > 0:
        cost += (usage.cache_read_tokens / 1_000_000.0) * pricing.cache_read_cost_per_million
    if pricing.cache_write_cost_per_million > 0:
        cost += (usage.cache_write_tokens / 1_000_000.0) * pricing.cache_write_cost_per_million
    if pricing.request_cost > 0:
        cost += pricing.request_cost * usage.request_count

    amount = round(cost, 6)
    status = "actual" if pricing.source in ("user_override", "official_docs_snapshot") else "estimated"
    label = f"${amount:.4f}"

    return CostResult(
        amount_usd=amount,
        status=status,
        source=pricing.source,
        label=label,
    )


def format_usage_display(
    session_usd: float, daily_usd: float, total_tokens: int
) -> str:
    """
    SPEC §1.10 line 2346:
    FUNCTION format_usage_display():
        RETURN "Session: ${session_total:.4f} | Today: ${daily_total:.4f} | Tokens: {total_tokens}"
    """
    tok_formatted = f"{total_tokens:,}"
    return f"Session: ${session_usd:.4f} | Today: ${daily_usd:.4f} | Tokens: {tok_formatted}"


class CostTrackerProvider(BaseCostTrackerProvider):
    """
    SPEC §1.10: Concrete CostTrackerProvider.
    Maintains session accumulation and daily persistence.
    """
    _lock = threading.RLock()
    _session_usd: float = 0.0
    _session_tokens: int = 0
    _daily_usd: float = 0.0
    _overrides: Dict[str, PricingEntry] = {}
    _today_date: str = ""

    def __init__(self) -> None:
        with self._lock:
            current_day = date.today().isoformat()
            if CostTrackerProvider._today_date != current_day:
                CostTrackerProvider._today_date = current_day
                self._load_daily_total(current_day)

    def _get_usage_dir(self) -> Path:
        p = config.get_locus_home() / "usage"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _load_daily_total(self, day_str: str) -> None:
        try:
            log_file = self._get_usage_dir() / f"{day_str}.json"
            if log_file.is_file():
                content = log_file.read_text(encoding="utf-8")
                data = json.loads(content)
                CostTrackerProvider._daily_usd = float(data.get("daily_total_usd", 0.0))
            else:
                CostTrackerProvider._daily_usd = 0.0
        except Exception:
            CostTrackerProvider._daily_usd = 0.0

    def _persist_daily_log(self, cost: float, tokens: int) -> None:
        try:
            day_str = date.today().isoformat()
            log_file = self._get_usage_dir() / f"{day_str}.json"
            current_log: Dict[str, Any] = {"daily_total_usd": CostTrackerProvider._daily_usd, "records": []}
            if log_file.is_file():
                try:
                    loaded = json.loads(log_file.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        current_log = loaded
                except Exception:
                    pass
            current_log["daily_total_usd"] = round(CostTrackerProvider._daily_usd, 6)
            records = current_log.get("records") or []
            records.append({"amount_usd": cost, "tokens": tokens})
            current_log["records"] = records[-500:]  # keep recent 500 records
            log_file.write_text(json.dumps(current_log, indent=2), encoding="utf-8")
        except Exception:
            pass

    def extract_usage(
        self, raw_response: Dict[str, Any], provider: str = ""
    ) -> CanonicalUsage:
        return extract_canonical_usage(raw_response, provider=provider)

    def resolve_pricing(
        self, model: str, provider: str = "", base_url: Optional[str] = None
    ) -> PricingEntry:
        with self._lock:
            return resolve_pricing(
                model=model,
                provider=provider,
                base_url=base_url,
                user_overrides=CostTrackerProvider._overrides,
            )

    def calculate_cost(
        self, usage: CanonicalUsage, pricing: PricingEntry
    ) -> CostResult:
        return calculate_cost(usage, pricing)

    def record_usage(
        self, usage: CanonicalUsage, model: str, provider: str = ""
    ) -> CostResult:
        with self._lock:
            pricing = self.resolve_pricing(model=model, provider=provider)
            res = self.calculate_cost(usage, pricing)
            CostTrackerProvider._session_usd += res.amount_usd
            CostTrackerProvider._session_tokens += usage.total_tokens
            CostTrackerProvider._daily_usd += res.amount_usd
            self._persist_daily_log(res.amount_usd, usage.total_tokens)
            return res

    def get_session_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_usd": round(CostTrackerProvider._session_usd, 6),
                "session_tokens": CostTrackerProvider._session_tokens,
                "daily_usd": round(CostTrackerProvider._daily_usd, 6),
                "display": self.format_usage_display(),
            }

    def format_usage_display(self) -> str:
        with self._lock:
            return format_usage_display(
                session_usd=CostTrackerProvider._session_usd,
                daily_usd=CostTrackerProvider._daily_usd,
                total_tokens=CostTrackerProvider._session_tokens,
            )

    def set_pricing_override(self, model: str, pricing: PricingEntry) -> None:
        with self._lock:
            norm = (model or "").strip().lower()
            if norm:
                CostTrackerProvider._overrides[norm] = pricing

    def reset_session(self) -> None:
        with self._lock:
            CostTrackerProvider._session_usd = 0.0
            CostTrackerProvider._session_tokens = 0


# Register default provider
get_registry().register("cost_tracker", "default", CostTrackerProvider)
get_registry().register("usage_cost", "default", CostTrackerProvider)
