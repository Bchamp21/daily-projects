"""SCD Type 2 merge in pure Python (mirrors databricks/02_scd2_merge.sql).

Dimension row shape:
  ticker_sk, ticker, company_name, sector, exchange, row_hash,
  valid_from, valid_to, is_current
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date

TRACKED = ("company_name", "sector", "exchange")  # changes here create a new version
OPEN_END = date(9999, 12, 31)


def row_hash(rec: dict) -> str:
    """Hash only tracked columns, so untracked noise never makes a new version."""
    raw = "|".join(str(rec.get(c, "")).strip().lower() for c in TRACKED)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class MergeStats:
    inserted: int = 0      # brand-new tickers
    changed: int = 0       # old version closed + new version opened
    unchanged: int = 0
    delisted: int = 0      # current row closed because ticker left the source
    log: list[str] = field(default_factory=list)


def scd2_merge(dim: list[dict], snapshot: list[dict], as_of: date,
               close_missing: bool = True) -> tuple[list[dict], MergeStats]:
    """Apply one source snapshot to the dimension. Returns (new_dim, stats).

    Idempotent: merging the same snapshot twice changes nothing.
    """
    stats = MergeStats()
    out = [dict(r) for r in dim]
    current = {r["ticker"]: r for r in out if r["is_current"]}
    next_sk = max((r["ticker_sk"] for r in out), default=0) + 1

    seen = set()
    for src in snapshot:
        t = src["ticker"].strip().upper()
        if t in seen:
            raise ValueError(f"duplicate ticker in snapshot: {t}")
        seen.add(t)
        h = row_hash(src)
        cur = current.get(t)
        if cur and cur["row_hash"] == h:
            stats.unchanged += 1
            continue
        if cur:
            if as_of <= cur["valid_from"]:
                raise ValueError(f"{t}: as_of {as_of} not after valid_from {cur['valid_from']}")
            cur["valid_to"], cur["is_current"] = as_of, False
            stats.changed += 1
            stats.log.append(f"{t}: new version")
        else:
            stats.inserted += 1
            stats.log.append(f"{t}: inserted")
        out.append({
            "ticker_sk": next_sk, "ticker": t,
            **{c: src.get(c) for c in TRACKED},
            "row_hash": h, "valid_from": as_of, "valid_to": OPEN_END, "is_current": True,
        })
        next_sk += 1

    if close_missing:
        for t, cur in current.items():
            if t not in seen and cur["is_current"]:
                cur["valid_to"], cur["is_current"] = as_of, False
                stats.delisted += 1
                stats.log.append(f"{t}: closed (missing from source)")
    return out, stats


def lookup_as_of(dim: list[dict], ticker: str, on: date) -> dict | None:
    """Point-in-time join: which version was true on date `on`?"""
    for r in dim:
        if r["ticker"] == ticker and r["valid_from"] <= on < r["valid_to"]:
            return r
    return None


def check_dim(dim: list[dict]) -> list[str]:
    """Data tests: one current row per ticker, no overlapping ranges."""
    errors = []
    by_t: dict[str, list[dict]] = {}
    for r in dim:
        by_t.setdefault(r["ticker"], []).append(r)
    for t, rows in by_t.items():
        if sum(r["is_current"] for r in rows) > 1:
            errors.append(f"{t}: more than one current row")
        rows = sorted(rows, key=lambda r: r["valid_from"])
        for a, b in zip(rows, rows[1:]):
            if a["valid_to"] > b["valid_from"]:
                errors.append(f"{t}: overlapping versions")
    return errors
