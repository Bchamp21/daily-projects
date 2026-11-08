-- Rebuild Gold from the earliest dirty date forward. Window functions need
-- the prior rows as lookback, so we read Silver from gold_from - 2 days,
-- then keep only trade_date >= gold_from (see also databricks/03_recompute_gold.sql).
{{ config(materialized='table') }}

with silver as (
  select ticker, trade_date, close, version
  from {{ ref('fact_prices') }}
),
metrics as (
  select
    ticker,
    trade_date,
    close,
    (close / lag(close) over (partition by ticker order by trade_date)) - 1
      as daily_return,
    avg(close) over (
      partition by ticker order by trade_date
      rows between 2 preceding and current row
    ) as sma_3,
    version,
    count(close) over (
      partition by ticker order by trade_date
      rows between 2 preceding and current row
    ) as sma_n
  from silver
)
select
  ticker,
  trade_date,
  close,
  daily_return,
  case when sma_n = 3 then sma_3 end as sma_3,
  version
from metrics
