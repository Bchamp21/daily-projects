# Run the Gold layer on Databricks

Needs Day 7's Silver table `market_silver.prices`.

1. On your laptop: `pip install dbt-databricks`
2. In Databricks: **SQL Warehouses** → pick one → **Connection details** → copy *Server hostname* and *HTTP path*.
3. Create a personal access token (User settings → Developer → Access tokens).
4. Export them:
   ```bash
   export DATABRICKS_HOST=...  DATABRICKS_HTTP_PATH=...  DATABRICKS_TOKEN=...
   ```
5. `cp databricks/profiles.example.yml ~/.dbt/profiles.yml` (edit `catalog` if not `main`).
6. From `dbt_market/`: `dbt build --profiles-dir ~/.dbt --target databricks --exclude resource_type:seed`
   - `stg_prices` now reads `source('market_silver','prices')`, not the seed.
7. Check in SQL editor:
   ```sql
   select * from main.market_gold.gold_ticker_summary order by period_return desc;
   ```
8. Optional: add a **dbt task** to the Day 4 job (Workflows → task type *dbt*) so Gold rebuilds after Silver.
