import pytest
from dq_expect.core import (Expectation, WARN, DROP, FAIL, ExpectationFailed, run, gate,
                            silver_price_rules, render_sql)


def row(**kw):
    base = {"ticker": "AAPL", "trade_date": "2026-11-13", "close": 10.0, "high": 11, "low": 9, "volume": 1}
    return {**base, **kw}


def test_clean_row_passes_all():
    res = run([row()], silver_price_rules())
    assert len(res.clean) == 1 and not res.quarantine
    assert all(m["failed"] == 0 for m in res.metrics.values())


def test_warn_keeps_row_but_counts():
    res = run([row(volume=-5)], silver_price_rules())
    assert len(res.clean) == 1
    assert res.metrics["volume_not_negative"]["failed"] == 1


def test_drop_quarantines_with_all_reasons():
    res = run([row(ticker="", close=-1)], silver_price_rules())
    assert not res.clean
    assert res.quarantine[0]["_dq_reasons"] == ["ticker_present", "positive_close"]


def test_null_value_is_a_violation_not_a_crash():
    res = run([row(close=None)], silver_price_rules())
    assert res.quarantine[0]["_dq_reasons"] == ["positive_close"]


def test_fail_stops_the_update():
    with pytest.raises(ExpectationFailed) as e:
        run([row(), row(trade_date=None)], silver_price_rules())
    assert e.value.name == "valid_date"


def test_no_rows_lost():
    rows = [row(), row(ticker=""), row(high=1, low=5), row(volume=-1)]
    res = run(rows, silver_price_rules())
    assert len(res.clean) + len(res.quarantine) == len(rows)
    assert res.pass_rate == 0.5


def test_gate_blocks_bad_batch():
    res = run([row(), row(close=0), row(close=0)], silver_price_rules())
    gate(res, 0.3)
    with pytest.raises(ExpectationFailed):
        gate(res, 0.9)


def test_empty_batch_is_ok():
    assert run([], silver_price_rules()).pass_rate == 1.0


def test_duplicate_names_rejected():
    e = Expectation("x", lambda r: True)
    with pytest.raises(ValueError):
        run([row()], [e, e])


def test_render_sql():
    sql = render_sql("silver_prices", silver_price_rules())
    assert "CONSTRAINT positive_close EXPECT (close > 0) ON VIOLATION DROP ROW" in sql
    assert "CONSTRAINT volume_not_negative EXPECT (volume >= 0)," in sql
    assert "ON VIOLATION FAIL UPDATE" in sql
