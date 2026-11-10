import pytest

from throttle.core import RateLimited, TokenBucket, TTLCache, cached_and_limited


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_burst_then_limited():
    c = FakeClock()
    b = TokenBucket(rate=1, capacity=3, clock=c, sleep=c.sleep)
    for _ in range(3):
        assert b.try_acquire() == 0.0
    assert b.try_acquire() == pytest.approx(1.0)


def test_refill_over_time_capped_at_capacity():
    c = FakeClock()
    b = TokenBucket(rate=2, capacity=2, clock=c)
    b.try_acquire(); b.try_acquire()
    c.t = 100
    b._refill()
    assert b.tokens == 2


def test_blocking_acquire_sleeps_exact_wait():
    c = FakeClock()
    b = TokenBucket(rate=2, capacity=1, clock=c, sleep=c.sleep)
    b.acquire(); b.acquire()
    assert c.t == pytest.approx(0.5)


def test_non_blocking_raises_with_retry_after():
    c = FakeClock()
    b = TokenBucket(rate=4, capacity=1, clock=c)
    b.acquire(block=False)
    with pytest.raises(RateLimited) as e:
        b.acquire(block=False)
    assert e.value.retry_after == pytest.approx(0.25)


def test_bad_config():
    with pytest.raises(ValueError):
        TokenBucket(rate=0, capacity=1)
    with pytest.raises(ValueError):
        TokenBucket(rate=1, capacity=1).try_acquire(cost=2)


def test_cache_ttl_expiry():
    c = FakeClock()
    cache = TTLCache(ttl=10, clock=c)
    cache.set("AAPL", 190)
    assert cache.get("AAPL") == 190
    c.t = 10
    assert cache.get("AAPL", None) is None
    assert cache.stats.expired == 1


def test_cache_lru_eviction_keeps_recently_used():
    cache = TTLCache(maxsize=2, ttl=100, clock=FakeClock())
    cache.set("a", 1); cache.set("b", 2)
    cache.get("a")          # a is now most recent
    cache.set("c", 3)       # evicts b
    assert cache.get("b", None) is None
    assert cache.get("a") == 1 and cache.get("c") == 3
    assert cache.stats.evictions == 1


def test_decorator_hits_skip_rate_limit():
    c = FakeClock()
    bucket = TokenBucket(rate=1, capacity=1, clock=c, sleep=c.sleep)
    calls = []

    @cached_and_limited(TTLCache(ttl=60, clock=c), bucket)
    def quote(t):
        calls.append(t)
        return len(t)

    for _ in range(5):
        assert quote("AAPL") == 4
    assert calls == ["AAPL"] and c.t == 0      # 4 cache hits, no waiting
    quote("MSFT")                              # miss: must wait for a token
    assert c.t == pytest.approx(1.0)
    assert quote.cache.stats.hits == 4


def test_decorator_non_blocking_raises():
    c = FakeClock()

    @cached_and_limited(TTLCache(clock=c), TokenBucket(1, 1, clock=c), block=False)
    def quote(t):
        return t

    quote("A")
    with pytest.raises(RateLimited):
        quote("B")
    assert quote("A") == "A"  # cached value still served while limited


def test_cli_runs(capsys):
    from throttle.cli import main
    main()
    out = capsys.readouterr().out
    assert "hit_rate" in out
