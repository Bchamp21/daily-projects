import random
import pytest
from delta_maint.core import (DeltaTable, MB, DEFAULT_TARGET, health, plan_optimize,
                              apply_optimize, plan_vacuum, apply_vacuum, UnsafeRetention,
                              render_sql)

P1, P2 = "trade_date=2026-11-12", "trade_date=2026-11-13"


def small_table(n=10, size=10 * MB):
    t = DeltaTable("t")
    for i in range(n):
        t.add(P1, size, now=i)
    return t


def test_health_flags_small_files():
    h = health(small_table())
    assert h.file_count == 10 and h.small_ratio == 1.0 and h.recommend_optimize


def test_bins_respect_target_and_partition():
    t = small_table(20, 30 * MB)
    for i in range(5):
        t.add(P2, 30 * MB, now=i)
    bins = plan_optimize(t)
    assert all(b.size <= DEFAULT_TARGET for b in bins)
    assert all(len({f.partition for f in b.files}) == 1 for b in bins)


def test_big_files_and_single_bins_skipped():
    t = DeltaTable("t")
    t.add(P1, 200 * MB, now=0)
    t.add(P2, 5 * MB, now=0)  # alone in its partition -> nothing to merge
    assert plan_optimize(t) == []


def test_optimize_keeps_bytes_and_is_one_commit():
    t = small_table(12)
    before_bytes, v = t.rows_bytes(), t.version
    bins = plan_optimize(t)
    apply_optimize(t, bins, now=20)
    assert t.rows_bytes() == before_bytes
    assert t.version == v + 1
    assert health(t).file_count < 12


def test_optimize_idempotent():
    t = small_table(12)
    apply_optimize(t, plan_optimize(t), now=20)
    assert plan_optimize(t) == []


def test_where_filter_only_touches_partition():
    t = small_table(4)
    for i in range(4):
        t.add(P2, 10 * MB, now=i)
    bins = plan_optimize(t, where_partitions={P2})
    assert {b.partition for b in bins} == {P2}


def test_vacuum_respects_retention():
    t = small_table(6)
    apply_optimize(t, plan_optimize(t), now=10)
    assert plan_vacuum(t, now=10 + 100) == []          # inside 7 days
    doomed = plan_vacuum(t, now=10 + 168)
    assert len(doomed) == 6
    apply_vacuum(t, doomed)
    assert all(f.active for f in t.files)


def test_vacuum_never_deletes_active_files():
    t = small_table(6)
    assert plan_vacuum(t, now=10_000) == []


def test_unsafe_retention_blocked():
    t = small_table(3)
    with pytest.raises(UnsafeRetention):
        plan_vacuum(t, now=500, retain_hours=1)
    assert plan_vacuum(t, now=500, retain_hours=1, allow_unsafe=True) == []


def test_retention_must_exceed_longest_reader():
    with pytest.raises(UnsafeRetention):
        plan_vacuum(small_table(2), now=500, retain_hours=200, longest_reader_hours=240)


def test_random_tables_preserve_data():
    rng = random.Random(1)
    for _ in range(30):
        t = DeltaTable("t")
        for i in range(rng.randint(1, 60)):
            t.add(rng.choice([P1, P2]), rng.randint(1, 150) * MB, now=i)
        total = t.rows_bytes()
        apply_optimize(t, plan_optimize(t), now=100)
        apply_vacuum(t, plan_vacuum(t, now=100 + 168))
        assert t.rows_bytes() == total


def test_render_sql():
    t = small_table(4)
    sql = render_sql("main.s.p", plan_optimize(t), 168)
    assert "OPTIMIZE main.s.p WHERE trade_date IN ('2026-11-12');" in sql
    assert "VACUUM main.s.p RETAIN 168 HOURS;" in sql
    lc = render_sql("main.s.p", [], 168, cluster_by=["ticker", "trade_date"])
    assert "CLUSTER BY (ticker, trade_date)" in lc
