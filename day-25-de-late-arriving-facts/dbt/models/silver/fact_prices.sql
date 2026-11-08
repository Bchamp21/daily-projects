-- Incremental lookback = allowed lateness. Same idea as apply_events():
-- reread the last N days so a late correction still lands in this run.
-- Version bump / quarantine live in databricks/02_merge_corrections.sql;
-- this model shows the dbt incremental pattern.
{{ config(
    materialized='incremental',
    unique_key=['ticker', 'trade_date'],
    incremental_strategy='merge'
) }}

select
  upper(trim(ticker)) as ticker,
  trade_date,
  cast(close as numeric(18, 4)) as close,
  published_at,
  current_date() as ingested_on
from {{ source('market_bronze', 'price_events') }}
{% if is_incremental() %}
where trade_date >= dateadd(
  day,
  -{{ var('allowed_lateness_days', 3) }},
  (select coalesce(max(trade_date), date '1900-01-01') from {{ this }})
)
{% endif %}
