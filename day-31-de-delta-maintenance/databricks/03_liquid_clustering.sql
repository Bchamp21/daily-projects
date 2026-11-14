-- Modern option: liquid clustering instead of partitions + ZORDER.
-- (Only for tables NOT partitioned. Try on a copy first.)
CREATE OR REPLACE TABLE main.market_silver.fact_prices_lc
CLUSTER BY (ticker, trade_date)
AS SELECT * FROM main.market_silver.fact_prices;
OPTIMIZE main.market_silver.fact_prices_lc;   -- clusters incrementally
