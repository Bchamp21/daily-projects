"""Token-bucket rate limiter + TTL/LRU cache for an API client (stdlib only)."""
from __future__ import annotations

import functools
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Hashable


class RateLimited(Exception):
    """Raised when a call would exceed the rate limit and blocking is off."""

    def __init__(self, retry_after: float):
        super().__init__(f"rate limited, retry after {retry_after:.2f}s")
        self.retry_after = retry_after


class TokenBucket:
    """Allow `rate` calls per second with bursts up to `capacity`.

    Tokens refill continuously. Each call spends `cost` tokens.
    Clock and sleep are injected so tests run instantly.
    """

    def __init__(self, rate: float, capacity: float, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        if rate <= 0 or capacity <= 0:
            raise ValueError("rate and capacity must be > 0")
        self.rate, self.capacity = rate, capacity
        self.clock, self.sleep = clock, sleep
        self.tokens = capacity
        self.last = clock()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now

    def try_acquire(self, cost: float = 1.0) -> float:
        """Spend tokens if available. Returns 0.0 on success, else seconds to wait."""
        if cost > self.capacity:
            raise ValueError("cost larger than bucket capacity")
        with self._lock:
            self._refill()
            if self.tokens >= cost:
                self.tokens -= cost
                return 0.0
            return (cost - self.tokens) / self.rate

    def acquire(self, cost: float = 1.0, block: bool = True) -> None:
        while True:
            wait = self.try_acquire(cost)
            if wait == 0.0:
                return
            if not block:
                raise RateLimited(wait)
            self.sleep(wait)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


_MISSING = object()


class TTLCache:
    """LRU cache where every entry also expires after `ttl` seconds."""

    def __init__(self, maxsize: int = 128, ttl: float = 60.0, clock: Callable[[], float] = time.monotonic):
        if maxsize <= 0:
            raise ValueError("maxsize must be > 0")
        self.maxsize, self.ttl, self.clock = maxsize, ttl, clock
        self._data: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self.stats = CacheStats()
        self._lock = threading.Lock()

    def get(self, key: Hashable, default: Any = _MISSING) -> Any:
        with self._lock:
            item = self._data.get(key)
            if item is not None:
                expires_at, value = item
                if self.clock() < expires_at:
                    self._data.move_to_end(key)  # mark as recently used
                    self.stats.hits += 1
                    return value
                del self._data[key]
                self.stats.expired += 1
            self.stats.misses += 1
            return default

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._data[key] = (self.clock() + self.ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)  # drop least recently used
                self.stats.evictions += 1

    def __len__(self) -> int:
        return len(self._data)


def cached_and_limited(cache: TTLCache, bucket: TokenBucket, block: bool = True):
    """Decorator: serve from cache first; only cache misses spend rate-limit tokens."""

    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__name__, args, tuple(sorted(kwargs.items())))
            value = cache.get(key)
            if value is not _MISSING:
                return value
            bucket.acquire(block=block)
            value = fn(*args, **kwargs)
            cache.set(key, value)
            return value

        wrapper.cache = cache
        wrapper.bucket = bucket
        return wrapper

    return deco
