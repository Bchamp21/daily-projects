-- Must return 0 rows.
-- Grain: one Silver row per (ticker, trade_date)
SELECT ticker, trade_date, count(*) AS n
FROM main.market_silver.fact_prices
GROUP BY ticker, trade_date
HAVING count(*) > 1;

-- Corrections must bump version
SELECT ticker, trade_date, version
FROM main.market_silver.fact_prices
WHERE is_correction AND version < 2;

-- Quarantine should hold the Sep 20 AAPL row after the demo load
-- (this one SHOULD return 1 row — sanity check, not a must-be-empty test)
SELECT ticker, trade_date, reason
FROM main.market_silver.price_quarantine
WHERE ticker = 'AAPL' AND trade_date = DATE '2026-09-20';
