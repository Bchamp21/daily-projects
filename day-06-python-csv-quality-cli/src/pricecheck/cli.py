import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .validator import validate_file, write_clean


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pricecheck", description="Validate a stock-price CSV.")
    p.add_argument("csv_file", type=Path, help="input CSV (symbol,trade_date,open,high,low,close,volume)")
    p.add_argument("--out", type=Path, help="write only the good rows to this CSV")
    p.add_argument("--report", type=Path, help="write a JSON quality report here")
    p.add_argument("--min-pass", type=float, default=0.0,
                   help="exit with code 1 if pass rate %% is below this (use in pipelines)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.csv_file.exists():
        print(f"error: file not found: {args.csv_file}", file=sys.stderr)
        return 2

    report = validate_file(args.csv_file)
    s = report.summary()
    print(f"rows={s['total_rows']} good={s['good_rows']} bad={s['bad_rows']} "
          f"dupes={s['duplicates_dropped']} pass={s['pass_rate_pct']}%")
    for err in report.bad:
        print(f"  line {err['line']}: {'; '.join(err['errors'])}")

    if args.out:
        write_clean(report, args.out)
    if args.report:
        args.report.write_text(json.dumps(s, indent=2))

    return 1 if report.pass_rate < args.min_pass else 0


if __name__ == "__main__":
    raise SystemExit(main())
