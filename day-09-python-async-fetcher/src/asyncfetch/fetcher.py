import asyncio
from dataclasses import dataclass

from .source import TransientError


@dataclass
class FetchResult:
    symbol: str
    ok: bool
    price: float | None = None
    attempts: int = 0
    error: str | None = None


async def fetch_with_retry(api, symbol, sem, retries=3, timeout=1.0, base_delay=0.1):
    """One symbol: wait for a slot, call with a timeout, retry transient errors with backoff."""
    attempts = 0
    async with sem:  # at most N calls in flight
        while True:
            attempts += 1
            try:
                data = await asyncio.wait_for(api.get(symbol), timeout)
                return FetchResult(symbol, True, data["price"], attempts)
            except (TransientError, asyncio.TimeoutError) as e:
                if attempts > retries:
                    return FetchResult(symbol, False, attempts=attempts,
                                       error=type(e).__name__ + (f": {e}" if str(e) else ""))
                await asyncio.sleep(base_delay * 2 ** (attempts - 1))  # 0.1, 0.2, 0.4...
            except Exception as e:  # permanent error: don't retry
                return FetchResult(symbol, False, attempts=attempts, error=f"{type(e).__name__}: {e}")


async def fetch_all(api, symbols, concurrency=3, **kw):
    """Fetch all symbols concurrently; one failure never kills the batch."""
    sem = asyncio.Semaphore(concurrency)
    tasks = [fetch_with_retry(api, s, sem, **kw) for s in symbols]
    return await asyncio.gather(*tasks)
