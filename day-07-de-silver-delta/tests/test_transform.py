import json
from pathlib import Path

import pytest

from silver.transform import add_derived, build_silver, dedupe_latest, merge_upsert

DATA = Path(__file__).resolve().parents[1] / "data" / "bronze_sample.jsonl"


def bronze():
    return [json.loads(l) for l in DATA.read_text().splitlines() if l.strip()]


def row(t, d, close, ts="2026-10-17T01:00:00Z", h="x", hi=None, lo=None):
    return {"ticker": t, "trade_date": d, "open": close, "high": hi or close + 1,
            "low": lo or close - 1, "close": close, "volume": 100,
            "_ingested_at": ts, "_source_row_hash": h}


def test_dedupe_keeps_latest_ingest():
    rows = [row("AAPL", "2026-10-03", 228.6, "2026-10-17T01:00:00Z", "old"),
            row("AAPL", "2026-10-03", 228.9, "2026-10-18T01:00:00Z", "new")]
    out = dedupe_latest(rows)
    assert len(out) == 1 and out[0]["close"] == 228.9


def test_sample_bronze_dedupes_to_one_row_per_key():
    silver = build_silver(bronze())
    keys = [(r["ticker"], r["trade_date"]) for r in silver]
    assert len(bronze()) == 9
    assert len(silver) == 7 and len(keys) == len(set(keys))
    aapl3 = next(r for r in silver if r["ticker"] == "AAPL" and r["trade_date"] == "2026-10-03")
    assert aapl3["close"] == 228.90  # corrected value from run-2 wins


def test_daily_return_uses_previous_close_per_ticker():
    out = add_derived([row("MSFT", "2026-10-02", 110.0), row("MSFT", "2026-10-01", 100.0),
                       row("AAPL", "2026-10-01", 50.0)])
    msft = [r for r in out if r["ticker"] == "MSFT"]
    assert msft[0]["prev_close"] is None and msft[0]["daily_return"] is None
    assert msft[1]["prev_close"] == 100.0
    assert msft[1]["daily_return"] == pytest.approx(0.10)
    aapl = [r for r in out if r["ticker"] == "AAPL"][0]
    assert aapl["prev_close"] is None  # does not leak across tickers


def test_price_range():
    out = add_derived([row("NVDA", "2026-10-01", 10.0, hi=12.5, lo=9.0)])
    assert out[0]["price_range"] == pytest.approx(3.5)


def test_merge_insert_update_and_idempotent():
    first, s1 = merge_upsert([], [row("A", "2026-10-01", 1.0, h="h1")])
    assert s1 == {"inserted": 1, "updated": 0, "unchanged": 0}
    same, s2 = merge_upsert(first, [row("A", "2026-10-01", 1.0, h="h1")])
    assert s2["unchanged"] == 1 and same == first
    changed, s3 = merge_upsert(same, [row("A", "2026-10-01", 2.0, h="h2"),
                                      row("B", "2026-10-01", 5.0, h="h3")])
    assert s3 == {"inserted": 1, "updated": 1, "unchanged": 0}
    assert len(changed) == 2 and changed[0]["close"] == 2.0


def test_cli_rerun_is_idempotent(tmp_path):
    from silver.__main__ import main
    target = tmp_path / "silver.jsonl"
    assert main([str(DATA), str(target)]) == 0
    first = target.read_text()
    assert main([str(DATA), str(target)]) == 0
    assert target.read_text() == first
    assert len(first.splitlines()) == 7
