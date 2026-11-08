"""Late-arriving facts for a Silver price table (mirrors databricks/02_merge_corrections.sql).

Fact grain: (ticker, trade_date). A later vendor publish of the same grain is a correction.
Events whose trade_date is older than watermark - allowed_lateness go to quarantine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal


def _as_date(v: date | str) -> date:
    return v if isinstance(v, date) and not isinstance(v, datetime) else date.fromisoformat(str(v)[:10])


def _as_dt(v: datetime | str) -> datetime:
    if isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v).replace("Z", "+00:00")).replace(tzinfo=None)


def _as_dec(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def derive_watermark(facts: list[dict]) -> date | None:
    if not facts:
        return None
    return max(_as_date(r["trade_date"]) for r in facts)


def too_late(trade_date: date, watermark: date | None, allowed_lateness_days: int) -> bool:
    """True when the event is older than the allowed lookback behind the watermark."""
    if watermark is None:
        return False
    return trade_date < watermark - timedelta(days=allowed_lateness_days)


@dataclass
class ApplyStats:
    inserted: int = 0
    corrected: int = 0
    unchanged: int = 0
    stale: int = 0
    quarantined: int = 0
    gold_from: date | None = None
    log: list[str] = field(default_factory=list)


def collapse_batch(events: list[dict]) -> list[dict]:
    """One row per (ticker, trade_date): keep the newest published_at."""
    best: dict[tuple[str, date], dict] = {}
    for raw in events:
        rec = {
            "ticker": normalize_ticker(raw["ticker"]),
            "trade_date": _as_date(raw["trade_date"]),
            "close": _as_dec(raw["close"]),
            "published_at": _as_dt(raw["published_at"]),
        }
        key = (rec["ticker"], rec["trade_date"])
        if key not in best or rec["published_at"] > best[key]["published_at"]:
            best[key] = rec
    return list(best.values())


def apply_events(
    facts: list[dict],
    events: list[dict],
    run_date: date,
    watermark: date | None = None,
    allowed_lateness_days: int = 3,
) -> tuple[list[dict], list[dict], ApplyStats]:
    """Apply one ingest batch. Returns (new_facts, quarantine, stats).

    Idempotent: replaying the same batch changes nothing.
    Stale: event.published_at older than the row already stored.
    """
    stats = ApplyStats()
    out = [dict(r) for r in facts]
    index = {(r["ticker"], _as_date(r["trade_date"])): r for r in out}
    if watermark is None:
        watermark = derive_watermark(out)

    quarantine: list[dict] = []
    dirty: list[date] = []

    for ev in collapse_batch(events):
        if too_late(ev["trade_date"], watermark, allowed_lateness_days):
            quarantine.append({**ev, "reason": "beyond_allowed_lateness", "quarantined_on": run_date})
            stats.quarantined += 1
            stats.log.append(f"{ev['ticker']} {ev['trade_date']}: quarantined (too late)")
            continue

        key = (ev["ticker"], ev["trade_date"])
        cur = index.get(key)
        if cur is None:
            row = {
                "ticker": ev["ticker"],
                "trade_date": ev["trade_date"],
                "close": ev["close"],
                "version": 1,
                "published_at": ev["published_at"],
                "ingested_on": run_date,
                "is_correction": False,
            }
            out.append(row)
            index[key] = row
            stats.inserted += 1
            dirty.append(ev["trade_date"])
            late = watermark is not None and ev["trade_date"] < watermark
            kind = "late insert" if late else "inserted"
            stats.log.append(f"{ev['ticker']} {ev['trade_date']}: {kind}")
            continue

        cur_pub = _as_dt(cur["published_at"])
        if ev["published_at"] < cur_pub:
            stats.stale += 1
            stats.log.append(f"{ev['ticker']} {ev['trade_date']}: stale, ignored")
            continue
        if ev["published_at"] == cur_pub and ev["close"] == _as_dec(cur["close"]):
            stats.unchanged += 1
            continue
        if ev["close"] == _as_dec(cur["close"]):
            cur["published_at"] = ev["published_at"]
            stats.unchanged += 1
            continue

        cur["close"] = ev["close"]
        cur["published_at"] = ev["published_at"]
        cur["version"] = int(cur["version"]) + 1
        cur["is_correction"] = True
        cur["ingested_on"] = run_date
        stats.corrected += 1
        dirty.append(ev["trade_date"])
        stats.log.append(
            f"{ev['ticker']} {ev['trade_date']}: corrected to {ev['close']} (v{cur['version']})"
        )

    stats.gold_from = min(dirty) if dirty else None
    return out, quarantine, stats


def compute_gold(facts: list[dict], from_date: date | None = None, sma_window: int = 3) -> list[dict]:
    """Daily return and SMA. from_date rows are returned; earlier rows are lookback only.

    Correcting day D dirties every later Gold row for that ticker, because returns
    and SMA both read D's close. Replace Gold from gold_from forward.
    """
    by_ticker: dict[str, list[dict]] = {}
    for r in facts:
        by_ticker.setdefault(r["ticker"], []).append(r)

    gold: list[dict] = []
    for ticker, rows in sorted(by_ticker.items()):
        rows = sorted(rows, key=lambda r: _as_date(r["trade_date"]))
        closes: list[Decimal] = []
        prev: Decimal | None = None
        for r in rows:
            close = _as_dec(r["close"])
            closes.append(close)
            ret = None if prev is None else (close / prev) - 1
            sma = None
            if len(closes) >= sma_window:
                window = closes[-sma_window:]
                sma = sum(window) / sma_window
            td = _as_date(r["trade_date"])
            if from_date is None or td >= from_date:
                gold.append({
                    "ticker": ticker,
                    "trade_date": td,
                    "close": close,
                    "daily_return": ret,
                    "sma": sma,
                    "version": r["version"],
                })
            prev = close
    return gold


def merge_gold(existing: list[dict], recomputed: list[dict], from_date: date) -> list[dict]:
    """Keep Gold rows before from_date; replace from_date onward with recomputed."""
    kept = [r for r in existing if _as_date(r["trade_date"]) < from_date]
    return kept + recomputed


def check_facts(facts: list[dict]) -> list[str]:
    """Must-be-empty data tests (same idea as Day 22 check_dim)."""
    errs: list[str] = []
    seen: set[tuple[str, date]] = set()
    for r in facts:
        key = (r["ticker"], _as_date(r["trade_date"]))
        if key in seen:
            errs.append(f"duplicate grain {key[0]} {key[1]}")
        seen.add(key)
        if _as_dec(r["close"]) <= 0:
            errs.append(f"{r['ticker']} {r['trade_date']}: close must be > 0")
        if int(r["version"]) < 1:
            errs.append(f"{r['ticker']} {r['trade_date']}: version < 1")
        if r.get("is_correction") and int(r["version"]) < 2:
            errs.append(f"{r['ticker']} {r['trade_date']}: correction must bump version")
    return errs
