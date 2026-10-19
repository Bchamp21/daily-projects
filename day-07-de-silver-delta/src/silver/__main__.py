"""CLI: read Bronze JSONL, build Silver, MERGE into data/silver/prices.jsonl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from silver.transform import build_silver, merge_upsert

HERE = Path(__file__).resolve().parents[2]


def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    bronze = Path(argv[0]) if argv else HERE / "data" / "bronze_sample.jsonl"
    target = Path(argv[1]) if len(argv) > 1 else HERE / "data" / "silver" / "prices.jsonl"
    silver_rows = build_silver(_read_jsonl(bronze))
    merged, stats = merge_upsert(_read_jsonl(target), silver_rows)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(json.dumps(r) + "\n" for r in merged))
    print(f"bronze={bronze.name} silver_rows={len(merged)} {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
