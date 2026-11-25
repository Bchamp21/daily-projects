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
| 11 | AI | [`day-11-ai-news-extractor`](./day-11-ai-news-extractor) — LLM JSON extraction from headlines with Pydantic validation and retry-on-error |
| 12 | Python | [`day-12-python-price-alerts`](./day-12-python-price-alerts) — config-driven alert CLI: rule registry, dataclasses, logging, exit codes, parametrized pytest |
| 13 | Data Engineering | [`day-13-de-unity-catalog`](./day-13-de-unity-catalog) — Unity Catalog governance as code: grants, tags, column mask, row filter, access simulator |
| 14 | AI | [`day-14-ai-llm-gateway`](./day-14-ai-llm-gateway) — LLM gateway: semantic cache (threshold, TTL, eviction), provider fallback, cost tracking |
| 15 | Python | [`day-15-python-portfolio-ledger`](./day-15-python-portfolio-ledger) — FIFO portfolio ledger: Decimal money, SQLite context manager, idempotent import, P&L report CLI |
| 16 | Data Engineering | [`day-16-de-genie-space`](./day-16-de-genie-space) — Genie space as code: validated YAML, column comments, result-set benchmark scoring |
| 17 | AI | [`day-17-ai-text-to-sql`](./day-17-ai-text-to-sql) — guarded text-to-SQL agent: SELECT-only guard, table allowlist, auto LIMIT, self-correction from SQL errors |
| 18 | Python | [`day-18-python-incremental-loader`](./day-18-python-incremental-loader) — incremental CSV loader: generators, @retry/@timed decorators, batching, upsert, atomic watermark |
| 19 | Data Engineering | [`day-19-de-pipeline-capstone`](./day-19-de-pipeline-capstone) — capstone: one task list runs Source→Bronze→Silver→Gold→quality gate locally and generates the Databricks Asset Bundle job |
| 20 | AI | [`day-20-ai-hybrid-search`](./day-20-ai-hybrid-search) — hybrid retrieval: BM25 + vector search fused with RRF, MMR de-duplication, pluggable Ollama embeddings |
| 21 | Python | [`day-21-python-schema-drift`](./day-21-python-schema-drift) — schema drift detector: type inference, data-contract diff, warn vs break severity, pipeline exit codes |
| 22 | Data Engineering | [`day-22-de-scd2-ticker-dim`](./day-22-de-scd2-ticker-dim) — SCD Type 2 ticker dimension: hash change detection, close/open versions, one-statement Delta MERGE, point-in-time join, dbt snapshot |
| 23 | AI | [`day-23-ai-prompt-injection-guard`](./day-23-ai-prompt-injection-guard) — Prompt-injection guard for RAG: unicode-normalized detector, quarantine, spotlighting, tool allowlist, canary-leak check |
| 24 | Python | [`day-24-python-circuit-breaker`](./day-24-python-circuit-breaker) — resilient API calls: circuit breaker (closed/open/half-open), retry only transient errors, full-jitter backoff, injectable clock
| 25 | Data Engineering | [`day-25-de-late-arriving-facts`](./day-25-de-late-arriving-facts) — late price corrections: watermark + lateness window, Silver MERGE, quarantine, Gold recompute from the dirty date
| 26 | AI | [`day-26-ai-citation-checker`](./day-26-ai-citation-checker) — citation checker for RAG answers: per-sentence number check, overlap score, wrong-citation repair, gray-zone LLM judge, PASS/FIX/BLOCK gate |
| 27 | Python | [`day-27-python-rate-limit-cache`](./day-27-python-rate-limit-cache) — token-bucket rate limiter + TTL/LRU cache decorator: burst control, retry_after, cache hits skip the limiter, injectable clock |
| 28 | Data Engineering | [`day-28-de-cdf-incremental-gold`](./day-28-de-cdf-incremental-gold) — Delta Change Data Feed → incremental Gold: insert/pre/post/delete deltas, version checkpoint, idempotent rerun, MERGE, proof vs full recompute |
| 29 | AI | [`day-29-ai-semantic-cache`](./day-29-ai-semantic-cache) — semantic cache for LLM calls: exact + embedding lookup, ticker/date entity guard, TTL, LFU eviction, invalidate-by-ticker, hit-rate stats |
| 30 | Python | [`day-30-python-sqlite-job-queue`](./day-30-python-sqlite-job-queue) — durable SQLite job queue: lease + visibility timeout, crash recovery, lease tokens, exponential backoff, dead-letter, idempotent enqueue |
| 31 | Data Engineering | [`day-31-de-delta-maintenance`](./day-31-de-delta-maintenance) — Delta table maintenance: small-file health check, per-partition bin-packing OPTIMIZE, safe VACUUM guard (7-day + longest-reader), liquid clustering, predictive optimization |
| 32 | AI | [`day-32-ai-context-packer`](./day-32-ai-context-packer) — context-window packer: token budget with answer reserve, priority order, recent turns kept whole, RAG chunk dedupe + cap, old turns summarized into one memory line |
| 33 | Python | [`day-33-python-mini-dag-runner`](./day-33-python-mini-dag-runner) — mini DAG runner: Kahn waves run in parallel, cycle path detection, retries with backoff, skip-downstream on failure, results passed to children, resume from state.json |
| 34 | Data Engineering | [`day-34-de-expectations-quarantine`](./day-34-de-expectations-quarantine) — Lakeflow data quality expectations: warn/drop/fail per rule, quarantine table with reasons, NULL-safe checks, batch pass-rate gate, event-log metrics |
| 35 | AI | [`day-35-ai-pii-redactor`](./day-35-ai-pii-redactor) — PII redaction gateway for LLM calls: email/SSN/card(Luhn)/phone/account detectors, reversible placeholder vault, allow-list, leak guard before the call, restore after |
| 36 | Python | [`day-36-python-kpi-report`](./day-36-python-kpi-report) — monthly KPI report CLI: bad-row rejection with reasons, revenue by month, MoM % with safe divide, running total, top ticker, Markdown output, exit code on bad data |
| 37 | Data Engineering | [`day-37-de-source-target-recon`](./day-37-de-source-target-recon) — source-to-target reconciliation: normalized row hash, counts + sums with tolerance, missing/extra/duplicate keys, freshness lag, recon_log, reload only the bad dates |
| 38 | AI | [`day-38-ai-pairwise-judge`](./day-38-ai-pairwise-judge) — pairwise LLM-as-judge: swap-order position-bias check, inconsistent = tie, ties count half, Wilson 95% CI, SHIP_NEW/KEEP_OLD/NEED_MORE_DATA/JUDGE_UNRELIABLE gate |
| 39 | Python | [`day-39-python-webhook-receiver`](./day-39-python-webhook-receiver) — secure, idempotent webhook receiver: HMAC-SHA256 signature (constant-time), 5-min replay window, dedupe by event id in SQLite, handler in same transaction (500 = retry, rollback), key rotation |
| 40 | Data Engineering | [`day-40-de-asset-bundle`](./day-40-de-asset-bundle) — the stock pipeline as a Databricks Asset Bundle: dev/prod targets, 4-task job with retries/timeouts/alerts, pure-Python bundle linter (DAG order, cycles, prod run_as, undeclared vars, secrets), CI workflow |

Each day has code, tests, and a short README with a diagram.
