"""Load prices, group by ticker, run every rule, return alerts."""
from __future__ import annotations

import csv
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .rules import Rule

log = logging.getLogger("pricealerts")


@dataclass(frozen=True)
class Alert:
    ticker: str
    rule: str
    message: str


def load_prices(path: str | Path) -> dict[str, list[float]]:
    """CSV with columns ticker,date,close -> {ticker: [closes sorted by date]}."""
    rows: dict[str, list[tuple[str, float]]] = defaultdict(list)
    with open(path, newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            try:
                rows[r["ticker"].upper()].append((r["date"], float(r["close"])))
            except (KeyError, ValueError, AttributeError):
                log.warning("skipping bad row %d: %r", i, r)
    return {t: [c for _, c in sorted(v)] for t, v in rows.items()}


def evaluate(rules: list[Rule], prices: dict[str, list[float]]) -> list[Alert]:
    alerts = []
    for rule in rules:
        closes = prices.get(rule.ticker)
        if not closes:
            log.info("no prices for %s, skipping %s", rule.ticker, rule.kind)
            continue
        msg = rule.check(closes)
        if msg:
            alerts.append(Alert(rule.ticker, rule.kind, msg))
    return alerts
