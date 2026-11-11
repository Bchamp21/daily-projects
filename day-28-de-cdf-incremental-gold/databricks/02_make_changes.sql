-- Make a correction and a delete so CDF has something to show.
UPDATE main.market_silver.fact_prices SET close = close + 1
WHERE ticker = 'AAPL' AND trade_date = (SELECT max(trade_date) FROM main.market_silver.fact_prices WHERE ticker = 'AAPL');

DELETE FROM main.market_silver.fact_prices
WHERE ticker = 'MSFT' AND trade_date = (SELECT min(trade_date) FROM main.market_silver.fact_prices WHERE ticker = 'MSFT');

-- Look at the raw change feed
SELECT ticker, trade_date, close, _change_type, _commit_version
FROM table_changes('main.market_silver.fact_prices',
  (SELECT last_version + 1 FROM main.market_gold._cdf_checkpoint))
ORDER BY _commit_version;
