# Databricks steps (about 20 minutes)

1. Make sure Day 10 Gold tables exist: `market.gold.gold_price_metrics` and `market.gold.gold_ticker_summary` (run `dbt build` from Day 10).
2. Open a SQL editor on a serverless SQL warehouse and run `databricks/comments.sql`.
3. Sidebar → **Genie** → **New**. Pick the warehouse and add both Gold tables.
4. In **Instructions**, paste the `instructions` lines from `genie_space.yml`.
5. Add each `sample_queries` item as an example SQL query with its question.
6. Grant `bi_readers` (from Day 13) `CAN RUN` on the space; they also need SELECT on `market.gold`.
7. Ask each benchmark question. Copy Genie's SQL (Show code) into `answers.json` as `{question: sql}`.
8. Locally: `python genie_check.py bench --answers answers.json`. Below 80%? Improve comments, instructions, or samples and retry.

Menu names can differ by workspace version; if something isn't where it says, look for Genie under AI/BI in the sidebar.
