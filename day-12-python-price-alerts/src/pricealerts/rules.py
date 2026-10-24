"""Alert rules: each rule looks at one ticker's price history and says fire / no fire.

A registry maps the JSON "type" string to a rule class, so adding a new rule
is one small class plus one decorator line (open/closed principle).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

RULES: dict[str, type["Rule"]] = {}


def register(name: str) -> Callable[[type["Rule"]], type["Rule"]]:
    def deco(cls: type["Rule"]) -> type["Rule"]:
        RULES[name] = cls
        cls.kind = name
        return cls
    return deco


@dataclass(frozen=True)
class Rule:
    ticker: str
    kind = "base"

    def check(self, closes: list[float]) -> str | None:  # pragma: no cover
        """Return a message if the rule fires, else None. closes = oldest -> newest."""
        raise NotImplementedError


@register("above")
@dataclass(frozen=True)
class Above(Rule):
    price: float = 0.0

    def check(self, closes):
        last = closes[-1]
        return f"{self.ticker} closed {last:.2f} above {self.price:.2f}" if last > self.price else None


@register("below")
@dataclass(frozen=True)
class Below(Rule):
    price: float = 0.0

    def check(self, closes):
        last = closes[-1]
        return f"{self.ticker} closed {last:.2f} below {self.price:.2f}" if last < self.price else None


@register("pct_change")
@dataclass(frozen=True)
class PctChange(Rule):
    """Fires when the last day's move is at least `pct` percent (up or down)."""
    pct: float = 5.0

    def check(self, closes):
        if len(closes) < 2 or closes[-2] == 0:
            return None
        move = (closes[-1] - closes[-2]) / closes[-2] * 100
        return f"{self.ticker} moved {move:+.1f}% in one day" if abs(move) >= self.pct else None


@register("sma_cross")
@dataclass(frozen=True)
class SmaCross(Rule):
    """Fires on the day the close crosses its N-day simple moving average."""
    window: int = 3

    def check(self, closes):
        n = self.window
        if len(closes) < n + 1:
            return None
        sma_today = sum(closes[-n:]) / n
        sma_prev = sum(closes[-n - 1:-1]) / n
        was_above = closes[-2] > sma_prev
        is_above = closes[-1] > sma_today
        if was_above == is_above:
            return None
        side = "above" if is_above else "below"
        return f"{self.ticker} crossed {side} its {n}-day SMA ({sma_today:.2f})"


class RuleConfigError(ValueError):
    pass


def build_rule(cfg: dict) -> Rule:
    cfg = dict(cfg)
    kind = cfg.pop("type", None)
    if kind not in RULES:
        raise RuleConfigError(f"unknown rule type {kind!r}; known: {sorted(RULES)}")
    if not cfg.get("ticker"):
        raise RuleConfigError(f"rule {kind!r} needs a ticker")
    cfg["ticker"] = str(cfg["ticker"]).upper()
    try:
        return RULES[kind](**cfg)
    except TypeError as e:
        raise RuleConfigError(f"bad fields for {kind!r}: {e}") from e


def load_rules(path: str | Path) -> list[Rule]:
    data = json.loads(Path(path).read_text())
    return [build_rule(r) for r in data["rules"]]
