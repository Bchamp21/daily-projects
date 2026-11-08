-- MERGE late arrivals and corrections into Silver.
-- Watermark = max trade_date already stored. Events older than watermark - 3 days
-- go to quarantine instead of silently rewriting history.
-- Ingest market.price_events to main.market_bronze.price_events the Day 4 way first.
WITH watermark AS (
  SELECT coalesce(max(trade_date), DATE '1900-01-01') AS wm
  FROM main.market_silver.fact_prices
),
src AS (
  SELECT upper(trim(ticker)) AS ticker,
         trade_date,
         cast(close AS DECIMAL(18,4)) AS close,
         published_at
  FROM main.market_bronze.price_events
),
classified AS (
  SELECT s.*,
         CASE WHEN s.trade_date < date_add(w.wm, -3) THEN true ELSE false END AS too_late
  FROM src s
  CROSS JOIN watermark w
),
good AS (
  SELECT * FROM classified WHERE NOT too_late
)
MERGE INTO main.market_silver.fact_prices t
USING good s
ON t.ticker = s.ticker AND t.trade_date = s.trade_date
WHEN MATCHED AND s.published_at > t.published_at AND s.close <> t.close THEN
  UPDATE SET
    close = s.close,
    published_at = s.published_at,
    version = t.version + 1,
    is_correction = true,
    ingested_on = current_date()
WHEN NOT MATCHED THEN
  INSERT (ticker, trade_date, close, version, published_at, ingested_on, is_correction)
  VALUES (s.ticker, s.trade_date, s.close, 1, s.published_at, current_date(), false);

INSERT INTO main.market_silver.price_quarantine
SELECT ticker, trade_date, close, published_at, current_date() AS quarantined_on,
       'beyond_allowed_lateness' AS reason
FROM classified
WHERE too_late;
