-- `main` is a placeholder catalog; use yours.
CREATE TABLE IF NOT EXISTS main.market_gold.dim_ticker (
  ticker_sk     BIGINT GENERATED ALWAYS AS IDENTITY,
  ticker        STRING NOT NULL,
  company_name  STRING,
  sector        STRING,
  exchange      STRING,
  row_hash      STRING,
  valid_from    DATE NOT NULL,
  valid_to      DATE NOT NULL,
  is_current    BOOLEAN NOT NULL
) USING DELTA;
