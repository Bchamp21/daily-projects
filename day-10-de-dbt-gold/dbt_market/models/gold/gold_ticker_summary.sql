-- One row per ticker: the "scoreboard" a business user asks for.
with m as (select * from {{ ref('gold_price_metrics') }}),
ranked as (
    select *,
        row_number() over (partition by ticker order by trade_date)      as rn_first,
        row_number() over (partition by ticker order by trade_date desc) as rn_last
    from m
)
select
    ticker,
    count(*)                                         as trading_days,
    min(trade_date)                                  as first_date,
    max(trade_date)                                  as last_date,
    max(case when rn_first = 1 then close end)       as first_close,
    max(case when rn_last  = 1 then close end)       as last_close,
    max(case when rn_last  = 1 then close end)
      / max(case when rn_first = 1 then close end) - 1 as period_return,
    avg(daily_return)                                as avg_daily_return,
    stddev_samp(daily_return)                        as volatility,
    min(drawdown)                                    as max_drawdown,
    avg(volume)                                      as avg_volume
from ranked
group by ticker
