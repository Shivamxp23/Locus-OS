"""
SPEC §1.9 / F-0009 / US-28: Rate Limit Tracking Implementation.
Parses 12 x-ratelimit-* headers (RPM/RPH/TPM/TPH caps, remaining, resets),
formats status for display, and provides pre-call guard throttling logic.
"""
from __future__ import annotations

import re
import threading
import time
from typing import Any, Dict, Optional, Tuple

from sidecar.providers.rate_limit import (
    BaseRateLimitProvider,
    RateLimitBucket,
    RateLimitState,
)
from sidecar.registry import get_registry


def _parse_int_value(val: Any) -> int:
    """Safely parse integer or suffixed number (e.g. '100k', '1M', '60')."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return max(0, int(val))
    s = str(val).strip().lower()
    if not s:
        return 0
    multiplier = 1
    if s.endswith("k"):
        multiplier = 1_000
        s = s[:-1].strip()
    elif s.endswith("m"):
        multiplier = 1_000_000
        s = s[:-1].strip()
    try:
        return max(0, int(float(s) * multiplier))
    except (ValueError, TypeError):
        return 0


def _parse_reset_seconds(val: Any, now: float) -> float:
    """
    Safely parse reset duration in seconds from header.
    Can be a number of seconds ('32', 32.5), a unit string ('32s', '2m', '1h'),
    or a unix epoch timestamp (> 1e8).
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        num = float(val)
        if num > 1e8:  # epoch timestamp
            return max(0.0, round(num - now, 3))
        return max(0.0, round(num, 3))
    
    s = str(val).strip().lower()
    if not s:
        return 0.0

    # Duration formats like "1m30s", "30s", "2m", "1h"
    total_sec = 0.0
    matched = False
    
    # Try ISO or simple float/int
    try:
        num = float(s)
        if num > 1e8:
            return max(0.0, round(num - now, 3))
        return max(0.0, round(num, 3))
    except ValueError:
        pass

    # Unit parsing: hours, minutes, seconds, milliseconds
    h_m = re.search(r"(\d+(?:\.\d+)?)\s*h", s)
    if h_m:
        total_sec += float(h_m.group(1)) * 3600.0
        matched = True
    m_m = re.search(r"(\d+(?:\.\d+)?)\s*m(?!s)", s)
    if m_m:
        total_sec += float(m_m.group(1)) * 60.0
        matched = True
    s_m = re.search(r"(\d+(?:\.\d+)?)\s*s(?!e)", s)
    if s_m:
        total_sec += float(s_m.group(1))
        matched = True
    ms_m = re.search(r"(\d+(?:\.\d+)?)\s*ms", s)
    if ms_m:
        total_sec += float(ms_m.group(1)) / 1000.0
        matched = True

    if matched:
        return max(0.0, round(total_sec, 3))
    return 0.0


def _find_header_val(norm_headers: Dict[str, Any], candidates: list[str]) -> Any:
    for c in candidates:
        if c in norm_headers:
            return norm_headers[c]
    return None


def parse_rate_limit_headers(
    response_headers: Dict[str, Any], provider: str = "", now: Optional[float] = None
) -> RateLimitState:
    """
    SPEC §1.9 line 2236:
    FUNCTION parse_rate_limit_headers(response_headers, provider):
        // Extract 12 x-ratelimit-* headers:
        //   x-ratelimit-limit-requests, x-ratelimit-remaining-requests, x-ratelimit-reset-requests
        //   x-ratelimit-limit-requests-1h, x-ratelimit-remaining-requests-1h, x-ratelimit-reset-requests-1h
        //   (same pattern for tokens)
    """
    curr_now = time.time() if now is None else now
    norm_headers: Dict[str, Any] = {}
    if response_headers:
        for k, v in response_headers.items():
            if isinstance(k, str):
                cleaned_key = k.strip().lower().replace("_", "-")
                norm_headers[cleaned_key] = v

    def parse_bucket(metric_prefix: str, hour_suffix: bool = False) -> RateLimitBucket:
        period_variants = ["-1h", "-hour", "_1h", "_hour"] if hour_suffix else ["", "-1m", "-minute"]
        
        limit_keys = [f"x-ratelimit-limit-{metric_prefix}{p}" for p in period_variants]
        rem_keys = [f"x-ratelimit-remaining-{metric_prefix}{p}" for p in period_variants]
        reset_keys = [f"x-ratelimit-reset-{metric_prefix}{p}" for p in period_variants]

        raw_limit = _find_header_val(norm_headers, limit_keys)
        raw_rem = _find_header_val(norm_headers, rem_keys)
        raw_reset = _find_header_val(norm_headers, reset_keys)

        limit_val = _parse_int_value(raw_limit)
        rem_val = _parse_int_value(raw_rem) if raw_rem is not None else limit_val
        reset_sec = _parse_reset_seconds(raw_reset, curr_now)

        return RateLimitBucket(
            limit=limit_val,
            remaining=rem_val,
            reset_seconds=reset_sec,
            captured_at=curr_now,
        )

    return RateLimitState(
        requests_min=parse_bucket("requests", hour_suffix=False),
        requests_hour=parse_bucket("requests", hour_suffix=True),
        tokens_min=parse_bucket("tokens", hour_suffix=False),
        tokens_hour=parse_bucket("tokens", hour_suffix=True),
        provider=provider or "default",
        captured_at=curr_now,
    )


def _format_token_count(n: int) -> str:
    """Format token count e.g. 100000 -> 100K, 1500000 -> 1.5M, 500 -> 500."""
    if n >= 1_000_000:
        val = n / 1_000_000.0
        return f"{val:.1f}M" if val % 1 != 0 else f"{int(val)}M"
    if n >= 1_000:
        val = n / 1_000.0
        return f"{val:.1f}K" if val % 1 != 0 else f"{int(val)}K"
    return str(n)


def format_rate_limit_display(state: Optional[RateLimitState]) -> str:
    """
    SPEC §1.9 line 2250:
    FUNCTION format_rate_limit_display(state):
        IF NOT state.has_data: RETURN "No rate limit data"
        // Format: "RPM: 45/60 (75%) | TPM: 12K/100K (12%) | resets in 32s"
    """
    if not state or not state.has_data:
        return "No rate limit data"

    lines: list[str] = []
    bucket_configs = [
        ("RPM", state.requests_min, False),
        ("RPH", state.requests_hour, False),
        ("TPM", state.tokens_min, True),
        ("TPH", state.tokens_hour, True),
    ]

    for label, bucket, is_token in bucket_configs:
        if bucket.limit > 0:
            used_str = _format_token_count(bucket.used) if is_token else str(bucket.used)
            limit_str = _format_token_count(bucket.limit) if is_token else str(bucket.limit)
            pct_str = f"{bucket.usage_pct:.0f}%" if bucket.usage_pct % 1 == 0 else f"{bucket.usage_pct:.1f}%"
            rem_sec = int(round(bucket.remaining_seconds_now))
            lines.append(f"{label}: {used_str}/{limit_str} ({pct_str}) resets {rem_sec}s")

    if not lines:
        return "No rate limit data"
    return " | ".join(lines)


def should_throttle(
    state: Optional[RateLimitState], safety_margin: float = 0.1
) -> Tuple[bool, float]:
    """
    SPEC §1.9 line 2260:
    PRE-CALL RATE GUARD (from nous_rate_guard.py):
        FUNCTION should_throttle(state, safety_margin=0.1):
            IF state.requests_min.remaining < state.requests_min.limit * safety_margin:
                sleep(state.requests_min.remaining_seconds_now)
            IF state.tokens_min.remaining < 1000:
                sleep(state.tokens_min.remaining_seconds_now)
    """
    if not state or not state.has_data:
        return False, 0.0

    sleep_time = 0.0

    # RPM guard: remaining requests less than safety margin (e.g. 10% of limit)
    if state.requests_min.limit > 0:
        threshold = state.requests_min.limit * safety_margin
        if state.requests_min.remaining < threshold:
            rem = state.requests_min.remaining_seconds_now
            if rem <= 0.0 and state.requests_min.reset_seconds > 0.0 and state.requests_min.captured_at <= 0.0:
                rem = state.requests_min.reset_seconds
            sleep_time = max(sleep_time, rem)

    # TPM guard: remaining tokens under 1000 or safety margin threshold
    if state.tokens_min.limit > 0:
        if state.tokens_min.remaining < 1000:
            rem = state.tokens_min.remaining_seconds_now
            if rem <= 0.0 and state.tokens_min.reset_seconds > 0.0 and state.tokens_min.captured_at <= 0.0:
                rem = state.tokens_min.reset_seconds
            sleep_time = max(sleep_time, rem)

    should_sleep = sleep_time > 0.0
    return should_sleep, round(sleep_time, 3)


class RateLimitTrackerProvider(BaseRateLimitProvider):
    """
    SPEC §1.9: Concrete RateLimitTracker provider.
    Maintains ephemeral thread-safe in-memory rate limit states across sessions.
    """
    _lock = threading.RLock()
    _shared_states: Dict[str, RateLimitState] = {}

    def parse_headers(
        self, response_headers: Dict[str, Any], provider: str = ""
    ) -> RateLimitState:
        with self._lock:
            prov = provider.strip() if provider else "default"
            state = parse_rate_limit_headers(response_headers, provider=prov)
            self._shared_states[prov] = state
            return state

    def get_state(self, provider: str = "") -> RateLimitState:
        with self._lock:
            prov = provider.strip() if provider else "default"
            return self._shared_states.get(prov, RateLimitState(provider=prov))

    def format_display(
        self, state: Optional[RateLimitState] = None, provider: str = ""
    ) -> str:
        with self._lock:
            active_state = state if state is not None else self.get_state(provider)
            return format_rate_limit_display(active_state)

    def should_throttle(
        self,
        state: Optional[RateLimitState] = None,
        provider: str = "",
        safety_margin: float = 0.1,
    ) -> Tuple[bool, float]:
        with self._lock:
            active_state = state if state is not None else self.get_state(provider)
            return should_throttle(active_state, safety_margin=safety_margin)

    def reset(self, provider: str = "") -> None:
        with self._lock:
            if provider:
                self._shared_states.pop(provider.strip(), None)
            else:
                self._shared_states.clear()


# Register default provider
get_registry().register("rate_limit", "default", RateLimitTrackerProvider)
