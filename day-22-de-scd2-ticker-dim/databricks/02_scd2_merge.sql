-- SCD2 in ONE Delta MERGE. Source = today's snapshot of market.tickers
-- landed in Bronze (main.market_bronze.tickers) by the Day 4 style ingest.
-- Trick: union the changed rows twice. Copy 1 (merge_key = ticker) closes the
-- old version; copy 2 (merge_key = NULL) never matches, so it inserts the new version.
WITH src AS (
  SELECT upper(trim(ticker)) AS ticker, company_name, sector, exchange,
         substr(sha2(concat_ws('|', lower(trim(company_name)), lower(trim(sector)), lower(trim(exchange))), 256), 1, 16) AS row_hash
  FROM main.market_bronze.tickers
),
changed AS (
  SELECT s.* FROM src s
  JOIN main.market_gold.dim_ticker d ON d.ticker = s.ticker AND d.is_current
  WHERE d.row_hash <> s.row_hash
),
staged AS (
  SELECT ticker AS merge_key, * FROM src
  UNION ALL
  SELECT NULL AS merge_key, * FROM changed
)
MERGE INTO main.market_gold.dim_ticker d
USING staged s
ON d.ticker = s.merge_key AND d.is_current
WHEN MATCHED AND d.row_hash <> s.row_hash THEN
  UPDATE SET valid_to = current_date(), is_current = false
WHEN NOT MATCHED THEN
  INSERT (ticker, company_name, sector, exchange, row_hash, valid_from, valid_to, is_current)
  VALUES (s.ticker, s.company_name, s.sector, s.exchange, s.row_hash, current_date(), DATE'9999-12-31', true)
WHEN NOT MATCHED BY SOURCE AND d.is_current THEN
  UPDATE SET valid_to = current_date(), is_current = false;
