"""Stock pipeline end to end on SQLite: source -> bronze -> silver -> gold -> quality gate.
Same shape as the Databricks job (Lakeflow ingest, PySpark Silver, dbt Gold)."""
from __future__ import annotations
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dag import Task


def load_source(ctx):
    """Day 1 stand-in: the on-prem Postgres market.prices table."""
    con: sqlite3.Connection = ctx["con"]
    con.execute("CREATE TABLE IF NOT EXISTS source_prices(ticker, trade_date, open, high, low, close, volume)")
    con.execute("DELETE FROM source_prices")
    with open(ctx["source_csv"], newline="") as f:
        rows = [tuple(r.values()) for r in csv.DictReader(f)]
    con.executemany("INSERT INTO source_prices VALUES (?,?,?,?,?,?,?)", rows)


def ingest_bronze(ctx):
    """Append raw rows + ingest metadata (like Lakeflow Connect). Never cleans."""
    con = ctx["con"]
    con.execute("""CREATE TABLE IF NOT EXISTS bronze_prices(
        ticker, trade_date, open, high, low, close, volume, _batch_id, _ingested_at)""")
    con.execute(
        "INSERT INTO bronze_prices SELECT *, ?, ? FROM source_prices",
        (ctx["batch_id"], datetime.now(timezone.utc).isoformat()),
    )


def build_silver(ctx):
    """Typed, valid, one row per (ticker, date), with daily return via LAG."""
    con = ctx["con"]
    con.executescript("""
    DROP TABLE IF EXISTS silver_prices;
    CREATE TABLE silver_prices AS
    WITH typed AS (
      SELECT ticker, trade_date, CAST(open AS REAL) open, CAST(high AS REAL) high,
             CAST(low AS REAL) low, CAST(close AS REAL) close, CAST(volume AS INTEGER) volume,
             ROW_NUMBER() OVER (PARTITION BY ticker, trade_date ORDER BY _ingested_at DESC) rn
      FROM bronze_prices
    ), valid AS (
      SELECT * FROM typed WHERE rn = 1 AND close > 0 AND low <= high
    )
    SELECT ticker, trade_date, open, high, low, close, volume,
           LAG(close) OVER (PARTITION BY ticker ORDER BY trade_date) prev_close,
           ROUND(close / LAG(close) OVER (PARTITION BY ticker ORDER BY trade_date) - 1, 6) daily_return
    FROM valid;
    """)
    bad = con.execute("""SELECT COUNT(*) FROM (SELECT ticker, trade_date FROM bronze_prices
        WHERE _batch_id = ? GROUP BY 1,2 HAVING MIN(CAST(close AS REAL)) <= 0)""",
        (ctx["batch_id"],)).fetchone()[0]
    ctx["quarantined"] = bad


def build_gold(ctx):
    """dbt-style Gold mart: one summary row per ticker."""
    con = ctx["con"]
    con.executescript("""
    DROP TABLE IF EXISTS gold_ticker_summary;
    CREATE TABLE gold_ticker_summary AS
    SELECT ticker, COUNT(*) trading_days, MIN(trade_date) first_day, MAX(trade_date) last_day,
           ROUND(MAX(high), 2) period_high, ROUND(MIN(low), 2) period_low,
           ROUND(AVG(daily_return), 6) avg_daily_return,
           ROUND((SELECT s2.close FROM silver_prices s2 WHERE s2.ticker = s.ticker
                  ORDER BY trade_date DESC LIMIT 1), 2) last_close
    FROM silver_prices s GROUP BY ticker;
    """)


def quality_gate(ctx):
    """Fail the run (and alert) if Silver/Gold break basic contracts."""
    con = ctx["con"]
    checks = {
        "silver_not_empty": "SELECT COUNT(*) = 0 FROM silver_prices",
        "silver_unique_key": """SELECT COUNT(*) > 0 FROM (SELECT ticker, trade_date FROM silver_prices
                                GROUP BY 1,2 HAVING COUNT(*) > 1)""",
        "silver_positive_close": "SELECT COUNT(*) > 0 FROM silver_prices WHERE close <= 0",
        "gold_matches_silver": """SELECT (SELECT COUNT(DISTINCT ticker) FROM silver_prices)
                                  != (SELECT COUNT(*) FROM gold_ticker_summary)""",
    }
    failed = [name for name, sql in checks.items() if con.execute(sql).fetchone()[0]]
    ctx["checks_failed"] = failed
    if failed:
        raise AssertionError(f"quality checks failed: {failed}")


def build_tasks() -> list[Task]:
    return [
        Task("load_source", load_source, [], "notebooks/00_load_source"),
        Task("ingest_bronze", ingest_bronze, ["load_source"], "notebooks/01_ingest_bronze", 2),
        Task("build_silver", build_silver, ["ingest_bronze"], "notebooks/02_build_silver", 1),
        Task("build_gold", build_gold, ["build_silver"], "notebooks/03_dbt_gold", 1),
        Task("quality_gate", quality_gate, ["build_gold"], "notebooks/04_quality_gate"),
    ]


def new_context(source_csv: str | Path, db: str = ":memory:", batch_id: str = "b1") -> dict:
    return {"con": sqlite3.connect(db), "source_csv": str(source_csv), "batch_id": batch_id}
