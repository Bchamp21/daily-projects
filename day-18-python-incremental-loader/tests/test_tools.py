import pytest
from incload.tools import batched, retry, timed


def test_batched_chunks_and_remainder():
    assert list(batched(range(5), 2)) == [[0, 1], [2, 3], [4]]


def test_batched_is_lazy():
    def gen():
        yield 1
        raise RuntimeError("should not be reached")
    assert next(batched(gen(), 1)) == [1]


def test_batched_rejects_zero():
    with pytest.raises(ValueError):
        list(batched([1], 0))


def test_retry_succeeds_after_failures():
    calls, waits = [], []

    @retry(times=3, delay=0.1, exceptions=(IOError,), sleep=waits.append)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise IOError("boom")
        return "ok"

    assert flaky() == "ok"
    assert waits == [0.1, 0.2]  # exponential backoff


def test_retry_gives_up_and_reraises():
    @retry(times=2, delay=0, exceptions=(IOError,), sleep=lambda s: None)
    def always_fails():
        raise IOError("nope")
    with pytest.raises(IOError):
        always_fails()


def test_retry_ignores_other_exceptions():
    calls = []

    @retry(times=3, exceptions=(IOError,), sleep=lambda s: None)
    def bad():
        calls.append(1)
        raise ValueError("not retried")
    with pytest.raises(ValueError):
        bad()
    assert len(calls) == 1


def test_timed_keeps_name_and_records_time():
    @timed
    def f():
        return 42
    assert f() == 42 and f.__name__ == "f" and f.last_seconds >= 0
