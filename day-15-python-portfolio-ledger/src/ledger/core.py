"""Pure FIFO cost-basis logic. Uses Decimal so money never drifts (0.1 + 0.2 problem)."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


class InsufficientShares(ValueError):
    """Raised when a SELL is bigger than the open position (no short selling)."""


@dataclass(frozen=True)
class Trade:
    day: date
    ticker: str
    side: str  # "BUY" or "SELL"
    qty: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")

    def __post_init__(self):
        if self.side not in ("BUY", "SELL"):
            raise ValueError(f"side must be BUY or SELL, got {self.side!r}")
        if self.qty <= 0 or self.price <= 0 or self.fee < 0:
            raise ValueError("qty and price must be > 0, fee >= 0")


@dataclass
class Lot:
    """One open purchase. cost_per_share includes the buy fee."""
    day: date
    qty: Decimal
    cost_per_share: Decimal


@dataclass
class Ledger:
    lots: dict[str, deque[Lot]] = field(default_factory=lambda: defaultdict(deque))
    realized: dict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))

    def apply(self, t: Trade) -> Decimal:
        """Apply one trade. Returns realized P&L from this trade (0 for buys)."""
        if t.side == "BUY":
            cps = (t.qty * t.price + t.fee) / t.qty
            self.lots[t.ticker].append(Lot(t.day, t.qty, cps))
            return Decimal("0")

        if t.qty > self.position(t.ticker):
            raise InsufficientShares(
                f"sell {t.qty} {t.ticker} but only {self.position(t.ticker)} held"
            )
        remaining, cost = t.qty, Decimal("0")
        queue = self.lots[t.ticker]
        while remaining > 0:  # FIFO: consume oldest lots first
            lot = queue[0]
            take = min(remaining, lot.qty)
            cost += take * lot.cost_per_share
            lot.qty -= take
            remaining -= take
            if lot.qty == 0:
                queue.popleft()
        pnl = t.qty * t.price - t.fee - cost
        self.realized[t.ticker] += pnl
        return money(pnl)

    def apply_all(self, trades) -> "Ledger":
        for t in sorted(trades, key=lambda t: (t.day, t.side != "BUY")):
            self.apply(t)
        return self

    def position(self, ticker: str) -> Decimal:
        return sum((l.qty for l in self.lots.get(ticker, ())), Decimal("0"))

    def cost_basis(self, ticker: str) -> Decimal:
        return sum((l.qty * l.cost_per_share for l in self.lots.get(ticker, ())), Decimal("0"))

    def report(self, prices: dict[str, Decimal]) -> list[dict]:
        rows = []
        for tk in sorted(set(self.lots) | set(self.realized)):
            qty, basis = self.position(tk), self.cost_basis(tk)
            mkt = qty * prices[tk] if qty and tk in prices else Decimal("0")
            rows.append({
                "ticker": tk,
                "qty": qty,
                "cost_basis": money(basis),
                "market_value": money(mkt),
                "unrealized": money(mkt - basis) if qty else Decimal("0.00"),
                "realized": money(self.realized.get(tk, Decimal("0"))),
            })
        return rows
