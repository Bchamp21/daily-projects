-- Both must return 0 rows.
SELECT ticker FROM main.market_gold.dim_ticker WHERE is_current GROUP BY ticker HAVING count(*) > 1;
SELECT a.ticker FROM main.market_gold.dim_ticker a JOIN main.market_gold.dim_ticker b
  ON a.ticker = b.ticker AND a.ticker_sk <> b.ticker_sk
 AND a.valid_from < b.valid_to AND b.valid_from < a.valid_to;
