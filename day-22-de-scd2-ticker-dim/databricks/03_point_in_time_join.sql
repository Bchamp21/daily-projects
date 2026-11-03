-- Each price row gets the company info that was true ON that trade date.
SELECT p.ticker, p.trade_date, p.close, d.company_name, d.sector
FROM main.market_silver.prices p
JOIN main.market_gold.dim_ticker d
  ON d.ticker = p.ticker
 AND p.trade_date >= d.valid_from
 AND p.trade_date <  d.valid_to;
