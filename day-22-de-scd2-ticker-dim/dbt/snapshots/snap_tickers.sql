{# dbt does SCD2 for you: add to the Day 10 dbt project, then run `dbt snapshot`. #}
{% snapshot snap_tickers %}
{{ config(
    target_schema='market_snapshots',
    unique_key='ticker',
    strategy='check',
    check_cols=['company_name', 'sector', 'exchange'],
    invalidate_hard_deletes=True
) }}
select ticker, company_name, sector, exchange
from {{ source('market_bronze', 'tickers') }}
{% endsnapshot %}
