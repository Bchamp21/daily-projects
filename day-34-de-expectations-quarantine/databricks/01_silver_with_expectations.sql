-- Lakeflow Declarative Pipeline (SQL). Add this file to your pipeline source.
CREATE OR REFRESH MATERIALIZED VIEW silver_prices (
  CONSTRAINT ticker_present      EXPECT (ticker IS NOT NULL AND ticker <> '') ON VIOLATION DROP ROW,
  CONSTRAINT positive_close      EXPECT (close > 0)                           ON VIOLATION DROP ROW,
  CONSTRAINT high_ge_low         EXPECT (high >= low)                         ON VIOLATION DROP ROW,
  CONSTRAINT volume_not_negative EXPECT (volume >= 0),
  CONSTRAINT valid_date          EXPECT (trade_date IS NOT NULL)              ON VIOLATION FAIL UPDATE
) AS SELECT * FROM bronze_prices;
