from datetime import date
from .core import compare, reload_dates

d1, d2, d3 = date(2026, 11, 18), date(2026, 11, 19), date(2026, 11, 20)
src = [
    {"ticker": "AAPL", "trade_date": d1, "close": 228.10, "volume": 100},
    {"ticker": "MSFT", "trade_date": d1, "close": 415.00, "volume": 200},
    {"ticker": "AAPL", "trade_date": d2, "close": 229.50, "volume": 110},
    {"ticker": "MSFT", "trade_date": d2, "close": 417.25, "volume": 210},
    {"ticker": "AAPL", "trade_date": d3, "close": 230.00, "volume": 120},
]
tgt = [
    {"ticker": "aapl ", "trade_date": d1, "close": 228.1, "volume": 100},  # same after normalize
    {"ticker": "MSFT", "trade_date": d1, "close": 415.00, "volume": 200},
    {"ticker": "AAPL", "trade_date": d2, "close": 229.50, "volume": 110},
    {"ticker": "MSFT", "trade_date": d2, "close": 471.25, "volume": 210},  # typo in flight
    # AAPL d3 never landed
]
KEYS, SUMS = ["ticker", "trade_date"], ["close", "volume"]
for f in compare(src, tgt, KEYS, SUMS, "trade_date"):
    print(f"{f.status:4}  {f.check:15} {f.detail}")
print("reload dates:", reload_dates(src, tgt, KEYS, SUMS, "trade_date"))
