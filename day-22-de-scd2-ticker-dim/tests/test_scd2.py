import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scd2.core import OPEN_END, check_dim, lookup_as_of, row_hash, scd2_merge  # noqa: E402

D1, D2, D3 = date(2026, 10, 1), date(2026, 10, 5), date(2026, 10, 9)
A = {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "exchange": "NASDAQ"}
M = {"ticker": "META", "company_name": "Facebook Inc.", "sector": "Technology", "exchange": "NASDAQ"}
M2 = {**M, "company_name": "Meta Platforms Inc.", "sector": "Comm Services"}


def test_initial_load_inserts_open_rows():
    dim, s = scd2_merge([], [A, M], D1)
    assert s.inserted == 2 and len(dim) == 2
    assert all(r["is_current"] and r["valid_to"] == OPEN_END for r in dim)


def test_change_closes_old_and_opens_new():
    dim, _ = scd2_merge([], [A, M], D1)
    dim, s = scd2_merge(dim, [A, M2], D2)
    assert s.changed == 1 and s.unchanged == 1
    meta = [r for r in dim if r["ticker"] == "META"]
    old, new = sorted(meta, key=lambda r: r["valid_from"])
    assert old["valid_to"] == D2 and not old["is_current"]
    assert new["valid_from"] == D2 and new["is_current"]
    assert new["ticker_sk"] != old["ticker_sk"]


def test_merge_is_idempotent():
    dim, _ = scd2_merge([], [A, M], D1)
    dim2, s = scd2_merge(dim, [A, M], D2)
    assert dim2 == dim and s.unchanged == 2


def test_hash_ignores_case_and_whitespace_and_untracked():
    assert row_hash(A) == row_hash({**A, "sector": " technology ", "note": "x"})


def test_missing_ticker_is_closed():
    dim, _ = scd2_merge([], [A, M], D1)
    dim, s = scd2_merge(dim, [A], D2)
    assert s.delisted == 1
    assert not any(r["is_current"] for r in dim if r["ticker"] == "META")


def test_point_in_time_lookup():
    dim, _ = scd2_merge([], [A, M], D1)
    dim, _ = scd2_merge(dim, [A, M2], D2)
    assert lookup_as_of(dim, "META", date(2026, 10, 3))["company_name"] == "Facebook Inc."
    assert lookup_as_of(dim, "META", D2)["company_name"] == "Meta Platforms Inc."
    assert lookup_as_of(dim, "META", date(2026, 9, 1)) is None


def test_duplicate_in_snapshot_rejected():
    with pytest.raises(ValueError):
        scd2_merge([], [A, A], D1)


def test_backdated_change_rejected():
    dim, _ = scd2_merge([], [M], D2)
    with pytest.raises(ValueError):
        scd2_merge(dim, [M2], D1)


def test_check_dim_passes_after_three_snapshots():
    dim, _ = scd2_merge([], [A, M], D1)
    dim, _ = scd2_merge(dim, [A, M2], D2)
    dim, _ = scd2_merge(dim, [M2], D3)
    assert check_dim(dim) == []


def test_check_dim_catches_two_current_rows():
    dim, _ = scd2_merge([], [A], D1)
    bad = dim + [{**dim[0], "ticker_sk": 99, "valid_from": D2}]
    assert any("more than one current" in e for e in check_dim(bad))
