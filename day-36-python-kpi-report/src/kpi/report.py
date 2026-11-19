"""Monthly KPI report: the Python version of a Power BI matrix + DAX measures."""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MonthKPI:
    month: str
    revenue: float
    trades: int
    mom_pct: float | None   # vs previous month (None for first month / zero base)
    running_total: float
    top_ticker: str


def load_rows(path: str | Path) -> tuple[list[dict], list[str]]:
    """Read CSV; return (good rows, list of rejected-row reasons)."""
    good, bad = [], []
    with open(path, newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):  # line 1 = header
            try:
                shares, price = float(r["shares"]), float(r["price"])
            except (TypeError, ValueError):
                bad.append(f"line {i}: bad shares/price {r.get('shares')!r}/{r.get('price')!r}")
                continue
            good.append({"month": r["date"][:7], "ticker": r["ticker"],
                         "amount": shares * price})
    return good, bad


def safe_pct(cur: float, prev: float | None) -> float | None:
    """Like DAX DIVIDE(): no crash on a zero/blank base."""
    if not prev:
        return None
    return round((cur - prev) / prev * 100, 1)


def monthly_kpis(rows: list[dict]) -> list[MonthKPI]:
    rev = defaultdict(float)
    cnt = defaultdict(int)
    by_ticker = defaultdict(lambda: defaultdict(float))
    for r in rows:
        rev[r["month"]] += r["amount"]
        cnt[r["month"]] += 1
        by_ticker[r["month"]][r["ticker"]] += r["amount"]

    out, prev, running = [], None, 0.0
    for m in sorted(rev):                       # sort = the date-table order
        running += rev[m]
        top = max(by_ticker[m].items(), key=lambda kv: (kv[1], kv[0]))[0]
        out.append(MonthKPI(m, round(rev[m], 2), cnt[m], safe_pct(rev[m], prev),
                            round(running, 2), top))
        prev = rev[m]
    return out


def to_markdown(kpis: list[MonthKPI], rejected: list[str]) -> str:
    lines = ["| Month | Revenue | Trades | MoM % | Running total | Top ticker |",
             "|---|---:|---:|---:|---:|---|"]
    for k in kpis:
        mom = "n/a" if k.mom_pct is None else f"{k.mom_pct:+.1f}%"
        lines.append(f"| {k.month} | {k.revenue:,.2f} | {k.trades} | {mom} | "
                     f"{k.running_total:,.2f} | {k.top_ticker} |")
    if rejected:
        lines += ["", f"Rejected rows ({len(rejected)}):"] + [f"- {r}" for r in rejected]
    return "\n".join(lines)
