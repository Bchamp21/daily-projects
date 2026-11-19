import argparse
import sys

from kpi.report import load_rows, monthly_kpis, to_markdown


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Monthly KPI report from a trades CSV")
    p.add_argument("csv", nargs="?", default="data/trades.csv")
    p.add_argument("--out", help="write Markdown here instead of stdout")
    a = p.parse_args(argv)
    rows, bad = load_rows(a.csv)
    md = to_markdown(monthly_kpis(rows), bad)
    if a.out:
        open(a.out, "w").write(md + "\n")
    else:
        print(md)
    return 1 if bad else 0   # nonzero exit = data needs a look


if __name__ == "__main__":
    sys.exit(main())
