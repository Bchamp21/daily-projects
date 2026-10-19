"""Pure-Python mirror of the PySpark Silver logic (so it runs and tests without Spark).

Bronze can hold the same (ticker, trade_date) more than once (re-runs, late fixes).
Silver keeps exactly one row per key: the most recently ingested one.
Then it adds prev_close, daily_return, and price_range per ticker in date order.
"""

from __future__ import annotations

from typing import Any, Iterable

KEY = ("ticker", "trade_date")

SILVER_COLUMNS: tuple[str, ...] = (
    "ticker",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "prev_close",
    "daily_return",
    "price_range",
    "_source_row_hash",
    "_ingested_at",
)


def dedupe_latest(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one row per (ticker, trade_date): the one with the latest _ingested_at.

    Spark equivalent: row_number() over (partition by key order by _ingested_at desc) == 1.
    Ties on _ingested_at keep the first one seen (stable).
    """
    best: dict[tuple, dict[str, Any]] = {}
    for r in rows:
        k = (r["ticker"], r["trade_date"])
        cur = best.get(k)
        if cur is None or r["_ingested_at"] > cur["_ingested_at"]:
            best[k] = r
    return sorted(best.values(), key=lambda r: (r["ticker"], r["trade_date"]))


def add_derived(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add prev_close, daily_return, price_range per ticker ordered by trade_date.

    Spark equivalent: lag("close").over(Window.partitionBy("ticker").orderBy("trade_date")).
    First day per ticker has prev_close/daily_return = None.
    """
    out: list[dict[str, Any]] = []
    prev_by_ticker: dict[str, float] = {}
    for r in sorted(rows, key=lambda r: (r["ticker"], r["trade_date"])):
        prev = prev_by_ticker.get(r["ticker"])
        ret = None if prev is None else round((r["close"] - prev) / prev, 6)
        out.append(
            {
                **{c: r[c] for c in ("ticker", "trade_date", "open", "high", "low", "close", "volume")},
                "prev_close": prev,
                "daily_return": ret,
                "price_range": round(r["high"] - r["low"], 6),
                "_source_row_hash": r["_source_row_hash"],
                "_ingested_at": r["_ingested_at"],
            }
        )
        prev_by_ticker[r["ticker"]] = r["close"]
    return out


def build_silver(bronze_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bronze rows -> Silver rows (dedupe, then derive)."""
    return add_derived(dedupe_latest(bronze_rows))


def merge_upsert(
    target: list[dict[str, Any]], updates: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Delta MERGE semantics on KEY.

    WHEN MATCHED AND (hash or prev_close differs) -> UPDATE
    WHEN MATCHED AND hash same    -> skip (no-op, keeps re-runs idempotent)
    WHEN NOT MATCHED              -> INSERT
    Returns (new_target, stats).
    """
    by_key = {(r["ticker"], r["trade_date"]): dict(r) for r in target}
    stats = {"inserted": 0, "updated": 0, "unchanged": 0}
    for u in updates:
        k = (u["ticker"], u["trade_date"])
        cur = by_key.get(k)
        if cur is None:
            by_key[k] = dict(u)
            stats["inserted"] += 1
        elif (cur["_source_row_hash"] != u["_source_row_hash"]
              or cur.get("prev_close") != u.get("prev_close")):
            by_key[k] = dict(u)
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    merged = sorted(by_key.values(), key=lambda r: (r["ticker"], r["trade_date"]))
    return merged, stats
