import sqlite3

SCHEMA = """
CREATE TABLE prices (
  ticker TEXT NOT NULL,
  trade_date TEXT NOT NULL,   -- YYYY-MM-DD
  close REAL NOT NULL,
  volume INTEGER NOT NULL,
  PRIMARY KEY (ticker, trade_date)
);
"""

ROWS = [
    ("AAPL", "2026-10-20", 231.5, 51_000_000), ("AAPL", "2026-10-21", 233.1, 48_000_000),
    ("AAPL", "2026-10-22", 229.8, 55_000_000), ("MSFT", "2026-10-20", 418.2, 21_000_000),
    ("MSFT", "2026-10-21", 421.9, 19_500_000), ("MSFT", "2026-10-22", 425.0, 23_000_000),
    ("NVDA", "2026-10-20", 138.4, 210_000_000), ("NVDA", "2026-10-21", 141.0, 198_000_000),
    ("NVDA", "2026-10-22", 136.7, 240_000_000),
]


def make_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO prices VALUES (?,?,?,?)", ROWS)
    return con


def schema_text() -> str:
    return SCHEMA.strip()
