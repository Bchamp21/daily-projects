import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from drift.core import diff, exit_code, infer_schema, load_contract


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Check a CSV against a data contract.")
    p.add_argument("csv", type=Path)
    p.add_argument("contract", type=Path)
    p.add_argument("--json", action="store_true", help="machine-readable output")
    a = p.parse_args(argv)

    changes = diff(load_contract(a.contract), infer_schema(a.csv))
    code = exit_code(changes)
    if a.json:
        print(json.dumps({"exit_code": code, "changes": [asdict(c) | {"severity": c.severity.value} for c in changes]}, indent=2))
    elif not changes:
        print("OK: schema matches contract")
    else:
        for c in changes:
            print(f"[{c.severity.value.upper():5}] {c.column}: {c.kind} ({c.detail})")
    return code


if __name__ == "__main__":
    sys.exit(main())
