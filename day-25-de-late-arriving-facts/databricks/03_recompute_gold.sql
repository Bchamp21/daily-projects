-- Correcting day D dirties every later Gold row for that ticker (return and SMA
-- both read D's close). Compute over full Silver history so lookback works,
-- then replace Gold only from gold_from forward.
-- Run after 02_merge_corrections.sql.
CREATE OR REPLACE TEMP VIEW dirty AS
SELECT ticker, min(trade_date) AS gold_from
FROM main.market_silver.fact_prices
WHERE ingested_on = current_date()
GROUP BY ticker;

CREATE OR REPLACE TEMP VIEW recomputed AS
SELECT
  f.ticker,
  f.trade_date,
  f.close,
  (f.close / lag(f.close) OVER (PARTITION BY f.ticker ORDER BY f.trade_date)) - 1
    AS daily_return,
  CASE
    WHEN count(f.close) OVER (
           PARTITION BY f.ticker ORDER BY f.trade_date
           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
         ) = 3
    THEN avg(f.close) OVER (
           PARTITION BY f.ticker ORDER BY f.trade_date
           ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
         )
  END AS sma_3,
  f.version
FROM main.market_silver.fact_prices f
WHERE f.ticker IN (SELECT ticker FROM dirty);

DELETE FROM main.market_gold.fact_price_metrics g
WHERE EXISTS (
  SELECT 1 FROM dirty d
  WHERE d.ticker = g.ticker AND g.trade_date >= d.gold_from
);

INSERT INTO main.market_gold.fact_price_metrics
SELECT r.*
FROM recomputed r
JOIN dirty d ON d.ticker = r.ticker
WHERE r.trade_date >= d.gold_from;
