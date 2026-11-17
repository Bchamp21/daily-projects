-- Keep the bad rows instead of losing them: the inverse of the DROP rules.
CREATE OR REFRESH MATERIALIZED VIEW quarantine_prices AS
SELECT *,
  filter(array(
    CASE WHEN ticker IS NULL OR ticker = '' THEN 'ticker_present' END,
    CASE WHEN NOT coalesce(close > 0, false) THEN 'positive_close' END,
    CASE WHEN NOT coalesce(high >= low, false) THEN 'high_ge_low' END
  ), x -> x IS NOT NULL) AS dq_reasons
FROM bronze_prices
WHERE ticker IS NULL OR ticker = '' OR NOT coalesce(close > 0, false) OR NOT coalesce(high >= low, false);
