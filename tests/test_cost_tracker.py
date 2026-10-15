import pytest
from sidecar.cost_tracker import (
    CanonicalUsage,
    PricingEntry,
    CostResult,
    calculate_request_cost,
    CostTracker,
)


def test_canonical_usage_properties():
    usage = CanonicalUsage(
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=200,
        cache_write_tokens=100,
        reasoning_tokens=50,
    )
    assert usage.prompt_tokens == 1300
    assert usage.total_tokens == 1850


def test_calculate_request_cost():
    usage = CanonicalUsage(input_tokens=1_000_000, output_tokens=1_000_000)
    pricing = PricingEntry(input_per_million=2.00, output_per_million=8.00)
    res = calculate_request_cost(usage, pricing)
    assert res.amount_usd == 10.00
    assert res.status == "actual"


def test_cost_tracker_aggregation():
    tracker = CostTracker()
    # DeepSeek flash turn: 10,000 prompt tokens, 500 output tokens
    res = tracker.record_usage(
        model="deepseek-chat",
        usage=CanonicalUsage(input_tokens=10_000, output_tokens=500),
    )
    assert res.amount_usd > 0.0
    assert tracker.total_cost_usd > 0.0
    assert "deepseek-chat" in tracker.cost_by_model

    summary = tracker.format_usage_summary()
    assert "Total Spend:" in summary
    assert "Tokens:" in summary
