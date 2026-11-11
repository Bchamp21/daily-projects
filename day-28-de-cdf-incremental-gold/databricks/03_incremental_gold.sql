-- Fold only the new changes into Gold. Run this as many times as you like.
CREATE OR REPLACE TEMP VIEW deltas AS
SELECT ticker,
       sum(CASE WHEN _change_type IN ('insert','update_postimage') THEN 1 ELSE -1 END) AS d_count,
       sum(CASE WHEN _change_type IN ('insert','update_postimage') THEN close ELSE -close END) AS d_sum,
       max(_commit_version) AS max_version
FROM table_changes('main.market_silver.fact_prices',
  (SELECT last_version + 1 FROM main.market_gold._cdf_checkpoint))
GROUP BY ticker;

MERGE INTO main.market_gold.ticker_summary g
USING deltas d ON g.ticker = d.ticker
WHEN MATCHED AND g.row_count + d.d_count = 0 THEN DELETE
WHEN MATCHED THEN UPDATE SET
  row_count = g.row_count + d.d_count,
  sum_close = g.sum_close + d.d_sum,
  avg_close = round((g.sum_close + d.d_sum) / (g.row_count + d.d_count), 4)
WHEN NOT MATCHED AND d.d_count > 0 THEN INSERT
  VALUES (d.ticker, d.d_count, d.d_sum, round(d.d_sum / d.d_count, 4));

UPDATE main.market_gold._cdf_checkpoint
SET last_version = (SELECT max(version) FROM (DESCRIBE HISTORY main.market_silver.fact_prices))
WHERE source = 'fact_prices';
