"""
Unit tests for SPEC §1.9 / F-0009 / US-28: Rate Limit Tracking.
Asserts core logic, 12-header parsing, boundary conditions, pre-call throttling, and off-switch behavior.
"""
from __future__ import annotations

import time
import pytest

from sidecar.providers.rate_limit import (
    BaseRateLimitProvider,
    RateLimitBucket,
    RateLimitState,
)
from sidecar.rate_limiter import (
    RateLimitTrackerProvider,
    format_rate_limit_display,
    parse_rate_limit_headers,
    should_throttle,
)
from sidecar.registry import get_registry
from sidecar import config


def test_rate_limit_bucket_used_computation():
    """SPEC §1.9 line 2225: "COMPUTED: used = max(0, limit - remaining)"."""
    # Standard usage
    b1 = RateLimitBucket(limit=60, remaining=45)
    assert b1.used == 15

    # Remaining equals limit (zero used)
    b2 = RateLimitBucket(limit=60, remaining=60)
    assert b2.used == 0

    # Remaining exceeds limit (defensive clamp to 0)
    b3 = RateLimitBucket(limit=60, remaining=70)
    assert b3.used == 0

    # Zero limit
    b4 = RateLimitBucket(limit=0, remaining=0)
    assert b4.used == 0


def test_rate_limit_bucket_usage_pct_computation():
    """SPEC §1.9 line 2226: "COMPUTED: usage_pct = (used / limit) * 100"."""
    b1 = RateLimitBucket(limit=60, remaining=15)
    # used = 45, 45/60 = 0.75 -> 75.0%
    assert b1.usage_pct == 75.0

    b2 = RateLimitBucket(limit=100, remaining=0)
    assert b2.usage_pct == 100.0

    # Zero limit boundary check
    b3 = RateLimitBucket(limit=0, remaining=0)
    assert b3.usage_pct == 0.0


def test_rate_limit_bucket_remaining_seconds_now_countdown():
    """SPEC §1.9 line 2227: "COMPUTED: remaining_seconds_now = max(0, reset_seconds - (now - captured_at))"."""
    captured = 1000.0
    reset_sec = 30.0
    bucket = RateLimitBucket(limit=60, remaining=45, reset_seconds=reset_sec, captured_at=captured)

    # 10 seconds later -> 20 seconds remaining
    assert bucket.get_remaining_seconds_now(now=1010.0) == 20.0

    # 30 seconds later -> exactly 0 seconds remaining
    assert bucket.get_remaining_seconds_now(now=1030.0) == 0.0

    # 50 seconds later -> clamped to 0.0
    assert bucket.get_remaining_seconds_now(now=1050.0) == 0.0


def test_rate_limit_state_structure_and_has_data():
    """SPEC §1.9 line 2229: "RateLimitState:"."""
    empty_state = RateLimitState()
    assert not empty_state.has_data
    assert empty_state.requests_min.limit == 0

    state = RateLimitState(
        requests_min=RateLimitBucket(limit=60, remaining=45),
        provider="anthropic",
        captured_at=1000.0,
    )
    assert state.has_data
    d = state.to_dict()
    assert d["provider"] == "anthropic"
    assert d["requests_min"]["limit"] == 60
    assert d["requests_min"]["used"] == 15

    restored = RateLimitState.from_dict(d)
    assert restored.provider == "anthropic"
    assert restored.requests_min.limit == 60
    assert restored.requests_min.remaining == 45


def test_parse_rate_limit_headers_12_canonical_headers():
    """SPEC §1.9 line 2237: "// Extract 12 x-ratelimit-* headers:"."""
    headers = {
        "x-ratelimit-limit-requests": "60",
        "x-ratelimit-remaining-requests": "45",
        "x-ratelimit-reset-requests": "15s",
        "x-ratelimit-limit-requests-1h": "1000",
        "x-ratelimit-remaining-requests-1h": "950",
        "x-ratelimit-reset-requests-1h": "30m",
        "x-ratelimit-limit-tokens": "100000",
        "x-ratelimit-remaining-tokens": "85000",
        "x-ratelimit-reset-tokens": "20s",
        "x-ratelimit-limit-tokens-1h": "1000000",
        "x-ratelimit-remaining-tokens-1h": "900000",
        "x-ratelimit-reset-tokens-1h": "45m",
    }
    state = parse_rate_limit_headers(headers, provider="openai", now=1000.0)
    assert state.provider == "openai"
    assert state.has_data

    # Check RPM bucket
    assert state.requests_min.limit == 60
    assert state.requests_min.remaining == 45
    assert state.requests_min.reset_seconds == 15.0

    # Check RPH bucket
    assert state.requests_hour.limit == 1000
    assert state.requests_hour.remaining == 950
    assert state.requests_hour.reset_seconds == 1800.0

    # Check TPM bucket
    assert state.tokens_min.limit == 100000
    assert state.tokens_min.remaining == 85000
    assert state.tokens_min.reset_seconds == 20.0

    # Check TPH bucket
    assert state.tokens_hour.limit == 1000000
    assert state.tokens_hour.remaining == 900000
    assert state.tokens_hour.reset_seconds == 2700.0


def test_parse_rate_limit_headers_case_insensitivity_and_formatting():
    """SPEC §1.9 line 2236: "FUNCTION parse_rate_limit_headers(response_headers, provider):"."""
    # Mixed case, underscores instead of hyphens, suffix numbers (e.g. 100k, 1M)
    headers = {
        "X_RateLimit_Limit_Requests": "100",
        "X-RATELIMIT-REMAINING-REQUESTS": "80",
        "X-RateLimit-Reset-Requests": "32.5",
        "X-RateLimit-Limit-Tokens": "100k",
        "X-RateLimit-Remaining-Tokens": "75k",
        "X-RateLimit-Reset-Tokens": "1m30s",
    }
    state = parse_rate_limit_headers(headers, provider="nous", now=1000.0)
    assert state.requests_min.limit == 100
    assert state.requests_min.remaining == 80
    assert state.requests_min.reset_seconds == 32.5

    assert state.tokens_min.limit == 100000
    assert state.tokens_min.remaining == 75000
    assert state.tokens_min.reset_seconds == 90.0


def test_parse_rate_limit_headers_epoch_timestamps():
    """SPEC §1.9 line 2236: "FUNCTION parse_rate_limit_headers(response_headers, provider):"."""
    fixed_now = 1700000000.0
    future_epoch = fixed_now + 42.0
    headers = {
        "x-ratelimit-limit-requests": "60",
        "x-ratelimit-remaining-requests": "50",
        "x-ratelimit-reset-requests": str(future_epoch),
    }
    state = parse_rate_limit_headers(headers, provider="openrouter", now=fixed_now)
    assert state.requests_min.reset_seconds == 42.0


def test_format_rate_limit_display_empty():
    """SPEC §1.9 line 2250: "FUNCTION format_rate_limit_display(state):"."""
    assert format_rate_limit_display(None) == "No rate limit data"
    assert format_rate_limit_display(RateLimitState()) == "No rate limit data"


def test_format_rate_limit_display_populated():
    """SPEC §1.9 line 2250: "FUNCTION format_rate_limit_display(state):"."""
    now = time.time()
    state = RateLimitState(
        requests_min=RateLimitBucket(limit=60, remaining=15, reset_seconds=32.0, captured_at=now),
        tokens_min=RateLimitBucket(limit=100000, remaining=88000, reset_seconds=45.0, captured_at=now),
    )
    display = format_rate_limit_display(state)
    assert "RPM: 45/60 (75%)" in display
    assert "TPM: 12K/100K (12%)" in display
    assert "resets 32s" in display


def test_should_throttle_under_safety_margin():
    """SPEC §1.9 line 2260: "FUNCTION should_throttle(state, safety_margin=0.1):"."""
    now = time.time()
    # RPM limit=60, remaining=5 (< 10% of 60 = 6) -> throttle!
    state = RateLimitState(
        requests_min=RateLimitBucket(limit=60, remaining=5, reset_seconds=18.0, captured_at=now),
        tokens_min=RateLimitBucket(limit=100000, remaining=50000, reset_seconds=10.0, captured_at=now),
    )
    throttled, sleep_sec = should_throttle(state, safety_margin=0.1)
    assert throttled is True
    assert 17.0 <= sleep_sec <= 18.0


def test_should_throttle_under_tokens_threshold():
    """SPEC §1.9 line 2260: "FUNCTION should_throttle(state, safety_margin=0.1):"."""
    now = time.time()
    # Tokens remaining = 500 (< 1000) -> throttle!
    state = RateLimitState(
        requests_min=RateLimitBucket(limit=60, remaining=40, reset_seconds=10.0, captured_at=now),
        tokens_min=RateLimitBucket(limit=100000, remaining=500, reset_seconds=25.0, captured_at=now),
    )
    throttled, sleep_sec = should_throttle(state, safety_margin=0.1)
    assert throttled is True
    assert 24.0 <= sleep_sec <= 25.0


def test_should_throttle_safe_conditions():
    """SPEC §1.9 line 2260: "FUNCTION should_throttle(state, safety_margin=0.1):"."""
    now = time.time()
    # Plentiful requests and tokens
    state = RateLimitState(
        requests_min=RateLimitBucket(limit=60, remaining=50, reset_seconds=10.0, captured_at=now),
        tokens_min=RateLimitBucket(limit=100000, remaining=80000, reset_seconds=10.0, captured_at=now),
    )
    throttled, sleep_sec = should_throttle(state, safety_margin=0.1)
    assert throttled is False
    assert sleep_sec == 0.0


def test_rate_limit_tracker_provider_lifecycle():
    """SPEC §1.9 line 2269: "Provider Interface: RateLimitTracker (singleton per session). Reads headers via Pi's afterToolCall / response hooks."."""
    reg = get_registry()
    provider_cls = reg.get("rate_limit", "default")
    assert provider_cls is not None
    provider: BaseRateLimitProvider = provider_cls()

    provider.reset("test-prov")
    headers = {
        "x-ratelimit-limit-requests": "100",
        "x-ratelimit-remaining-requests": "90",
        "x-ratelimit-reset-requests": "10",
    }
    parsed = provider.parse_headers(headers, provider="test-prov")
    assert parsed.requests_min.limit == 100

    stored = provider.get_state("test-prov")
    assert stored.requests_min.remaining == 90

    display = provider.format_display(provider="test-prov")
    assert "RPM: 10/100 (10%)" in display

    throttled, _ = provider.should_throttle(provider="test-prov")
    assert throttled is False

    provider.reset("test-prov")
    cleared = provider.get_state("test-prov")
    assert not cleared.has_data


def test_rate_limit_modular_off_switch_behavior(monkeypatch):
    """SPEC §1.9 line 2271: "Swappable / off state: locus.tracking.rate_limit.enabled. Off → rate limit headers not parsed; TUI footer shows no rate-limit status; no pre-call throttling."."""
    # Test sidecar config flag
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "rate_limit" in key else True)
    assert not config.is_enabled("locus.rate_limit_tracking.enabled")
    assert not config.is_enabled("locus.tracking.rate_limit.enabled")
