"""Demo: load daily prices for tickers; one ticker is flaky, one is always broken."""
from .queue import JobQueue


class FakeClock:
    def __init__(self):
        self.t = 1_000.0

    def __call__(self):
        return self.t


def main() -> None:
    clock = FakeClock()
    q = JobQueue(clock=clock, max_attempts=3, base_backoff=2)
    calls = {"MSFT": 0}

    def load_prices(p):
        t = p["ticker"]
        if t == "MSFT":
            calls["MSFT"] += 1
            if calls["MSFT"] < 2:
                raise TimeoutError("source timed out")
        if t == "BAD":
            raise ValueError("unknown ticker")
        print(f"  loaded {t}")

    for t in ["AAPL", "MSFT", "BAD", "AAPL"]:  # AAPL twice -> deduped
        q.enqueue("load_prices", {"ticker": t}, dedupe_key=f"load:{t}:2026-11-12")

    for step in range(4):
        print(f"t={clock.t:.0f} worker pass {step}: handled {q.work({'load_prices': load_prices})}")
        print("  stats:", q.stats())
        clock.t += 5  # time passes, backoffs expire


if __name__ == "__main__":
    main()
