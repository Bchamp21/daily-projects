-- Must return 0 rows: incremental Gold equals a full recompute.
SELECT * FROM (
  SELECT ticker, row_count, round(sum_close, 4) s FROM main.market_gold.ticker_summary
  EXCEPT
  SELECT ticker, count(*), round(sum(close), 4) FROM main.market_silver.fact_prices GROUP BY ticker);
