"""Lakeflow-style data quality expectations for Silver stock prices.

Mirrors Databricks declarative pipeline semantics:
  WARN  -> keep the row, count the violation
  DROP  -> remove the row, count it (we also route it to quarantine with reasons)
  FAIL  -> stop the whole update (nothing is written)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

WARN, DROP, FAIL = "warn", "drop", "fail"
Row = dict


class ExpectationFailed(Exception):
    def __init__(self, name: str, row: Row):
        super().__init__(f"expectation '{name}' failed on row {row}")
        self.name, self.row = name, row


@dataclass(frozen=True)
class Expectation:
    name: str
    check: Callable[[Row], bool]
    action: str = WARN
    sql: str = ""  # the SQL constraint we render for Databricks

    def ok(self, row: Row) -> bool:
        try:
            return bool(self.check(row))
        except (TypeError, KeyError, ValueError):
            return False  # a None/missing value is a violation, like SQL NULL -> not true


@dataclass
class Result:
    clean: list = field(default_factory=list)
    quarantine: list = field(default_factory=list)  # rows + "_dq_reasons"
    metrics: dict = field(default_factory=dict)      # name -> {"passed", "failed", "action"}

    @property
    def pass_rate(self) -> float:
        total = len(self.clean) + len(self.quarantine)
        return 1.0 if total == 0 else len(self.clean) / total


def run(rows: list[Row], expectations: list[Expectation]) -> Result:
    names = [e.name for e in expectations]
    if len(names) != len(set(names)):
        raise ValueError("expectation names must be unique")
    res = Result(metrics={e.name: {"passed": 0, "failed": 0, "action": e.action} for e in expectations})
    for row in rows:
        failed_drop = []
        for e in expectations:
            if e.ok(row):
                res.metrics[e.name]["passed"] += 1
                continue
            res.metrics[e.name]["failed"] += 1
            if e.action == FAIL:
                raise ExpectationFailed(e.name, row)  # all-or-nothing: caller writes nothing
            if e.action == DROP:
                failed_drop.append(e.name)
        if failed_drop:
            res.quarantine.append({**row, "_dq_reasons": failed_drop})
        else:
            res.clean.append(row)
    return res


def gate(res: Result, min_pass_rate: float) -> None:
    """Batch-level guard: stop if too many rows were quarantined (bad upstream feed)."""
    if res.pass_rate < min_pass_rate:
        raise ExpectationFailed(f"pass_rate>={min_pass_rate}", {"pass_rate": round(res.pass_rate, 3)})


def silver_price_rules() -> list[Expectation]:
    return [
        Expectation("ticker_present", lambda r: bool(r["ticker"]), DROP, "ticker IS NOT NULL AND ticker <> ''"),
        Expectation("positive_close", lambda r: r["close"] > 0, DROP, "close > 0"),
        Expectation("high_ge_low", lambda r: r["high"] >= r["low"], DROP, "high >= low"),
        Expectation("volume_not_negative", lambda r: r["volume"] >= 0, WARN, "volume >= 0"),
        Expectation("valid_date", lambda r: r["trade_date"] is not None, FAIL, "trade_date IS NOT NULL"),
    ]


def render_sql(table: str, expectations: list[Expectation]) -> str:
    """Render a Lakeflow SQL materialized view with the same constraints."""
    clause = {WARN: "", DROP: " ON VIOLATION DROP ROW", FAIL: " ON VIOLATION FAIL UPDATE"}
    lines = [f"  CONSTRAINT {e.name} EXPECT ({e.sql}){clause[e.action]}" for e in expectations]
    return (f"CREATE OR REFRESH MATERIALIZED VIEW {table} (\n" + ",\n".join(lines)
            + "\n) AS SELECT * FROM bronze_prices;")
