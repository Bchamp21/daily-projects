"""A fake quote API so everything runs offline.

Swap FakeQuoteAPI.get for a real HTTP call (e.g. httpx.AsyncClient) later;
the fetcher only needs an `async def get(symbol) -> dict`.
"""
import asyncio
import random

BASE = {"AAPL": 231.4, "MSFT": 418.2, "NVDA": 121.7, "GOOGL": 165.3, "AMZN": 186.9}


class TransientError(Exception):
    """Like an HTTP 429/503: worth retrying."""


class FakeQuoteAPI:
    def __init__(self, latency=0.2, fail_first=None, hang=(), seed=42):
        self.latency = latency
        self.fail_first = dict(fail_first or {})  # symbol -> how many calls fail first
        self.hang = set(hang)                    # symbols that never answer
        self.calls = {}
        self.in_flight = 0
        self.max_in_flight = 0
        self._rng = random.Random(seed)

    async def get(self, symbol):
        self.calls[symbol] = self.calls.get(symbol, 0) + 1
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if symbol in self.hang:
                await asyncio.sleep(3600)
            await asyncio.sleep(self.latency)
            if symbol not in BASE:
                raise KeyError(f"unknown symbol {symbol}")
            if self.fail_first.get(symbol, 0) > 0:
                self.fail_first[symbol] -= 1
                raise TransientError(f"{symbol}: 503 try again")
            price = round(BASE[symbol] * (1 + self._rng.uniform(-0.01, 0.01)), 2)
            return {"symbol": symbol, "price": price}
        finally:
            self.in_flight -= 1
