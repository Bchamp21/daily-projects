"""Day 43 DE: streaming 1-minute OHLC bars with a watermark (pure-Python model of
Spark Structured Streaming append mode), so the semantics can be unit-tested locally.

Rules (same as Spark):
- watermark = max(event_time seen) - delay
- an event older than the watermark is LATE -> dropped (counted)
- duplicate event_id is dropped while it is newer than the watermark
- a window is emitted ONCE (append mode) when window_end <= watermark
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tick:
    event_id: str
    ticker: str
    ts: int        # event time, epoch seconds
    price: float
    qty: int


@dataclass
class Bar:
    ticker: str
    window_start: int
    window_end: int
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float
    trades: int


@dataclass
class _Acc:
    first_ts: int
    open: float
    last_ts: int
    close: float
    high: float
    low: float
    volume: int = 0
    notional: float = 0.0
    trades: int = 0

    def add(self, t: Tick) -> None:
        # out-of-order safe: open = earliest event time, close = latest event time
        if t.ts < self.first_ts:
            self.first_ts, self.open = t.ts, t.price
        if t.ts >= self.last_ts:
            self.last_ts, self.close = t.ts, t.price
        self.high = max(self.high, t.price)
        self.low = min(self.low, t.price)
        self.volume += t.qty
        self.notional += t.price * t.qty
        self.trades += 1


@dataclass
class OhlcStream:
    window_s: int = 60
    delay_s: int = 30
    max_ts: int | None = None
    late_dropped: int = 0
    dup_dropped: int = 0
    bad_dropped: int = 0
    _state: dict = field(default_factory=dict)     # (ticker, wstart) -> _Acc
    _seen: dict = field(default_factory=dict)      # event_id -> ts

    @property
    def watermark(self) -> int | None:
        return None if self.max_ts is None else self.max_ts - self.delay_s

    def _window(self, ts: int) -> int:
        return ts - ts % self.window_s

    def process_batch(self, ticks: list[Tick]) -> list[Bar]:
        """One micro-batch. Watermark used for dropping is the one from the
        END of the previous batch (exactly like Spark)."""
        wm = self.watermark
        for t in ticks:
            if t.price <= 0 or t.qty <= 0:
                self.bad_dropped += 1
                continue
            if wm is not None and t.ts < wm:
                self.late_dropped += 1
                continue
            if t.event_id in self._seen:
                self.dup_dropped += 1
                continue
            self._seen[t.event_id] = t.ts
            key = (t.ticker, self._window(t.ts))
            acc = self._state.get(key)
            if acc is None:
                self._state[key] = acc = _Acc(t.ts, t.price, t.ts, t.price, t.price, t.price)
                acc.volume = 0
            acc.add(t)
        # advance watermark after the batch
        if ticks:
            batch_max = max(t.ts for t in ticks)
            self.max_ts = batch_max if self.max_ts is None else max(self.max_ts, batch_max)
        return self._emit_closed()

    def _emit_closed(self) -> list[Bar]:
        wm = self.watermark
        if wm is None:
            return []
        out = []
        for (tk, ws), a in sorted(self._state.items()):
            we = ws + self.window_s
            if we <= wm:
                out.append(Bar(tk, ws, we, a.open, a.high, a.low, a.close, a.volume,
                               round(a.notional / a.volume, 4), a.trades))
        for b in out:
            del self._state[(b.ticker, b.window_start)]
        # state cleanup: forget dedupe ids older than the watermark (bounded state)
        self._seen = {k: v for k, v in self._seen.items() if v >= wm}
        return out

    def state_size(self) -> int:
        return len(self._state) + len(self._seen)
