"""SQLite storage. Decimals are stored as TEXT so no precision is lost."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from .core import Trade

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day TEXT NOT NULL, ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
  qty TEXT NOT NULL, price TEXT NOT NULL, fee TEXT NOT NULL DEFAULT '0',
  UNIQUE (day, ticker, side, qty, price)  -- re-importing a file is a no-op
);
"""


@contextmanager
def connect(path: str):
    """Commit on success, roll back on any error, always close."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_trades(conn, trades) -> int:
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO trades(day,ticker,side,qty,price,fee) VALUES (?,?,?,?,?,?)",
        [(t.day.isoformat(), t.ticker, t.side, str(t.qty), str(t.price), str(t.fee)) for t in trades],
    )
    return conn.total_changes - before


def load_trades(conn) -> list[Trade]:
    rows = conn.execute("SELECT day,ticker,side,qty,price,fee FROM trades ORDER BY day,id")
    return [Trade(date.fromisoformat(d), tk, s, Decimal(q), Decimal(p), Decimal(f))
            for d, tk, s, q, p, f in rows]
