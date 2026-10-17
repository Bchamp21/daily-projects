from stock_agent.tools import call_tool, latest_price, moving_average, pct_return


def test_latest_price():
    assert latest_price("aapl") == {"symbol": "AAPL", "date": "2026-10-09", "close": 232.0}


def test_moving_average():
    assert moving_average("MSFT", 3)["sma"] == round((421.30 + 419.10 + 424.60) / 3, 2)


def test_pct_return():
    assert pct_return("NVDA")["pct"] == round((128.35 - 121.40) / 121.40 * 100, 2)


def test_bad_inputs_return_errors_not_crashes():
    assert "error" in call_tool("latest_price", {"symbol": "TSLA"})
    assert "error" in call_tool("moving_average", {"symbol": "AAPL", "window": 99})
    assert "error" in call_tool("delete_db", {})
