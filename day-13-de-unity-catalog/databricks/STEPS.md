# Run on Databricks (Unity Catalog workspace)

1. **Groups**: Settings → Identity and access → Groups. Create `data_engineers`, `analysts`, `analysts_us`, `bi_readers`, `data_platform_admins`. Add yourself to `data_engineers`.
2. **Generate SQL** locally: `python uc_plan.py -o databricks/uc_setup.sql`.
3. **Run it**: open SQL Editor on a SQL warehouse (or a UC-enabled cluster) and run `uc_setup.sql`. The Silver/Gold tables from Days 7 and 10 must exist first for the `ALTER TABLE` lines; re-running is safe.
4. **Check grants**: `SHOW GRANTS ON SCHEMA market.gold;`
5. **Check the row filter**: remove yourself from `data_engineers`, add yourself to `analysts_us`, then `SELECT DISTINCT ticker FROM market.silver.prices;` should show only AAPL and MSFT, with `volume` NULL.
6. **Lineage**: Catalog Explorer → `market.gold.gold_ticker_summary` → Lineage tab shows Bronze → Silver → Gold.
7. **Tags**: `SELECT * FROM system.information_schema.table_tags WHERE catalog_name = 'market';`

Free option: Databricks Free Edition supports Unity Catalog; use the workspace `main` catalog if you can't create a new one (set `catalog: main` in the YAML).
