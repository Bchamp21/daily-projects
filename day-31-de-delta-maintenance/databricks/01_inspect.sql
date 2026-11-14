-- How healthy is Silver? Look at file count and average file size.
DESCRIBE DETAIL main.market_silver.fact_prices;   -- numFiles, sizeInBytes
SELECT sizeInBytes / numFiles / 1024 / 1024 AS avg_file_mb
FROM (DESCRIBE DETAIL main.market_silver.fact_prices);
DESCRIBE HISTORY main.market_silver.fact_prices LIMIT 20;  -- many small WRITE/MERGE commits?
