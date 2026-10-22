# daily-projects

Small end-to-end builds, one per day, rotating:

**Data Engineering → AI → Python → (repeat)**

| Day | Track | Folder |
|-----|-------|--------|
| 1 | Data Engineering | Delivered separately (local Postgres `market.prices` for the stock Databricks theme) — not in this repo yet |
| 2 | AI | [`day-02-ai-stock-news-rag`](./day-02-ai-stock-news-rag) — offline RAG over sample stock headlines |
| 3 | Python | [`day-03-python-price-api`](./day-03-python-price-api) — FastAPI + Pydantic validation + SQLite + pytest |
| 4 | Data Engineering | [`day-04-de-lakeflow-bronze`](./day-04-de-lakeflow-bronze) — Lakeflow/JDBC-style ingest → Bronze Delta for `market.prices` |
| 5 | AI | [`day-05-ai-stock-agent-tools`](./day-05-ai-stock-agent-tools) — tool-calling LLM agent (offline, Groq, or Ollama) |
| 6 | Python | [`day-06-python-csv-quality-cli`](./day-06-python-csv-quality-cli) — installable CLI that validates price CSVs (Pydantic, argparse, pytest) |
| 7 | Data Engineering | [`day-07-de-silver-delta`](./day-07-de-silver-delta) — PySpark/Delta Silver: dedupe, window returns, idempotent MERGE |
| 8 | AI | [`day-08-ai-rag-evals`](./day-08-ai-rag-evals) — RAG eval harness: hit@k, recall@k, MRR, groundedness, CI quality gate |
| 9 | Python | [`day-09-python-async-fetcher`](./day-09-python-async-fetcher) — asyncio fetcher: semaphore limit, timeouts, retries with backoff |
| 10 | Data Engineering | [`day-10-de-dbt-gold`](./day-10-de-dbt-gold) — dbt Gold: SMA, drawdown, ticker summary, data tests (DuckDB local, Databricks ready) |

Each day has code, tests, and a short README with a diagram.
