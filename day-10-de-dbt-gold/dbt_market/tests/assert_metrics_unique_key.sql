-- Fails if any ticker+trade_date appears twice in Gold.
select ticker, trade_date, count(*) as n
from {{ ref('gold_price_metrics') }}
group by ticker, trade_date
having count(*) > 1
