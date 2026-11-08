"""Demo: two on-time days, then a late AAPL correction plus a too-old row."""
import json
from datetime import date
from pathlib import Path

from .core import apply_events, check_facts, compute_gold, derive_watermark

DATA = Path(__file__).resolve().parents[2] / "data"


def _fmt(v) -> str:
    if v is None:
        return "   -   "
    if hasattr(v, "quantize"):
        return f"{v:.4f}"
    return str(v)


def main() -> None:
    facts: list[dict] = []
    for name in sorted(p.name for p in DATA.glob("batch_*.json")):
        run_date = date.fromisoformat(name[6:16])
        events = json.loads((DATA / name).read_text())
        facts, quarantine, s = apply_events(facts, events, run_date)
        print(f"{run_date}: +{s.inserted} new, {s.corrected} corrected, "
              f"{s.unchanged} same, {s.stale} stale, {s.quarantined} quarantined"
              f"  gold_from={s.gold_from}")
        for line in s.log:
            print(f"  {line}")
        for q in quarantine:
            print(f"  QUARANTINE {q['ticker']} {q['trade_date']} ({q['reason']})")

    print()
    print(f"{'ticker':6} {'date':10} {'close':>8} {'ver':>3} corr")
    for r in sorted(facts, key=lambda x: (x["ticker"], x["trade_date"])):
        print(f"{r['ticker']:6} {r['trade_date']} {r['close']:>8} {r['version']:>3} "
              f"{'Y' if r['is_correction'] else 'N'}")

    gold = compute_gold(facts, sma_window=3)
    print()
    print(f"{'ticker':6} {'date':10} {'close':>8} {'return':>8} {'sma3':>8}")
    for r in gold:
        print(f"{r['ticker']:6} {r['trade_date']} {r['close']:>8} {_fmt(r['daily_return']):>8} {_fmt(r['sma']):>8}")

    print()
    print("watermark:", derive_watermark(facts))
    print("fact checks:", "PASS" if not check_facts(facts) else check_facts(facts))


if __name__ == "__main__":
    main()
