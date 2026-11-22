-- Same normalization both sides, then anti-joins + row-hash compare.
CREATE OR REPLACE TEMP VIEW tgt AS
SELECT upper(trim(ticker)) AS ticker, trade_date, CAST(close AS DECIMAL(18,4)) AS close, volume
FROM main.market.silver_prices;

-- missing in target
SELECT s.ticker, s.trade_date FROM src s LEFT ANTI JOIN tgt t USING (ticker, trade_date);
-- extra in target
SELECT t.ticker, t.trade_date FROM tgt t LEFT ANTI JOIN src s USING (ticker, trade_date);
-- duplicate keys in target
SELECT ticker, trade_date, count(*) AS n FROM tgt GROUP BY ALL HAVING count(*) > 1;
-- changed values
SELECT s.ticker, s.trade_date
FROM src s JOIN tgt t USING (ticker, trade_date)
WHERE md5(concat_ws('|', s.close, s.volume)) <> md5(concat_ws('|', t.close, t.volume));
