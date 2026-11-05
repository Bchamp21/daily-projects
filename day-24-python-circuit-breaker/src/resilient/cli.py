"""Demo: a flaky quote API that fails 3 times, then recovers."""
from __future__ import annotations

import random

from .breaker import CircuitBreaker, CircuitOpenError, TransientError, call_with_retry


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


def main() -> None:
    clock = FakeClock()
    breaker = CircuitBreaker(failure_threshold=3, reset_timeout=10, clock=clock)
    calls = {"n": 0}

    def get_quote() -> float:
        calls["n"] += 1
        if calls["n"] <= 3:
            raise TransientError("503 from quote API")
        return 187.42

    for i in range(5):
        try:
            price = call_with_retry(get_quote, breaker, retries=2, sleep=clock.sleep,
                                    rng=random.Random(1))
            print(f"request {i}: AAPL={price} state={breaker.state.value}")
        except CircuitOpenError:
            print(f"request {i}: failed fast (circuit open) t={clock.t:.1f}s")
        except TransientError as e:
            print(f"request {i}: gave up after retries ({e})")
        clock.t += 6
    print("transitions:", breaker.transitions)


if __name__ == "__main__":
    main()
