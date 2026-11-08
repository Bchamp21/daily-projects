import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from late_facts.core import (  # noqa: E402
    apply_events,
    check_facts,
    collapse_batch,
    compute_gold,
    derive_watermark,
    merge_gold,
    too_late,
)

D3, D4, D6 = date(2026, 10, 3), date(2026, 10, 4), date(2026, 10, 6)
SEP20 = date(2026, 9, 20)

A3 = {"ticker": "AAPL", "trade_date": D3, "close": "178.50", "published_at": "2026-10-03T21:00:00"}
M3 = {"ticker": "MSFT", "trade_date": D3, "close": "420.00", "published_at": "2026-10-03T21:00:00"}
A4 = {"ticker": "AAPL", "trade_date": D4, "close": "180.00", "published_at": "2026-10-04T21:00:00"}
M4 = {"ticker": "MSFT", "trade_date": D4, "close": "422.00", "published_at": "2026-10-04T21:00:00"}
A3_FIX = {"ticker": "AAPL", "trade_date": D3, "close": "177.20", "published_at": "2026-10-06T08:15:00"}
A6 = {"ticker": "AAPL", "trade_date": D6, "close": "181.10", "published_at": "2026-10-06T21:00:00"}
M6 = {"ticker": "MSFT", "trade_date": D6, "close": "419.50", "published_at": "2026-10-06T21:00:00"}
OLD = {"ticker": "AAPL", "trade_date": SEP20, "close": "170.00", "published_at": "2026-10-06T08:00:00"}


def load_two_days():
    facts, _, _ = apply_events([], [A3, M3], D3)
    facts, _, _ = apply_events(facts, [A4, M4], D4)
    return facts


def test_initial_load_inserts():
    facts, q, s = apply_events([], [A3, M3], D3)
    assert s.inserted == 2 and not q and s.gold_from == D3
    assert all(r["version"] == 1 and not r["is_correction"] for r in facts)
    assert derive_watermark(facts) == D3


def test_on_time_next_day_advances_watermark():
    facts = load_two_days()
    assert derive_watermark(facts) == D4
    assert len(facts) == 4


def test_correction_updates_close_and_bumps_version():
    facts = load_two_days()
    facts, q, s = apply_events(facts, [A3_FIX], D6)
    assert s.corrected == 1 and not q
    aapl = next(r for r in facts if r["ticker"] == "AAPL" and r["trade_date"] == D3)
    assert aapl["close"] == Decimal("177.20")
    assert aapl["version"] == 2 and aapl["is_correction"]
    assert aapl["ingested_on"] == D6


def test_correction_changes_next_day_return():
    facts = load_two_days()
    before = compute_gold(facts)
    ret_before = next(r for r in before if r["ticker"] == "AAPL" and r["trade_date"] == D4)["daily_return"]
    facts, _, s = apply_events(facts, [A3_FIX], D6)
    after = compute_gold(facts, from_date=s.gold_from)
    ret_after = next(r for r in after if r["ticker"] == "AAPL" and r["trade_date"] == D4)["daily_return"]
    assert ret_before == (Decimal("180.00") / Decimal("178.50")) - 1
    assert ret_after == (Decimal("180.00") / Decimal("177.20")) - 1
    assert ret_after != ret_before
    assert s.gold_from == D3


def test_replay_is_idempotent():
    facts, _, _ = apply_events([], [A3, M3], D3)
    again, _, s = apply_events(facts, [A3, M3], D3)
    assert again == facts and s.unchanged == 2 and s.inserted == 0


def test_stale_publish_is_ignored():
    facts = load_two_days()
    facts, _, s = apply_events(facts, [A3_FIX], D6)
    stale = {**A3, "close": "999.00", "published_at": "2026-10-03T20:00:00"}
    facts2, _, s2 = apply_events(facts, [stale], D6)
    aapl = next(r for r in facts2 if r["ticker"] == "AAPL" and r["trade_date"] == D3)
    assert s2.stale == 1 and aapl["close"] == Decimal("177.20")


def test_too_late_event_is_quarantined():
    facts = load_two_days()
    facts2, q, s = apply_events(facts, [OLD], D6)
    assert s.quarantined == 1 and len(q) == 1
    assert q[0]["trade_date"] == SEP20
    assert not any(r["trade_date"] == SEP20 for r in facts2)
    assert facts2 == facts


def test_late_first_arrival_within_window_is_inserted():
    facts = load_two_days()
    missing = {"ticker": "MSFT", "trade_date": date(2026, 10, 2), "close": "418.00",
               "published_at": "2026-10-06T09:00:00"}
    facts, q, s = apply_events(facts, [missing], D6)
    assert s.inserted == 1 and not q
    assert any(r["ticker"] == "MSFT" and r["trade_date"] == date(2026, 10, 2) for r in facts)


def test_tighter_lateness_quarantines_the_correction():
    facts = load_two_days()
    facts2, q, s = apply_events(facts, [A3_FIX], D6, allowed_lateness_days=1)
    # watermark is Oct 4; Oct 4 - 1 day = Oct 3; too_late is strictly before Oct 3.
    # Oct 3 == cutoff, so still accepted at lateness=1. lateness=0 rejects anything before Oct 4.
    facts3, q0, s0 = apply_events(facts, [A3_FIX], D6, allowed_lateness_days=0)
    assert s.corrected == 1 and not q
    assert s0.quarantined == 1 and q0[0]["trade_date"] == D3
    assert not any(r.get("is_correction") for r in facts3)


def test_sma_uses_lookback_before_from_date():
    facts = load_two_days()
    facts, _, _ = apply_events(facts, [A6, M6], D6)
    gold = compute_gold(facts, from_date=D6, sma_window=3)
    aapl = next(r for r in gold if r["ticker"] == "AAPL")
    assert aapl["trade_date"] == D6
    expected = (Decimal("178.50") + Decimal("180.00") + Decimal("181.10")) / 3
    assert aapl["sma"] == expected


def test_collapse_keeps_newest_publish_in_batch():
    older = {**A3_FIX, "close": "176.00", "published_at": "2026-10-06T07:00:00"}
    collapsed = collapse_batch([older, A3_FIX])
    assert len(collapsed) == 1
    assert collapsed[0]["close"] == Decimal("177.20")


def test_merge_gold_replaces_from_dirty_date():
    facts = load_two_days()
    gold = compute_gold(facts)
    facts, _, s = apply_events(facts, [A3_FIX], D6)
    recomputed = compute_gold(facts, from_date=s.gold_from)
    merged = merge_gold(gold, recomputed, s.gold_from)
    # every gold row is on/after D3, so the whole table is replaced
    aapl_d4 = next(r for r in merged if r["ticker"] == "AAPL" and r["trade_date"] == D4)
    assert aapl_d4["daily_return"] == (Decimal("180.00") / Decimal("177.20")) - 1


def test_check_facts_catches_dupes_and_bad_correction():
    facts, _, _ = apply_events([], [A3], D3)
    dup = facts + [dict(facts[0])]
    assert any("duplicate grain" in e for e in check_facts(dup))
    bad = [{**facts[0], "is_correction": True, "version": 1}]
    assert any("correction must bump version" in e for e in check_facts(bad))


def test_demo_batches_end_to_end():
    data = Path(__file__).resolve().parents[1] / "data"
    facts: list[dict] = []
    last_q = []
    last_s = None
    for name in sorted(p.name for p in data.glob("batch_*.json")):
        import json
        run_date = date.fromisoformat(name[6:16])
        events = json.loads((data / name).read_text())
        facts, last_q, last_s = apply_events(facts, events, run_date)
    assert last_s.corrected == 1 and last_s.quarantined == 1
    assert last_q[0]["trade_date"] == SEP20
    aapl = next(r for r in facts if r["ticker"] == "AAPL" and r["trade_date"] == D3)
    assert aapl["close"] == Decimal("177.20") and aapl["version"] == 2
    assert check_facts(facts) == []
    assert too_late(SEP20, D4, 3) is True
    assert too_late(D3, D4, 3) is False


def test_normalize_ticker_and_iso_strings():
    facts, _, s = apply_events(
        [],
        [{"ticker": " aapl ", "trade_date": "2026-10-03", "close": 178.5,
          "published_at": datetime(2026, 10, 3, 21, 0, 0)}],
        D3,
    )
    assert s.inserted == 1 and facts[0]["ticker"] == "AAPL"
