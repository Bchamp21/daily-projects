from datetime import date
from decimal import Decimal

from recon import compare, key_diff, profile, reload_dates, row_hash, value_diff, date_counts_diff

d1, d2 = date(2026, 11, 18), date(2026, 11, 19)
K, S = ["ticker", "trade_date"], ["close", "volume"]
SRC = [
    {"ticker": "AAPL", "trade_date": d1, "close": 228.10, "volume": 100},
    {"ticker": "MSFT", "trade_date": d1, "close": 415.00, "volume": 200},
    {"ticker": "AAPL", "trade_date": d2, "close": 229.50, "volume": 110},
]


def status(findings):
    return {f.check: f.status for f in findings}


def test_identical_tables_all_pass():
    assert set(status(compare(SRC, list(SRC), K, S, "trade_date")).values()) == {"PASS"}


def test_hash_normalizes_case_space_and_float_noise():
    a = {"ticker": "AAPL", "close": 228.1}
    b = {"ticker": " aapl", "close": Decimal("228.10000")}
    assert row_hash(a, ["ticker", "close"]) == row_hash(b, ["ticker", "close"])
    assert row_hash({"x": None}, ["x"]) != row_hash({"x": ""}, ["x"])


def test_missing_and_extra_keys():
    tgt = SRC[:2] + [{"ticker": "TSLA", "trade_date": d2, "close": 1, "volume": 1}]
    missing, extra, dups = key_diff(SRC, tgt, K)
    assert missing == [("AAPL", "2026-11-19")]
    assert extra == [("TSLA", "2026-11-19")]
    assert dups == []


def test_duplicates_fail_even_when_counts_look_ok():
    tgt = [SRC[0], SRC[0], SRC[2]]  # MSFT lost, AAPL doubled -> count still 3
    s = status(compare(SRC, tgt, K, S, "trade_date"))
    assert s["row_count"] == "PASS"
    assert s["duplicate_keys"] == "FAIL" and s["missing_keys"] == "FAIL"


def test_changed_value_found_by_hash_and_sum():
    tgt = [dict(r) for r in SRC]
    tgt[1]["close"] = 451.00
    assert value_diff(SRC, tgt, K, S) == [("MSFT", "2026-11-18")]
    s = status(compare(SRC, tgt, K, S, "trade_date"))
    assert s["sum_close"] == "FAIL" and s["changed_values"] == "FAIL"


def test_sum_tolerance_allows_rounding():
    tgt = [dict(r) for r in SRC]
    tgt[0]["close"] = 228.105
    s = status(compare(SRC, tgt, K, S, "trade_date", tolerance=Decimal("0.01")))
    assert s["sum_close"] == "PASS"


def test_freshness_lag():
    s = status(compare(SRC, SRC[:2], K, S, "trade_date", max_lag_days=0))
    assert s["freshness"] == "FAIL"
    s = status(compare(SRC, SRC[:2], K, S, "trade_date", max_lag_days=1))
    assert s["freshness"] == "PASS"


def test_date_counts_and_reload_dates():
    tgt = [dict(r) for r in SRC[:2]]
    tgt[0]["volume"] = 999
    assert date_counts_diff(profile(SRC, S, "trade_date"), profile(tgt, S, "trade_date")) == {d2: (1, 0)}
    assert reload_dates(SRC, tgt, K, S, "trade_date") == [d1, d2]


def test_empty_target_is_safe():
    s = status(compare(SRC, [], K, S, "trade_date"))
    assert s["row_count"] == "FAIL" and s["freshness"] == "FAIL"
