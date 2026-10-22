"""Build the Gold layer locally with dbt + DuckDB and print the summary table.

Usage:  python run_gold.py
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
from dbt.cli.main import dbtRunner

PROJECT = Path(__file__).parent / "dbt_market"


def build(db_path: str | Path) -> bool:
    """Run `dbt build` (seed + models + tests). Returns True if everything passed."""
    os.environ["DBT_DUCKDB_PATH"] = str(db_path)
    args = ["build", "--project-dir", str(PROJECT), "--profiles-dir", str(PROJECT)]
    return dbtRunner().invoke(args).success


def summary(db_path: str | Path) -> list[tuple]:
    with duckdb.connect(str(db_path)) as con:
        return con.execute(
            "select ticker, trading_days, round(period_return, 4), "
            "round(volatility, 4), round(max_drawdown, 4) "
            "from gold_ticker_summary order by ticker"
        ).fetchall()


if __name__ == "__main__":
    db = PROJECT / "market.duckdb"
    if not build(db):
        raise SystemExit("dbt build failed")
    print("ticker | days | period_return | volatility | max_drawdown")
    for row in summary(db):
        print(" | ".join(str(v) for v in row))
