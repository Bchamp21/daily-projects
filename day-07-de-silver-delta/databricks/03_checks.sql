-- Run after the MERGE. Each query should return 0 rows / 0.
-- Duplicate keys?
SELECT ticker, trade_date, COUNT(*) c FROM main.market_silver.prices GROUP BY 1,2 HAVING c > 1;
-- Bad ranges?
SELECT * FROM main.market_silver.prices WHERE low > high OR close NOT BETWEEN low AND high;
-- Row count Silver vs distinct keys in Bronze (should match)
SELECT (SELECT COUNT(*) FROM main.market_silver.prices)
     - (SELECT COUNT(DISTINCT ticker, trade_date) FROM main.market_bronze.prices) AS diff;
