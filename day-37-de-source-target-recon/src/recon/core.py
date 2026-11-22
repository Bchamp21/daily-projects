"""Source-to-target reconciliation: prove Silver matches Postgres market.prices."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

Row = dict


def _norm(v) -> str:
    """Normalize a value so Postgres and Spark hash the same way."""
    if v is None:
        return "<NULL>"
    if isinstance(v, (float, Decimal)):
        return str(Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
    if isinstance(v, date):
        return v.isoformat()
    return str(v).strip().upper() if isinstance(v, str) else str(v)


def row_hash(row: Row, cols: list[str]) -> str:
    """md5 of normalized values joined with '|' (same as SQL md5(concat_ws('|', ...)))."""
    return hashlib.md5("|".join(_norm(row.get(c)) for c in cols).encode()).hexdigest()


def _key(row: Row, keys: list[str]) -> tuple:
    return tuple(_norm(row.get(k)) for k in keys)


@dataclass
class Profile:
    row_count: int
    sums: dict[str, Decimal]
    max_date: date | None
    per_date: dict[date, int] = field(default_factory=dict)


def profile(rows: list[Row], sum_cols: list[str], date_col: str) -> Profile:
    sums = {c: Decimal("0") for c in sum_cols}
    per_date: dict[date, int] = {}
    for r in rows:
        for c in sum_cols:
            if r.get(c) is not None:
                sums[c] += Decimal(str(r[c]))
        d = r.get(date_col)
        if d is not None:
            per_date[d] = per_date.get(d, 0) + 1
    return Profile(len(rows), sums, max(per_date) if per_date else None, per_date)


def key_diff(src: list[Row], tgt: list[Row], keys: list[str]):
    """Anti-joins both ways: (missing_in_target, extra_in_target, duplicate_keys_in_target)."""
    s = {_key(r, keys) for r in src}
    seen: set = set()
    dups: set = set()
    for r in tgt:
        k = _key(r, keys)
        (dups if k in seen else seen).add(k)
    return sorted(s - seen), sorted(seen - s), sorted(dups)


def value_diff(src: list[Row], tgt: list[Row], keys: list[str], cols: list[str]) -> list[tuple]:
    """Keys present on both sides whose row hash differs (a value changed in flight)."""
    sh = {_key(r, keys): row_hash(r, cols) for r in src}
    out = []
    for r in tgt:
        k = _key(r, keys)
        if k in sh and sh[k] != row_hash(r, cols):
            out.append(k)
    return sorted(set(out))


def date_counts_diff(sp: Profile, tp: Profile) -> dict[date, tuple[int, int]]:
    """Dates where source and target row counts differ: {date: (src, tgt)}."""
    days = set(sp.per_date) | set(tp.per_date)
    return {d: (sp.per_date.get(d, 0), tp.per_date.get(d, 0))
            for d in sorted(days) if sp.per_date.get(d, 0) != tp.per_date.get(d, 0)}


@dataclass
class Finding:
    check: str
    status: str  # PASS / FAIL
    detail: str


def compare(src: list[Row], tgt: list[Row], keys: list[str], sum_cols: list[str],
            date_col: str, tolerance: Decimal = Decimal("0.01"), max_lag_days: int = 1) -> list[Finding]:
    sp, tp = profile(src, sum_cols, date_col), profile(tgt, sum_cols, date_col)
    f: list[Finding] = []
    ok = sp.row_count == tp.row_count
    f.append(Finding("row_count", "PASS" if ok else "FAIL", f"source={sp.row_count} target={tp.row_count}"))
    for c in sum_cols:
        gap = abs(sp.sums[c] - tp.sums[c])
        f.append(Finding(f"sum_{c}", "PASS" if gap <= tolerance else "FAIL",
                         f"source={sp.sums[c]} target={tp.sums[c]} gap={gap}"))
    missing, extra, dups = key_diff(src, tgt, keys)
    f.append(Finding("missing_keys", "FAIL" if missing else "PASS", f"{len(missing)} {missing[:3]}"))
    f.append(Finding("extra_keys", "FAIL" if extra else "PASS", f"{len(extra)} {extra[:3]}"))
    f.append(Finding("duplicate_keys", "FAIL" if dups else "PASS", f"{len(dups)} {dups[:3]}"))
    changed = value_diff(src, tgt, keys, [c for c in sum_cols])
    f.append(Finding("changed_values", "FAIL" if changed else "PASS", f"{len(changed)} {changed[:3]}"))
    lag = (sp.max_date - tp.max_date).days if sp.max_date and tp.max_date else None
    fresh = lag is not None and lag <= max_lag_days
    f.append(Finding("freshness", "PASS" if fresh else "FAIL", f"source_max={sp.max_date} target_max={tp.max_date} lag_days={lag}"))
    return f


def reload_dates(src: list[Row], tgt: list[Row], keys: list[str], sum_cols: list[str], date_col: str) -> list[date]:
    """Smallest set of dates to reload: count gaps + dates of changed/missing keys."""
    sp, tp = profile(src, sum_cols, date_col), profile(tgt, sum_cols, date_col)
    bad = set(date_counts_diff(sp, tp))
    by_key = {_key(r, keys): r.get(date_col) for r in src + tgt}
    missing, extra, dups = key_diff(src, tgt, keys)
    for k in missing + extra + dups + value_diff(src, tgt, keys, sum_cols):
        if by_key.get(k) is not None:
            bad.add(by_key[k])
    return sorted(bad)
