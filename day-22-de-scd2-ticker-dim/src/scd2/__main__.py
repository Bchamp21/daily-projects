"""Demo: apply 3 daily snapshots, then do a point-in-time lookup."""
import json
from datetime import date
from pathlib import Path

from .core import check_dim, lookup_as_of, scd2_merge

DATA = Path(__file__).resolve().parents[2] / "data"


def main() -> None:
    dim: list[dict] = []
    for name in sorted(p.name for p in DATA.glob("snapshot_*.json")):
        as_of = date.fromisoformat(name[9:19])
        snap = json.loads((DATA / name).read_text())
        dim, s = scd2_merge(dim, snap, as_of)
        print(f"{as_of}: +{s.inserted} new, {s.changed} changed, "
              f"{s.unchanged} same, {s.delisted} closed")
    print()
    print(f"{'sk':>3} {'ticker':6} {'company_name':22} {'sector':12} {'from':10} {'to':10} cur")
    for r in dim:
        print(f"{r['ticker_sk']:>3} {r['ticker']:6} {r['company_name']:22} {r['sector']:12} "
              f"{r['valid_from']} {r['valid_to']} {'Y' if r['is_current'] else 'N'}")
    v = lookup_as_of(dim, "META", date(2026, 10, 2))
    print(f"\nMETA on 2026-10-02 was: {v['company_name']} ({v['sector']})")
    errs = check_dim(dim)
    print("dim checks:", "PASS" if not errs else errs)


if __name__ == "__main__":
    main()
