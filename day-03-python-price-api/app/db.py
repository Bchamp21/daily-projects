"""Tiny SQLite store (stdlib only). Same shape as market.prices from Day 1."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    volume INTEGER,
    PRIMARY KEY (ticker, trade_date)
);
"""


def connect(path: str = "prices.db") -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def upsert(conn: sqlite3.Connection, row: dict) -> None:
    conn.execute(
        """INSERT INTO prices VALUES (:ticker, :trade_date, :open, :high, :low, :close, :volume)
           ON CONFLICT(ticker, trade_date) DO UPDATE SET
             open=excluded.open, high=excluded.high, low=excluded.low,
             close=excluded.close, volume=excluded.volume""",
        row,
    )
    conn.commit()


def get_prices(conn: sqlite3.Connection, ticker: str) -> list[dict]:
    cur = conn.execute(
        "SELECT * FROM prices WHERE ticker = ? ORDER BY trade_date", (ticker.upper(),)
    )
    return [dict(r) for r in cur.fetchall()]
