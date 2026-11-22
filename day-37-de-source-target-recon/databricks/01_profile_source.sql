-- Profile the on-prem source through Lakehouse Federation (foreign catalog over Postgres).
-- Change pg_market / main.market to your names.
CREATE OR REPLACE TEMP VIEW src AS
SELECT upper(trim(ticker)) AS ticker, trade_date, CAST(close AS DECIMAL(18,4)) AS close, volume
FROM pg_market.market.prices;

SELECT 'source' AS side, count(*) AS row_count, sum(close) AS sum_close,
       sum(volume) AS sum_volume, max(trade_date) AS max_date
FROM src;
