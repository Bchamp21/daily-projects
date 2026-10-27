"""CLI: `python -m ledger.cli import trades.csv` then `python -m ledger.cli report --prices prices.csv`."""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from decimal import Decimal, InvalidOperation

from .core import Ledger, Trade, InsufficientShares
from .store import connect, insert_trades, load_trades


def read_trades_csv(path: str) -> list[Trade]:
    out = []
    with open(path, newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            try:
                out.append(Trade(date.fromisoformat(r["day"]), r["ticker"].strip().upper(),
                                 r["side"].strip().upper(), Decimal(r["qty"]),
                                 Decimal(r["price"]), Decimal(r.get("fee") or "0")))
            except (ValueError, InvalidOperation, KeyError) as e:
                raise SystemExit(f"{path}:{n}: bad row ({e})")
    return out


def read_prices_csv(path: str) -> dict[str, Decimal]:
    with open(path, newline="") as f:
        return {r["ticker"].upper(): Decimal(r["close"]) for r in csv.DictReader(f)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ledger")
    p.add_argument("--db", default="ledger.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("import").add_argument("csv")
    sub.add_parser("report").add_argument("--prices", required=True)
    a = p.parse_args(argv)

    with connect(a.db) as conn:
        if a.cmd == "import":
            added = insert_trades(conn, read_trades_csv(a.csv))
            print(f"imported {added} new trades")
            return 0
        try:
            led = Ledger().apply_all(load_trades(conn))
        except InsufficientShares as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        rows = led.report(read_prices_csv(a.prices))
    cols = ["ticker", "qty", "cost_basis", "market_value", "unrealized", "realized"]
    print("  ".join(f"{c:>12}" for c in cols))
    for r in rows:
        print("  ".join(f"{str(r[c]):>12}" for c in cols))
    return 0


if __name__ == "__main__":
    sys.exit(main())
