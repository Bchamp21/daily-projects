-- Bronze DDL for market.prices ingest
-- Replace `main` with your Unity Catalog name before running.

-- CREATE CATALOG IF NOT EXISTS main;  -- optional; often already exists
CREATE SCHEMA IF NOT EXISTS main.market_bronze
COMMENT 'Bronze landing zone for market data (raw-ish + ingest metadata)';

CREATE TABLE IF NOT EXISTS main.market_bronze.prices (
  ticker            STRING   COMMENT 'Exchange ticker, uppercased',
  trade_date        DATE     COMMENT 'Trade session date (UTC calendar day)',
  open              DOUBLE   COMMENT 'Open price',
  high              DOUBLE   COMMENT 'High price',
  low               DOUBLE   COMMENT 'Low price',
  close             DOUBLE   COMMENT 'Close price',
  volume            BIGINT   COMMENT 'Share volume',
  _ingested_at      TIMESTAMP COMMENT 'UTC time this row landed in Bronze',
  _source_system    STRING   COMMENT 'e.g. postgres.market.prices',
  _batch_id         STRING   COMMENT 'Pipeline / Lakeflow run id',
  _source_row_hash  STRING   COMMENT 'SHA-256 of business columns'
)
USING DELTA
PARTITIONED BY (trade_date)
COMMENT 'Bronze OHLCV from Postgres market.prices via Lakeflow / JDBC';
