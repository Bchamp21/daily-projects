# Databricks steps · Day 4 Bronze

```text
Postgres market.prices
        │
        ▼
  secret scope + JDBC   ──or──  Volume JSONL upload
        │
        ▼
  run 01_bronze_ddl.sql
        │
        ▼
  Lakeflow / DLT pipeline (02_lakeflow_pipeline.py)
        │
        ▼
  main.market_bronze.prices  →  SELECT LIMIT 10
```

1. **Catalog / schema** — pick a catalog (placeholder `main`). Run schema DDL from `01_bronze_ddl.sql`.
2. **Secrets** — create scope `market-pg` with keys named exactly: `POSTGRES_JDBC_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (values from your env; never commit them).
3. **DDL** — run `01_bronze_ddl.sql` in a SQL warehouse / notebook (replace catalog name).
4. **Pipeline** — create a Lakeflow / DLT pipeline; paste `02_lakeflow_pipeline.py`; point JDBC at `market.prices` **or** upload `data/bronze/prices.jsonl` to a Volume and use the volume path.
5. **Verify** — `SELECT * FROM main.market_bronze.prices LIMIT 10;`
6. **Checks** — confirm `_ingested_at` is populated; `SELECT count(*) … GROUP BY _batch_id;` matches expectation.
