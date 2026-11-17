from .core import run, silver_price_rules, render_sql

rows = [
    {"ticker": "AAPL", "trade_date": "2026-11-13", "close": 230.1, "high": 231, "low": 228, "volume": 5_000_000},
    {"ticker": "", "trade_date": "2026-11-13", "close": 10.0, "high": 11, "low": 9, "volume": 100},
    {"ticker": "MSFT", "trade_date": "2026-11-13", "close": -1.0, "high": 5, "low": 9, "volume": 100},
    {"ticker": "NVDA", "trade_date": "2026-11-13", "close": 140.0, "high": 141, "low": 139, "volume": -5},
]
res = run(rows, silver_price_rules())
print(f"clean={len(res.clean)} quarantine={len(res.quarantine)} pass_rate={res.pass_rate:.0%}")
for q in res.quarantine:
    print("  quarantined:", q["ticker"] or "<blank>", q["_dq_reasons"])
for name, m in res.metrics.items():
    print(f"  {name:22} {m['action']:5} passed={m['passed']} failed={m['failed']}")
print(render_sql("silver_prices", silver_price_rules()))
