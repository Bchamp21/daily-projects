import statistics
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_gold import build  # noqa: E402


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    path = tmp_path_factory.mktemp("dbt") / "test.duckdb"
    assert build(path), "dbt build (models + data tests) should pass"
    con = duckdb.connect(str(path))
    yield con
    con.close()


def test_summary_has_one_row_per_ticker(db):
    rows = db.execute("select ticker from gold_ticker_summary order by 1").fetchall()
    assert rows == [("AAPL",), ("MSFT",)]


def test_period_return_matches_first_and_last_close(db):
    r = db.execute(
        "select period_return from gold_ticker_summary where ticker='AAPL'"
    ).fetchone()[0]
    assert r == pytest.approx(229.50 / 226.80 - 1)


def test_volatility_is_sample_stddev_ignoring_null_first_day(db):
    v = db.execute(
        "select volatility from gold_ticker_summary where ticker='MSFT'"
    ).fetchone()[0]
    assert v == pytest.approx(statistics.stdev([0.003476, 0.004181, -0.019986, 0.007040]))


def test_sma3_and_completeness_flag(db):
    rows = db.execute(
        "select sma_3, sma_3_complete from gold_price_metrics "
        "where ticker='AAPL' order by trade_date"
    ).fetchall()
    assert rows[0] == (pytest.approx(226.80), False)
    assert rows[2] == (pytest.approx((226.80 + 227.40 + 228.60) / 3), True)


def test_max_drawdown_from_running_high(db):
    dd = db.execute(
        "select max_drawdown from gold_ticker_summary where ticker='MSFT'"
    ).fetchone()[0]
    assert dd == pytest.approx(411.90 / 420.30 - 1)
