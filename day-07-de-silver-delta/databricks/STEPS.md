# Databricks steps (Day 7 · Silver)

Prereq: Day 4 Bronze table `main.market_bronze.prices` exists and has rows.

1. Open your workspace and pick a catalog you can write to (swap `main` if needed).
2. **SQL Editor:** run `01_silver_ddl.sql` to create `market_silver.prices`.
3. **Workspace → Import:** bring in `02_silver_merge.py` as a notebook. Attach serverless or a small cluster.
4. Optional: set the catalog with `spark.conf.set("market.catalog", "<your_catalog>")` in the first cell.
5. Run all. You should see the history (a MERGE operation) and the Silver rows.
6. Run the notebook **again**. In `DESCRIBE HISTORY`, the 2nd MERGE should show `numTargetRowsUpdated = 0` (idempotent).
7. **SQL Editor:** run `03_checks.sql`. All checks should come back empty or 0.
8. Bonus: add it as a task after the Bronze pipeline in a **Databricks Workflow** (Jobs → Create → Notebook task, depends on Bronze).
