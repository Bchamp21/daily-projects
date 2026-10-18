import pytest
from pydantic import ValidationError

from pricecheck.models import PriceRow

GOOD = dict(symbol=" aapl ", trade_date="2026-10-12", open=10, high=12, low=9, close=11, volume=100)


def test_good_row_is_cleaned():
    row = PriceRow(**GOOD)
    assert row.symbol == "AAPL"
    assert row.trade_date.isoformat() == "2026-10-12"


@pytest.mark.parametrize("change", [
    {"open": -1},            # negative price
    {"low": 13},             # low > high
    {"close": 20},           # close above high
    {"volume": -5},          # negative volume
    {"trade_date": "2026-13-01"},  # bad date
    {"symbol": "AB1"},       # digits in symbol
])
def test_bad_rows_rejected(change):
    with pytest.raises(ValidationError):
        PriceRow(**{**GOOD, **change})
