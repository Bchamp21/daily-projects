"""Demo: 12 quote lookups against a fake API limited to 2 calls/sec, burst 3."""
from .core import TokenBucket, TTLCache, cached_and_limited


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def main() -> None:
    clock = FakeClock()
    bucket = TokenBucket(rate=2, capacity=3, clock=clock, sleep=clock.sleep)
    cache = TTLCache(maxsize=2, ttl=5, clock=clock)
    api_calls = []

    @cached_and_limited(cache, bucket)
    def get_quote(ticker: str) -> float:
        api_calls.append((round(clock(), 2), ticker))
        return {"AAPL": 190.1, "MSFT": 410.5, "NVDA": 120.3}[ticker]

    for t in ["AAPL", "MSFT", "AAPL", "NVDA", "AAPL", "MSFT", "MSFT", "NVDA", "AAPL", "NVDA", "MSFT", "AAPL"]:
        print(f"t={clock():5.2f}s  {t} = {get_quote(t)}")
    print("real API calls:", api_calls)
    s = cache.stats
    print(f"hits={s.hits} misses={s.misses} evictions={s.evictions} hit_rate={s.hit_rate:.0%}")


if __name__ == "__main__":
    main()
