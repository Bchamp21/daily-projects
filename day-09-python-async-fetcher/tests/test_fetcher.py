import asyncio
import time

from asyncfetch import fetch_all, fetch_with_retry
from asyncfetch.__main__ import main
from asyncfetch.source import FakeQuoteAPI


def run(coro):
    return asyncio.run(coro)


def test_all_ok_and_order_kept():
    api = FakeQuoteAPI(latency=0.01)
    res = run(fetch_all(api, ["AAPL", "MSFT", "NVDA"]))
    assert [r.symbol for r in res] == ["AAPL", "MSFT", "NVDA"]
    assert all(r.ok and r.price > 0 and r.attempts == 1 for r in res)


def test_concurrency_limit_respected():
    api = FakeQuoteAPI(latency=0.05)
    run(fetch_all(api, ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"], concurrency=2))
    assert api.max_in_flight == 2


def test_concurrent_is_faster_than_sequential():
    syms = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]
    t = time.perf_counter(); run(fetch_all(FakeQuoteAPI(latency=0.1), syms, concurrency=5))
    fast = time.perf_counter() - t
    t = time.perf_counter(); run(fetch_all(FakeQuoteAPI(latency=0.1), syms, concurrency=1))
    slow = time.perf_counter() - t
    assert fast < 0.3 and slow >= 0.5


def test_transient_error_retried_then_succeeds():
    api = FakeQuoteAPI(latency=0.01, fail_first={"NVDA": 2})
    r = run(fetch_with_retry(api, "NVDA", asyncio.Semaphore(1), retries=3, base_delay=0.01))
    assert r.ok and r.attempts == 3 and api.calls["NVDA"] == 3


def test_gives_up_after_retries():
    api = FakeQuoteAPI(latency=0.01, fail_first={"MSFT": 10})
    r = run(fetch_with_retry(api, "MSFT", asyncio.Semaphore(1), retries=2, base_delay=0.01))
    assert not r.ok and r.attempts == 3 and "TransientError" in r.error


def test_timeout_is_retried_then_fails():
    api = FakeQuoteAPI(latency=0.01, hang={"AAPL"})
    r = run(fetch_with_retry(api, "AAPL", asyncio.Semaphore(1), retries=1, timeout=0.05, base_delay=0.01))
    assert not r.ok and r.attempts == 2 and r.error.startswith("TimeoutError")


def test_permanent_error_not_retried():
    api = FakeQuoteAPI(latency=0.01)
    r = run(fetch_with_retry(api, "TSLA", asyncio.Semaphore(1), retries=3))
    assert not r.ok and r.attempts == 1 and "KeyError" in r.error


def test_one_failure_does_not_kill_batch():
    api = FakeQuoteAPI(latency=0.01)
    res = run(fetch_all(api, ["AAPL", "TSLA", "MSFT"]))
    assert [r.ok for r in res] == [True, False, True]


def test_cli_exit_code(capsys):
    assert main(["AAPL", "NVDA", "--timeout", "2"]) == 0
    assert main(["AAPL", "TSLA"]) == 1
    assert "ok in" in capsys.readouterr().out
