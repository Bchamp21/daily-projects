-- Local runs read the seed; Databricks runs read the real Silver Delta table.
select
    ticker,
    cast(trade_date as date)     as trade_date,
    cast(close as double)        as close,
    cast(volume as bigint)       as volume,
    cast(daily_return as double) as daily_return
{% if target.type == 'duckdb' %}
from {{ ref('silver_prices_sample') }}
{% else %}
from {{ source('market_silver', 'prices') }}
{% endif %}
