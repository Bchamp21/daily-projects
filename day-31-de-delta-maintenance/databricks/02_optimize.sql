-- Compact small files (bin-packing). Only recent dates to keep it cheap.
OPTIMIZE main.market_silver.fact_prices
WHERE trade_date >= current_date() - INTERVAL 7 DAYS;
-- operationMetrics shows numRemovedFiles / numAddedFiles
DESCRIBE HISTORY main.market_silver.fact_prices LIMIT 1;
