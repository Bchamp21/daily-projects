import argparse
import asyncio
import json
import time

from .fetcher import fetch_all
from .source import FakeQuoteAPI


def main(argv=None):
    p = argparse.ArgumentParser(prog="asyncfetch", description="Fetch quotes concurrently.")
    p.add_argument("symbols", nargs="*", default=["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA"])
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--timeout", type=float, default=1.0)
    p.add_argument("--sequential", action="store_true", help="compare: concurrency=1")
    a = p.parse_args(argv)
    api = FakeQuoteAPI(latency=0.3, fail_first={"NVDA": 2})  # NVDA flakes twice, then works
    start = time.perf_counter()
    results = asyncio.run(fetch_all(api, a.symbols, 1 if a.sequential else a.concurrency,
                                    retries=a.retries, timeout=a.timeout))
    secs = time.perf_counter() - start
    for r in results:
        print(json.dumps(r.__dict__))
    ok = sum(r.ok for r in results)
    print(f"{ok}/{len(results)} ok in {secs:.2f}s (max in flight: {api.max_in_flight})")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
