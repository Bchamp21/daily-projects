"""Circuit breaker + retry with exponential backoff and jitter.

States: CLOSED (calls flow) -> OPEN (fail fast) -> HALF_OPEN (one trial call).
Clock and sleep are injectable so tests run instantly.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypeVar

T = TypeVar("T")


class State(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised instead of calling the dependency while the circuit is open."""


class TransientError(Exception):
    """Errors worth retrying (timeouts, 429, 5xx)."""


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    reset_timeout: float = 30.0
    clock: Callable[[], float] = time.monotonic
    state: State = State.CLOSED
    failures: int = 0
    opened_at: float = 0.0
    transitions: list[str] = field(default_factory=list)

    def _move(self, new: State) -> None:
        if new != self.state:
            self.transitions.append(f"{self.state.value}->{new.value}")
            self.state = new

    def allow(self) -> bool:
        if self.state == State.OPEN:
            if self.clock() - self.opened_at >= self.reset_timeout:
                self._move(State.HALF_OPEN)  # let one trial call through
                return True
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self._move(State.CLOSED)

    def record_failure(self) -> None:
        self.failures += 1
        if self.state == State.HALF_OPEN or self.failures >= self.failure_threshold:
            self.opened_at = self.clock()
            self._move(State.OPEN)

    def call(self, fn: Callable[[], T]) -> T:
        if not self.allow():
            raise CircuitOpenError("circuit open: failing fast")
        try:
            result = fn()
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result


def backoff_delays(retries: int, base: float = 0.5, cap: float = 8.0,
                   rng: random.Random | None = None) -> list[float]:
    """Full-jitter exponential backoff: uniform(0, min(cap, base*2**n))."""
    rng = rng or random.Random()
    return [rng.uniform(0, min(cap, base * 2 ** n)) for n in range(retries)]


def call_with_retry(fn: Callable[[], T], breaker: CircuitBreaker, retries: int = 3,
                    sleep: Callable[[float], None] = time.sleep,
                    rng: random.Random | None = None) -> T:
    """Retry only TransientError; never retry while the breaker is open."""
    delays = backoff_delays(retries, rng=rng)
    attempt = 0
    while True:
        try:
            return breaker.call(fn)
        except TransientError:
            if attempt >= retries:
                raise
            sleep(delays[attempt])
            attempt += 1
