-- Let Databricks run OPTIMIZE + VACUUM for you (Unity Catalog managed tables).
ALTER SCHEMA main.market_silver ENABLE PREDICTIVE OPTIMIZATION;
-- Check what it did:
SELECT * FROM system.storage.predictive_optimization_operations_history
WHERE table_name = 'fact_prices' ORDER BY start_time DESC LIMIT 20;
