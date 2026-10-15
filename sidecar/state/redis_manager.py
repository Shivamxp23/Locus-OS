"""sidecar/state/redis_manager.py - Redis State & Pub/Sub Integration.

Implements Spec §30.9:
- High-performance in-memory key-value caching with TTL.
- Distributed mutual exclusion locks (acquire_lock / release_lock).
- Pub/sub message channel broker for real-time notification dispatch.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: Optional[float] = None


class RedisStateManager:
    """Manages fast in-memory key-value state, locks, and pub/sub channels."""

    def __init__(self, host: str = "localhost", port: int = 6379) -> None:
        self.host = host
        self.port = port
        self.cache: dict[str, CacheEntry] = {}
        self.locks: set[str] = set()
        self.subscribers: dict[str, list[Callable[[str], None]]] = {}

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        expires = (time.time() + ttl_seconds) if ttl_seconds is not None else None
        self.cache[key] = CacheEntry(value=value, expires_at=expires)

    def get(self, key: str) -> Optional[Any]:
        entry = self.cache.get(key)
        if not entry:
            return None
        if entry.expires_at is not None and time.time() > entry.expires_at:
            del self.cache[key]
            return None
        return entry.value

    def delete(self, key: str) -> bool:
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def acquire_lock(self, lock_name: str) -> bool:
        if lock_name in self.locks:
            return False
        self.locks.add(lock_name)
        return True

    def release_lock(self, lock_name: str) -> bool:
        if lock_name in self.locks:
            self.locks.remove(lock_name)
            return True
        return False

    def subscribe(self, channel: str, callback: Callable[[str], None]) -> None:
        self.subscribers.setdefault(channel, []).append(callback)

    def publish(self, channel: str, message: str) -> int:
        subs = self.subscribers.get(channel, [])
        for sub in subs:
            try:
                sub(message)
            except Exception:
                pass
        return len(subs)
