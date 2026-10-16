"""CLI: land sample Postgres extract → Bronze JSONL."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from bronze.ingest import land_batch, write_jsonl
from bronze.schema import SOURCE_SYSTEM_DEFAULT

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXTRACT = ROOT / "data" / "sample_extract.json"
DEFAULT_OUT = ROOT / "data" / "bronze" / "prices.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Land sample market.prices extract to Bronze JSONL")
    parser.add_argument("--extract", type=Path, default=DEFAULT_EXTRACT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--batch-id", default=None, help="defaults to a new UUID")
    parser.add_argument("--source-system", default=SOURCE_SYSTEM_DEFAULT)
    args = parser.parse_args(argv)

    raw = json.loads(args.extract.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("extract JSON must be a list of row objects")

    batch_id = args.batch_id or str(uuid.uuid4())
    landed, rejected = land_batch(raw, batch_id=batch_id, source_system=args.source_system)
    n = write_jsonl(landed, args.out)

    print(f"batch_id={batch_id}")
    print(f"input={len(raw)} landed={n} rejected={len(rejected)}")
    print(f"wrote={args.out}")
    for r in rejected:
        print(f"  reject: {r['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
