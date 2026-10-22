-- Fails if a drawdown is above zero (a bug in the running-high window).
select * from {{ ref('gold_price_metrics') }}
where drawdown > 1e-9
