-- One row per ticker per day, with rolling metrics for dashboards / Genie.
with p as (select * from {{ ref('stg_prices') }})
select
    ticker,
    trade_date,
    close,
    volume,
    daily_return,
    avg(close) over (
        partition by ticker order by trade_date
        rows between 2 preceding and current row
    )                                             as sma_3,
    count(*) over (
        partition by ticker order by trade_date
        rows between 2 preceding and current row
    ) = 3                                         as sma_3_complete,
    max(close) over (
        partition by ticker order by trade_date
        rows between unbounded preceding and current row
    )                                             as running_high,
    close / max(close) over (
        partition by ticker order by trade_date
        rows between unbounded preceding and current row
    ) - 1                                         as drawdown
from p
