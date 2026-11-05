import random

import pytest

from resilient.breaker import (CircuitBreaker, CircuitOpenError, State,
                               TransientError, backoff_delays, call_with_retry)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def boom():
    raise TransientError("503")


def test_opens_after_threshold_and_fails_fast():
    b = CircuitBreaker(failure_threshold=2, clock=Clock())
    for _ in range(2):
        with pytest.raises(TransientError):
            b.call(boom)
    assert b.state == State.OPEN
    called = []
    with pytest.raises(CircuitOpenError):
        b.call(lambda: called.append(1))
    assert called == []  # dependency never touched


def test_half_open_success_closes():
    c = Clock()
    b = CircuitBreaker(failure_threshold=1, reset_timeout=10, clock=c)
    with pytest.raises(TransientError):
        b.call(boom)
    c.t = 10
    assert b.call(lambda: "ok") == "ok"
    assert b.state == State.CLOSED
    assert b.transitions == ["closed->open", "open->half_open", "half_open->closed"]


def test_half_open_failure_reopens():
    c = Clock()
    b = CircuitBreaker(failure_threshold=1, reset_timeout=10, clock=c)
    with pytest.raises(TransientError):
        b.call(boom)
    c.t = 11
    with pytest.raises(TransientError):
        b.call(boom)
    assert b.state == State.OPEN and b.opened_at == 11


def test_success_resets_failure_count():
    b = CircuitBreaker(failure_threshold=2, clock=Clock())
    with pytest.raises(TransientError):
        b.call(boom)
    b.call(lambda: 1)
    with pytest.raises(TransientError):
        b.call(boom)
    assert b.state == State.CLOSED


@pytest.mark.parametrize("n", [0, 1, 5])
def test_backoff_within_cap(n):
    d = backoff_delays(n, base=1, cap=4, rng=random.Random(0))
    assert len(d) == n
    assert all(0 <= x <= min(4, 2 ** i) for i, x in enumerate(d))


def test_retry_recovers_from_transient():
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TransientError("timeout")
        return 42

    sleeps = []
    b = CircuitBreaker(failure_threshold=5, clock=Clock())
    assert call_with_retry(flaky, b, retries=3, sleep=sleeps.append,
                           rng=random.Random(0)) == 42
    assert len(sleeps) == 2


def test_non_transient_not_retried():
    sleeps = []

    def bad():
        raise ValueError("400 bad ticker")

    with pytest.raises(ValueError):
        call_with_retry(bad, CircuitBreaker(clock=Clock()), sleep=sleeps.append)
    assert sleeps == []


def test_retry_stops_when_circuit_opens():
    sleeps = []
    b = CircuitBreaker(failure_threshold=2, clock=Clock())
    with pytest.raises(CircuitOpenError):
        call_with_retry(boom, b, retries=5, sleep=sleeps.append, rng=random.Random(0))
    assert len(sleeps) == 2  # 2 real failures, then fail fast
