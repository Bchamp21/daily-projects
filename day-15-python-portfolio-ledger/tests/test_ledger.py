from datetime import date
from decimal import Decimal as D

import pytest

from ledger import Ledger, Trade, InsufficientShares
from ledger.cli import main
from ledger.store import connect, insert_trades, load_trades


def T(day, side, qty, price, fee="0", tk="AAPL"):
    return Trade(date(2026, 10, day), tk, side, D(qty), D(price), D(fee))


@pytest.fixture
def led():
    return Ledger().apply_all([T(1, "BUY", "10", "100", "1"), T(5, "BUY", "10", "120", "1")])


def test_fifo_sell_uses_oldest_lot_first(led):
    # 10 @ 100.10 + 5 @ 120.10 = 1601.50 cost; proceeds 15*130 - 1 = 1949
    assert led.apply(T(10, "SELL", "15", "130", "1")) == D("347.50")
    assert led.position("AAPL") == D("5")
    assert led.cost_basis("AAPL") == D("600.50")


def test_decimal_has_no_float_drift():
    l = Ledger().apply_all([T(1, "BUY", "3", "0.1"), T(2, "SELL", "3", "0.3")])
    assert l.realized["AAPL"] == D("0.6")  # float would give 0.6000000000000001


def test_oversell_raises(led):
    with pytest.raises(InsufficientShares):
        led.apply(T(9, "SELL", "21", "130"))


@pytest.mark.parametrize("kw", [dict(side="HOLD"), dict(qty="0"), dict(price="-1"), dict(fee="-1")])
def test_bad_trades_rejected(kw):
    args = dict(day=1, side="BUY", qty="1", price="10", fee="0") | kw
    with pytest.raises(ValueError):
        T(**args)


def test_report_unrealized_and_realized(led):
    led.apply(T(10, "SELL", "15", "130", "1"))
    (row,) = led.report({"AAPL": D("125")})
    assert row["market_value"] == D("625.00")
    assert row["unrealized"] == D("24.50")
    assert row["realized"] == D("347.50")


def test_store_roundtrip_and_idempotent_import(tmp_path):
    db = str(tmp_path / "l.db")
    trades = [T(1, "BUY", "1.5", "33.333"), T(2, "SELL", "0.5", "40")]
    with connect(db) as c:
        assert insert_trades(c, trades) == 2
        assert insert_trades(c, trades) == 0  # duplicates ignored
    with connect(db) as c:
        assert load_trades(c) == trades


def test_rollback_on_error(tmp_path):
    db = str(tmp_path / "l.db")
    with pytest.raises(RuntimeError):
        with connect(db) as c:
            insert_trades(c, [T(1, "BUY", "1", "10")])
            raise RuntimeError("boom")
    with connect(db) as c:
        assert load_trades(c) == []


def test_cli_end_to_end(tmp_path, capsys):
    db = str(tmp_path / "l.db")
    assert main(["--db", db, "import", "sample/trades.csv"]) == 0
    assert main(["--db", db, "report", "--prices", "sample/prices.csv"]) == 0
    out = capsys.readouterr().out
    assert "imported 4 new trades" in out
    assert "347.50" in out and "50.00" in out  # AAPL realized, MSFT unrealized
