"""Rate Limit Tracking & Header Parsing (§1.9).

Captures upstream provider rate limit telemetry from x-ratelimit-* response headers:
RPM, RPH, TPM, TPH limits, remaining capacity, and reset windows.
Provides pre-call rate-limiting guards and formatted summaries.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RateLimitBucket:
    limit: int = 0
    remaining: int = 0
    reset_seconds: float = 0.0
    captured_at: float = field(default_factory=time.time)

    @property
    def used(self) -> int:
        return max(0, self.limit - self.remaining)

    @property
    def usage_pct(self) -> float:
        if self.limit <= 0:
            return 0.0
        return round((self.used / self.limit) * 100.0, 2)

    def remaining_seconds_now(self) -> float:
        elapsed = time.time() - self.captured_at
        return max(0.0, self.reset_seconds - elapsed)


@dataclass
class RateLimitState:
    provider: str = "generic"
    requests_min: RateLimitBucket = field(default_factory=RateLimitBucket)
    requests_hour: RateLimitBucket = field(default_factory=RateLimitBucket)
    tokens_min: RateLimitBucket = field(default_factory=RateLimitBucket)
    tokens_hour: RateLimitBucket = field(default_factory=RateLimitBucket)


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class RateLimitTracker:
    """Tracks rate limits per provider and provides preemptive pause checks."""

    def __init__(self) -> None:
        self.states_by_provider: Dict[str, RateLimitState] = {}

    def get_state(self, provider: str = "generic") -> RateLimitState:
        if provider not in self.states_by_provider:
            self.states_by_provider[provider] = RateLimitState(provider=provider)
        return self.states_by_provider[provider]

    def update_from_headers(self, headers: Dict[str, str], provider: str = "generic") -> RateLimitState:
        # Standardize header keys to lowercase
        norm_headers = {k.lower(): v for k, v in headers.items()}
        state = self.get_state(provider)
        now = time.time()

        # 1. RPM (Requests per minute)
        rpm_limit = _safe_int(norm_headers.get("x-ratelimit-limit-requests"))
        rpm_rem = _safe_int(norm_headers.get("x-ratelimit-remaining-requests"))
        rpm_reset = _safe_float(norm_headers.get("x-ratelimit-reset-requests"))
        if rpm_limit > 0:
            state.requests_min = RateLimitBucket(rpm_limit, rpm_rem, rpm_reset, now)

        # 2. RPH (Requests per hour)
        rph_limit = _safe_int(norm_headers.get("x-ratelimit-limit-requests-1h"))
        rph_rem = _safe_int(norm_headers.get("x-ratelimit-remaining-requests-1h"))
        rph_reset = _safe_float(norm_headers.get("x-ratelimit-reset-requests-1h"))
        if rph_limit > 0:
            state.requests_hour = RateLimitBucket(rph_limit, rph_rem, rph_reset, now)

        # 3. TPM (Tokens per minute)
        tpm_limit = _safe_int(norm_headers.get("x-ratelimit-limit-tokens"))
        tpm_rem = _safe_int(norm_headers.get("x-ratelimit-remaining-tokens"))
        tpm_reset = _safe_float(norm_headers.get("x-ratelimit-reset-tokens"))
        if tpm_limit > 0:
            state.tokens_min = RateLimitBucket(tpm_limit, tpm_rem, tpm_reset, now)

        # 4. TPH (Tokens per hour)
        tph_limit = _safe_int(norm_headers.get("x-ratelimit-limit-tokens-1h"))
        tph_rem = _safe_int(norm_headers.get("x-ratelimit-remaining-tokens-1h"))
        tph_reset = _safe_float(norm_headers.get("x-ratelimit-reset-tokens-1h"))
        if tph_limit > 0:
            state.tokens_hour = RateLimitBucket(tph_limit, tph_rem, tph_reset, now)

        return state

    def should_pause(self, provider: str = "generic", min_remaining_requests: int = 2) -> bool:
        """True if any active bucket is exhausted below safety threshold."""
        state = self.get_state(provider)
        if state.requests_min.limit > 0 and state.requests_min.remaining < min_remaining_requests:
            if state.requests_min.remaining_seconds_now() > 0:
                return True
        if state.tokens_min.limit > 0 and state.tokens_min.remaining < 500:
            if state.tokens_min.remaining_seconds_now() > 0:
                return True
        return False

    def format_summary(self, provider: str = "generic") -> str:
        state = self.get_state(provider)
        parts = [f"Provider: {provider}"]
        if state.requests_min.limit > 0:
            parts.append(f"RPM: {state.requests_min.remaining}/{state.requests_min.limit} ({state.requests_min.usage_pct}% used)")
        if state.tokens_min.limit > 0:
            parts.append(f"TPM: {state.tokens_min.remaining}/{state.tokens_min.limit} ({state.tokens_min.usage_pct}% used)")
        return " | ".join(parts)
