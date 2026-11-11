-- Turn on Change Data Feed for the Silver prices table (from Day 7 / Day 25).
ALTER TABLE main.market_silver.fact_prices
  SET TBLPROPERTIES (delta.enableChangeDataFeed = true);

-- Gold summary + a 1-row checkpoint table that remembers the last version used.
CREATE TABLE IF NOT EXISTS main.market_gold.ticker_summary (
  ticker STRING, row_count BIGINT, sum_close DOUBLE, avg_close DOUBLE);

CREATE TABLE IF NOT EXISTS main.market_gold._cdf_checkpoint (
  source STRING, last_version BIGINT);
INSERT INTO main.market_gold._cdf_checkpoint
SELECT 'fact_prices', (SELECT max(version) FROM (DESCRIBE HISTORY main.market_silver.fact_prices))
WHERE NOT EXISTS (SELECT 1 FROM main.market_gold._cdf_checkpoint);

-- First load the slow way (full scan) so Gold starts correct.
INSERT OVERWRITE main.market_gold.ticker_summary
SELECT ticker, count(*), sum(close), round(avg(close), 4)
FROM main.market_silver.fact_prices GROUP BY ticker;
