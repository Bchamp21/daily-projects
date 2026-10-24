"""CLI: python -m pricealerts --prices prices.csv --rules rules.json"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .engine import evaluate, load_prices
from .rules import RuleConfigError, load_rules


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pricealerts")
    p.add_argument("--prices", required=True)
    p.add_argument("--rules", required=True)
    p.add_argument("--json", action="store_true", help="print alerts as JSON")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")
    try:
        rules = load_rules(a.rules)
    except RuleConfigError as e:
        print(f"config error: {e}", file=sys.stderr)
        return 2
    alerts = evaluate(rules, load_prices(a.prices))
    if a.json:
        print(json.dumps([vars(x) for x in alerts], indent=2))
    else:
        for x in alerts:
            print(f"ALERT [{x.rule}] {x.message}")
        if not alerts:
            print("no alerts")
    return 1 if alerts else 0  # exit 1 = alerts fired (handy for cron/n8n)


if __name__ == "__main__":
    raise SystemExit(main())
