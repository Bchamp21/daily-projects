"""Incremental loader: only rows newer than the saved watermark get loaded."""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .tools import batched, retry, timed


@dataclass(frozen=True)
class Row:
    ticker: str
    ts: str      # ISO timestamp, sorts as text
    close: float


def read_rows(path: Path) -> Iterator[Row]:
    """Stream rows one at a time (a generator), skipping bad lines."""
    with open(path, newline="") as f:
        for rec in csv.DictReader(f):
            try:
                yield Row(rec["ticker"].strip().upper(), rec["ts"].strip(), float(rec["close"]))
            except (KeyError, ValueError, AttributeError):
                continue


class Watermark:
    """A tiny JSON checkpoint: the max ts already loaded."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def get(self) -> str:
        if self.path.exists():
            return json.loads(self.path.read_text()).get("max_ts", "")
        return ""

    def set(self, value: str) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"max_ts": value}))
        tmp.replace(self.path)  # atomic swap: no half-written checkpoint


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS prices (ticker TEXT, ts TEXT, close REAL, PRIMARY KEY (ticker, ts))"
    )


@retry(times=3, delay=0.05, exceptions=(sqlite3.OperationalError,))
def write_batch(conn: sqlite3.Connection, batch: list[Row]) -> None:
    with conn:  # one transaction per batch
        conn.executemany(
            "INSERT INTO prices VALUES (?, ?, ?) "
            "ON CONFLICT(ticker, ts) DO UPDATE SET close = excluded.close",
            [(r.ticker, r.ts, r.close) for r in batch],
        )


@timed
def run(csv_path: Path, db_path: Path, wm_path: Path, batch_size: int = 500) -> dict:
    wm = Watermark(wm_path)
    since = wm.get()
    conn = sqlite3.connect(db_path)
    try:
        ensure_table(conn)
        new_rows = (r for r in read_rows(csv_path) if r.ts > since)
        loaded, max_ts = 0, since
        for batch in batched(new_rows, batch_size):
            write_batch(conn, batch)
            loaded += len(batch)
            max_ts = max(max_ts, max(r.ts for r in batch))
            wm.set(max_ts)  # checkpoint after each committed batch
    finally:
        conn.close()
    return {"since": since, "loaded": loaded, "watermark": max_ts}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Incrementally load a price CSV into SQLite")
    p.add_argument("csv", type=Path)
    p.add_argument("--db", type=Path, default=Path("prices.db"))
    p.add_argument("--watermark", type=Path, default=Path("watermark.json"))
    p.add_argument("--batch-size", type=int, default=500)
    a = p.parse_args(argv)
    if not a.csv.exists():
        print(f"error: {a.csv} not found", file=sys.stderr)
        return 2
    print(json.dumps(run(a.csv, a.db, a.watermark, a.batch_size)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
