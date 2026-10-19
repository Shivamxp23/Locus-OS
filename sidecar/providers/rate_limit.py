"""
SPEC §1.9 / F-0009 / US-28: Rate Limit Tracking Provider Contracts.
Defines RateLimitBucket, RateLimitState, and BaseRateLimitProvider.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
import time
from typing import Any, Dict, Optional, Tuple


@dataclass
class RateLimitBucket:
    """
    SPEC §1.9 line 2219:
    RateLimitBucket:
        limit: int              // e.g. 60 RPM
        remaining: int          // e.g. 45 remaining
        reset_seconds: float    // seconds until window resets
        captured_at: float      // timestamp of capture
        
        COMPUTED: used = max(0, limit - remaining)
        COMPUTED: usage_pct = (used / limit) * 100
        COMPUTED: remaining_seconds_now = max(0, reset_seconds - (now - captured_at))
    """
    limit: int = 0
    remaining: int = 0
    reset_seconds: float = 0.0
    captured_at: float = 0.0

    @property
    def used(self) -> int:
        """SPEC §1.9 line 2225: COMPUTED: used = max(0, limit - remaining)"""
        return max(0, self.limit - self.remaining)

    @property
    def usage_pct(self) -> float:
        """SPEC §1.9 line 2226: COMPUTED: usage_pct = (used / limit) * 100"""
        if self.limit <= 0:
            return 0.0
        return round((self.used / self.limit) * 100.0, 2)

    def get_remaining_seconds_now(self, now: Optional[float] = None) -> float:
        """SPEC §1.9 line 2227: COMPUTED: remaining_seconds_now = max(0, reset_seconds - (now - captured_at))"""
        current_time = time.time() if now is None else now
        elapsed = max(0.0, current_time - self.captured_at)
        return max(0.0, round(self.reset_seconds - elapsed, 3))

    @property
    def remaining_seconds_now(self) -> float:
        """SPEC §1.9 line 2227: Live countdown accessor using current time."""
        return self.get_remaining_seconds_now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_seconds": self.reset_seconds,
            "captured_at": self.captured_at,
            "used": self.used,
            "usage_pct": self.usage_pct,
            "remaining_seconds_now": self.remaining_seconds_now,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RateLimitBucket:
        if not data:
            return cls()
        return cls(
            limit=int(data.get("limit", 0)),
            remaining=int(data.get("remaining", 0)),
            reset_seconds=float(data.get("reset_seconds", 0.0)),
            captured_at=float(data.get("captured_at", 0.0)),
        )


@dataclass
class RateLimitState:
    """
    SPEC §1.9 line 2229:
    RateLimitState:
        requests_min: RateLimitBucket    // RPM
        requests_hour: RateLimitBucket   // RPH
        tokens_min: RateLimitBucket      // TPM
        tokens_hour: RateLimitBucket     // TPH
        provider: string
    """
    requests_min: RateLimitBucket = field(default_factory=RateLimitBucket)
    requests_hour: RateLimitBucket = field(default_factory=RateLimitBucket)
    tokens_min: RateLimitBucket = field(default_factory=RateLimitBucket)
    tokens_hour: RateLimitBucket = field(default_factory=RateLimitBucket)
    provider: str = ""
    captured_at: float = 0.0

    @property
    def has_data(self) -> bool:
        """True if any rate limit bucket has been initialized with positive limit or remaining data."""
        return any(
            b.limit > 0 or b.remaining > 0
            for b in (self.requests_min, self.requests_hour, self.tokens_min, self.tokens_hour)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_min": self.requests_min.to_dict(),
            "requests_hour": self.requests_hour.to_dict(),
            "tokens_min": self.tokens_min.to_dict(),
            "tokens_hour": self.tokens_hour.to_dict(),
            "provider": self.provider,
            "captured_at": self.captured_at,
            "has_data": self.has_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RateLimitState:
        if not data:
            return cls()
        return cls(
            requests_min=RateLimitBucket.from_dict(data.get("requests_min", {})),
            requests_hour=RateLimitBucket.from_dict(data.get("requests_hour", {})),
            tokens_min=RateLimitBucket.from_dict(data.get("tokens_min", {})),
            tokens_hour=RateLimitBucket.from_dict(data.get("tokens_hour", {})),
            provider=str(data.get("provider", "")),
            captured_at=float(data.get("captured_at", 0.0)),
        )


class BaseRateLimitProvider(abc.ABC):
    """Abstract interface for rate limit tracking and throttling."""

    @abc.abstractmethod
    def parse_headers(
        self, response_headers: Dict[str, Any], provider: str = ""
    ) -> RateLimitState:
        """
        SPEC §1.9 line 2236:
        Extract 12 x-ratelimit-* headers and return updated RateLimitState.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_state(self, provider: str = "") -> RateLimitState:
        """Retrieve current in-memory rate limit state for provider."""
        raise NotImplementedError

    @abc.abstractmethod
    def format_display(
        self, state: Optional[RateLimitState] = None, provider: str = ""
    ) -> str:
        """
        SPEC §1.9 line 2250:
        Format rate limit state for display in TUI/CLI footer.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def should_throttle(
        self,
        state: Optional[RateLimitState] = None,
        provider: str = "",
        safety_margin: float = 0.1,
    ) -> Tuple[bool, float]:
        """
        SPEC §1.9 line 2260:
        Pre-call rate guard check returning (should_throttle, sleep_seconds).
        """
        raise NotImplementedError

    @abc.abstractmethod
    def reset(self, provider: str = "") -> None:
        """Clear recorded rate limit state."""
        raise NotImplementedError
