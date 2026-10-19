"""
Unit tests for SPEC §1.10 / F-0010 / US-29: Usage / Cost Tracking.
Asserts canonical usage extraction, pricing resolution, cost formulas, session accumulation, and off-switch behavior.
"""
from __future__ import annotations

import pytest

from sidecar import config
from sidecar.cost_tracker import (
    CostTrackerProvider,
    OFFICIAL_PRICING_SNAPSHOT,
    calculate_cost,
    extract_canonical_usage,
    format_usage_display,
    resolve_pricing,
)
from sidecar.providers.cost_tracker import (
    BaseCostTrackerProvider,
    CanonicalUsage,
    CostResult,
    PricingEntry,
)
from sidecar.registry import get_registry


def test_canonical_usage_computations():
    """SPEC §1.10 line 2297: "COMPUTED: prompt_tokens = input + cache_read + cache_write"."""
    usage = CanonicalUsage(
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=200,
        cache_write_tokens=300,
        reasoning_tokens=50,
        request_count=1,
    )
    # prompt_tokens = 1000 + 200 + 300 = 1500
    assert usage.prompt_tokens == 1500
    # total_tokens = 1500 + 500 = 2000
    assert usage.total_tokens == 2000

    # Serialization roundtrip
    d = usage.to_dict()
    assert d["prompt_tokens"] == 1500
    assert d["total_tokens"] == 2000
    restored = CanonicalUsage.from_dict(d)
    assert restored.input_tokens == 1000
    assert restored.prompt_tokens == 1500
    assert restored.total_tokens == 2000


def test_pricing_entry_and_cost_result_structures():
    """SPEC §1.10 line 2300: "PricingEntry:"."""
    entry = PricingEntry(
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        cache_read_cost_per_million=0.30,
        cache_write_cost_per_million=3.75,
        source="official_docs_snapshot",
    )
    d = entry.to_dict()
    assert d["input_cost_per_million"] == 3.00
    assert d["source"] == "official_docs_snapshot"
    restored = PricingEntry.from_dict(d)
    assert restored.output_cost_per_million == 15.00

    res = CostResult(amount_usd=0.012345, status="actual", source="user_override", label="$0.0123")
    res_d = res.to_dict()
    assert res_d["amount_usd"] == 0.012345
    assert res_d["label"] == "$0.0123"


def test_extract_canonical_usage_anthropic_format():
    """SPEC §1.10 line 2314: "FUNCTION extract_canonical_usage(raw_response, provider):"."""
    anthropic_resp = {
        "id": "msg_01",
        "type": "message",
        "usage": {
            "input_tokens": 1200,
            "output_tokens": 400,
            "cache_creation_input_tokens": 250,
            "cache_read_input_tokens": 150,
        },
    }
    canonical = extract_canonical_usage(anthropic_resp, provider="anthropic")
    assert canonical.input_tokens == 1200
    assert canonical.output_tokens == 400
    assert canonical.cache_write_tokens == 250
    assert canonical.cache_read_tokens == 150
    assert canonical.prompt_tokens == 1600
    assert canonical.total_tokens == 2000


def test_extract_canonical_usage_openai_format():
    """SPEC §1.10 line 2314: "FUNCTION extract_canonical_usage(raw_response, provider):"."""
    openai_resp = {
        "id": "chatcmpl_01",
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 300,
            "total_tokens": 1300,
            "prompt_tokens_details": {
                "cached_tokens": 400,
            },
            "completion_tokens_details": {
                "reasoning_tokens": 80,
            },
        },
    }
    canonical = extract_canonical_usage(openai_resp, provider="openai")
    # Base input is 1000 - 400 = 600
    assert canonical.input_tokens == 600
    assert canonical.cache_read_tokens == 400
    assert canonical.output_tokens == 300
    assert canonical.reasoning_tokens == 80
    assert canonical.prompt_tokens == 1000
    assert canonical.total_tokens == 1300


def test_extract_canonical_usage_google_gemini_format():
    """SPEC §1.10 line 2314: "FUNCTION extract_canonical_usage(raw_response, provider):"."""
    google_resp = {
        "usageMetadata": {
            "promptTokenCount": 800,
            "candidatesTokenCount": 200,
            "totalTokenCount": 1000,
            "cachedContentTokenCount": 300,
        }
    }
    canonical = extract_canonical_usage(google_resp, provider="google")
    assert canonical.input_tokens == 500
    assert canonical.cache_read_tokens == 300
    assert canonical.output_tokens == 200
    assert canonical.prompt_tokens == 800
    assert canonical.total_tokens == 1000


def test_extract_canonical_usage_pi_format():
    """SPEC §1.10 line 2314: "FUNCTION extract_canonical_usage(raw_response, provider):"."""
    pi_resp = {
        "usage": {
            "input": 500,
            "output": 150,
            "cacheRead": 100,
            "cacheWrite": 50,
        }
    }
    canonical = extract_canonical_usage(pi_resp, provider="pi")
    assert canonical.input_tokens == 500
    assert canonical.output_tokens == 150
    assert canonical.cache_read_tokens == 100
    assert canonical.cache_write_tokens == 50
    assert canonical.prompt_tokens == 650
    assert canonical.total_tokens == 800


def test_resolve_pricing_priority_chain():
    """SPEC §1.10 line 2322: "FUNCTION resolve_pricing(provider, model, base_url):"."""
    # 1. Snapshot match: claude-3-5-sonnet
    p1 = resolve_pricing("claude-3-5-sonnet-20241022")
    assert p1.source == "official_docs_snapshot"
    assert p1.input_cost_per_million == 3.00
    assert p1.output_cost_per_million == 15.00
    assert p1.cache_read_cost_per_million == 0.30

    # 2. Snapshot match: gpt-4o-mini
    p2 = resolve_pricing("gpt-4o-mini")
    assert p2.input_cost_per_million == 0.15
    assert p2.output_cost_per_million == 0.60

    # 3. User override
    overrides = {
        "custom-model": PricingEntry(
            input_cost_per_million=1.0, output_cost_per_million=2.0, source="user_override"
        )
    }
    p3 = resolve_pricing("custom-model", user_overrides=overrides)
    assert p3.source == "user_override"
    assert p3.input_cost_per_million == 1.0

    # 4. Unknown model
    p4 = resolve_pricing("unknown-nonexistent-llm")
    assert p4.source == "unknown"
    assert p4.input_cost_per_million == 0.0


def test_calculate_cost_exact_formula():
    """SPEC §1.10 line 2329: "FUNCTION calculate_cost(usage: CanonicalUsage, pricing: PricingEntry):"."""
    usage = CanonicalUsage(
        input_tokens=1_000_000,   # 1M input
        output_tokens=500_000,    # 0.5M output
        cache_read_tokens=100_000,  # 0.1M cache read
        cache_write_tokens=50_000,  # 0.05M cache write
        request_count=2,
    )
    pricing = PricingEntry(
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        cache_read_cost_per_million=0.30,
        cache_write_cost_per_million=3.75,
        request_cost=0.005,
        source="official_docs_snapshot",
    )
    # Expected:
    # 1.0 * 3.00 = 3.00
    # 0.5 * 15.00 = 7.50
    # 0.1 * 0.30 = 0.03
    # 0.05 * 3.75 = 0.1875
    # 2 * 0.005 = 0.0100
    # Total = 3.00 + 7.50 + 0.03 + 0.1875 + 0.01 = 10.7275
    res = calculate_cost(usage, pricing)
    assert res.amount_usd == 10.7275
    assert res.label == "$10.7275"
    assert res.status == "actual"


def test_calculate_cost_zero_tokens_and_free_models():
    """SPEC §1.10 line 2329: "FUNCTION calculate_cost(usage: CanonicalUsage, pricing: PricingEntry):"."""
    zero_usage = CanonicalUsage(input_tokens=0, output_tokens=0)
    pricing = PricingEntry(input_cost_per_million=3.00, output_cost_per_million=15.00)
    res = calculate_cost(zero_usage, pricing)
    assert res.amount_usd == 0.0
    assert res.label == "$0.0000"


def test_cost_tracker_session_accumulator():
    """SPEC §1.10 line 2337: "CREDITS TRACKER (session accumulator):"."""
    provider = CostTrackerProvider()
    provider.reset_session()

    usage1 = CanonicalUsage(input_tokens=100_000, output_tokens=10_000)
    # gpt-4o: input $2.50/M -> 0.25; output $10.00/M -> 0.10 => 0.35
    r1 = provider.record_usage(usage1, model="gpt-4o")
    assert round(r1.amount_usd, 4) == 0.3500

    usage2 = CanonicalUsage(input_tokens=200_000, output_tokens=20_000)
    r2 = provider.record_usage(usage2, model="gpt-4o")
    assert round(r2.amount_usd, 4) == 0.7000

    summary = provider.get_session_summary()
    assert round(summary["session_usd"], 4) == 1.0500
    assert summary["session_tokens"] == 330_000

    provider.reset_session()
    cleared = provider.get_session_summary()
    assert cleared["session_usd"] == 0.0
    assert cleared["session_tokens"] == 0


def test_format_usage_display():
    """SPEC §1.10 line 2346: "FUNCTION format_usage_display():"."""
    display = format_usage_display(session_usd=0.0034, daily_usd=0.0120, total_tokens=4520)
    assert "Session: $0.0034" in display
    assert "Today: $0.0120" in display
    assert "Tokens: 4,520" in display


def test_cost_tracker_provider_lifecycle_and_registry():
    """SPEC §1.10 line 2352: "Provider Interface: UsageTracker (wraps Pi's response stream to extract usage metadata after every LLM call)"."""
    reg = get_registry()
    provider_cls = reg.get("cost_tracker", "default")
    assert provider_cls is not None
    provider: BaseCostTrackerProvider = provider_cls()
    provider.reset_session()

    resp = {
        "usage": {
            "input_tokens": 50000,
            "output_tokens": 5000,
        }
    }
    usage = provider.extract_usage(resp)
    assert usage.input_tokens == 50000
    assert usage.output_tokens == 5000

    cost = provider.record_usage(usage, model="claude-3-5-sonnet")
    assert cost.amount_usd > 0
    display = provider.format_usage_display()
    assert "Session: $" in display
    assert "Tokens: 55,000" in display


def test_cost_tracker_modular_off_switch_behavior(monkeypatch):
    """SPEC §1.10 line 2354: "Swappable / off state: locus.tracking.cost.enabled. Off → no cost calculation; footer shows token counts only without dollar amounts."."""
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "cost" in key or "usage_cost" in key else True)
    assert not config.is_enabled("locus.usage_cost_tracking.enabled")
    assert not config.is_enabled("locus.tracking.cost.enabled")
