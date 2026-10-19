-- Silver DDL for market.prices. Replace `main` with your Unity Catalog name.
CREATE SCHEMA IF NOT EXISTS main.market_silver
COMMENT 'Silver: cleaned, deduped, one row per ticker + trade_date';

CREATE TABLE IF NOT EXISTS main.market_silver.prices (
  ticker            STRING    NOT NULL COMMENT 'Exchange ticker',
  trade_date        DATE      NOT NULL COMMENT 'Trade session date',
  open              DOUBLE,
  high              DOUBLE,
  low               DOUBLE,
  close             DOUBLE,
  volume            BIGINT,
  prev_close        DOUBLE    COMMENT 'Close of previous trade_date for this ticker',
  daily_return      DOUBLE    COMMENT '(close - prev_close) / prev_close',
  price_range       DOUBLE    COMMENT 'high - low',
  _source_row_hash  STRING    COMMENT 'From Bronze; used to skip unchanged rows in MERGE',
  _ingested_at      TIMESTAMP COMMENT 'Bronze ingest time of the winning row',
  _silver_updated_at TIMESTAMP COMMENT 'When this Silver row was last written',
  CONSTRAINT pk_prices PRIMARY KEY (ticker, trade_date) RELY
)
USING DELTA
CLUSTER BY (ticker, trade_date)
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

ALTER TABLE main.market_silver.prices ADD CONSTRAINT valid_hl CHECK (low <= high);
