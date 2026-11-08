-- `main` is a placeholder catalog; use yours.
CREATE TABLE IF NOT EXISTS main.market_silver.fact_prices (
  ticker         STRING        NOT NULL,
  trade_date     DATE          NOT NULL,
  close          DECIMAL(18,4) NOT NULL,
  version        INT           NOT NULL,
  published_at   TIMESTAMP     NOT NULL,
  ingested_on    DATE          NOT NULL,
  is_correction  BOOLEAN       NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS main.market_silver.price_quarantine (
  ticker          STRING        NOT NULL,
  trade_date      DATE          NOT NULL,
  close           DECIMAL(18,4) NOT NULL,
  published_at    TIMESTAMP     NOT NULL,
  quarantined_on  DATE          NOT NULL,
  reason          STRING        NOT NULL
) USING DELTA;

CREATE TABLE IF NOT EXISTS main.market_gold.fact_price_metrics (
  ticker        STRING        NOT NULL,
  trade_date    DATE          NOT NULL,
  close         DECIMAL(18,4) NOT NULL,
  daily_return  DECIMAL(18,8),
  sma_3         DECIMAL(18,4),
  version       INT           NOT NULL
) USING DELTA;
