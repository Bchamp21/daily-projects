# Day 18 (Python): Incremental CSV loader

Loads only **new** price rows into SQLite, using a saved watermark. Shows generators, decorators (`@retry`, `@timed`), batching, upserts, and atomic checkpoints.

```mermaid
flowchart LR
  A[prices.csv] -->|generator: read_rows| B{ts > watermark?}
  B -->|no| X[skip]
  B -->|yes| C[batched 500]
  C --> D["write_batch @retry<br/>UPSERT in 1 transaction"]
  D --> E[(prices.db)]
  D --> F[save watermark.json<br/>atomic replace]
  F -.next run reads.-> B
```

## Run

```bash
cd day-18-python-incremental-loader
pip install -r requirements.txt
PYTHONPATH=src python3 -m incload.loader sample/prices.csv   # loads 4 rows
PYTHONPATH=src python3 -m incload.loader sample/prices.csv   # loads 0 (already done)
pytest -q
```

## Key ideas
- `read_rows` is a generator, so a 10 GB file uses little memory.
- `batched` uses `islice` to chunk lazily.
- `@retry` retries only `sqlite3.OperationalError` (e.g., "database is locked") with backoff.
- Watermark is saved after each committed batch, so a crash resumes where it stopped.
- `ON CONFLICT ... DO UPDATE` makes reruns safe (idempotent).
