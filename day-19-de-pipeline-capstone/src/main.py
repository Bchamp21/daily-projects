"""Run the whole pipeline locally, or regenerate bundle/databricks.yml."""
import argparse
import sys
from pathlib import Path

import dag
from bundle import to_bundle_yaml
from pipeline import build_tasks, new_context

HERE = Path(__file__).resolve().parent.parent


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["run", "bundle"])
    p.add_argument("--source", default=str(HERE / "data/source_prices.csv"))
    p.add_argument("--db", default=":memory:")
    a = p.parse_args(argv)
    tasks = build_tasks()
    if a.command == "bundle":
        out = HERE / "bundle/databricks.yml"
        out.write_text(to_bundle_yaml(tasks))
        print(f"wrote {out}")
        return 0
    ctx = new_context(a.source, a.db)
    status = dag.run(tasks, ctx)
    for k, s in status.items():
        print(f"{s:8} {k}")
    print(f"quarantined rows: {ctx.get('quarantined', 0)}")
    for row in ctx["con"].execute("SELECT ticker, trading_days, last_close FROM gold_ticker_summary"):
        print("gold:", row)
    return 0 if all(s == "SUCCESS" for s in status.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
