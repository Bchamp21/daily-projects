"""Tests for bronze.normalize."""

from __future__ import annotations

import pytest

from bronze.normalize import NormalizeError, normalize_row, source_row_hash


def test_happy_path_uppercases_ticker_and_coerces():
    raw = {
        "ticker": "aapl",
        "trade_date": "2026-10-02",
        "open": "100.5",
        "high": "102",
        "low": "99",
        "close": "101",
        "volume": "1000",
    }
    out = normalize_row(raw)
    assert out["ticker"] == "AAPL"
    assert out["trade_date"] == "2026-10-02"
    assert out["open"] == 100.5
    assert out["high"] == 102.0
    assert out["low"] == 99.0
    assert out["close"] == 101.0
    assert out["volume"] == 1000
    assert isinstance(out["volume"], int)


def test_hash_stable_across_calls():
    biz = normalize_row(
        {
            "ticker": "MSFT",
            "trade_date": "2026-10-01",
            "open": 415,
            "high": 418.25,
            "low": 413.5,
            "close": 417.1,
            "volume": 22150000,
        }
    )
    h1 = source_row_hash(biz)
    h2 = source_row_hash(dict(biz))
    assert h1 == h2
    assert len(h1) == 64


def test_hash_changes_when_close_changes():
    a = normalize_row(
        {
            "ticker": "NVDA",
            "trade_date": "2026-10-01",
            "open": 120.5,
            "high": 123,
            "low": 119.8,
            "close": 122.4,
            "volume": 100,
        }
    )
    b = dict(a)
    b["close"] = 122.5
    assert source_row_hash(a) != source_row_hash(b)


def test_reject_low_greater_than_high():
    with pytest.raises(NormalizeError) as ei:
        normalize_row(
            {
                "ticker": "BADX",
                "trade_date": "2026-10-01",
                "open": 100,
                "high": 101,
                "low": 105,
                "close": 100.5,
                "volume": 1000,
            }
        )
    assert "low" in ei.value.reason.lower()


def test_reject_bad_trade_date():
    with pytest.raises(NormalizeError) as ei:
        normalize_row(
            {
                "ticker": "ZZ",
                "trade_date": "not-a-date",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "volume": 500,
            }
        )
    assert "trade_date" in ei.value.reason


def test_reject_missing_ticker():
    with pytest.raises(NormalizeError) as ei:
        normalize_row(
            {
                "ticker": "",
                "trade_date": "2026-10-01",
                "open": 1,
                "high": 2,
                "low": 0.5,
                "close": 1.5,
                "volume": 10,
            }
        )
    assert "ticker" in ei.value.reason


def test_reject_open_outside_range():
    with pytest.raises(NormalizeError) as ei:
        normalize_row(
            {
                "ticker": "X",
                "trade_date": "2026-10-01",
                "open": 200,
                "high": 110,
                "low": 100,
                "close": 105,
                "volume": 10,
            }
        )
    assert "open" in ei.value.reason
