import pytest
import time
from sidecar.rate_limiter import (
    RateLimitBucket,
    RateLimitState,
    RateLimitTracker,
)


def test_bucket_properties():
    now = time.time()
    bucket = RateLimitBucket(limit=60, remaining=45, reset_seconds=15.0, captured_at=now)
    assert bucket.used == 15
    assert bucket.usage_pct == 25.0
    assert bucket.remaining_seconds_now() <= 15.0


def test_update_from_headers():
    tracker = RateLimitTracker()
    headers = {
        "X-RateLimit-Limit-Requests": "100",
        "X-RateLimit-Remaining-Requests": "80",
        "X-RateLimit-Reset-Requests": "12.5",
        "X-RateLimit-Limit-Tokens": "50000",
        "X-RateLimit-Remaining-Tokens": "42000",
        "X-RateLimit-Reset-Tokens": "8.0",
    }
    state = tracker.update_from_headers(headers, provider="anthropic")
    assert state.requests_min.limit == 100
    assert state.requests_min.remaining == 80
    assert state.tokens_min.limit == 50000
    assert state.tokens_min.remaining == 42000
    assert not tracker.should_pause(provider="anthropic")


def test_should_pause_when_exhausted():
    tracker = RateLimitTracker()
    headers = {
        "x-ratelimit-limit-requests": "60",
        "x-ratelimit-remaining-requests": "1",  # below min_remaining=2
        "x-ratelimit-reset-requests": "30.0",
    }
    tracker.update_from_headers(headers, provider="openai")
    assert tracker.should_pause(provider="openai", min_remaining_requests=2)
    summary = tracker.format_summary("openai")
    assert "RPM: 1/60" in summary
